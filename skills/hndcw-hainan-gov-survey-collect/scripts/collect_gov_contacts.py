# -*- coding: utf-8 -*-
"""
政府网站群公告 · 联系方式补全（collect_gov_contacts.py）

【为什么需要这个脚本】
collect_details.py / collect_details_p0.py / enrich_detail.py 三个补全脚本的取数 SQL
全部硬编码了 `source_url LIKE '%ccgp.gov.cn%'`（或 source_name='中国政府采购网'），
所以**政府网站群来源的记录（hainan.gov.cn 等）从建库起就不在任何补全任务的范围内**，
owner_contact / agent_contact / contact_name / contact_phone / owner_address / agent_address
永远为空 ⇒ 前端 hasContact=false ⇒ 档案页显示「原公告未公开详细联系方式」。

实测（2026-09-17 抽样 40 条 hainan.gov.cn 社会调查公告）：
  35% 正文含真实项目联系电话（如「受理单位：海南省监狱管理局 该项目采购小组 联系电话：0898-65785545」）
  55% 只有网站页脚的举报电话（必须剔除，否则会写成假联系方式）
  10% 抓取失败

【铁律】
1. **先切页脚再提取**。政府站页脚含「网站违法和不良信息举报电话」「政府综合服务热线」
   「开发维护：海南信息岛技术服务中心 联系电话：0898-12315」等，不切掉必然误存。
2. **宁缺勿滥**。拿不准就留空 —— 假联系方式比没有联系方式更糟。
3. 举报/投诉/纪检/信访 类电话**一律不当作项目联系方式**（监督电话默认不收）。
4. 只填空字段，绝不覆盖已有值。

用法：
    python3 collect_gov_contacts.py                 # 全量（受 LIMIT 限制）
    LIMIT=15 DRY=1 python3 collect_gov_contacts.py  # 小批预演，只打印不写库
    SLEEP=1.5 LIMIT=200 python3 collect_gov_contacts.py
环境变量：LIMIT / SLEEP / DRY / MIN_TITLE_YEAR / DB
"""
import os
import re
import sys
import time
import ssl
import json
import sqlite3
import html as H
import urllib.request
import urllib.error

DB = os.environ.get('DB', '/www/wwwroot/hndcw.com/data/hndcw.db')
LIMIT = int(os.environ.get('LIMIT', '0') or 0)
SLEEP = float(os.environ.get('SLEEP', '1.5'))
DRY = os.environ.get('DRY', '') not in ('', '0')
TIMEOUT = int(os.environ.get('TIMEOUT', '25'))
RETRY = int(os.environ.get('RETRY', '2'))

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0 Safari/537.36')

# ---------------------------------------------------------------- 页脚截断
# 强标记：几乎绝不出现在正文里，命中即从这里截断
FOOTER_STRONG = [
    '违法和不良信息举报', '举报邮箱', '政府网站标识码', '网站标识码',
    '政府综合服务热线', '公安备案号', '公网安备', 'ICP备', '网站地图',
    '开发维护：', '开发维护:', '联系地址：海南省海口',
]
# 弱标记：可能出现在正文，仅在没有强标记时兜底
FOOTER_WEAK = ['主办单位：', '技术支持：', '版权所有', '站点地图', '琼公网安备']

# 绝不可当作项目联系方式的上下文
REJECT_CTX = re.compile(
    r'(举报|投诉|信访|纪检|监委|监督电话|消费者|12315|12345|'
    r'不良信息|违法和|扫黄打非|舆情|辟谣)')

CONTACT_KW = re.compile(
    r'(联系人|项目联系人|采购人联系人|咨询联系人|报名联系人|'
    r'联系电话|咨询电话|联系方式|联系号码|报名电话|电话)')

NAME_P = re.compile(r'(?:联系人|咨询联系人|采购人联系人|报名联系人)[：:\s]*'
                    r'([\u4e00-\u9fa5·]{2,6})')
