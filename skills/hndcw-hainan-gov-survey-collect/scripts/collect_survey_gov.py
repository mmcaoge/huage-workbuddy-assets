# -*- coding: utf-8 -*-
"""
海南省政府网站群 · 社会调查类项目定向采集（survey collector）

背景（2026-09-17 数据源诊断结论）：
  - ccgp（中国政府采购网）：社会调查类项目**标题检索在海南几乎为 0**
    （"满意度"标题仅 2 条，且省份 zone 过滤对本类项目失效），不可用。
  - 海南公共资源交易平台（ggzy.hainan.gov.cn）：全品类 22.4 万条，
    但"残疾人基本状况""公共服务监测""旅游满意度"等**检索不到**，
    因为比选/遴选类小额服务采购**不发在交易平台**。
  - ✅ 真正的发布渠道 = **海南省政府网站群**（*.hainan.gov.cn 及省厅局站点），
    统一检索接口 /igs/front/search.jhtml，覆盖 44 个站点（12 市县 + 省厅局）。

本脚本 = 遍历 44 个站点的统一检索接口，用社会调查类关键词捞取公告，
  落成 JSONL 原始集（url 去重、幂等），供后续过滤/入库。

用法（服务器）：
  cd /www/wwwroot/hndcw.com
  nohup python3 -u tools/collect_survey_gov.py > logs/survey_collect.log 2>&1 &

环境变量：
  OUT        输出 JSONL 路径（默认 data/survey_gov_raw.jsonl）
  PAGE_SIZE  每页条数（默认 50）
  MAX_PAGE   每词每站最多翻几页（默认 2）
  SLEEP      请求间隔秒（默认 0.7，政府站要克制）
  ONLY       只跑指定 siteId（逗号分隔，调试用）
"""
import os, sys, json, time, ssl, hashlib, urllib.request, urllib.parse

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
CODE = '460cba3871804a4f8f696b6429e0fa08'   # 站群 SSI 检索固定 code（从检索页 JS 提取）
API = 'https://db.hainan.gov.cn/igs/front/search.jhtml'
REFERER = 'https://db.hainan.gov.cn/ssi/search.html?siteId=50'

# ===== 44 个活跃站点（2026-09-17 枚举 1~250 实测所得）=====
SITES = [
    (3, '省应急管理厅'), (4, '省教育厅'), (5, '保亭县'), (6, '澄迈县'),
    (7, '省市场监管局(工商)'), (8, '省科技厅'), (9, '陵水县'), (10, '省考试局'),
    (11, '省审计厅'), (12, '琼中县'), (13, '屯昌县'), (14, '万宁市'),
    (15, '省药监局'), (16, '省卫健委'), (17, '省统计局'), (18, '琼海市'),
    (19, '省农业农村厅'), (20, '白沙县'), (22, '儋州市'), (23, '省林业局'),
    (24, '省质监局'), (25, '临高县'), (26, '省国资委'), (28, '定安县'),
    (30, '省生态环境厅'), (31, '省司法厅'), (32, '省交通运输厅'), (33, '省自然资源和规划厅'),
    (37, '省外事办'), (38, '阳光海南网'), (39, '东方市'), (40, '省市场监管局'),
    (41, '省文体厅'), (42, '省旅文厅'), (44, '省医保局'), (45, '省大数据发展中心'),
    (46, '省知识产权局'), (47, '海南自由贸易港'), (49, '省残联'), (50, '省营商环境建设厅'),
    (51, '省海洋厅'), (52, '省检验检测研究院'), (53, '省测绘地理信息局'),
    (54, '海南热带雨林国家公园管理局'),
]

# ===== 社会调查类关键词（标题检索，覆盖用户点名 5 类 + 通用 + 第三方/绩效）=====
# 注：不用"比选公告/遴选公告/询价公告"这类泛词做检索（噪音大且非社会调查特征），
#     采购方式改由采集后按标题关键词标注（见 survey_filter.py）。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from survey_topics import TOPICS  # noqa: E402 —— 词表单一真源（tools/survey_topics.py）

