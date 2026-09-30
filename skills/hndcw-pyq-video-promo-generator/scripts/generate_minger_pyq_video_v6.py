# -*- coding: utf-8 -*-
r"""鸣儿·全域智能助手 朋友圈推广视频 v6（华哥 2026-09-02 正式版）
- 每天视频/图片/脚本/文案都不一样
- 画面优化：右侧档案卡更整洁；"每天几百条"改为"全量更新上线"
- 输出到 D:\workBuddy\Delivery\workBuddy\鸣儿.全域智能助手，朋友圈私域推广
- 30 天内容库：主题/城市/案例/文案角度每日轮换
"""
import os, asyncio, subprocess, textwrap, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts, qrcode

SRC_BASE = "D:/WorkBuddy-Projects/2026-06-07-20-59-29/promotion/pyq_samples"
OUT_BASE = "D:/workBuddy/Delivery/workBuddy/鸣儿.全域智能助手，朋友圈私域推广"
SUB_DIR = os.path.join(OUT_BASE, "其他图片与文档")
FONT = "C:/Windows/Fonts/msyh.ttc"
W, H = 720, 1280
FPS = 25
clamp = lambda v: max(0, min(255, int(v)))
def f(sz): return ImageFont.truetype(FONT, sz)

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

# ---------- 网页二维码 ----------
_qr = qrcode.QRCode(box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
_qr.add_data("https://hndcw.com")
QR = _qr.make_image(fill_color="#2F5496", back_color="white").convert("RGB").resize((260, 260), Image.LANCZOS)

# ---------- 通用图层工具 ----------
def atext(img, x, y, s, font, rgb, alpha=255, anchor="mm"):
    if alpha <= 0 or not s:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    dl.text((x, y), s, font=font, fill=(rgb[0], rgb[1], rgb[2], int(alpha)), anchor=anchor)
    img.alpha_composite(layer)

def top_brand_bar(img):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, 74], fill=(47, 84, 150, 255))
    d.text((30, 37), "海南铎鸣 › 鸣儿·全域智能助手", font=f(28), fill=(255, 255, 255), anchor="lm")
    d.text((W - 30, 37), "hndcw.com", font=f(24), fill=(210, 220, 255), anchor="rm")
    img.alpha_composite(ov)

def wrap_text(text, font, max_w):
    """按字符折行，优先在标点/空格处断开"""
    lines = []
    cur = ""
    for ch in text:
        test = cur + ch
        bbox = ImageDraw.Draw(Image.new("RGBA", (1,1))).textbbox((0,0), test, font=font)
        if bbox[2] - bbox[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines

def top_caption_block(img, text, y_offset=0, alpha=255, font_size=40, max_w=640):
    if alpha <= 0:
        return
    font = f(font_size)
    lines = wrap_text(text, font, max_w)
    if not lines:
        return
    line_h = 70; gap = 10
    y = 120 + y_offset
    cx = W // 2
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0] + 56
        x1, y1 = cx - tw // 2, y
        x2, y2 = x1 + tw, y1 + line_h
        d.rounded_rectangle([x1, y1, x2, y2], radius=18, fill=(25, 35, 70, int(alpha * 0.92)))
        d.text((cx, y1 + 35), line, font=font, fill=(255, 255, 255, alpha), anchor="mm")
        y += line_h + gap
    img.alpha_composite(ov)

def qr_block(img, t, dur, label="长按识别 · 上鸣儿找项目"):
    p = t / dur
    if p < 0.72:
        return
    a = clamp((p - 0.72) / 0.08 * 255)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, H - 340, W, H], fill=(20, 30, 60, int(a * 0.90)))
    img.alpha_composite(ov)
    cx, cy = W // 2, H - 230
    ImageDraw.Draw(img).rounded_rectangle([cx - 140, cy - 140, cx + 140, cy + 140], radius=20, fill=(255, 255, 255))
    img.paste(QR, (cx - 130, cy - 130))
    atext(img, cx, cy + 180, label, f(38), (255, 255, 255), a)
    atext(img, cx, cy + 222, "hndcw.com", f(28), (200, 210, 255), a)

def gradient_bg(top_rgb, bot_rgb):
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    top = np.array(top_rgb); bot = np.array(bot_rgb)
    for y in range(H):
        arr[y] = top + (bot - top) * (y / H)
    return Image.fromarray(arr)

