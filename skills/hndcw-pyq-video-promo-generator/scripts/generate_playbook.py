# -*- coding: utf-8 -*-
"""生成朋友圈私域推广发布操作手册 + 每日报数模板"""
import os, re
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

OUT_PATH = "D:/workBuddy/Delivery/workBuddy/朋友圈私域推广_发布操作手册与每日报数.docx"
MINGER_DIR = "D:/workBuddy/Delivery/workBuddy/鸣儿.全域智能助手，朋友圈私域推广"
BANG_DIR = "D:/workBuddy/Delivery/workBuddy/榜上有鸣：朋友圈私域推广"

def set_run_font(run, size=11, bold=False, color=(0,0,0)):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(*color)
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    rFonts.set(qn('w:eastAsia'), '微软雅黑')

def add_title(doc, text, level=1):
    p = doc.add_heading(level=level)
    r = p.add_run(text)
    set_run_font(r, 18 if level==1 else 14, bold=True, color=(0,80,150) if level==1 else (0,0,0))
    return p

def add_para(doc, text, size=11, bold=False, color=(0,0,0), align="left"):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run_font(r, size, bold, color)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p

def add_bullet(doc, text, size=11):
    p = doc.add_paragraph(style='List Bullet')
    r = p.add_run(text)
    set_run_font(r, size)

