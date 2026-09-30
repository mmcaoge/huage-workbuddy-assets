#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站群外「独立系统」市县 · 社会调查类公告采集器
================================================================
背景：海南省政府网站群 SSI（tools/collect_survey_gov.py）只覆盖 44 个站点
      （12 市县 + 省厅局）。以下 6 个市县使用**独立检索系统**，本脚本单独采集：

  ┌────────────────────────────┬──────────────────────────────────────────┐
  │ 类型                        │ 站点 / 接口                                │
  ├────────────────────────────┼──────────────────────────────────────────┤
  │ 开普云 search5 站内实例      │ 文昌、五指山、乐东、昌江                    │
  │   POST https://{host}/search5/search/s                                 │
  │   body: siteCode/searchWord/column/uc/left_right_index/pageSize/pageNum │
  │ 开普云 search5 独立搜索域    │ 三亚  search.sanya.gov.cn/search/s         │
  │ 拓尔思 IGS（JSON POST）      │ 海口  /irs/front/search                    │
  │   body: code/dataTypeId/searchWord/pageNo/pageSize/searchBy/orderBy     │
  │                            │  （orderBy/searchBy 必填，否则"排序方式不能为空"）│
  ├────────────────────────────┼──────────────────────────────────────────┤
  │ 三沙市                      │ ✗ 站点长期不可达（sansha.hainan.gov.cn）    │
  └────────────────────────────┴──────────────────────────────────────────┘

输出：与 collect_survey_gov.py **完全同构**的 JSONL，可直接喂 survey_filter.py。

用法（服务器）：
  cd /www/wwwroot/hndcw.com
  python3 -u tools/collect_survey_indep.py                    # 全量增量
  ONLY=haikou python3 -u tools/collect_survey_indep.py        # 单站调试
  MAX_PAGE=1 SLEEP=0.5 WORKERS=6 python3 -u tools/collect_survey_indep.py

环境变量：
  OUT        输出 JSONL（默认 data/survey_indep_raw.jsonl）
  PAGE_SIZE  每页条数（默认 50）
  MAX_PAGE   每词每站最多翻几页（默认 2）
  SLEEP      请求间隔秒（默认 0.6，政府站要克制）
  WORKERS    并发站点数（默认 3）
  ONLY       只跑指定站点 key（逗号分隔）