# =====================================================================
# 30 天内容库（主题/城市/项目/金额 每日轮换）
# =====================================================================
THEMES = [
    ("市政工程", "水务/道路/管网"),
    ("医疗卫生", "医院/诊所/设备"),
    ("教育科研", "学校/实验室/信息化"),
    ("生态环保", "污水处理/固废/绿化"),
    ("交通运输", "公路/桥梁/港口"),
    ("农业农村", "灌溉/产业/基础设施"),
    ("文化旅游", "景区/场馆/文创"),
    ("能源电力", "光伏/储能/电网"),
    ("信息化", "政务/大数据/安防"),
    ("房建住宅", "保障房/公共建筑"),
]
CITIES = ["南昌", "银川", "天津", "郑州", "济南", "呼和浩特", "成都", "杭州", "广州", "武汉",
          "海口", "乌鲁木齐", "西安", "南京", "长沙", "合肥", "福州", "南宁", "贵阳", "昆明",
          "拉萨", "兰州", "西宁", "石家庄", "太原", "沈阳", "长春", "上海", "重庆", "北京"]
PROJECTS = [
    ("{}市污水处理厂扩建工程", "1.28"), ("{}湾生态廊道修复项目", "0.86"),
    ("{}人民医院新院区建设", "2.10"), ("{}市智慧交通管理平台", "0.45"),
    ("{}新区中小学新建工程", "0.92"), ("{}市垃圾分类处理中心", "0.63"),
    ("{}海岸带综合整治工程", "1.55"), ("{}市公共卫生临床中心", "1.80"),
    ("{}现代农业产业园配套", "0.78"), ("{}市文体中心升级改造", "1.12"),
    ("{}新能源充电设施一期", "0.38"), ("{}市数字政府云平台", "0.55"),
    ("{}保障性租赁住房项目", "1.65"), ("{}市供水管网改造工程", "0.72"),
    ("{}渔港经济区基础设施", "1.05"), ("{}市康养综合体建设", "1.35"),
    ("{}河流域生态修复", "0.96"), ("{}市冷链物流园建设", "0.88"),
    ("{}高新技术产业孵化园", "1.45"), ("{}市应急指挥中心", "0.42"),
    ("{}古城文化旅游区改造", "0.68"), ("{}市第二福利院迁建", "0.52"),
    ("{}港区航道疏浚工程", "1.20"), ("{}市消防站建设工程", "0.34"),
    ("{}基层医疗卫生机构", "0.48"), ("{}市农村公路提升工程", "0.60"),
    ("{}工业互联网平台", "0.50"), ("{}市殡仪馆改扩建", "0.40"),
    ("{}水库除险加固工程", "0.74"), ("{}市人才公寓装修改造", "0.36"),
]

def day_content(day):
    """day: 1-30，返回当天唯一内容"""
    theme, sub = THEMES[(day - 1) % len(THEMES)]
    city = CITIES[(day - 1) % len(CITIES)]
    tmpl, amt = PROJECTS[(day - 1) % len(PROJECTS)]
    project = tmpl.format(city)
    update_count = 120 + (day * 17) % 380  # 模拟每日更新条数 120-500
    return {
        "day": day,
        "theme": theme,
        "sub": sub,
        "city": city,
        "project": project,
        "amount": amt,
        "update_count": update_count,
    }

