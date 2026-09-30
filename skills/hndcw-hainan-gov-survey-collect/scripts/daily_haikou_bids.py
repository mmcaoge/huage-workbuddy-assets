# -*- coding: utf-8 -*-
"""
每日海口可投标清单（hndcw.com）

用途：每天早上自动捞「海口 + 能力线内」的标，出 HTML 报告 + 控制台摘要。
调用：python daily_haikou_bids.py            （默认只出海口）
      python daily_haikou_bids.py --city 儋州 （可换城市）
      python daily_haikou_bids.py --all       （不限能力线，全量）

设计要点：
- 只读，不写库，绝不修改线上数据。
- 取数走 SSH（复用 ~/.ssh/wb_auto2），known_hosts 落 D 盘，不碰 C 盘。
- 报告落 D:\\WorkBuddy\\Delivery\\workBuddy\\，命名带日期与城市标识。
"""
import base64
import datetime
import json
import os
import subprocess
import sys

SSH_KEY = os.path.expanduser("~/.ssh/wb_auto2")
KNOWN = r"D:\workBuddy\tmp\ssh\known_hosts"
HOST = "root@YOUR_SERVER_IP"
PORT = "YOUR_SSH_PORT"
ROOT = "/www/wwwroot/hndcw.com"
OUT_DIR = r"D:\WorkBuddy\Delivery\workBuddy"

# 远程取数脚本：只 SELECT，不 UPDATE
REMOTE_PY = r'''
import sqlite3, json, base64, sys, datetime
city = sys.argv[1]
only_fit = sys.argv[2] == "1"
db = sqlite3.connect("/www/wwwroot/hndcw.com/data/hndcw.db")
HK = "(city LIKE '%' || ? || '%' OR owner_unit LIKE '%' || ? || '%' OR title LIKE '%' || ? || '%')"
base = "FROM projects WHERE biddable=1 AND " + HK
if only_fit:
    base += " AND bid_fit=1"
rows = db.execute(
    "SELECT dm_code,title,owner_unit,budget_amount,key_dates,contact_name,contact_phone,"
    "owner_address,publish_date,COALESCE(city,''),source_url,COALESCE(fit_reason,''),"
    "COALESCE(qualification,''),COALESCE(evaluation,''),COALESCE(purchase_items,''),"
    "length(COALESCE(raw_content,'')) " + base + " ORDER BY publish_date DESC",
    (city, city, city)).fetchall()
out = []
for r in rows:
    kd = {}
    try:
        kd = json.loads(r[4] or "{}")
    except Exception:
        pass
    out.append({
        "dm": r[0], "title": r[1], "owner": r[2], "budget_wan": r[3],
        "deadline": kd.get("bid_deadline", ""), "contact": r[5], "phone": r[6],
        "addr": r[7], "pub": r[8], "city": r[9], "url": r[10], "reason": r[11],
        "qual": r[12], "eva": r[13], "items": r[14], "rawlen": r[15],
    })
sys.stdout.write(base64.b64encode(json.dumps(out, ensure_ascii=False).encode()).decode())
'''


def ssh_run(remote_cmd):
    cmd = ["ssh", "-i", SSH_KEY, "-o", "UserKnownHostsFile=" + KNOWN,
           "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15",
           "-p", PORT, HOST, remote_cmd]
    p = subprocess.run(cmd, capture_output=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "ignore")[:300])
    return p.stdout.decode("utf-8", "ignore").strip()


def fetch(city, only_fit=True):
    """调用服务器侧 tools/fetch_city_bids.py（只读脚本），取回 base64(JSON)。"""
    os.makedirs(os.path.dirname(KNOWN), exist_ok=True)
    remote = "cd %s && python3 tools/fetch_city_bids.py %s %s" % (
        ROOT, city, "1" if only_fit else "0")
    return json.loads(base64.b64decode(ssh_run(remote)).decode("utf-8"))


def money(v):
    try:
        b = float(v or 0)
    except Exception:
        return "未披露"
    if b <= 0:
        return "未披露"
    s = ("%.4f" % b).rstrip("0").rstrip(".")
    return s + " 万元"


def esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render(data, city, today):
    live, unk, exp = [], [], []
    for d in data:
        dl = str(d.get("deadline") or "")
        if not dl:
            unk.append(d)
        elif dl[:10] >= today:
            live.append(d)
        else:
            exp.append(d)
    live.sort(key=lambda x: str(x.get("deadline") or ""))
    unk.sort(key=lambda x: str(x.get("pub") or ""), reverse=True)

    def rows(lst, start=1):
        out = []
        for i, d in enumerate(lst, start):
            dl = esc(d.get("deadline")) or "—"
            bud = money(d.get("budget_wan"))
            own = esc((d.get("owner") or "")[:22]) or "—"
            ph = esc(d.get("phone")) or "—"
            ct = esc(d.get("contact")) or ""
            title = esc(d.get("title") or "")
            url = esc(d.get("url") or "#")
            link = ('<a href="%s" target="_blank">%s</a>' % (url, title[:52])) if d.get("url") else title[:52]
            dm = esc(d.get("dm") or "")
            det = ('<a href="https://hndcw.com/projects/%s" target="_blank">详情</a>' % dm) if dm else "—"
            out.append(
                "<tr><td>%d</td><td>%s</td><td>%s</td><td>%s</td><td><b>%s</b></td>"
                "<td>%s%s</td><td>%s</td></tr>"
                % (i, link, own, bud, dl, ph, ("（" + ct + "）") if ct else "", det))
        return "".join(out) or "<tr><td colspan='7' class='empty'>无</td></tr>"

    stats = [
        ("能力线内总量", len(data)),
        ("现在能投（截止未过）", len(live)),
        ("截止待确认", len(unk)),
        ("已过截止", len(exp)),
    ]
    stat_html = "".join("<div class='kpi'><b>%d</b><span>%s</span></div>" % (v, k) for k, v in stats)

    tpl = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>__CITY__可投标清单 __DATE__</title><style>
