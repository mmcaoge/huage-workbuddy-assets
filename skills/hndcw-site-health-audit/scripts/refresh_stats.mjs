#!/usr/bin/env node
/**
 * 预计算刷新器 —— hndcw.com（2026-09-17 立）
 *
 * 解决两类根因（见当日排查报告）：
 *   P0-A/B/C：首页与榜单页的 GROUP BY + ORDER BY c DESC + LIMIT 无法下推，
 *             必须扫全表建临时树排序（首页 2.7s / 榜单 3.1s），
 *             且同步 API 阻塞 Node 单线程 ⇒ 单点慢变成全站排队。
 *   P0-C   ：代理机构名在**查询期**用 13 层 CASE 清洗（每行最多 13 次后缀 LIKE），
 *             既用不上索引，又和展示侧规则口径分裂。
 *
 * 做法：把「清洗」与「聚合」从事务路径搬到离线路径 —— 查询期只读预计算结果。
 *   ① projects.investor_clean / owner_clean 预计算列（清洗规则来自 src/lib/unitName.js 唯一真源）
 *   ② 汇总表 stats_owner / stats_agent / stats_bidder / stats_group / stats_meta
 *   ③ ANALYZE 让优化器知道真实分布
 *
 * 用法：
 *   node tools/refresh_stats.mjs            增量（默认，cron 每日跑）
 *   node tools/refresh_stats.mjs --full     全量重算清洗列（首次 / 改清洗规则后 / 每周一次兜底）
 *   node tools/refresh_stats.mjs --stats-only   只重建汇总表，不碰清洗列
 *
 * ⚠️ 幂等：任何模式重复跑结果一致，可安全重跑。
 * ⚠️ 写事务用 BEGIN IMMEDIATE 分批提交，不长时间占写锁（采集脚本同时在写库）。
 */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getDb } from '../db/db.js';
import { cleanUnitName, unitKey } from '../src/lib/unitName.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const argv = process.argv.slice(2);
const FULL = argv.includes('--full');
const STATS_ONLY = argv.includes('--stats-only');

const t0 = Date.now();
const log = (...a) => console.log(`[${new Date().toISOString()}]`, ...a);
const step = (name) => log(`▸ ${name}`);

function tableExists(db, name) {
  return !!db.prepare("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?").get(name);
}
function columnExists(db, table, col) {
  return db.prepare(`PRAGMA table_info(${table})`).all().some((r) => r.name === col);
}

// ---------------------------------------------------------------- ① schema

function ensureSchema(db) {
  step('建 schema（预计算列 / 索引 / 汇总表）');
  let added = [];
  for (const col of ['investor_clean', 'owner_clean']) {
    if (!columnExists(db, 'projects', col)) {
      db.exec(`ALTER TABLE projects ADD COLUMN ${col} TEXT`);
      added.push(col);
    }
  }
  log(added.length ? `  + 新增列 ${added.join(', ')}` : '  = 预计算列已存在');

  // 索引：画像页按名精确匹配、以及增量回填的 IS NULL 扫描都用它
  db.exec('CREATE INDEX IF NOT EXISTS idx_projects_investor_clean ON projects(investor_clean)');
  db.exec('CREATE INDEX IF NOT EXISTS idx_projects_owner_clean ON projects(owner_clean)');
  // 原值索引：详情页链接由字段原值生成，兜底第一轮按原值精确匹配（原先无索引 ⇒ 全表扫）
  db.exec('CREATE INDEX IF NOT EXISTS idx_projects_investor ON projects(investor)');
  // 🔴 2026-09-17：created_at 此前**无任何索引**，导致「今日新增」（情报库首屏四大数字之一，
  //    每次请求都要现算、且无缓存）只能全表扫 16.9 万行 —— 实测稳定 960~1160ms，
  //    是情报库「点了半天才出来」的直接原因。
  //    原写法 `date(created_at,'+8 hours')=date('now','+8 hours')` 对**列**套了函数，
  //    SQLite 无法用它做范围扫描；改成 `created_at >= 常量` 的形式后，
  //    有了本索引即可直接定位到今日那一段（预计 <5ms），且结果与旧写法完全等价
  //    （已实测两者同为 4330 条）。
  db.exec('CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at)');

  db.exec(`CREATE TABLE IF NOT EXISTS stats_owner (
    nm TEXT PRIMARY KEY, c INTEGER NOT NULL DEFAULT 0, s REAL NOT NULL DEFAULT 0)`);
  db.exec(`CREATE TABLE IF NOT EXISTS stats_agent (
    nm TEXT PRIMARY KEY, c INTEGER NOT NULL DEFAULT 0, s REAL NOT NULL DEFAULT 0)`);
  db.exec(`CREATE TABLE IF NOT EXISTS stats_bidder (
    nm TEXT PRIMARY KEY, c INTEGER NOT NULL DEFAULT 0, s REAL NOT NULL DEFAULT 0)`);
  // 分组汇总（首页 + 情报库共用）：k = stage | province | industry
  // s = 该组预算金额合计（情报库地图需要按金额做视觉映射）
  db.exec(`CREATE TABLE IF NOT EXISTS stats_group (
    k TEXT NOT NULL, nm TEXT NOT NULL DEFAULT '', c INTEGER NOT NULL DEFAULT 0,
    s REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (k, nm))`);
  // 兼容早先建过的无 s 列版本
  if (!columnExists(db, 'stats_group', 's')) {
    db.exec('ALTER TABLE stats_group ADD COLUMN s REAL NOT NULL DEFAULT 0');
    log('  + stats_group 补 s 列');
  }
  db.exec(`CREATE TABLE IF NOT EXISTS stats_meta (k TEXT PRIMARY KEY, v TEXT)`);
  // 榜单是 ORDER BY c DESC LIMIT n ⇒ 必须让它走索引，否则又是"全表扫 + 排序"
  db.exec('CREATE INDEX IF NOT EXISTS idx_stats_owner_c ON stats_owner(c DESC)');
  db.exec('CREATE INDEX IF NOT EXISTS idx_stats_agent_c ON stats_agent(c DESC)');
  db.exec('CREATE INDEX IF NOT EXISTS idx_stats_bidder_c ON stats_bidder(c DESC)');
  db.exec('CREATE INDEX IF NOT EXISTS idx_stats_group_kc ON stats_group(k, c DESC)');
  log('  ✓ 索引与汇总表就绪');
}