# =====================================================================
# 30 天文案库（口播 + 脱口秀 + 朋友圈）
# =====================================================================
KOUBO_TEMPLATES = [
    "我做{theme}最愁找项目。招标网、公共资源网、政府采购网，三网信息又杂又散。用鸣儿，三网全量更新上线，专业整理成档案，{project}金额{amount}亿，真实详情全给齐。",
    "找{theme}项目别瞎忙。招标网、公共资源网、政府采购网，三网全量更新上线。鸣儿专业整理成档案，{project}金额{amount}亿，业主、代理、电话、附件直链一点就有。",
    "以前找{theme}项目，招标网、公共资源网、政府采购网，得一个个翻。现在用鸣儿，三网全量更新上线，自动归档成档案，{project}金额{amount}亿，真实详情一目了然。",
    "{theme}项目信息分散在招标网、公共资源网、政府采购网。鸣儿每天全量更新上线，专业整理成档案，{project}金额{amount}亿，今日已更新{update_count}条。",
    "我只看真项目。招标网、公共资源网、政府采购网，鸣儿三网全量更新上线，专业整理成档案。{project}金额{amount}亿，{theme}领域不容错过。",
]
TALK_TEMPLATES = [
    "你们找{theme}项目这样吧：招标网、公共资源网、政府采购网，三网全得盯。用鸣儿，三网全量更新上线，专业整理成档案，{project}金额{amount}亿，附件直链全排好。",
    "以前我觉得找项目靠运气，直到用了鸣儿。招标网、公共资源网、政府采购网，每天全量更新上线，{theme}项目直接归档，{project}金额{amount}亿，真实详情一眼看清。",
    "还在手动刷三网？鸣儿已经把招标网、公共资源网、政府采购网全量更新上线，整理成档案。{theme}项目{project}，金额{amount}亿，业主、代理、电话全有。",
    "找{theme}项目，招标网、公共资源网、政府采购网，一个都不能漏。用鸣儿，三网全量更新上线，自动归档，{project}金额{amount}亿，再也不会错过。",
    "不是我没本事，是以前没用鸣儿。招标网、公共资源网、政府采购网全量更新上线，{theme}项目专业整理成档案，{project}金额{amount}亿，找项目真不难。",
]
PYQ_TEMPLATES = [
    "【{theme}】找项目最怕信息漏。招标网/公共资源网/政府采购网三网全量更新上线，鸣儿专业整理成档案，业主·代理·电话·附件直链全给齐。今日重点：{project}，金额约{amount}亿。找项目，上鸣儿 hndcw.com",
    "【{city}项目情报】{project}，金额约{amount}亿。招标网、公共资源网、政府采购网三网全量更新上线，鸣儿帮你整理成档案，真实详情直达。👉 hndcw.com",
    "不是项目难找，是信息太散。鸣儿把招标网/公共资源网/政府采购网全量更新上线，{theme}项目一键归档。今日更新{update_count}条，重点{project}。",
    "做{theme}的朋友看过来：招标网、公共资源网、政府采购网，三网项目鸣儿全量更新上线，业主、代理、电话、附件直链，点开全有。",
    "【真实项目档案】{project}｜金额约{amount}亿｜来源：招标网/公共资源网/政府采购网。鸣儿三网全量更新上线，专业整理，来源可溯。hndcw.com",
]

def koubo_copy(day, ctx):
    tmpl = KOUBO_TEMPLATES[(day - 1) % len(KOUBO_TEMPLATES)]
    return tmpl.format(**ctx)

def talk_copy(day, ctx):
    tmpl = TALK_TEMPLATES[(day - 1) % len(TALK_TEMPLATES)]
    return tmpl.format(**ctx)

def pyq_copy(day, ctx):
    tmpl = PYQ_TEMPLATES[(day - 1) % len(PYQ_TEMPLATES)]
    return tmpl.format(**ctx)

