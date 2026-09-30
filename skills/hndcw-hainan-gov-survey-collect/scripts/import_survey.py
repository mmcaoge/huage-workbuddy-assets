# -*- coding: utf-8 -*-
"""
把 filtered.jsonl（海南政府网站群·社会调查类项目）导入 hndcw.com projects 表

字段映射（对齐 collect_province.py 口径）：
  province='海南省'  industry='服务'  sector='社会调查'（新增二级标签）
  dm_code = DM-琼-{年}-{6位流水}（续现网最大序号，年取采集年）
  stage   = 沿用 TYPE_PATTERNS 取值：招标公告/竞争性磋商/询价/单一来源/中标成交/更正/终止/其他
  source_name = 发布站点（如「儋州市人民政府网」）

安全：
  - 先自动备份 data/hndcw.db → data/_bak_survey_YYYYMMDD/
  - 以 source_url 幂等去重，可重复执行
  - --dry-run 只统计不落库

用法：
  python3 tools/import_survey.py --dry-run
  python3 tools/import_survey.py
"""
import os, re, sys, json, sqlite3, shutil, time

DB = os.environ.get('DB_PATH', '/www/wwwroot/hndcw.com/data/hndcw.db')
SRC = os.environ.get('SRC', '/www/wwwroot/hndcw.com/data/survey_gov_filtered.jsonl')
DRY = '--dry-run' in sys.argv
# 周采集用：整库备份 600MB+，每周一次不可持续（回滚可按 dm_code 范围）
NOBAK = '--no-backup' in sys.argv

CITY_FULL = {
    '海口': '海口市', '三亚': '三亚市', '三沙': '三沙市', '儋州': '儋州市',
    '五指山': '五指山市', '琼海': '琼海市', '文昌': '文昌市', '万宁': '万宁市',
    '东方': '东方市', '定安': '定安县', '屯昌': '屯昌县', '澄迈': '澄迈县',
    '临高': '临高县', '白沙': '白沙黎族自治县', '昌江': '昌江黎族自治县',
    '乐东': '乐东黎族自治县', '陵水': '陵水黎族自治县',
    # ⚠️ 对齐现网 projects.city 既有写法（2026-09-17 实测：现网用简写，
    #    去掉了「苗族」——「保亭黎族自治县」「琼中黎族自治县」，勿写官方全称，
    #    否则同一县会出现两种写法，前台筛选/统计分裂）
    '保亭': '保亭黎族自治县', '琼中': '琼中黎族自治县',
}

STAGE_RULES = [
    (r'终止|废标|流标', '终止'),
    (r'更正|变更|补充公告|澄清', '更正'),
    (r'中标|成交|中选|结果(公告|公示)|入选|比选结果|遴选结果', '中标成交'),
    (r'询价', '询价'),
    (r'竞争性磋商|磋商', '竞争性磋商'),
    (r'竞争性谈判', '竞争性谈判'),
    (r'单一来源', '单一来源'),
    (r'招标公告|采购公告|比选公告|遴选公告|选聘|选取|征集|邀请|公开选取|选聘公告|公告', '招标公告'),
]


def blob_of(r):
    """site + groupname 一起参与城市识别（groupname = 采集器写入的所属市县）。"""
    return '%s %s' % (r.get('site') or '', r.get('groupname') or '')


def city_of(title, site):
    blob = (title or '') + ' ' + (site or '')
    for k, v in CITY_FULL.items():
        if k in blob:
            return v
    return ''


def owner_of(title, site):
    """从标题抽取采购单位：取「关于」之前的机构名（含「局/厅/委/办/中心/联合会/学校/院/站/公司/政府」）。"""
    t = (title or '').strip()
    m = re.match(r'^(.{4,30}?(?:厅|局|委|办|中心|联合会|协会|学校|学院|医院|研究院|站|所|政府|管委会|管理局))\s*(?:关于|关)', t)
    if m:
        return m.group(1)
    m = re.match(r'^(.{4,30}?(?:厅|局|委|办|中心|联合会|协会|学校|学院|医院|研究院|站|所|政府|管委会|管理局))', t)
    if m:
        return m.group(1)
    # 兜底：站点名（去掉「政府网/人民政府网站」等）
    return re.sub(r'(政府网|人民政府网|人民政府网站|政府门户网站|人民政府)$', '', site or '')


def stage_of(title):
    for pat, st in STAGE_RULES:
        if re.search(pat, title or ''):
            return st
    return '其他'