"""
import os
import sys
import re
import json
import time
import ssl
import html
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from survey_topics import TOPICS  # 词表单一真源（tools/survey_topics.py）

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# ===== 站群外独立系统站点 =====
# kind: search5（开普云） | haikou（拓尔思 IGS）
TARGETS = [
    {'key': 'wenchang',   'name': '文昌市人民政府',      'city': '文昌市',
     'host': 'wenchang.hainan.gov.cn',  'kind': 'search5', 'code': '4690050001'},
    {'key': 'wzs',        'name': '五指山市人民政府',    'city': '五指山市',
     'host': 'wzs.hainan.gov.cn',       'kind': 'search5', 'code': '4690010001'},
    {'key': 'ledong',     'name': '乐东黎族自治县人民政府', 'city': '乐东黎族自治县',
     'host': 'ledong.hainan.gov.cn',    'kind': 'search5', 'code': '4690270001'},
    {'key': 'changjiang', 'name': '昌江黎族自治县人民政府', 'city': '昌江黎族自治县',
     'host': 'changjiang.hainan.gov.cn', 'kind': 'search5', 'code': '4690260001'},
    {'key': 'sanya',      'name': '三亚市人民政府',      'city': '三亚市',
     'host': 'search.sanya.gov.cn',     'kind': 'search5', 'code': '4602000035',
     'path': '/search/s'},
    {'key': 'haikou',     'name': '海口市人民政府',      'city': '海口市',
     'host': 'www.haikou.gov.cn',       'kind': 'haikou'},
]

# 海口 IGS 检索参数（从站内搜索页 www.haikou.gov.cn/irs-c-web/search.shtml 提取）
HK_CODE = '17d1d69fedf'
HK_DTID = '259'
HK_REF = 'http://www.haikou.gov.cn/irs-c-web/search.shtml?code=%s&dataTypeId=%s' % (HK_CODE, HK_DTID)

OUT = os.environ.get('OUT', '/www/wwwroot/hndcw.com/data/survey_indep_raw.jsonl')
PAGE_SIZE = int(os.environ.get('PAGE_SIZE', '50'))
MAX_PAGE = int(os.environ.get('MAX_PAGE', '2'))
SLEEP = float(os.environ.get('SLEEP', '0.6'))
WORKERS = int(os.environ.get('WORKERS', '3'))
ONLY = [x.strip() for x in os.environ.get('ONLY', '').split(',') if x.strip()]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def clean_text(s):
    """去掉检索结果里的高亮标签（<span>/<em>）与 HTML 实体。

    注意：政府站检索结果偶尔把 title/content 返回成 dict/list（结构漂移），
    必须做类型兜底，否则 re.sub 会抛 "expected string or bytes-like object"。
    """
    if not isinstance(s, str):
        s = '' if s is None else str(s)
    s = re.sub(r'<[^>]{0,40}>', '', s)
    return html.unescape(s).strip()


def http_post(url, data, as_json=False, referer=None, timeout=30, retry=2):
    """POST 并解析 JSON；失败重试。"""
    if as_json:
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        ctype = 'application/json; charset=UTF-8'
    else:
        body = urllib.parse.urlencode(data).encode('utf-8')
        ctype = 'application/x-www-form-urlencoded; charset=UTF-8'
    last = None
    for _ in range(retry + 1):
        req = urllib.request.Request(url, data=body, headers={
            'User-Agent': UA, 'Content-Type': ctype,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': referer or url})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                txt = r.read().decode('utf-8', 'ignore')
            return json.loads(txt)
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise last


def fetch_search5(t, word, page):
    """开普云 search5 → (total, records)。文昌/五指山/乐东/昌江/三亚通用。"""
    host = t['host']
    api = 'https://%s%s' % (host, t.get('path', '/search5/search/s'))
    ref = 'https://%s/search5/html/searchResult.html?siteCode=%s' % (host, t['code'])
    d = http_post(api, {
        'siteCode': t['code'], 'searchWord': word, 'column': '', 'uc': 1,
        'left_right_index': '', 'pageSize': PAGE_SIZE, 'pageNum': page},
        referer=ref)
    sr = d.get('searchResultAll') or {}
    out = []
    for it in (sr.get('searchTotal') or []):
        url = it.get('url') or ''
        if not url:
            continue
        out.append({
            'title': clean_text(it.get('title')),
            'url': url,
            'date': (it.get('pubDate') or '')[:10],
            'content': clean_text(it.get('content') or it.get('shortContent') or '')[:500],
            'site': it.get('siteName') or t['name'],
        })
    return int(sr.get('total') or 0), out


def fetch_haikou(t, word, page):
    """拓尔思 IGS → (total, records)。orderBy/searchBy 必填。"""
    d = http_post('http://www.haikou.gov.cn/irs/front/search', {
        'code': HK_CODE, 'dataTypeId': HK_DTID, 'searchWord': word,
        'pageNo': page, 'pageSize': PAGE_SIZE,
        'searchBy': 'all', 'orderBy': 'relevance'},
        as_json=True, referer=HK_REF)
    dd = d.get('data') or {}
    total = int(((dd.get('pager') or {}).get('total')) or 0)
    out = []
    for blk in (((dd.get('middle') or {}).get('listAndBox')) or []):
        x = blk.get('data') or {}
        if not x.get('url'):
            continue
        out.append({
            'title': clean_text(x.get('title') or x.get('title_no_tag')),
            'url': x.get('url'),
            'date': (x.get('time') or '')[:10],
            'content': clean_text(x.get('content') or '')[:500],
            'site': clean_text(x.get('source')) or t['name'],
        })
    return total, out


FETCHERS = {'search5': fetch_search5, 'haikou': fetch_haikou}


def main():
    targets = [t for t in TARGETS if (not ONLY or t['key'] in ONLY)]
    print('== 站群外独立县市 · 社会调查类采集 ==')
    print('== 站点 %d 个 × 关键词 %d 个，每词每站 ≤%d 页 × %d 条 =='
          % (len(targets), len(TOPICS), MAX_PAGE, PAGE_SIZE))

    seen = set()
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            for line in f:
                try:
                    seen.add(json.loads(line)['url'])
                except Exception:
                    pass
        print('== 已有 %d 条（url 去重集），增量追加 ==' % len(seen))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fout = open(OUT, 'a', encoding='utf-8')
    stat = {'req': 0, 'new': 0, 'err': 0}
    hit_stat = []

    def do_site(t):
        site_new = 0
        f = FETCHERS[t['kind']]
        for word in TOPICS:
            try:
                total, recs = f(t, word, 1)
                stat['req'] += 1
                if total:
                    hit_stat.append((t['name'], word, total))
            except Exception as e:
                stat['err'] += 1
                print('    ! %s / %s : %s' % (t['key'], word, str(e)[:70]))
                time.sleep(2)
                continue
            pages = min(MAX_PAGE, max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE))
            for pg in range(2, pages + 1):
                try:
                    _, more = f(t, word, pg)
                    stat['req'] += 1
                    recs = recs + more
                except Exception:
                    stat['err'] += 1
                time.sleep(SLEEP)
            buf = []
            for it in recs:
                url = it.get('url') or ''
                if not url or url in seen:
                    continue
                seen.add(url)
                buf.append({
                    'url': url,
                    'title': it['title'],
                    'content': it['content'],
                    'pub_date': it['date'],
                    'site': it['site'],
                    'site_id': t.get('code') or t['key'],
                    'groupname': t['city'],
                    'filenum': '',
                    'keyword': word,
                })
            for rec in buf:
                fout.write(json.dumps(rec, ensure_ascii=False) + '\n')
            fout.flush()
            stat['new'] += len(buf)
            site_new += len(buf)
            time.sleep(SLEEP)
        print('  [%-11s] %-22s 新增 %4d 条' % (t['key'], t['name'], site_new))
        sys.stdout.flush()
        return site_new

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(do_site, t): t for t in targets}
        for fu in as_completed(futs):
            t = futs[fu]
            try:
                fu.result()
            except Exception as e:
                # 必须显式取 result，否则线程内异常会被静默吞掉（曾导致"只请求 1 次、新增 0 条"却无任何报错）
                import traceback
                print('  !! 站点 %s 中断: %s' % (t['key'], e))
                traceback.print_exc()

    fout.close()
    print('\n完成：请求 %d 次，新增 %d 条，失败 %d 次，输出 %s'
          % (stat['req'], stat['new'], stat['err'], OUT))
    print('\n=== 高召回 (站点, 关键词, 命中总数) TOP30 ===')
    for row in sorted(hit_stat, key=lambda x: -x[2])[:30]:
        print('   %-24s %-14s %d' % row)


if __name__ == '__main__':
    main()
