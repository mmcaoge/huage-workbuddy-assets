# -*- coding: utf-8 -*-
"""
服务器侧取数脚本（只读，绝不写库）
用法：python3 tools/fetch_city_bids.py <城市> [1=只能力线内|0=全部]
输出：base64(JSONL 清单) 到 stdout
"""
import base64
import json
import sqlite3
import sys

DB = "/www/wwwroot/hndcw.com/data/hndcw.db"


def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "海口"
    only_fit = (sys.argv[2] if len(sys.argv) > 2 else "1") == "1"

    db = sqlite3.connect(DB, timeout=60)
    db.execute("PRAGMA busy_timeout=60000")
    hk = "(city LIKE '%' || ? || '%' OR owner_unit LIKE '%' || ? || '%' OR title LIKE '%' || ? || '%')"
    where = "biddable=1 AND " + hk + (" AND bid_fit=1" if only_fit else "")

    sql = (
        "SELECT dm_code,title,owner_unit,budget_amount,key_dates,contact_name,contact_phone,"
        "owner_address,publish_date,COALESCE(city,''),source_url,COALESCE(fit_reason,''),"
        "COALESCE(qualification,''),COALESCE(evaluation,''),COALESCE(purchase_items,''),"
        "length(COALESCE(raw_content,'')) FROM projects WHERE " + where +
        " ORDER BY publish_date DESC"
    )
    rows = db.execute(sql, (city, city, city)).fetchall()

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


if __name__ == "__main__":
    main()