// ---------------------------------------------------------------- ② 回填清洗列

/**
 * 逐行调用唯一真源清洗并写回。同步 API + 分批事务。
 * @returns {{investor:number, owner:number}}
 */
function backfillClean(db, col, srcCol) {
  const where = FULL
    ? `${srcCol} IS NOT NULL AND ${srcCol} <> ''`
    : `${col} IS NULL AND ${srcCol} IS NOT NULL AND ${srcCol} <> ''`;

  const total = db.prepare(`SELECT COUNT(*) c FROM projects WHERE ${where}`).get().c;
  if (!total) return 0;
  log(`  ${col} ← ${srcCol}：待处理 ${total.toLocaleString()} 行${FULL ? '（全量）' : '（增量）'}`);

  const rows = db.prepare(`SELECT id, ${srcCol} AS v FROM projects WHERE ${where}`).all();
  const upd = db.prepare(`UPDATE projects SET ${col} = ? WHERE id = ?`);
  const BATCH = 20000;
  let done = 0;
  for (let i = 0; i < rows.length; i += BATCH) {
    const slice = rows.slice(i, i + BATCH);
    db.exec('BEGIN IMMEDIATE');
    try {
      for (const r of slice) upd.run(unitKey(r.v), r.id);
      db.exec('COMMIT');
    } catch (e) {
      db.exec('ROLLBACK');
      throw e;
    }
    done += slice.length;
    log(`    … ${done.toLocaleString()}/${total.toLocaleString()}`);
  }
  return done;
}

// ---------------------------------------------------------------- ③ 汇总表

function rebuildStats(db) {
  step('重建汇总表');
  const jobs = [
    ['stats_owner', () => db.exec(`
      INSERT INTO stats_owner(nm, c, s)
      SELECT owner_clean AS nm, COUNT(*) AS c, COALESCE(SUM(budget_amount), 0) AS s
      FROM projects
      WHERE status = 1
        AND owner_unit IS NOT NULL AND owner_unit <> ''
        AND owner_unit NOT LIKE '%详情见公告正文%'
        AND COALESCE(owner_clean, '') <> ''
      GROUP BY owner_clean`)],
    ['stats_agent', () => db.exec(`
      INSERT INTO stats_agent(nm, c, s)
      SELECT investor_clean AS nm, COUNT(*) AS c, COALESCE(SUM(budget_amount), 0) AS s
      FROM projects
      WHERE status = 1
        AND investor IS NOT NULL AND investor <> ''
        AND COALESCE(investor_clean, '') <> ''
      GROUP BY investor_clean`)],
    ['stats_bidder', () => db.exec(`
      INSERT INTO stats_bidder(nm, c, s)
      SELECT m.winner AS nm, COUNT(*) AS c, COALESCE(SUM(p.budget_amount), 0) AS s
      FROM bid_winner_map m JOIN projects p ON p.id = m.project_id
      WHERE p.status = 1 AND m.winner IS NOT NULL AND m.winner <> ''
      GROUP BY m.winner`)],
    // 四个维度一次性建好：
    //   · 首页用 stage / province
    //   · 情报库（/projects/map）用 province / stage / industry
    //   · 项目列表（/projects/list）的下拉筛选项用 province / industry / stage / sector
    // 原先这些都在路由里现算 —— 情报库 4 条全表 GROUP BY 合计 3.5s；
    // 列表页 4 条 `SELECT DISTINCT` 全表扫描合计约 4s（836/1099/1097/956ms）。
    // 对 node:sqlite 这种**同步 API**，等于每次访问把整个站点冻结好几秒 —— 现在全读这里。
    ['stats_group', () => {
      for (const k of ['stage', 'province', 'industry', 'sector']) {
        db.exec(`INSERT INTO stats_group(k, nm, c, s)
                 SELECT '${k}', COALESCE(${k}, ''), COUNT(*), COALESCE(SUM(budget_amount), 0)
                 FROM projects WHERE status = 1 GROUP BY 2`);
      }
    }],
  ];

  db.exec('BEGIN IMMEDIATE');
  try {
    db.exec('DELETE FROM stats_owner; DELETE FROM stats_agent; DELETE FROM stats_bidder; DELETE FROM stats_group;');
    db.exec('COMMIT');
  } catch (e) { db.exec('ROLLBACK'); throw e; }

  for (const [name, fn] of jobs) {
    const s = Date.now();
    try {
      db.exec('BEGIN IMMEDIATE');
      fn();
      db.exec('COMMIT');
      const n = db.prepare(`SELECT COUNT(*) c FROM ${name}`).get().c;
      log(`  ✓ ${name}: ${n.toLocaleString()} 行 (${Date.now() - s}ms)`);
    } catch (e) {
      db.exec('ROLLBACK');
      log(`  ✗ ${name} 失败: ${e.message}`);
      throw e;
    }
  }
}