# 姓名黑名单：这些是模板占位/泛指词，不是人名
# ⚠️ 「及地址」「或个人签字」都是实测漏进来的 —— 来自「联系人及地址」「联系人或个人签字」上下文
NAME_BAD = re.compile(r'(姓名|手机号|电话|联系|方式|公告|详见|如下|单位|部门|本人|他人|'
                      r'申请人|异议|以上|相关|有关|该项|项目|负责人|经办人|工作人|'
                      r'及地址|及电话|或个人|签字|地址|及|个人)')
TEL_P = re.compile(r'(?:联系电话|咨询电话|联系号码|报名电话|电话号码|电话)'
                   r'[：:\s]*((?:0898|0\d{2,3})[-\s]?\d{7,8}|1[3-9]\d{9})')
TEL_ANY = re.compile(r'((?:0898|0\d{2,3})[-\s]?\d{7,8}|1[3-9]\d{9})')
ADDR_P = re.compile(r'(?:单位地址|联系地址|递交地址|邮寄地址|地址|采购人地址|遴选人地址)'
                    r'[：:\s]*([\u4e00-\u9fa5A-Za-z0-9（）()\-—号栋楼层室路街道镇区县市省\.\s]{6,80})')
# 地址尾部噪声：从这里截断
# ⚠️ 这份清单是实测补出来的 —— 政府站公示常见「地址…3.成交金额」「…中标（成交）金额」
#    「…采购代理机构信息名称」「…）评选工作由选聘人…」这类把下一段标题整段吞进来的情况。
ADDR_STOP = re.compile(
    r'(邮政编码|邮编|联系电话|联系人|联系方式|电子邮箱|邮箱|传真|'
    r'电话|手机|及联系|会议室|公示期|特此|附件|'
    r'采购项目|采购代理|代理机构|信息名称|采购人|中标|成交|金额|预算|'
    r'评选|评审|选聘|专家|随机|抽取|组成|委员会|公告|如下|'
    r'递交|要求|装订|报名|获取|时间|日期|\d{4}\s*年|年\d{1,2}月)')
# 地址形状校验：必须含「道路/门牌类字」。
# ⚠️ 判据演进：
#   1) 只用 (省|市|县|区|路|号|楼…) 一个大集合 → 太松，
#      「海南大田国家级自然**保护区**管理局」靠"保护区"的"区"就蒙过去了；
#   2) 改成"必须同时有行政区划字 + 门牌字" → 太紧，
#      把「海府路36号银都大厦402室」这种不带城市前缀的合法地址也杀了；
#   3) 定为**只要门牌类字** —— 这才是地址真正的标志，且天然排除"…管理局/统计局/委员会"这类机构名。
ADDR_SHAPE_B = re.compile(r'(路|街|道|巷|镇|乡|村|号|栋|幢|座|楼|层|室|苑|院|园|大厦|广场|大道|大街)')
ADDR_SHAPE = ADDR_SHAPE_B   # 兼容旧引用
OWNER_CTX = re.compile(r'(采购人|业主|受理单位|遴选人|招标人|我局|本单位|该局|服务中心|'
                       r'联系人|我方|项目业主)')
# 若上下文指向代理/第三方机构，则不要写成「采购人联系」
AGENT_CTX = re.compile(r'(代理|项目管理有限公司|咨询有限公司|招标有限公司|'
                       r'采购代理|受托|中介)')

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def log(m):
    sys.stdout.write(m + '\n')
    sys.stdout.flush()


def to_text(raw):
    """字节 → 纯文本（保留换行做语义边界，剥标签、去页脚）。"""
    t = None
    for enc in ('utf-8', 'gbk', 'gb18030'):
        try:
            t = raw.decode(enc)
            break
        except Exception:
            continue
    if t is None:
        t = raw.decode('utf-8', 'ignore')
    # 去 script/style
    t = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', t)
    # 块级标签转换行，其余标签转空格
    t = re.sub(r'(?i)<\s*(br|/p|/div|/tr|/li|/h[1-6]|/td)\s*/?\s*>', '\n', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = H.unescape(t)
    t = t.replace('\u3000', ' ').replace('\xa0', ' ')
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t).strip()
    return t


