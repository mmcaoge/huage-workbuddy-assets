# -*- coding: utf-8 -*-
"""
投标截止日期 · 离线重抽（不联网，秒级）
=========================================
背景：enrich_biddable.py 用 get_text('|') 逐单元格切分，政府公告的 HTML 表格把
日期切碎成 "1、时间：202" + "6年9月15日" + "至" + "202" + "6年9月22日"，
导致首屏正则全落空 —— 174 条能力线内标只抽出 51 条截止（覆盖率 29%）。

本脚本不联网，只对库里已有的 raw_content 做：
  1) 数字粘连修复（把被分隔符切碎的数字拼回来）
  2) 强正则抽取"截止时间/递交截止/响应截止/开标时间"
  3) 支持区间取右端、无年份日期按发布年推断、"X个工作日"相对推算

用法（服务器 /www/wwwroot/hndcw.com）：
  DRY=1  python3 tools/reextract_dates.py          # 预演，打印前后对比
          python3 tools/reextract_dates.py          # 正式写库
  SCOPE=fit  python3 tools/reextract_dates.py       # 只跑能力线内（默认）
  SCOPE=all  python3 tools/reextract_dates.py       # 跑全部 biddable=1
"""
import datetime
import json
import os
import re
import sqlite3

DB = os.environ.get("HNCW_DB", "/www/wwwroot/hndcw.com/data/hndcw.db")
DRY = os.environ.get("DRY") == "1"
SCOPE = os.environ.get("SCOPE", "fit")

# ---------------------------------------------------------------- 预处理
# 被 | / 空白 切碎的数字粘回来： "202|6年9月15日" -> "2026年9月15日"
SPLIT_NUM = re.compile(r"(\d)[\s|　]+(\d)")


def glue(text):
    if not text:
        return ""
    t = text
    for _ in range(3):
        t2 = SPLIT_NUM.sub(r"\1\2", t)
        if t2 == t:
            break
        t = t2
    return t