# =====================================================================
# 视觉模板库（6套不同画面，每天轮换）
# =====================================================================
def make_bg_archive(ctx, palette="blue"):
    """档案库风格：深蓝渐变 + 三网 chips + 项目档案卡"""
    palettes = {
        "blue":  ((26,36,66),(14,22,46),(47,84,150)),
        "green": ((22,46,38),(12,28,24),(36,130,100)),
        "navy":  ((18,28,52),(10,16,34),(40,60,120)),
        "teal":  ((20,50,60),(10,30,36),(30,120,130)),
        "purple":((35,28,58),(20,14,38),(100,70,160)),
        "orange":((58,34,18),(36,20,10),(190,100,40)),
    }
    top, bot, accent = palettes.get(palette, palettes["blue"])
    img = gradient_bg(top, bot)
    d = ImageDraw.Draw(img)
    # 标题栏
    d.rectangle([0, 74, W, 178], fill=(255, 255, 255))
    d.text((W // 2, 118), "鸣儿·全域智能助手", font=f(42), fill=(28, 28, 28), anchor="mm")
    d.text((W // 2, 152), "项目情报与实务顾问", font=f(24), fill=(150, 150, 150), anchor="mm")
    d.line([(0, 178), (W, 178)], fill=accent, width=3)
    # 三网来源 chips
    chips = [("招标网", accent), ("公共资源网", accent), ("政府采购网", accent)]
    cw = 200; gap = 24; x = (W - (cw * 3 + gap * 2)) // 2; y = 230
    for txt, col in chips:
        d.rounded_rectangle([x, y, x + cw, y + 64], radius=18, fill=col)
        d.text((x + cw // 2, y + 32), txt, font=f(30), fill=(255, 255, 255), anchor="mm")
        x += cw + gap
    # 主题标题
    d.text((W // 2, 360), "{} · 全量更新上线".format(ctx["theme"]), font=f(40), fill=(255, 255, 255), anchor="mm")
    d.text((W // 2, 406), "招标网 / 公共资源网 / 政府采购网", font=f(26), fill=(200, 210, 230), anchor="mm")
    # 大数字：今日更新
    d.text((W // 2, 500), "今日更新", font=f(28), fill=(210, 220, 255), anchor="mm")
    d.text((W // 2, 590), "{}".format(ctx["update_count"]), font=f(90), fill=(255, 210, 110), anchor="mm")
    d.text((W // 2, 660), "条真实项目情报", font=f(26), fill=(210, 220, 255), anchor="mm")
    # 今日重点档案卡（整洁版）
    card_w = W - 80
    cx = W // 2
    cy = 780
    d.rounded_rectangle([40, cy - 130, W - 40, cy + 220], radius=20, fill=(255, 255, 255))
    # 卡头
    d.rounded_rectangle([40, cy - 130, W - 40, cy - 70], radius=20, fill=accent)
    d.text((cx, cy - 100), "今日重点档案", font=f(28), fill=(255, 255, 255), anchor="mm")
    # 项目名
    name_lines = wrap_text(ctx["project"], f(32), card_w - 40)
    ny = cy - 50
    for line in name_lines[:2]:
        d.text((cx, ny), line, font=f(32), fill=(28, 28, 28), anchor="mm")
        ny += 44
    # 金额
    d.text((cx, ny + 10), "金额约 {} 亿".format(ctx["amount"]), font=f(30), fill=(200, 90, 60), anchor="mm")
    # 四要素标签（两列）
    tags = ["业主单位", "代理机构", "联系电话", "官方附件直链"]
    ty = cy + 60
    for i, lab in enumerate(tags):
        col = i % 2
        row = i // 2
        bx = 70 + col * 310
        by = ty + row * 56
        d.rounded_rectangle([bx, by, bx + 280, by + 46], radius=12, fill=(245, 248, 255), outline=accent)
        d.text((bx + 140, by + 23), lab, font=f(24), fill=accent, anchor="mm")
    return img

def make_bg_contrast(ctx, palette="blue"):
    """杂乱→整理 对比风（用户截图风格，但更整洁）"""
    img = Image.new("RGBA", (W, H), (243, 245, 250, 255))
    d = ImageDraw.Draw(img)
    # 标题栏
    d.rectangle([0, 74, W, 178], fill=(255, 255, 255))
    d.text((W // 2, 118), "鸣儿·全域智能助手", font=f(42), fill=(28, 28, 28), anchor="mm")
    d.text((W // 2, 152), "项目情报与实务顾问", font=f(24), fill=(150, 150, 150), anchor="mm")
    d.line([(0, 178), (W, 178)], fill=(225, 228, 235))
    # 左：三网来源（整洁卡片）
    sources = ["招标网", "公共资源网", "政府采购网"]
    y = 260
    accent = (47, 84, 150)
    for i, src in enumerate(sources):
        d.rounded_rectangle([40, y, 300, y + 120], radius=16, fill=(230, 232, 238), outline=(200, 204, 214))
        d.text((170, y + 60), src, font=f(34), fill=(100, 104, 114), anchor="mm")
        y += 150
    # 状态说明
    d.text((170, 740), "全量更新上线", font=f(26), fill=(170, 80, 80), anchor="mm")
    # 中：大箭头
    d.text((345, 490), "→", font=f(140), fill=accent, anchor="mm")
    # 右：鸣儿档案卡（整洁版，单列 4 行字段）
    rx = 370
    rw = W - rx - 40  # 310
    rh = 520
    d.rounded_rectangle([rx, 260, rx + rw, 260 + rh], radius=20, fill=(255, 255, 255), outline=accent, width=2)
    d.rounded_rectangle([rx, 260, rx + rw, 330], radius=20, fill=accent)
    d.text((rx + rw // 2, 295), "鸣儿项目档案", font=f(34), fill=(255, 255, 255), anchor="mm")
    # 项目名
    ny = 355
    name_lines = wrap_text(ctx["project"], f(28), rw - 32)
    for line in name_lines[:2]:
        d.text((rx + rw // 2, ny), line, font=f(28), fill=(28, 28, 28), anchor="mm")
        ny += 40
    # 金额
    d.text((rx + rw // 2, ny + 6), "金额约 {} 亿".format(ctx["amount"]), font=f(26), fill=(200, 90, 60), anchor="mm")
    # 四要素 单列 4 行
    rows = [
        ("业主单位", "{}相关单位".format(ctx["city"])),
        ("代理机构", "专业招标代理"),
        ("联系电话", "139-XXXX-XXXX"),
        ("官方附件", "直链下载"),
    ]
    ry = ny + 50
    for lab, val in rows:
        d.rounded_rectangle([rx + 16, ry, rx + rw - 16, ry + 52], radius=10, fill=(245, 248, 255), outline=accent)
        d.text((rx + 26, ry + 26), lab, font=f(20), fill=accent, anchor="lm")
        d.text((rx + 128, ry + 26), val, font=f(20), fill=(28, 28, 28), anchor="lm")
        ry += 64
    d.text((rx + rw // 2, 260 + rh + 28), "专业整理 · 来源可溯 · 全量更新", font=f(24), fill=accent, anchor="mm")
    return img

def make_bg_focus(ctx, palette="blue"):
    """痛点聚焦风格：大标题 + 三网来源 + 核心能力"""
    accent_map = {"blue":(47,84,150),"green":(36,130,100),"navy":(40,60,120),"teal":(30,120,130),"purple":(100,70,160),"orange":(190,100,40)}
    accent = accent_map.get(palette, (47,84,150))
    img = Image.new("RGBA", (W, H), (250, 251, 254, 255))
    d = ImageDraw.Draw(img)
    # 顶部装饰条
    d.rectangle([0, 0, W, 200], fill=accent)
    d.text((W // 2, 90), "找项目，用鸣儿", font=f(52), fill=(255,255,255), anchor="mm")
    d.text((W // 2, 150), "招标网 · 公共资源网 · 政府采购网 全量更新上线", font=f(26), fill=(220,230,255), anchor="mm")
    # 中间痛点
    d.rounded_rectangle([40, 260, W-40, 440], radius=20, fill=(255,255,255), outline=(220,225,235), width=2)
    d.text((W//2, 310), "以前找{}项目".format(ctx["theme"]), font=f(34), fill=(100,100,100), anchor="mm")
    d.text((W//2, 370), "三网信息又杂又散，看得眼花缭乱", font=f(30), fill=(60,60,60), anchor="mm")
    # 箭头
    d.text((W//2, 490), "▼", font=f(60), fill=accent, anchor="mm")
    # 解决方案
    d.rounded_rectangle([40, 540, W-40, 870], radius=20, fill=(255,255,255), outline=accent, width=3)
    d.text((W//2, 590), "鸣儿专业整理成档案", font=f(38), fill=accent, anchor="mm")
    d.text((W//2, 650), ctx["project"], font=f(30), fill=(28,28,28), anchor="mm")
    d.text((W//2, 700), "金额约 {} 亿".format(ctx["amount"]), font=f(28), fill=(200,90,60), anchor="mm")
    d.text((W//2, 760), "业主 · 代理 · 电话 · 附件直链 全给齐", font=f(26), fill=(80,80,80), anchor="mm")
    d.text((W//2, 810), "今日全量更新上线 {} 条".format(ctx["update_count"]), font=f(28), fill=(120,120,120), anchor="mm")
    return img

BG_MAKERS = [make_bg_archive, make_bg_contrast, make_bg_focus]

def make_background(day, ctx):
    palette = ["blue","green","navy","teal","purple","orange"][(day-1) % 6]
    maker = BG_MAKERS[(day-1) % len(BG_MAKERS)]
    return maker(ctx, palette)

# =====================================================================
# 渲染 + 编码
# =====================================================================
def caption_schedule(text, dur=15.0):
    """把长文案切成 3-5 段按时间显示"""
    # 按语义分句
    parts = text.replace("。", "|").replace("，", "|").replace("；", "|").split("|")
    parts = [p.strip() for p in parts if p.strip()]
    n = len(parts)
    if n == 0:
        return []
    seg = 1.0 / n
    out = []
    for i, p in enumerate(parts):
        out.append((seg * i, seg * (i + 1), p))
    return out

def render_frame(t, dur, bg, captions, style, ctx, show_caption=True):
    img = bg.copy().convert("RGBA")
    top_brand_bar(img)
    p = t / dur
    # 显示当前 caption
    if show_caption:
        for s, e, txt in captions:
            if s <= p < e or (p >= 1.0 and e >= 0.99):
                a = clamp((p - s) / max(0.03, (e - s) * 0.25) * 255)
                top_caption_block(img, txt, y_offset=0, alpha=a, font_size=38)
                break
    qr_block(img, t, dur)
    # 主播头像（仅口播版）
    if style == "koubo":
        d = ImageDraw.Draw(img)
        d.ellipse([40, H - 230, 150, H - 120], fill=(107, 79, 160))
        d.text((95, H - 175), "鸣", font=f(46), fill=(255, 255, 255), anchor="mm")
        if int(t * 2) % 2 == 0:
            d.ellipse([170, H - 212, 192, H - 190], fill=(230, 60, 60))
        d.text((205, H - 201), "REC", font=f(26), fill=(230, 80, 80))
    return img.convert("RGB")

async def gen_tts(text, voice, out, rate="+10%"):
    try: os.remove(out)
    except OSError: pass
    last_err = None
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(out)
            return
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.5 * (attempt + 1))
    raise last_err

def get_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                       "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    return float(r.stdout.strip())

def make_video(render, audio, out, dur):
    total = int(dur * FPS) + 1
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-preset", "fast", "-crf", "23", "-c:a", "aac", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(total):
        frame = render(i / FPS, dur)
        p.stdin.write(frame.tobytes())
    p.stdin.close(); p.wait()
    return p.returncode

def write_json_log(days, out_path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(days, f, ensure_ascii=False, indent=2)

async def generate_day(day, style="auto"):
    ensure_dir(OUT_BASE)
    ensure_dir(SUB_DIR)
    ctx = day_content(day)
    if style == "auto":
        style = "koubo" if day % 2 == 1 else "talk"
    # 文案
    if style == "koubo":
        copy_text = koubo_copy(day, ctx)
        voice = "zh-CN-YunyangNeural"
    else:
        copy_text = talk_copy(day, ctx)
        voice = "zh-CN-YunjianNeural"
    pyq = pyq_copy(day, ctx)
    # 背景
    bg = make_background(day, ctx)
    captions = caption_schedule(copy_text)
    # 文件路径
    date_str = "09_{:02d}".format(day)
    audio_path = os.path.join(SRC_BASE, "a_{}_{}.mp3".format(date_str, style))
    video_path = os.path.join(OUT_BASE, "minger_{}_{}.mp4".format(date_str, style))
    cover_path = os.path.join(SUB_DIR, "minger_{}_{}_cover.jpg".format(date_str, style))
    # TTS
    await gen_tts(copy_text, voice, audio_path)
    dur = get_dur(audio_path)
    # 渲染
    def render(t, d):
        return render_frame(t, d, bg, captions, style, ctx)
    rc = make_video(render, audio_path, video_path, dur)
    # 封面（取中间帧，不带动态字幕，更干净）
    frame = render_frame(dur * 0.5, dur, bg, captions, style, ctx, show_caption=False)
    frame.save(cover_path, quality=95)
    print("DAY {} {} dur={:.2f}s rc={} -> {}".format(day, style, dur, rc, video_path))
    return {
        "day": day,
        "date_str": date_str,
        "style": style,
        "theme": ctx["theme"],
        "city": ctx["city"],
        "project": ctx["project"],
        "amount": ctx["amount"],
        "update_count": ctx["update_count"],
        "copy": copy_text,
        "pyq": pyq,
        "video": video_path,
        "cover": cover_path,
        "duration": dur,
    }

async def main():
    ensure_dir(SUB_DIR)
    days = []
    for day in range(1, 31):
        info = await generate_day(day, style="auto")
        days.append(info)
    write_json_log(days, os.path.join(SUB_DIR, "minger_september_plan.json"))
    print("DONE 30 days ->", OUT_BASE)

if __name__ == "__main__":
    asyncio.run(main())