def strip_footer(t):
    """截掉网站页脚。返回 (正文, 是否截断)。"""
    cut = len(t)
    for mk in FOOTER_STRONG:
        i = t.find(mk)
        if i > 0:
            cut = min(cut, i)
    if cut == len(t):                      # 强标记没命中，用弱标记兜底
        for mk in FOOTER_WEAK:
            i = t.find(mk)
            if i > 0:
                cut = min(cut, i)
    return (t[:cut], cut < len(t)) if cut > 40 else (t, False)


def ctx_rejected(s, pos):
    """命中词的上下文是否属于举报/投诉类（取前后 45 字判断）。"""
    seg = s[max(0, pos - 45): pos + 90]
    return bool(REJECT_CTX.search(seg))


def clean_addr(a):
    """地址二次清洗（抽成独立函数，便于对已存值做离线复洗）。不合法返回 ''。"""
    if not a:
        return ''
    a = re.sub(r'\s+', '', a)
    m = ADDR_STOP.search(a)
    if m:
        a = a[:m.start()]
    # 括号配对：出现悬空开头，从其位置截断
    if a.count('（') > a.count('）'):
        a = a[:a.rindex('（')]
    if a.count('(') > a.count(')'):
        a = a[:a.rindex('(')]
    a = a.strip()
    # 超长优先砍括号补充说明：政府站常写「…D栋18楼（18A1801-18B1802）3」，
    # 括号里是房号细化、后面还跟个列表序号，整段超 45 字。砍括号保住主干。
    if len(a) > 45 and ('（' in a or '(' in a):
        i1 = a.find('（')
        i2 = a.find('(')
        cand = [x for x in (i1, i2) if x > 0]
        if cand:
            a = a[:min(cand)].strip()
    # ⚠️ 先摘尾部序号（"…农业审批室3."），**再**去标点 —— 反了就会把"3."的"."先吃掉，
    #    只剩裸数字"3"，而裸数字绝不能删（"…3座501"是合法门牌尾）。
    a = re.sub(r'\d+\s*[.、]\s*$', '', a)
    a = re.sub(r'[\s，。；;、：:）)】\]\.]+$', '', a)
    a = re.sub(r'^[\s，。；;、：:（(【\[]+', '', a).strip()
    if not (6 <= len(a) <= 45):
        return ''
    if not ADDR_SHAPE_B.search(a):
        return ''
    if ADDR_STOP.search(a):
        return ''
    return a


def extract(t):
    """从已切页脚的正文提取联系方式。宁缺勿滥。"""
    out = {'contact_name': '', 'contact_phone': '',
           'owner_contact': '', 'owner_address': '', 'agent_contact': ''}

    # ---- 电话：优先带关键词的，且排除举报类上下文
    cand = []
    for m in TEL_P.finditer(t):
        if ctx_rejected(t, m.start()):
            continue
        cand.append((m.start(), m.group(1).replace(' ', ''), t[max(0, m.start() - 60): m.end() + 10]))
    if not cand:                            # 兜底：正文里裸电话（要求落在采购/业主语境里）
        for m in TEL_ANY.finditer(t):
            seg = t[max(0, m.start() - 45): m.end() + 45]
            if REJECT_CTX.search(seg):
                continue
            if not OWNER_CTX.search(seg):
                continue
            cand.append((m.start(), m.group(1).replace(' ', ''), seg))
    if cand:
        pos, tel, seg = cand[0]
        out['contact_phone'] = tel
        # 「采购人联系」只在语境指向采购人/业主、且不是代理机构时才写
        if OWNER_CTX.search(seg) and not AGENT_CTX.search(seg):
            out['owner_contact'] = tel
        # 姓名：全文首个合法人名优先，其次同段
        for src in (t, seg):
            for nm in NAME_P.finditer(src):
                cand_name = nm.group(1)
                if not NAME_BAD.search(cand_name):
                    out['contact_name'] = cand_name
                    break
            if out['contact_name']:
                break

    # ---- 地址：截断尾部噪声 + 形状校验
    am = ADDR_P.search(t)
    if am:
        out['owner_address'] = clean_addr(am.group(1))

    return out


