# -*- coding: utf-8 -*-
"""鸣儿能力情报补抽：资格要求(qualification) + 评分标准(evaluation)
离线、幂等、不联网。只对已有 raw_content 的行补空字段（已抽到的不覆盖）。
根因：enrich_biddable.py 的 RE_QUAL 只认「资格要求/资格条件」，比选类公告写
「五、申报单位条件」「参选条件」「报价人资格」全部漏抽；evaluation 压根没写正则。

用法：
  DRY=1 python3 tools/reextract_qual.py            # 预演，打印样例
  python3 tools/reextract_qual.py                  # 正式写库
  SCOPE=fit 只处理 bid_fit=1；DM=xxx 只处理单条
"""
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from reextract_dates import glue  # 复用数字粘连：HTML 表格把内容切碎
except Exception:
    def glue(s):
        return s

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'hndcw.db')
DRY = os.environ.get('DRY', '') == '1'
SCOPE = os.environ.get('SCOPE', '')
ONLY_DM = os.environ.get('DM', '')

# ── 起始锚点：资格 / 条件 ────────────────────────────────────────────
P_START = re.compile(
    r'(?:^|[|｜\s，,。;；、：:.．）)])'
    r'(?:\d+[、.．]|[一二三四五六七八九十]{1,3}[、.．])?\s*'
    r'(?:申报单位条件|申报人条件|申报条件|投标人资格要求|投标人资格条件|投标人资格|'
    r'供应商资格要求|供应商资格条件|供应商资格|申请人的资格要求|申请人资格要求|'
    r'资格要求|资格条件|资格审查|参选单位条件|参选人条件|参选条件|'
    r'报价人资格|响应人资格|响应供应商资格|遴选条件|遴选资格|比选申请人资格|'
    r'报名条件|投标人条件|供应商条件|投标单位资格|投标单位条件|'
    r'承接单位条件|承担单位条件|申报单位资格|参加比选条件|参加遴选条件)'
)

# ── 起始锚点：评分 / 评审 ────────────────────────────────────────────
E_START = re.compile(
    r'(?:^|[|｜\s，,。;；、：:.．）)])'
    r'(?:\d+[、.．]|[一二三四五六七八九十]{1,3}[、.．])?\s*'
    r'(?:评分标准|评分办法|评分细则|评分因素|评分内容|评审办法|评审标准|评审因素|'
    r'评审细则|综合评分法|评选办法|评选标准|评选细则|比选办法|遴选办法|'
    r'评定办法|评标办法|评标标准|打分办法|择优办法|选取办法)'
)

# ── 结束锚点：下一同级标题（命中即截断）─────────────────────────────
P_END = re.compile(
    r'(?:\d+[、.．]|[一二三四五六七八九十]{1,3}[、.．])?\s*'
    r'(?:申报材料|报名方式|报名时间|报名事项|报名资格|获取文件|获取比选|获取采购|获取谈判|'
    r'递交|响应文件|资格要求|资格条件|申请人资格|投标人资格|供应商资格|参选条件|遴选条件|'
    r'评选|评审|开标|比选程序|遴选程序|比选办法|评选办法|评分标准|评审办法|评标办法|'
    r'公告期限|公告时间|发布公告|联系方式|联系事项|联系人|监督|质疑|答疑|'
    r'其他事项|其他说明|其他要求|附件|时间安排|材料要求|报价要求|'
    r'中标|成交|确定中选|结果|保证金|履约|付款方式|验收|'
    r'项目预算|预算金额|资金来源|合同履行|服务期限|服务地点|'
    r'评分标准|评审细则)'
)

# ── 起始锚点：采购标的 / 服务内容 ────────────────────────────────────
I_START = re.compile(
    r'(?:(?:^|[|｜\s。，,；;：:）)】])(?:\d{1,2}|[一二三四五六七八九十]{1,3})[、.．]|[|｜]|^)\s*.{0,6}?'
    r'(?:采购标的|采购内容|采购需求|采购清单|采购范围|服务内容|服务需求|服务范围|'
    r'实施内容|建设内容|工作内容|项目内容|项目概况及需求|项目需求|技术要求|'
    r'标的内容|标的情况|服务事项|委托内容|主要工作内容|工作内容及要求)'
)

# 误抽过滤：抽出来是资质证照类句子，说明锚点落到资格段了
BAD_ITEM = re.compile(
    r'营业执照|税务登记|组织机构代码|三证合一|承诺函|重大违法|商业信誉|'
    r'财务会计制度|缴纳税收|社会保障资金|独立承担民事责任|'
    r'资金来源|招标范围|合同履行期限|投标保证金|预算金额|取费标准|'
    r'公告期限|联系方式|监督管理部门|'
    r'具备|须提供|须具有|应提供|职称|执业资格|注册会计师|年以上|'
    r'从业人员|团队配置|项目负责人|无重大'
)

