# -*- coding: utf-8 -*-
"""
可投标池 · 业务线过滤器
=========================
用途：把「可投标」池（biddable=1）里铎鸣投不了的噪声标滤掉，只留能力线内的标。

判定逻辑（排除优先，宁缺毋滥）：
  1) 命中"中介类/工程货物类"排除词  -> bid_fit=0
  2) 否则命中"能力线"白名单        -> bid_fit=1
  3) 都不命中                      -> bid_fit=0
  判定依据写入 fit_reason，便于人工复核放行。

用法（服务器 /www/wwwroot/hndcw.com）：
  DRY=1  python3 tools/classify_biddable.py        # 预演，不写库
          python3 tools/classify_biddable.py        # 正式写库
  LIMIT=50 DRY=1 python3 tools/classify_biddable.py # 只跑前 50 条

铁律：不编造数据，只做分类打标。
"""
import os
import re
import sqlite3
import sys

DB = os.environ.get("HNCW_DB", "/www/wwwroot/hndcw.com/data/hndcw.db")
DRY = os.environ.get("DRY") == "1"
LIMIT = int(os.environ.get("LIMIT", "0") or 0)

# ---------------------------------------------------------------- 排除词表
# A. 中介类：业主在找"帮它招标/编预算/监理/设计"的中介，不是找投标人
EX_MIDDLE = [
    "招标代理", "代理机构", "代理单位", "代理公司", "遴选代理", "招标代理机构",
    "预算编制", "预算审核", "结算审核", "造价咨询", "造价服务", "工程量清单",
    "工程监理", "监理单位", "监理工作", "监理服务", "代建",
    "工程设计", "设计工作", "设计单位", "设计服务", "方案设计", "施工图",
    "工程测绘", "勘察", "地勘",
]

# B. 工程施工 / 硬件货物 / 后勤物资：铎鸣无资质、无供货能力
EX_HARD = [
    "工程施工", "施工及", "施工招标", "施工单位", "施工总承包", "改造工程", "扩建工程",
    "修缮", "维修", "维保工程", "补漏", "防水", "装修", "装饰", "硬板化", "硬化",
    "除险加固", "加固工程", "危桥", "路面", "道路施工", "养护工程",
    "绿化", "苗木", "林木采伐", "采伐", "造林", "肥料", "有机肥", "农药", "饲料",
    "食材", "食品", "营养餐", "营养改善计划", "食堂", "副食品",
    "公务用车", "车辆采购", "车辆维修", "车采购", "油料", "船艇", "执法船", "船舶",
    "服装", "被服", "鞋", "标识牌", "展馆", "搭建", "会展", "博览会", "展厅",
    "印刷", "出版物", "图书采购", "农家书屋", "课桌椅", "家具", "办公用品",
    "空调", "电梯", "消防", "路灯", "变压器", "供电", "配电", "发电机",
    "监控摄像头", "摄像头采购", "设备采购", "设备更新", "设备购置", "仪器采购",
    "货物采购", "供货商", "供货单位", "采购安装", "材料采购", "物资采购",
    "污水处理", "污水处理厂", "水库", "水利", "管网", "供水工程", "河道", "疏浚",
    "公墓", "殡仪", "陵园", "殡葬",
    "体检", "药品", "试剂", "医疗器械", "诊疗",
    "审计服务", "审计机构", "法律服务", "法律顾问", "劳务派遣", "保安服务",
    "物业服务", "保洁", "垃圾清运", "食堂承包",
    "质量检测", "工程检测", "食品检测", "药品检验", "农产品检测", "水质检测",
    "林木收购", "收购单位", "招商推介", "推介活动", "演出", "联谊", "赛事承办",
    "体检项目", "健康体检",
]

# C. 通用兜底：明确是"工程建设类"标的
EX_TYPE = ["工程招标", "施工标", "货物标", "材料标"]

# D. 已结束：结果/成交/中标类公告，进去已经投不了
EX_DONE = [
    "中选结果", "成交结果", "中标结果", "结果公示", "结果的公示", "结果公告",
    "中标公示", "中标公告", "成交公告", "成交公示", "中选公示", "遴选结果",
    "比选结果", "中标候选人", "废标", "流标", "终止招标", "更正公告", "变更公告",
    "澄清", "答疑", "补充公告", "排查存在问题", "通报批评", "意见建议的公告",
    "征求意见", "线索征集",
    # 2026-09-18 补：结果型公告的其余写法（首轮漏网，"中选公告"最典型）
    "中选公告", "成交结果公告", "中标结果公告", "中选通知书", "中标通知书",
    "关于确定", "确定为", "评选结果", "评审结果", "排名公示", "候选人公示",
]