body{font-family:"Microsoft YaHei",sans-serif;background:#0f1115;color:#e6e8ec;margin:0;padding:28px}
h1{font-size:22px;margin:0 0 6px;color:#fff}
h2{font-size:17px;margin:26px 0 10px;color:#8ab4f8;border-left:4px solid #8ab4f8;padding-left:9px}
.sub{color:#9aa0a6;font-size:13px;margin-bottom:18px}
.kpis{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}
.kpi{background:#171a21;border:1px solid #262b36;border-radius:8px;padding:12px 18px;min-width:120px}
.kpi b{display:block;font-size:24px;color:#7ee787}
.kpi span{font-size:12px;color:#9aa0a6}
table{width:100%;border-collapse:collapse;font-size:13px;background:#14171d}
th{background:#1d222c;color:#c9d1d9;padding:9px 8px;text-align:left;border:1px solid #262b36}
td{padding:8px;border:1px solid #22262f;vertical-align:top}
tr:nth-child(even) td{background:#171b22}
a{color:#8ab4f8;text-decoration:none}a:hover{text-decoration:underline}
.empty{text-align:center;color:#6e7681;padding:16px}
.note{background:#1a1f2b;border-left:3px solid #f0a020;padding:10px 14px;font-size:13px;color:#c9d1d9;margin:12px 0}
</style></head><body>
<h1>__CITY__ · 可投标清单</h1>
<div class="sub">生成日期 __DATE__ · 数据源 hndcw.com 项目库 · 口径：__CITY__ + 能力线内（调查统计/评估测评/数据信息化/咨询研究/民生服务）</div>
<div class="kpis">__STATS__</div>
<div class="note">判定说明：「现在能投」= 已抽到投标截止且未过期；「截止待确认」= 公告正文未写明截止或写在附件里，需点开原公告核对。
预算单位统一为万元。点击项目名打开官方公告，点「详情」看本站完整档案（含三件套与鸣儿情报）。</div>
<h2>一、现在能投（__N_LIVE__ 条）</h2>
<table><tr><th>#</th><th>项目</th><th>采购人</th><th>预算</th><th>投标截止</th><th>电话</th><th>档案</th></tr>__ROWS_LIVE__</table>
<h2>二、截止待确认（__N_UNK__ 条 · 按发布倒序）</h2>
<table><tr><th>#</th><th>项目</th><th>采购人</th><th>预算</th><th>截止</th><th>电话</th><th>档案</th></tr>__ROWS_UNK__</table>
<h2>三、已过截止（__N_EXP__ 条 · 复盘参考）</h2>
<table><tr><th>#</th><th>项目</th><th>采购人</th><th>预算</th><th>截止</th><th>电话</th><th>档案</th></tr>__ROWS_EXP__</table>
</body></html>"""
    for k, v in [("__CITY__", city), ("__DATE__", today), ("__STATS__", stat_html),
                 ("__N_LIVE__", str(len(live))), ("__N_UNK__", str(len(unk))),
                 ("__N_EXP__", str(len(exp))),
                 ("__ROWS_LIVE__", rows(live)), ("__ROWS_UNK__", rows(unk)),
                 ("__ROWS_EXP__", rows(exp))]:
        tpl = tpl.replace(k, v)
    return tpl, len(live), len(unk), len(exp)


def main():
    city = "海口"
    only_fit = True
    args = sys.argv[1:]
    if "--city" in args:
        city = args[args.index("--city") + 1]
    if "--all" in args:
        only_fit = False
    today = datetime.date.today().isoformat()

    data = fetch(city, only_fit)
    html, n_live, n_unk, n_exp = render(data, city, today)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "hndcw_%s可投标清单_%s.html" % (city, today.replace("-", "")))
    open(path, "w", encoding="utf-8").write(html)

    print("城市: %s | 能力线内 %d 条" % (city, len(data)))
    print("  现在能投: %d | 截止待确认: %d | 已过截止: %d" % (n_live, n_unk, n_exp))
    for d in sorted([x for x in data if str(x.get("deadline") or "")[:10] >= today],
                    key=lambda x: str(x.get("deadline") or ""))[:8]:
        print("   ★ %s | %s | %s | %s" % (
            str(d.get("deadline"))[:16], (d.get("title") or "")[:34],
            (d.get("owner") or "")[:14], money(d.get("budget_wan"))))
    print("报告: %s" % path)


if __name__ == "__main__":
    main()