OUT = os.environ.get('OUT', '/www/wwwroot/hndcw.com/data/survey_gov_raw.jsonl')
PAGE_SIZE = int(os.environ.get('PAGE_SIZE', '50'))
MAX_PAGE = int(os.environ.get('MAX_PAGE', '2'))
SLEEP = float(os.environ.get('SLEEP', '0.7'))
ONLY = [int(x) for x in os.environ.get('ONLY', '').split(',') if x.strip()]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def search(site, word, page, title_only=True):
    """调用站群统一检索接口，返回 (total, records)。

    title_only=True  → position=TITLE（只匹配标题，精度高：
                        儋州"满意度调查"标题 12 条 vs 全文 560 条）
    orderby=time     → 时间倒序，保证先拿到**最新**公告（找可投项目）
    """
    u = ('%s?code=%s&pageSize=%d&searchWord=%s&siteId=%d&pageNumber=%d'
         % (API, CODE, PAGE_SIZE, urllib.parse.quote(word), site, page))
    if title_only:
        u += '&position=TITLE'
    u += '&orderby=time&timeOrder=desc'
    req = urllib.request.Request(u, headers={
        'User-Agent': UA, 'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest', 'Referer': REFERER})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        d = json.loads(r.read().decode('utf-8', 'ignore'))
    p = d.get('page') or {}
    return p.get('total'), (p.get('content') or [])


def strip_em(s):
    """去掉检索高亮 <em> 标签。"""
    return (s or '').replace('<em>', '').replace('</em>', '').strip()


def main():
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    sites = [s for s in SITES if (not ONLY or s[0] in ONLY)]
    workers = int(os.environ.get('WORKERS', '4'))
    print('== 海南政府网站群·社会调查类采集 ==')
    print('== 站点 %d 个 × 关键词 %d 个，每词每站 ≤%d 页 × %d 条，并发 %d =='
          % (len(sites), len(TOPICS), MAX_PAGE, PAGE_SIZE, workers))

    seen = set()
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            for line in f:
                try:
                    seen.add(json.loads(line)['url'])
                except Exception:
                    pass
        print('== 已有 %d 条（url 去重集），将增量追加 ==' % len(seen))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fout = open(OUT, 'a', encoding='utf-8')
    lock = threading.Lock()
    stat = {'new': 0, 'req': 0, 'err': 0}
    hit_stat = []

    def do_site(sid, sname):
        """单站采集（站内串行，控制对该站的请求密度）。"""
        site_new = 0
        for word in TOPICS:
            try:
                total, recs = search(sid, word, 1)
                with lock:
                    stat['req'] += 1
                if total and int(total) > 0:
                    hit_stat.append((sname, word, int(total)))
            except Exception:
                with lock:
                    stat['err'] += 1
                time.sleep(1.5)
                continue
            pages = min(MAX_PAGE, max(1, (int(total or 0) + PAGE_SIZE - 1) // PAGE_SIZE))
            for pg in range(2, pages + 1):
                try:
                    _, more = search(sid, word, pg)
                    with lock:
                        stat['req'] += 1
                    recs = recs + more
                except Exception:
                    with lock:
                        stat['err'] += 1
                time.sleep(SLEEP)
            buf = []
            with lock:
                for it in recs:
                    url = it.get('url') or ''
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    buf.append({
                        'url': url,
                        'title': strip_em(it.get('title')),
                        'content': strip_em(it.get('content'))[:500],
                        'pub_date': (it.get('trs_time') or it.get('pubdate') or '')[:10],
                        'site': it.get('trs_site') or sname,
                        'site_id': sid,
                        'groupname': it.get('GROUPNAME') or '',
                        'filenum': strip_em(it.get('filenum')),
                        'keyword': word,
                    })
                for rec in buf:
                    fout.write(json.dumps(rec, ensure_ascii=False) + '\n')
                fout.flush()
                stat['new'] += len(buf)
                site_new += len(buf)
            time.sleep(SLEEP)
        print('  [%2d] %-18s 新增 %4d 条' % (sid, sname, site_new))
        sys.stdout.flush()
        return site_new

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(do_site, sid, sn) for sid, sn in sites]
        for _ in as_completed(futs):
            pass

    fout.close()
    print('\n完成：请求 %d 次，新增 %d 条，失败 %d 次，输出 %s'
          % (stat['req'], stat['new'], stat['err'], OUT))
    print('\n=== 高召回 (站点, 关键词, 命中总数) TOP40 ===')
    for row in sorted(hit_stat, key=lambda x: -x[2])[:40]:
        print('   %-18s %-14s %d' % row)


if __name__ == '__main__':
    main()