def fetch(url):
    last = None
    for _ in range(RETRY + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA,
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'zh-CN,zh;q=0.9',
            })
            return urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX).read()
        except Exception as e:
            last = e
            time.sleep(0.8)
    raise last


# 回抓水位（天）：detail_fetched_at 在 REFETCH_DAYS 之内的记录不再重抓。
# ⚠️ 必须有这道闸门 —— 大量政府站公告原文本来就没有项目联系电话（实测约一半），
#    若只按「字段为空」筛待补集合，这些记录永远命中，每周都从头重抓一遍、零新增，
#    既白烧时间又反复骚扰政府网站。这与 ccgp 的 collect_details.py 是同一个坑。
REFETCH_DAYS = int(os.environ.get('REFETCH_DAYS', '30'))

def main():
    con = sqlite3.connect(DB, timeout=30)
    con.execute('PRAGMA busy_timeout=30000')
    cur = con.cursor()

    # 待补集合：非 ccgp + 无任何联系方式（与前端 hasContact 判据一致）+ 水位过期
    # ⚠️ 这里**不能用 % 格式化**：SQL 里有 '%ccgp.gov.cn%'，%c 会被当成转换符直接炸。
    sql = """
      SELECT id, dm_code, source_url, title FROM projects
      WHERE source_url NOT LIKE '%ccgp.gov.cn%'
        AND source_url LIKE 'http%'
        AND status=1
        AND COALESCE(owner_contact,'')='' AND COALESCE(contact_phone,'')=''
        AND COALESCE(contact_name,'')='' AND COALESCE(owner_address,'')=''
        AND COALESCE(agent_contact,'')='' AND COALESCE(agent_address,'')=''
        AND (detail_fetched_at IS NULL
             OR detail_fetched_at < datetime('now','-""" + str(REFETCH_DAYS) + """ day'))
      ORDER BY publish_date DESC
    """
    if LIMIT:
        sql += ' LIMIT %d' % LIMIT
    rows = cur.execute(sql).fetchall()
    log('待补 %d 条（非 ccgp · 无联系方式）%s' % (len(rows), '  [DRY-RUN]' if DRY else ''))

    ok = fail = nohit = 0
    written = []
    for i, (pid, dm, url, title) in enumerate(rows, 1):
        try:
            raw = fetch(url)
        except Exception as e:
            fail += 1
            log('  %4d/%d %s 抓取失败 %s' % (i, len(rows), dm, e))
            if not DRY:
                cur.execute("UPDATE projects SET detail_fetched_at=datetime('now') WHERE id=?", (pid,))
                con.commit()
            time.sleep(SLEEP)
            continue

        body, cut = strip_footer(to_text(raw))
        info = extract(body)
        if info['contact_phone']:
            ok += 1
            log('  %4d/%d %s ✔ %s | %s | %s' % (
                i, len(rows), dm, info['contact_phone'],
                info['contact_name'] or '-', (title or '')[:34]))
            written.append((dm, info))
            if not DRY:
                sets, vals = [], []
                for k in ('contact_name', 'contact_phone', 'owner_contact', 'owner_address', 'agent_contact'):
                    if info.get(k):
                        sets.append('%s=?' % k)
                        vals.append(info[k])
                sets.append("detail_fetched_at=datetime('now')")
                vals.append(pid)
                cur.execute('UPDATE projects SET ' + ','.join(sets) + ' WHERE id=?', vals)
                con.commit()
        else:
            nohit += 1
            log('  %4d/%d %s ✗ 无项目级联系方式（页脚已切=%s）' % (i, len(rows), dm, cut))
            if not DRY:
                cur.execute("UPDATE projects SET detail_fetched_at=datetime('now') WHERE id=?", (pid,))
                con.commit()
        time.sleep(SLEEP)

    log('\n完成：处理 %d，补到 %d，无命中 %d，失败 %d' % (len(rows), ok, nohit, fail))
    if DRY and written:
        log('\n[DRY-RUN] 本会写入：')
        for dm, inf in written:
            log('  %s %s' % (dm, json.dumps(inf, ensure_ascii=False)))
    con.close()


if __name__ == '__main__':
    main()
