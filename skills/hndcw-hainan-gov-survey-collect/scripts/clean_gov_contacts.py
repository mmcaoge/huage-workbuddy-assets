# -*- coding: utf-8 -*-
"""
政府站联系方式 · 离线复洗（clean_gov_contacts.py）

用途：`collect_gov_contacts.py` 抓完后的收口清洗。**不联网**，只对已存值做纯字符串复洗。
为什么需要：抓取侧的正则会随实测样本不断加严，早期批次写进去的脏值（如把
「…11号）评选工作由选聘人…」整句吞进地址、把「联系人及地址」当成姓名）需要统一收口。
清洗逻辑与 collect_gov_contacts.py 的 clean_addr / NAME_BAD **共用同一套规则**
（本脚本直接 import，避免两处规则漂移）。

幂等：可反复跑。

用法：
    DRY=1 python3 clean_gov_contacts.py     # 只看会改什么
    python3 clean_gov_contacts.py           # 落库
"""
import os
import re
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collect_gov_contacts import clean_addr, NAME_BAD   # noqa: E402  单一真源

DB = os.environ.get('DB', '/www/wwwroot/hndcw.com/data/hndcw.db')
DRY = os.environ.get('DRY', '') not in ('', '0')
W = "source_url NOT LIKE '%ccgp.gov.cn%'"

con = sqlite3.connect(DB, timeout=30)
con.execute('PRAGMA busy_timeout=30000')
cur = con.cursor()

# ---- 1) 地址复洗
rows = cur.execute("SELECT id, dm_code, owner_address FROM projects WHERE " + W +
                   " AND COALESCE(owner_address,'')<>''").fetchall()
chg = blank = same = 0
for pid, dm, old in rows:
    new = clean_addr(old)
    if new == old:
        same += 1
        continue
    if new:
        chg += 1
        print('  地址改写 %s\n    旧: %s\n    新: %s' % (dm, old[:64], new[:64]))
    else:
        blank += 1
        print('  地址作废 %s（清洗后不合形状/仍含截断词）\n    旧: %s' % (dm, old[:64]))
    if not DRY:
        cur.execute('UPDATE projects SET owner_address=? WHERE id=?', (new, pid))
print('\n地址：共 %d 条，无需改 %d，改写 %d，作废 %d' % (len(rows), same, chg, blank))

# ---- 2) 姓名复洗
rows2 = cur.execute("SELECT id, dm_code, contact_name FROM projects WHERE " + W +
                    " AND COALESCE(contact_name,'')<>''").fetchall()
nb = 0
for pid, dm, nm in rows2:
    if NAME_BAD.search(nm) or not (2 <= len(nm) <= 4):
        nb += 1
        print('  姓名作废 %s  %r' % (dm, nm))
        if not DRY:
            cur.execute("UPDATE projects SET contact_name='' WHERE id=?", (pid,))
print('姓名：共 %d 条，其中作废 %d' % (len(rows2), nb))

# ---- 3) 收口：把「已尝试过、确实没有联系方式」的记录打上水位
# ⚠️ 这里**绝不能**把 detail_fetched_at 置 NULL！约一半政府站公告原文本来就没有项目联系电话，
#    置 NULL ⇒ 下一轮又把它们全抓一遍、零新增，正是 REFETCH_DAYS 要防的「永远命中」陷阱。
#    正确做法：凡是「非 ccgp + 字段全空 + 水位为空」的，补一个 now，30 天内不再重试。
if not DRY:
    cur.execute("""
      UPDATE projects SET detail_fetched_at=datetime('now')
      WHERE source_url NOT LIKE '%ccgp.gov.cn%' AND status=1
        AND COALESCE(owner_contact,'')='' AND COALESCE(contact_phone,'')=''
        AND COALESCE(contact_name,'')='' AND COALESCE(owner_address,'')=''
        AND COALESCE(agent_contact,'')='' AND COALESCE(agent_address,'')=''
        AND detail_fetched_at IS NULL""")
    print('已给「确无联系方式」的记录补水位: %d 条（30 天内不再重抓）' % cur.rowcount)
    con.commit()
    print('\n已落库。')
else:
    print('\n[DRY-RUN] 未写库。')
con.close()
