/**
 * 单位名清洗 —— 全站唯一真源（2026-09-17 立）
 *
 * 为什么要有这个文件：
 *   库内 owner_unit / investor 有大量记录粘连了公告标题尾巴与 HTML 实体，
 *   例如「烟台润城工程项目管理有限公司 公开招标公告」「&nbsp; 徐瑞杰」。
 *   历史上清洗规则存在**两份**且口径不同：
 *     · 展示侧 cleanUnitName()：26 种后缀 + HTML 实体 + 可重复剥 4 次（本文件）
 *     · 查询侧 agentCleanExpr()：13 种后缀 + 只剥 1 次（owners.js 内联）
 *   两者对同一单位给出不同结果 ⇒ 同一家代理机构在不同页面被拆成两个名字，
 *   且最致命的是 13 层 CASE 那条根本剥不干净：
 *     「天津市政府采购中心 公开招标公告」→ 命中 '%招标公告' → 只剩「天津市政府采购中心 公开」。
 *
 * 现在只有一个真源：
 *   · Web 请求侧 import 本文件的 cleanUnitName() 做展示
 *   · 落库侧 tools/refresh_stats.mjs 用**同一个函数**把结果写进
 *     projects.investor_clean / projects.owner_clean 预计算列，
 *     查询期不再做任何字符串清洗（也就能走索引了）
 *
 * ⚠️ 改规则只改这里，改完必须重跑 `node tools/refresh_stats.mjs --full` 全量回填，
 *    否则库内预计算列与新规则不一致，前后端口径又会分裂。
 */

// 公告后缀：从长到短排列，正则 alternation 是「左优先」，
// 所以「公开招标公告」必须排在「招标公告」之前，否则「XX 公开招标公告」
// 会被剥成「XX 公开」而不是「XX」。
export const UNIT_TAIL_RE = /(?:\s*(?:公开招标公告|公开招标|招标公告|中标公告|中标结果公告|成交公告|结果公告|更正公告|变更公告|采购公告|竞争性磋商公告|竞争性谈判公告|竞争性磋商|竞争性谈判|询价公告|比选公告|邀标公告|单一来源公示|需求公示|终止公告|废标公告|流标公告|其他公告|暂停公告|公告|公示))$/;

// HTML 实体还原表（采集源把 &nbsp; 直接写进了字段）
const ENTITIES = [
  [/&nbsp;?/gi, ' '],
  [/&amp;/gi, '&'],
  [/&lt;/gi, '<'],
  [/&gt;/gi, '>'],
  [/&quot;/gi, '"'],
  [/&#39;/g, "'"],
];

/**
 * 清洗单位名。幂等：cleanUnitName(cleanUnitName(x)) === cleanUnitName(x)
 *
 * 两个刻意的设计：
 *   ① 剥完变空 或 剥完短于 4 字 → 停止并保留上一版。
 *      库里存在 investor 整串就是「其他公告」的脏数据（322 行），
 *      若剥成空串会让这个"单位"凭空消失或占满榜单，保留原值更诚实。
 *   ② 最多剥 4 轮。实测存在「XX公司 中标公告 中标公告」这类多层粘连。
 *
 * @param {*} s 原始值
 * @returns {string} 清洗后的单位名（空输入返回空串）
 */
export function cleanUnitName(s) {
  let v = String(s == null ? '' : s);
  for (const [re, to] of ENTITIES) v = v.replace(re, to);
  v = v.replace(/\s+/g, ' ').trim();
  for (let i = 0; i < 4; i++) {
    const nv = v.replace(UNIT_TAIL_RE, '').trim();
    if (!nv || nv === v || nv.length < 4) break;
    v = nv;
  }
  return v;
}

/**
 * 单位名的分组键：清洗后为空则退回原值，两者都空则为 ''。
 * 用于 GROUP BY —— 保证「剥完变空」的脏数据仍能被分组，不会丢统计。
 */
export function unitKey(raw) {
  const c = cleanUnitName(raw);
  if (c) return c;
  const r = String(raw == null ? '' : raw).trim();
  return r;
}

/**
 * 是否像"真单位名"（用于榜单过滤掉明显不是单位的值）。
 * 判定保守：只挡明显不是名字的（过短 / 纯公告词 / 纯符号数字），宁可放过不可错杀。
 */
export function looksLikeUnit(s) {
  const v = cleanUnitName(s);
  if (!v) return false;
  if (v.length < 4) return false;
  // 整串就是公告后缀（清洗前后一样且命中后缀模式）
  if (UNIT_TAIL_RE.test(v)) return false;
  // 纯数字 / 纯符号 / 无中文也无字母
  if (!/[\u4e00-\u9fa5A-Za-z]/.test(v)) return false;
  return true;
}

export default { cleanUnitName, unitKey, looksLikeUnit, UNIT_TAIL_RE };