def summary_of(rec):
    return ('%s于%s发布《%s》，属%s阶段的社会调查服务类采购项目（地区：%s）。'
            % (rec.get('site') or '海南省政府网站', rec.get('pub_date') or '近期',
               (rec.get('title') or '').strip(), stage_of(rec.get('title')),
               city_of(rec.get('title'), blob_of(rec)) or '海南省'))


def main():
    rows = []
    with open(SRC, encoding='utf-8') as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    print('待导入 %d 条（来源 %s）' % (len(rows), SRC))
    if not rows:
        print('无数据，退出'); return

    con = sqlite3.connect(DB, timeout=30)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA busy_timeout=30000')
    cur = con.cursor()

    exist = set(r[0] for r in cur.execute(
        'SELECT source_url FROM projects WHERE source_url IS NOT NULL').fetchall())
    todo = [r for r in rows if r.get('url') and r['url'] not in exist]
    print('已在库 %d 条，本次新增 %d 条' % (len(rows) - len(todo), len(todo)))

    # 续 dm_code 序号
    seq = cur.execute(
        "SELECT COALESCE(MAX(CAST(substr(dm_code,11) AS INTEGER)),0) FROM projects "
        "WHERE dm_code LIKE 'DM-琼-%'").fetchone()[0]
    year = time.strftime('%Y')
    print('现网 DM-琼 最大序号 %d，本次从 %d 起编号' % (seq, seq + 1))

    st_cnt = {}
    city_cnt = {}
    for r in todo:
        st = stage_of(r.get('title'))
        st_cnt[st] = st_cnt.get(st, 0) + 1
        c = city_of(r.get('title'), blob_of(r))
        city_cnt[c or '(省级/未识别)'] = city_cnt.get(c or '(省级/未识别)', 0) + 1

    print('\n=== 阶段分布 ===')
    for k, v in sorted(st_cnt.items(), key=lambda x: -x[1]):
        print('   %-10s %d' % (k, v))
    print('=== 地区分布 ===')
    for k, v in sorted(city_cnt.items(), key=lambda x: -x[1]):
        print('   %-14s %d' % (k, v))

    if DRY:
        print('\n[dry-run] 未写库。样例：')
        for r in todo[:10]:
            seq += 1
            print('   DM-琼-%s-%06d | %s | %s | %s' % (year, seq, r.get('pub_date'),
                  city_of(r.get('title'), blob_of(r)) or '-', (r.get('title') or '')[:44]))
        con.close(); return

    # 备份（--no-backup 时跳过：周采集增量通常仅数十条，整库 600MB+ 备份不划算；
    # 回滚依据：本次写入的 dm_code 区间 + 过滤产物 JSONL 存档）
    if NOBAK:
        print('\n[--no-backup] 跳过整库备份；本次 dm_code 自 DM-琼-%s-%06d 起' % (year, seq + 1))
    else:
        bakdir = '/www/wwwroot/hndcw.com/data/_bak_survey_%s' % time.strftime('%Y%m%d_%H%M')
        os.makedirs(bakdir, exist_ok=True)
        shutil.copy2(DB, os.path.join(bakdir, 'hndcw.db'))
        print('\n已备份 → %s' % bakdir)

    ins = 0
    for r in todo:
        seq += 1
        city = city_of(r.get('title'), blob_of(r)) or None
        try:
            cur.execute(
                """INSERT INTO projects
                   (dm_code, title, province, city, industry, sector, owner_unit,
                    stage, publish_date, source_name, source_url, summary, raw_content,
                    status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1,datetime('now'),datetime('now'))""",
                ('DM-琼-%s-%06d' % (year, seq),
                 (r.get('title') or '').strip(),
                 '海南省', city, '服务', '社会调查',
                 owner_of(r.get('title'), r.get('site')),
                 stage_of(r.get('title')), r.get('pub_date') or None,
                 r.get('site') or '海南省政府网站', r.get('url'),
                 summary_of(r), r.get('content') or ''))
            ins += 1
        except sqlite3.IntegrityError as e:
            print('  [跳过] %s -> %s' % ((r.get('title') or '')[:40], e))
    con.commit()
    con.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    total = cur.execute("SELECT count(*) FROM projects WHERE sector='社会调查'").fetchone()[0]
    con.close()
    print('\n导入完成：新增 %d 条，库内 sector=社会调查 共 %d 条' % (ins, total))


if __name__ == '__main__':
    main()