function writeMeta(db) {
  step('写入站点统计 meta');
  const one = (sql) => db.prepare(sql).get().c;
  const meta = {
    projects: one('SELECT COUNT(*) c FROM projects WHERE status=1'),
    provinces: one('SELECT COUNT(DISTINCT province) c FROM projects WHERE status=1'),
    supply: one('SELECT COUNT(*) c FROM supply_demand WHERE status=1'),
    disputes: one('SELECT COUNT(*) c FROM project_disputes'),
    users: one('SELECT COUNT(*) c FROM users'),
    refreshed_at: new Date().toISOString(),
    refreshed_ts: String(Date.now()),
    mode: FULL ? 'full' : (STATS_ONLY ? 'stats-only' : 'incremental'),
  };
  // 情报库首屏另外两个数字（企业画像 / 政策红利）。这两张表可能尚未建，
  // 失败时**不写 key**，避免把「表不存在」固化成页面上的 0。
  for (const [k, sql] of [
    ['supplier_count', 'SELECT COUNT(*) c FROM suppliers'],
    ['policy_count', 'SELECT COUNT(*) c FROM policies WHERE status=1'],
  ]) {
    try { meta[k] = one(sql); } catch { /* 表不存在 → 跳过 */ }
  }
  const up = db.prepare('INSERT INTO stats_meta(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v');
  db.exec('BEGIN IMMEDIATE');
  try {
    for (const [k, v] of Object.entries(meta)) up.run(k, String(v));
    db.exec('COMMIT');
  } catch (e) { db.exec('ROLLBACK'); throw e; }
  log('  ✓', JSON.stringify({ projects: meta.projects, provinces: meta.provinces }));
}

// ---------------------------------------------------------------- main

function main() {
  const db = getDb();
  log(`refresh_stats 启动  mode=${FULL ? 'full' : (STATS_ONLY ? 'stats-only' : 'incremental')}  db=${path.join(ROOT, 'data', 'hndcw.db')}`);

  ensureSchema(db);

  if (!STATS_ONLY) {
    step('回填清洗列（唯一真源：src/lib/unitName.js）');
    const a = backfillClean(db, 'investor_clean', 'investor');
    const b = backfillClean(db, 'owner_clean', 'owner_unit');
    log(`  ✓ 本轮清洗 investor ${a.toLocaleString()} 行 / owner_unit ${b.toLocaleString()} 行`);
    const left = db.prepare(`SELECT
        (SELECT COUNT(*) FROM projects WHERE investor IS NOT NULL AND investor <> '' AND investor_clean IS NULL) AS ai,
        (SELECT COUNT(*) FROM projects WHERE owner_unit IS NOT NULL AND owner_unit <> '' AND owner_clean IS NULL) AS ao`).get();
    log(`  剩余未清洗：investor ${left.ai} / owner_unit ${left.ao}${left.ai + left.ao === 0 ? '  ✓ 已全量覆盖' : '  ⚠ 仍有残留'}`);
  }

  rebuildStats(db);
  writeMeta(db);

  step('ANALYZE（让查询优化器知道真实分布）');
  db.exec('ANALYZE');
  log('  ✓ ANALYZE 完成');

  log(`全部完成，用时 ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}

main();
