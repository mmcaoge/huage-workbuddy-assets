# -*- coding: utf-8 -*-
"""
可投标池正文补全（enrich_biddable）
背景：monitor_tenders_daily.py 只做「标题级」采集（content 字段=搜索接口摘要，约 175 字节），
      导致 biddable=1 池 1017 条 budget_amount=0 / key_dates=0 / raw_content 空，
      详情页「预算金额/投资额/投标截止/采购人/代理机构/联系方式」全部显示「—（以官方公告为准）」。

本脚本：按 source_url 抓公告正文 → 结构化抽取 → 回写 projects 表 → 打 body_fetched_at 水位。
幂等可重复跑；水位必打（即使未抽到字段，也标记已抓，避免下轮重抓）。

环境变量：
  DRY=1        只抓取与打印，不写库
  LIMIT=N      只处理 N 条（试点用）
  WORKERS=N    并发数，默认 6
  ORDER=recent 优先近 90 天（默认按 publish_date DESC）
"""
import os
import re
import sys
import json
import time
import sqlite3
import threading
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    requests.packages.urllib3.disable_warnings()
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'data', 'hndcw.db')

DRY = os.environ.get('DRY') == '1'
LIMIT = int(os.environ.get('LIMIT') or 0)
WORKERS = int(os.environ.get('WORKERS') or 6)

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
HEADERS = {
    'User-Agent': UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

_lock = threading.Lock()
_stat = {'fetch_ok': 0, 'fetch_fail': 0, 'hit': {}}


# ---------------------------------------------------------------- 抓取
def fetch(url, timeout=18):
    if not url or not url.startswith('http'):
        return None
    for i in range(2):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
            if r.status_code != 200:
                time.sleep(0.6)
                continue
            r.encoding = r.apparent_encoding or r.encoding or 'utf-8'
            return r.text
        except Exception:
            time.sleep(0.6 * (i + 1))
    return None


CONTENT_SELECTORS = [
    'div.TRS_Editor', 'div#zoom', 'div.zoom', 'div#js_content', 'div.rich_media_content',
    'div.article-content', 'div.article_content', 'div.artical', 'div.news_content',
    'div.detail-content', 'div.detail_content', 'div.content', 'div#content', 'div.con',
    'div.view', 'div.wzcon', 'div.xxgk-content', 'div#mainText', 'div.main-content',
]


def html_to_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script', 'style', 'noscript', 'iframe']):
        t.decompose()
    node = None
    best = 0
    for sel in CONTENT_SELECTORS:
        for cand in soup.select(sel):
            n = len(cand.get_text(strip=True))
            if n > max(150, best):
                node, best = cand, n
    if node is None:
        node = soup.body or soup
    text = node.get_text('\n', strip=True)
    text = text.replace('\u3000', ' ').replace('\xa0', ' ')
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()


# ---------------------------------------------------------------- 抽取
RE_BUDGET = [
    # 单位在数字后：预算金额：131.64万元
    r'(?:采购)?预算(?:金额|价|总金额|总额|价款|控制价)?\s*[:：]?\s*(?:人民币|￥|¥)?\s*([0-9][0-9,，]*\.?[0-9]*)\s*(万元|元)',
    r'最高限价\s*[:：]?\s*(?:人民币|￥|¥)?\s*([0-9][0-9,，]*\.?[0-9]*)\s*(万元|元)',
    r'(?:项目|采购|服务)(?:预算|投资)(?:金额|总额)?\s*[:：]?\s*(?:人民币|￥|¥)?\s*([0-9][0-9,，]*\.?[0-9]*)\s*(万元|元)',
    r'(?:招标|采购)控制价\s*[:：]?\s*(?:人民币|￥|¥)?\s*([0-9][0-9,，]*\.?[0-9]*)\s*(万元|元)',
]
# 单位在括号内前置：预算金额（万元）：131.64
RE_BUDGET_PRE = [
    r'(?:采购)?预算(?:金额|价|总金额|总额)?\s*[（(\[]\s*(万元|元)\s*[)）\]]\s*[:：]?\s*([0-9][0-9,，]*\.?[0-9]*)',
    r'最高限价\s*[（(\[]\s*(万元|元)\s*[)）\]]\s*[:：]?\s*([0-9][0-9,，]*\.?[0-9]*)',
]
RE_DEADLINE = [
    r'(?:响应文件|投标文件|报价文件|磋商文件|申请文件)(?:的)?(?:递交|提交|送达|接收)?(?:截止时间|截止日期|递交截止时间)\s*[:：]?\s*([0-9]{4}\s*[年\-/.]\s*[0-9]{1,2}\s*[月\-/.]\s*[0-9]{1,2}[^，。；;\n]{0,16})',
    r'(?:投标|响应|报价|报名)\s*(?:文件)?\s*(?:递交|提交)?\s*截止\s*(?:时间|日期)\s*[:：]?\s*([0-9]{4}\s*[年\-/.]\s*[0-9]{1,2}\s*[月\-/.]\s*[0-9]{1,2}[^，。；;\n]{0,16})',
    r'截止时间\s*[:：]\s*([0-9]{4}\s*[年\-/.]\s*[0-9]{1,2}\s*[月\-/.]\s*[0-9]{1,2}[^，。；;\n]{0,16})',
]
RE_OPEN = [
    r'开标时间\s*[:：]?\s*([0-9]{4}\s*[年\-/.]\s*[0-9]{1,2}\s*[月\-/.]\s*[0-9]{1,2}[^，。；;\n]{0,16})',
    r'(?:磋商|谈判|评审|比选)时间\s*[:：]?\s*([0-9]{4}\s*[年\-/.]\s*[0-9]{1,2}\s*[月\-/.]\s*[0-9]{1,2}[^，。；;\n]{0,16})',
]
RE_GETFILE = [
    r'(?:获取|领取|下载|获取招标|领取招标)(?:采购|招标|磋商)?文件(?:时间|期限)?\s*[:：]?\s*([0-9]{4}\s*[年\-/.]\s*[0-9]{1,2}\s*[月\-/.]\s*[0-9]{1,2}[^，。；;\n]{0,20})',
]
RE_SIGNUP = [
    r'报名(?:时间|期限)\s*[:：]?\s*([0-9]{4}\s*[年\-/.]\s*[0-9]{1,2}\s*[月\-/.]\s*[0-9]{1,2}[^，。；;\n]{0,20})',
]
RE_OWNER = [
    r'(?:采购人|招标人|采购单位|招标单位|采购方|建设单位|实施单位|委托单位)(?:信息|基本|概况|名称)?\s*(?:名\s*称|单位名称|全称)?\s*[:：]?\s*([^\s，,。；;、\|]{4,40})',
]
RE_AGENT = [
    r'(?:采购)?(?:代理机构|招标代理|代理单位)(?:信息|名称)?\s*(?:名\s*称|单位名称)?\s*[:：]?\s*([^\s，,。；;、\|]{4,40})',
]
# 「以上合计人民币…（¥9,240）」类：小标常以合计金额为最高限价
RE_BUDGET_ALT = [
    r'(?:合计|共计|总计|最高限价|限价|预算|控制价)[^。；\n]{0,40}?[¥￥]\s*([0-9][0-9,，]*\.?[0-9]*)',
    r'[¥￥]\s*([0-9][0-9,，]*\.?[0-9]*)\s*(?:元)?(?:整)?[^。；\n]{0,10}?(?:为|即)?(?:最高限价|采购预算|预算金额)',
]
RE_CODE = [
    r'项目编号\s*[:：]\s*([A-Za-z0-9\-_（）()\[\]]{4,50})',
    r'(?:招标|采购|磋商)编号\s*[:：]\s*([A-Za-z0-9\-_（）()\[\]]{4,50})',
    r'采购计划编号\s*[:：]\s*([A-Za-z0-9\-_（）()\[\]]{4,50})',
]
RE_CONTACT = [
    r'项目?联系人\s*(?:姓名)?\s*[:：]\s*([^\s，,。；;\n\|]{2,20})',
    r'联系人\s*[:：]\s*([^\s，,。；;\n\|]{2,20})',
]
RE_PHONE = [
    r'(?:联系)?(?:电话|方式|手机)\s*(?:号码)?\s*[:：]\s*(0\d{2,3}[-\s]?\d{7,8}(?:\s*转\s*\d+)?|1[3-9]\d{9})',
    r'(?:联系)?(?:电话|方式|手机)\s*(?:号码)?\s*[:：]\s*([^\s，,。；;\n\|]{7,25})',
]
RE_QUAL = [
    r'(?:投标|供应商|申请人|响应)(?:人)?(?:资格|资质)(?:要求|条件)\s*[:：]?\s*([\s\S]{20,900}?)(?=\n\s*(?:[一二三四五六七八九十]+[、.]|\d+[、.])|获取|报名|递交|开标|$)',
    r'资格要求\s*[:：]?\s*([\s\S]{20,900}?)(?=\n\s*(?:[一二三四五六七八九十]+[、.]|\d+[、.])|获取|报名|递交|开标|$)',
]
RE_ADDR = [
    r'(?:地\s*址|联系地址)\s*[:：]\s*([^\n，。；;]{6,60})',
]

BAD_OWNER = re.compile(r'^(?:详见|见|略|无|待定|另行|以.*为准|招标文件|采购文件)')
SITE_NAME = re.compile(r'(政府网|门户网站|人民政府网|政务网|信息网|公众信息网|省政府|市政府|县政府|厅$|局$|委员会$)')

# 机构名识别：政府公告里「采购单位」常无冒号直接跟值（如「一、采购单位\n白沙黎族自治县残疾人联合会」），
# 且大量公告的采购人只出现在标题中，故需机构名白名单式校验 + 标题推断兜底。
AGENCY_TAIL = (r'(?:管理局|管理站|管理所|管委会|办事处|办公室|工作室|联合会|协会|学会|商会|基金会|'
               r'委员会|工会|妇联|残联|团委|党委|党组|总站|分站|服务站|中心|集团|公司|医院|'
               r'学校|学院|大学|研究院|研究所|设计院|检察院|法院|监狱|戒毒所|图书馆|博物馆|'
               r'体育馆|纪念馆|电视台|广播电台|广播台|银行|支行|政府|'
               r'局|厅|委|院|站|所|处|署)')
BAD_AGENCY_HEAD = re.compile(
    r'^(?:关于|公告|通知|项目|本次|以上|本|现|方式|内容|要求|条件|时间|地点|预算|金额|数量|说明|'
    r'范围|信息|名称|地址|电话|人|方|需|应当|须|将|拟|可|在|为|是|及|与|和|见|详见|无|略|待)')
BAD_AGENCY_TAIL_WORD = re.compile(r'(网站|网页|平台|家园|公园|宾馆|酒店)$')
AGENCY_TAIL_RE = re.compile(AGENCY_TAIL + r'$')


def is_agency(v):
    if not v:
        return False
    v = v.strip().strip('：:（()）【】')
    if not (4 <= len(v) <= 40):
        return False
    if BAD_AGENCY_HEAD.match(v):
        return False
    if BAD_AGENCY_TAIL_WORD.search(v):
        return False
    if re.search(r'[0-9]', v):
        return False
    if re.search(r'(公告|通知|文件|我方|贵方|贵单位|贵司|本项目)', v):
        return False
    return bool(AGENCY_TAIL_RE.search(v))


def agency_from_title(title):
    """从标题推断采购人：优先「XX局关于……」的「关于」之前片段，其次首个机构名。"""
    if not title:
        return ''
    t = re.sub(r'\s+', '', title)
    m = re.match(r'^(.{4,40}?)(?:关于|就|拟|现|将|公开|组织|开展|举办|采购|实施)', t)
    if m and is_agency(m.group(1)):
        return m.group(1)
    for m2 in re.finditer(r'([\u4e00-\u9fa5]{2,25}' + AGENCY_TAIL + r')', t):
        if is_agency(m2.group(1)):
            return m2.group(1)
    return ''


def norm_date(s):
    if not s:
        return ''
    s = s.strip().replace('：', ':')
    m = re.search(r'(\d{4})\s*[年\-/.]\s*(\d{1,2})\s*[月\-/.]\s*(\d{1,2})', s)
    if not m:
        return s[:32]
    y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
    out = '%s-%02d-%02d' % (y, mo, d)
    tail = s[m.end():]
    hm = re.search(r'(\d{1,2})\s*[时:点]\s*(\d{1,2})?\s*分?', tail) or re.search(r'(\d{1,2}):(\d{2})', tail)
    if hm:
        hh = int(hm.group(1))
        mm = int(hm.group(2) or 0)
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            out += ' %02d:%02d' % (hh, mm)
    return out


def to_wan(num, unit):
    """⚠️ 库内 projects.budget_amount 单位为「万元」（见 src/util/format.js 注释），
    故此处统一换算为万元；写成「元」会让详情页把 5 万元显示成 5 亿元。"""
    try:
        v = float(num.replace(',', '').replace('，', ''))
    except Exception:
        return None
    wan = v if unit == '万元' else v / 10000.0
    if 0.001 <= wan <= 200000:
        return round(wan, 4)
    return None


def first_match(pats, text, norm=None):
    for p in pats:
        m = re.search(p, text)
        if m:
            v = m.group(1).strip()
            if norm:
                v = norm(v)
            if v:
                return v
    return ''


def first_agency(pats, text):
    """标签命中后逐个用 is_agency 校验，取第一个真正像机构名的值。"""
    for p in pats:
        for m in re.finditer(p, text):
            v = m.group(1)
            if is_agency(v):
                return v.strip().strip('：:')
    return ''


def extract(text, title):
    d = {}
    head = text[:8000]
    # 政府公告大量采用「表格 / 标签换行」结构（如 采购人信息\n名 称：XX局），
    # 故除多行原文外，另构造单行压平文本用于标签-取值匹配。
    flat = re.sub(r'\s+', ' ', head)

    for p in RE_BUDGET:
        m = re.search(p, flat)
        if m:
            v = to_wan(m.group(1), m.group(2))
            if v:
                d['budget_amount'] = v
                break
    if 'budget_amount' not in d:
        for p in RE_BUDGET_PRE:
            m = re.search(p, flat)
            if m:
                v = to_wan(m.group(2), m.group(1))
                if v:
                    d['budget_amount'] = v
                    break

    if 'budget_amount' not in d:
        for p in RE_BUDGET_ALT:
            m = re.search(p, flat)
            if m:
                v = to_wan(m.group(1), '元')
                if v:
                    d['budget_amount'] = v
                    break

    kd = {}
    v = first_match(RE_GETFILE, flat, norm_date)
    if v:
        kd['get_file'] = v
    v = first_match(RE_DEADLINE, flat, norm_date)
    if v:
        kd['bid_deadline'] = v
    v = first_match(RE_OPEN, flat, norm_date)
    if v:
        kd['open_time'] = v
    v = first_match(RE_SIGNUP, flat, norm_date)
    if v:
        kd['signup_deadline'] = v
    if kd:
        d['key_dates'] = kd

    v = first_agency(RE_OWNER, flat) or agency_from_title(title)
    if v:
        d['owner_unit'] = v
    v = first_agency(RE_AGENT, flat)
    if v:
        d['investor'] = v
    v = first_match(RE_CODE, flat)
    if v:
        d['project_code'] = v
    v = first_match(RE_CONTACT, flat)
    if v and not BAD_OWNER.match(v):
        d['contact_name'] = v
    v = first_match(RE_PHONE, flat)
    if v:
        d['contact_phone'] = v
    v = first_match(RE_QUAL, head) or first_match(RE_QUAL, flat)
    if v:
        v = re.sub(r'\s*\n\s*', ' ', v).strip()
        d['qualification'] = v[:800]
    v = first_match(RE_ADDR, head) or first_match(RE_ADDR, flat)
    if v:
        d['owner_address'] = v
    return d


# ---------------------------------------------------------------- 主流程
def load_targets():
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute('PRAGMA busy_timeout=60000')
    sql = ("SELECT id,dm_code,title,source_url,source_name,owner_unit,budget_amount,key_dates "
           "FROM projects WHERE biddable=1 "
           "AND (body_fetched_at IS NULL OR body_fetched_at='') "
           "AND source_url LIKE 'http%' "
           "ORDER BY publish_date DESC")
    if LIMIT:
        sql += ' LIMIT %d' % LIMIT
    rows = conn.execute(sql).fetchall()
    conn.close()
    return rows


def work(row):
    _id, dm, title, url, sname, owner, budget, kd = row
    html = fetch(url)
    if not html:
        with _lock:
            _stat['fetch_fail'] += 1
        return (_id, None, None)
    text = html_to_text(html)
    if len(text) < 60:
        with _lock:
            _stat['fetch_fail'] += 1
        return (_id, None, None)
    with _lock:
        _stat['fetch_ok'] += 1
    ex = extract(text, title)
    ex['_raw'] = text[:20000]
    ex['_summary'] = re.sub(r'\s+', ' ', text)[:220]
    ex['_title'] = title
    ex['_sname'] = sname
    return (_id, ex, text)


def build_update(row, ex):
    _id, dm, title, url, sname, owner, budget, kd = row
    sets, vals = [], []
    # 业主单位：原值若为站点名则允许覆盖为真实采购人
    new_owner = ex.get('owner_unit')
    if new_owner:
        cur_owner = (owner or '').strip()
        # 占位值（站点名 / 纯市县名 / 空）允许被真实采购人覆盖
        is_site = ((not cur_owner) or cur_owner == (sname or '')
                   or bool(SITE_NAME.search(cur_owner))
                   or (len(cur_owner) <= 5 and not AGENCY_TAIL_RE.search(cur_owner)))
        if is_site and new_owner != cur_owner:
            sets.append('owner_unit=?')
            vals.append(new_owner)
    if ex.get('investor'):
        sets.append('investor=?')
        vals.append(ex['investor'])
    if ex.get('budget_amount') and not (budget or 0):
        sets.append('budget_amount=?')
        vals.append(ex['budget_amount'])
    if ex.get('key_dates'):
        cur = {}
        try:
            cur = json.loads(kd) if kd else {}
        except Exception:
            cur = {}
        if not isinstance(cur, dict):
            cur = {}
        merged = dict(cur)
        for k, v in ex['key_dates'].items():
            merged.setdefault(k, v)
        if merged != cur:
            sets.append('key_dates=?')
            vals.append(json.dumps(merged, ensure_ascii=False))
    for col in ('project_code', 'contact_name', 'contact_phone', 'qualification', 'owner_address'):
        if ex.get(col):
            sets.append(col + '=?')
            vals.append(ex[col])
    sets.append('raw_content=?')
    vals.append(ex['_raw'])
    if ex.get('_summary'):
        sets.append("summary=CASE WHEN summary IS NULL OR summary='' THEN ? ELSE summary END")
        vals.append(ex['_summary'])
    sets.append("body_fetched_at=datetime('now')")
    sets.append("updated_at=datetime('now')")
    vals.append(_id)
    return 'UPDATE projects SET ' + ','.join(sets) + ' WHERE id=?', vals


def main():
    rows = load_targets()
    print('[enrich] 待补全 %d 条（biddable=1 且无正文水位），并发 %d，DRY=%s' % (len(rows), WORKERS, DRY))
    if not rows:
        return
    t0 = time.time()
    conn = None
    if not DRY:
        conn = sqlite3.connect(DB, timeout=60)
        conn.isolation_level = None
        conn.execute('PRAGMA busy_timeout=60000')

    done = written = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex_pool:
        fut = {ex_pool.submit(work, r): r for r in rows}
        for f in as_completed(fut):
            row = fut[f]
            try:
                _id, ex, text = f.result()
            except Exception as e:
                print('[err]', str(e)[:100])
                continue
            done += 1
            if ex is None:
                if not DRY and conn:
                    # 抓取失败也打水位（避免反复重试同一批死链）
                    try:
                        conn.execute('BEGIN')
                        conn.execute("UPDATE projects SET body_fetched_at=datetime('now') WHERE id=?", (_id,))
                        conn.execute('COMMIT')
                    except Exception:
                        try:
                            conn.execute('ROLLBACK')
                        except Exception:
                            pass
                continue
            for k in ('budget_amount', 'key_dates', 'owner_unit', 'investor', 'project_code',
                      'contact_name', 'contact_phone', 'qualification', 'owner_address'):
                if ex.get(k):
                    _stat['hit'][k] = _stat['hit'].get(k, 0) + 1
            if DRY:
                print('--- [%s] %s' % (row[1], row[2][:46]))
                print('    抽取:', json.dumps({k: v for k, v in ex.items() if not k.startswith('_') and v},
                                              ensure_ascii=False)[:400])
                continue
            sql, vals = build_update(row, ex)
            for t in range(5):
                try:
                    conn.execute('BEGIN')
                    conn.execute(sql, vals)
                    conn.execute('COMMIT')
                    written += 1
                    break
                except Exception as e:
                    try:
                        conn.execute('ROLLBACK')
                    except Exception:
                        pass
                    if 'locked' in str(e).lower() and t < 4:
                        time.sleep(1 + t)
                        continue
                    print('[db] 写失败(跳过):', str(e)[:100], row[2][:30])
                    break
            if done % 50 == 0:
                print('[enrich] 进度 %d/%d（写库 %d，耗时 %.0fs）' % (done, len(rows), written, time.time() - t0))

    if conn:
        conn.close()
    print('[enrich] 完成：处理 %d 条，抓取成功 %d，失败 %d，写库 %d，耗时 %.0fs'
          % (done, _stat['fetch_ok'], _stat['fetch_fail'], written, time.time() - t0))
    print('[enrich] 字段命中数:', json.dumps(_stat['hit'], ensure_ascii=False))


if __name__ == '__main__':
    main()