MAXLEN = 1200
MINLEN = 12

NOISE = re.compile(r'^(?:详见|见附件|无|略|同上|以.*为准)')

ITEM_MARK = re.compile(r'(?:（[一二三四五六七八九十]{1,3}）|[（(]\d{1,2}[)）]|[①-⑳]|\d{1,2}[、.．](?=\s*\S))')
RE_BUD_IN = re.compile(r'(\d+(?:\.\d+)?)\s*万?元')
RE_QTY = re.compile(r'(\d+(?:\.\d+)?)\s*(个|项|次|套|台|人|批|处|条|份|年|月|家|名)')


def split_items(seg):
    """把「服务内容」段按编号拆成条目，最多 12 条"""
    marks = list(ITEM_MARK.finditer(seg))
    if len(marks) < 2:
        if len(seg) < 15:
            return []
        bm = RE_BUD_IN.search(seg)
        qm = RE_QTY.search(seg)
        return [{'name': seg[:80], 'qty': (qm.group(1) + qm.group(2)) if qm else '',
                 'budget': (bm.group(1) + '万元') if bm else ''}]
    out = []
    for i, m in enumerate(marks):
        s = m.end()
        e = marks[i + 1].start() if i + 1 < len(marks) else len(seg)
        t = seg[s:e].strip(' ：:　、.')
        if len(t) < 8:
            continue
        if NOISE.match(t):
            continue
        bm = RE_BUD_IN.search(t)
        qm = RE_QTY.search(t)
        out.append({
            'name': t[:80],
            'qty': (qm.group(1) + qm.group(2)) if qm else '',
            'budget': (bm.group(1) + '万元') if bm else '',
        })
        if len(out) >= 12:
            break
    return out


def cut(text, start_re):
    """从起始锚点截到下一个同级标题，返回清理后的文本"""
    t = glue(text or '')
    m = start_re.search(t)
    if not m:
        return ''
    s = m.end()
    e = P_END.search(t, s)
    end = e.start() if (e and e.start() - s >= 120) else min(len(t), s + MAXLEN)
    if end <= s:
        end = min(len(t), s + MAXLEN)
    seg = t[s:end]
    seg = re.sub(r'\s*[|｜]\s*', ' ', seg)
    seg = re.sub(r'\s+', ' ', seg).strip(' ：:　')
    if len(seg) < MINLEN:
        return ''
    if NOISE.match(seg):
        return ''
    if len(seg) > MAXLEN:
        seg = seg[:MAXLEN]
    return seg


def main():
    db = sqlite3.connect(DB)
    where = 'biddable=1'
    if SCOPE == 'fit':
        where += ' AND bid_fit=1'
    if ONLY_DM:
        where += " AND dm_code='%s'" % ONLY_DM.replace("'", '')
    rows = db.execute(
        'SELECT dm_code,title,raw_content,qualification,evaluation,purchase_items FROM projects WHERE ' + where
    ).fetchall()

    nq = ne = ni = 0
    samples = []
    for dm, title, raw, qual, eva, pit in rows:
        if not raw or len(raw) < 100:
            continue
        upd = {}
        if not (pit and str(pit).strip()):
            seg = cut(raw, I_START)
            if seg:
                its = [x for x in split_items(seg) if not BAD_ITEM.search(x['name'])]
                if its and not BAD_ITEM.search(its[0]['name']):
                    upd['purchase_items'] = json.dumps(its, ensure_ascii=False)
                    ni += 1
        if not (qual and str(qual).strip()):
            v = cut(raw, P_START)
            if v:
                upd['qualification'] = v
                nq += 1
        if not (eva and str(eva).strip()):
            v = cut(raw, E_START)
            if v:
                upd['evaluation'] = v
                ne += 1
        if upd:
            if len(samples) < 12:
                samples.append((dm, title, upd))
            if not DRY:
                sets = ','.join(k + '=?' for k in upd)
                db.execute('UPDATE projects SET ' + sets + ' WHERE dm_code=?',
                           list(upd.values()) + [dm])
    if not DRY:
        db.commit()

    print('范围: %s | 扫描 %d 条' % (where, len(rows)))
    print('资格要求补抽: %d 条' % nq)
    print('评分标准补抽: %d 条' % ne)
    print('采购标的补抽: %d 条' % ni)
    print('模式: %s' % ('预演(未写库)' if DRY else '已写库'))
    print()
    for dm, title, upd in samples[:8]:
        print('--- %s | %s' % (dm, title[:34]))
        for k, v in upd.items():
            print('    [%s] %s…' % (k, v[:110]))


if __name__ == '__main__':
    main()