# ---------------------------------------------------------------- 能力线白名单
# 铎鸣三条能力线：社会调查与统计 / 第三方评估与测评 / 数据信息化与咨询研究
W_SURVEY = [
    "调查", "民意", "问卷", "访谈", "暗访", "普查", "抽样", "摸底", "走访",
    "统计调查", "数据采集", "数据收集", "入户", "需求调查",
]
W_EVAL = [
    "评估", "评价", "测评", "考核", "绩效评价", "绩效评估", "满意度",
    "第三方评估", "风险评估", "影响评价", "核验", "核查", "评查",
    "监测评估", "验收评估", "认定评估", "等级保护测评",
]
W_DATA = [
    "数据治理", "数据处理", "数据分析", "数据库", "数据平台", "数据服务",
    "信息化", "信息系统", "系统运维", "系统维护", "平台运维", "平台维护",
    "软件开发", "软件维护", "软件开发服务", "网络安全", "技术支持服务",
    "智慧", "数字化",
]
W_CONSULT = [
    "课题研究", "课题", "规划编制", "方案编制", "可行性研究", "咨询",
    "智库", "调研报告", "指数", "编制", "技术服务", "政策研究",
]
W_PUBLIC = [
    "残疾人", "养老服务", "养老评估", "社会工作", "社工", "未成年人保护",
    "宣传服务", "宣传活动", "培训服务", "文明城市", "乡村振兴规划",
]

GROUPS = [
    ("调查统计", W_SURVEY),
    ("评估测评", W_EVAL),
    ("数据信息化", W_DATA),
    ("咨询研究", W_CONSULT),
    ("民生服务", W_PUBLIC),
]

ALL_EX = EX_MIDDLE + EX_HARD + EX_TYPE + EX_DONE


def classify(title):
    """返回 (bid_fit, reason)。1=能力线内可投，0=噪声"""
    t = (title or "").strip()
    if not t:
        return 0, "空标题"

    # 已结束类优先判定（最高优先级）
    done = [w for w in EX_DONE if w in t]
    if done:
        return 0, "已结束:" + "、".join(done[:2])

    hits = [w for w in ALL_EX if w in t]
    if hits:
        return 0, "排除:" + "、".join(hits[:3])

    for gname, words in GROUPS:
        g = [w for w in words if w in t]
        if g:
            return 1, "%s(%s)" % (gname, "、".join(g[:2]))

    return 0, "未命中能力线"


def ensure_cols(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)")}
    if "bid_fit" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN bid_fit INTEGER DEFAULT 0")
    if "fit_reason" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN fit_reason TEXT")
    conn.commit()


def main():
    conn = sqlite3.connect(DB, timeout=60)
    conn.execute("PRAGMA busy_timeout=60000")
    if not DRY:
        ensure_cols(conn)

    extra = os.environ.get("WHERE_EXTRA", "").strip()
    sql = "SELECT id,title FROM projects WHERE " + (extra if extra else "biddable=1")
    if LIMIT:
        sql += " LIMIT %d" % LIMIT
    rows = conn.execute(sql).fetchall()

    n_fit = n_noise = n_chg = 0
    buckets = {}
    samples = []
    for pid, title in rows:
        fit, reason = classify(title)
        buckets.setdefault(reason.split("(")[0].split(":")[0], 0)
        buckets[reason.split("(")[0].split(":")[0]] += 1
        if fit:
            n_fit += 1
            if len(samples) < 25:
                samples.append((title, reason))
        else:
            n_noise += 1

        if not DRY:
            conn.execute("UPDATE projects SET bid_fit=?, fit_reason=? WHERE id=?", (fit, reason, pid))
            n_chg += 1

    if not DRY:
        conn.commit()

    print("=" * 62)
    print("可投标池业务线过滤 · %s" % ("预演(DRY)" if DRY else "正式写库"))
    print("=" * 62)
    print("样本总数   : %d" % len(rows))
    print("能力线内   : %d  (%.1f%%)" % (n_fit, 100.0 * n_fit / max(len(rows), 1)))
    print("噪声/无关  : %d  (%.1f%%)" % (n_noise, 100.0 * n_noise / max(len(rows), 1)))
    if not DRY:
        print("实际写库   : %d 条" % n_chg)
    print("-" * 62)
    print("判定分布 TOP:")
    for k, v in sorted(buckets.items(), key=lambda x: -x[1])[:14]:
        print("  %-16s %d" % (k, v))
    print("-" * 62)
    print("能力线内样例:")
    for t, r in samples[:20]:
        print("  [%s] %s" % (r, t[:46]))


if __name__ == "__main__":
    main()