def add_code_block(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run_font(r, 11, color=(50,50,50))
    p.paragraph_format.left_indent = Inches(0.3)
    p.paragraph_format.space_after = Pt(8)

def collect_minger_days():
    days = {}
    for f in os.listdir(MINGER_DIR):
        m = re.match(r'minger_09_(\d{2})_(koubo|talk)\.mp4', f)
        if m:
            day = int(m.group(1))
            style = "口播版" if m.group(2)=="koubo" else "脱口秀版"
            days[day] = (f, style)
    return days

def collect_bang_days():
    days = {}
    for f in os.listdir(BANG_DIR):
        m = re.match(r'bang_09_(\d{2})\.mp4', f)
        if m:
            day = int(m.group(1))
            days[day] = f
    return days

def main():
    doc = Document()
    # 标题
    add_para(doc, "朋友圈私域推广", 20, bold=True, align="center")
    add_para(doc, "发布操作手册 + 每日报数模板", 16, bold=True, color=(0,100,200), align="center")
    add_para(doc, "适用周期：2026 年 9 月 1 日 - 9 月 30 日", 11, align="center")
    doc.add_paragraph()

    # 一、铁律速查
    add_title(doc, "一、铁律速查（发布前必看）", 1)
    add_bullet(doc, "鸣儿对外动作一律说「找项目」，禁用「查项目」。")
    add_bullet(doc, "鸣儿项目来源必须完整说「招标网 / 公共资源网 / 政府采购网」，不准简化。")
    add_bullet(doc, "鸣儿数据更新用「全量更新上线」，禁用「每天几百条」。")
    add_bullet(doc, "每天视频、封面、配音脚本、朋友圈文案必须都不一样。")
    add_bullet(doc, "两产品素材分仓：鸣儿与榜上有鸣分别进入各自 D 盘文件夹，不混放。")
    doc.add_paragraph()

    # 二、发布节奏
    add_title(doc, "二、发布节奏", 1)
    add_bullet(doc, "每天 2 条朋友圈：上午/下午各 1 条，或集中晚上发布。建议早 7:30-8:30、晚 20:00-21:30。")
    add_bullet(doc, "鸣儿 1 条 + 榜上有鸣 1 条，避免同产品连发刷屏。")
    add_bullet(doc, "发布时先复制 docx 里的「朋友圈文案」，再上传对应日期的 mp4 视频。")
    add_bullet(doc, "视频发出去后，在评论区补一条承接钩子，引导私聊或搜索。")
    doc.add_paragraph()

    # 三、每日发布 SOP
    add_title(doc, "三、每日发布 SOP（5 分钟/天）", 1)
    steps = [
        "打开本手册尾部的「9 月发布日历速查表」，确认今日鸣儿/榜上有鸣对应的视频文件名。",
        "从 D 盘对应文件夹复制视频文件到手机（或电脑直接发朋友圈）。",
        "从 docx《鸣儿/榜上有鸣 9月朋友圈私域推广排期》复制今日「朋友圈文案」。",
        "发朋友圈：粘贴文案 → 上传视频 → 发布。",
        "发布后 3 分钟内，在评论区发一条承接钩子（见第六节）。",
        "晚上 22:00 前按第七节格式填写每日报数，发到工作群。"
    ]
    for i, s in enumerate(steps, 1):
        add_bullet(doc, f"{i}. {s}")
    doc.add_paragraph()

    # 四、每日报数模板
    add_title(doc, "四、每日报数模板", 1)
    add_para(doc, "每天 22:00 前按以下固定格式报数，便于追踪各渠道效果。", 11)
    add_code_block(doc, "【9 月 X 日 朋友圈私域推广报数】\nvideo= 0 条\nminiapp= 0 次\nhndcw= 0 次\nold= 0 次\n备注：")
    add_para(doc, "字段说明：", 11, bold=True)
    add_bullet(doc, "video：当天发布的视频数（鸣儿+榜上有鸣合计，正常=2）。")
    add_bullet(doc, "miniapp：榜上有鸣小程序通过搜一搜/朋友圈带来的访问/新增次数（从小程序后台读取）。")
    add_bullet(doc, "hndcw：鸣儿/hndcw.com 网站访问次数（从网站统计/服务器日志读取）。")
    add_bullet(doc, "old：海南铎鸣老站/服务号阅读或互动次数（从老站后台/公众号后台读取）。")
    add_bullet(doc, "备注：异常、爆款、用户反馈、需跟进事项。")
    doc.add_paragraph()

    # 五、素材路径速查
    add_title(doc, "五、素材路径速查", 1)
    add_code_block(doc, f"鸣儿素材：{MINGER_DIR}\n榜上有鸣素材：{BANG_DIR}")
    doc.add_paragraph()

    # 六、评论钩子 SOP
    add_title(doc, "六、评论承接钩子 SOP", 1)
    add_para(doc, "每条朋友圈发完后，用主号在评论区补充一条钩子，降低硬广感，提升转化率。", 11)
    add_para(doc, "鸣儿用钩子：", 12, bold=True)
    hooks_minger = [
        "刚把今天三网项目整理完，想要完整档案的私我「找项目」。",
        "项目金额、业主、代理、电话都在档案里，点进去自己看。",
        "不是项目难找，是信息太散；用这个整理好的入口确实省时间。"
    ]
    for h in hooks_minger:
        add_bullet(doc, h)
    add_para(doc, "榜上有鸣用钩子：", 12, bold=True)
    hooks_bang = [
        "微信搜一搜「榜上有鸣」就能让孩子试答几题。",
        "不补课、不逼学，每天答几题养成习惯。",
        "我家娃答了一周，现在主动要pk班级榜。"
    ]
    for h in hooks_bang:
        add_bullet(doc, h)
    doc.add_paragraph()

    # 七、9月发布日历速查表
    add_title(doc, "七、9 月发布日历速查表", 1)
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Light Grid Accent 1'
    hdr = table.rows[0].cells
    headers = ["日期", "鸣儿视频", "鸣儿风格", "榜上有鸣视频", "备注"]
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            set_run_font(p.runs[0], 11, bold=True, color=(255,255,255))
        hdr[i]._tc.get_or_add_tcPr().append(
            docx.oxml.parse_xml(r'<w:shd {} w:fill="2F5496"/>'.format(docx.oxml.ns.nsdecls('w'))))
    minger_days = collect_minger_days()
    bang_days = collect_bang_days()
    for day in range(1, 31):
        row = table.add_row().cells
        row[0].text = "9 月 {} 日".format(day)
        m_video, m_style = minger_days.get(day, ("-", "-"))
        b_video = bang_days.get(day, "-")
        row[1].text = m_video
        row[2].text = m_style
        row[3].text = b_video
        row[4].text = ""
        for cell in row:
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if p.runs:
                    set_run_font(p.runs[0], 10)
    doc.save(OUT_PATH)
    print("DOCX ->", OUT_PATH)

if __name__ == "__main__":
    main()