# ---------------------------------------------------------------- 日期模式
DATE_FULL = re.compile(
    r"(20\d{2})\s*[年\-/\.]\s*(\d{1,2})\s*[月\-/\.]\s*(\d{1,2})\s*日?"
)
DATE_SHORT = re.compile(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*日")
TIME = re.compile(r"(\d{1,2})\s*[:：时]\s*(\d{2})?")

# 截止类关键词（避免命中"前三年内""截止至投标截止日"这类无关表述）
KW_DEADLINE = [
    "响应文件递交截止时间", "递交响应文件截止时间", "响应截止时间",
    "投标文件递交截止时间", "递交投标文件截止时间", "投标截止时间",
    "响应文件截止时间", "响应文件递交截止", "递交截止时间",
    "报名截止时间", "获取招标文件截止时间", "获取文件截止时间",
    "提交响应文件截止时间", "响应文件递交时间", "投标文件递交时间",
    "截止时间", "递交时间", "开标时间", "开启时间", "磋商时间",
    "报价截止时间", "送达截止时间",
]
# 噪音：这些句子里的"截止"不是投标截止
NOISE = re.compile(r"前三年|近三年|经验年限|计算截止|截止至投标截止日|均无|无。")


def norm_dt(y, m, d, hh=None, mm=None):
    try:
        y, m, d = int(y), int(m), int(d)
        if not (1 <= m <= 12 and 1 <= d <= 31):
            return None
        dt = datetime.datetime(y, m, d, int(hh or 0), int(mm or 0))
    except Exception:
        return None
    return dt


def find_dates_near(text, kw_pos, window=160, pub_year=None):
    """在关键词附近窗口内找日期，优先取窗口内最后一个（区间右端）"""
    left = max(0, kw_pos - 20)
    right = min(len(text), kw_pos + window)
    seg = text[left:right]
    cands = []
    for m in DATE_FULL.finditer(seg):
        cands.append((m.start(), norm_dt(m.group(1), m.group(2), m.group(3))))
    if not cands and pub_year:
        for m in DATE_SHORT.finditer(seg):
            cands.append((m.start(), norm_dt(pub_year, m.group(1), m.group(2))))
    cands = [c for c in cands if c[1]]
    if not cands:
        return None
    # 区间（A至B / A-B）取右端
    if len(cands) >= 2:
        between = seg[cands[0][0]:cands[-1][0]]
        if re.search(r"[至到\-~—]", between[-30:]):
            return cands[-1][1]
    return cands[0][1]


# ★ 政府采购标准句式："并于2026年09月15日15:30（北京时间）前提交响应文件"
#   这条覆盖率极高，是"项目概况"段的固定写法，必须单独匹配
PAT_BEFORE_SUBMIT = re.compile(
    r"于?\s*(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?\s*"
    r"(?:(\d{1,2})\s*[:：]\s*(\d{2}))?\s*（?\s*北京时间\s*）?\s*"
    r"(?:之)?前\s*(?:提交|递交|送达|上传|送达至)"
)

REL_WORKDAY = re.compile(r"(?:自)?(?:公告|本公告)?发布(?:之日)?起\s*(\d{1,2})\s*个?工作日")
REL_CALDAY = re.compile(r"(?:自)?(?:公告|本公告)?发布(?:之日)?起\s*(\d{1,2})\s*个?(?:日历日|自然日|日)")


def add_workdays(start, n):
    d = start
    added = 0
    while added < n:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d


def extract(raw, pub_date):
    """返回 (bid_deadline, open_time) 字符串或 (None, None)"""
    if not raw:
        return None, None
    text = glue(raw)
    pub_year = None
    pub_dt = None
    if pub_date:
        try:
            pub_dt = datetime.datetime.strptime(str(pub_date)[:10], "%Y-%m-%d")
            pub_year = pub_dt.year
        except Exception:
            pass

    # 0) 最高优先级：标准句式"XX前提交响应文件"
    deadline = None
    m = PAT_BEFORE_SUBMIT.search(text)
    if m:
        deadline = norm_dt(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5))

    # 1) 关键词定位
    if not deadline:
        for kw in KW_DEADLINE:
            p = 0
            while True:
                idx = text.find(kw, p)
                if idx < 0:
                    break
                p = idx + 1
                ctx = text[max(0, idx - 60):idx + len(kw) + 20]
                if NOISE.search(ctx):
                    continue
                dt = find_dates_near(text, idx + len(kw), pub_year=pub_year)
                if dt:
                    deadline = dt
                    break
            if deadline:
                break

    # 2) 相对日期兜底（公告之日起 N 个工作日）
    if not deadline and pub_dt:
        m = REL_WORKDAY.search(text) or REL_CALDAY.search(text)
        if m:
            n = int(m.group(1))
            deadline = add_workdays(pub_dt, n) if REL_WORKDAY.search(text) else pub_dt + datetime.timedelta(days=n)

    # 3) 开标时间
    open_t = None
    for kw in ["开标时间", "开启时间", "磋商时间", "开启响应文件时间"]:
        idx = text.find(kw)
        if idx >= 0:
            open_t = find_dates_near(text, idx + len(kw), pub_year=pub_year)
            if open_t:
                break

    fmt = lambda d: d.strftime("%Y-%m-%d %H:%M") if (d.hour or d.minute) else d.strftime("%Y-%m-%d")
    return (fmt(deadline) if deadline else None), (fmt(open_t) if open_t else None)


def main():
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    where = "biddable=1 AND bid_fit=1" if SCOPE == "fit" else "biddable=1"
    rows = conn.execute(
        "SELECT id,title,raw_content,key_dates,publish_date FROM projects WHERE %s" % where
    ).fetchall()

    before = after = improved = 0
    samples = []
    for pid, title, raw, kd, pub in rows:
        try:
            cur = json.loads(kd or "{}")
        except Exception:
            cur = {}
        had = bool(cur.get("bid_deadline"))
        if had:
            before += 1
        dl, ot = extract(raw, pub)
        if dl:
            after += 1
            if not had:
                improved += 1
                if len(samples) < 12:
                    samples.append((title, dl))
        if not DRY and dl and not had:
            cur["bid_deadline"] = dl
            if ot and not cur.get("open_time"):
                cur["open_time"] = ot
            conn.execute("UPDATE projects SET key_dates=? WHERE id=?", (json.dumps(cur, ensure_ascii=False), pid))
    if not DRY:
        conn.commit()

    print("=" * 60)
    print("投标截止日期离线重抽 · %s · 范围=%s" % ("预演(DRY)" if DRY else "正式写库", SCOPE))
    print("=" * 60)
    print("样本总数     : %d" % len(rows))
    print("重抽前有截止 : %d" % before)
    print("重抽后有截止 : %d  (+%d)" % (after, improved))
    if not DRY:
        print("已写库       : %d 条" % improved)
    print("-" * 60)
    print("新增样例:")
    for t, d in samples:
        print("  [%s] %s" % (d, t[:46]))


if __name__ == "__main__":
    main()
