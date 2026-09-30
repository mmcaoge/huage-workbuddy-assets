# -*- coding: utf-8 -*-
"""鸣儿·全域智能助手 朋友圈推广视频 v5（华哥 2026-09-02 加固版）
- 仅两风格：口播(koubo) + 脱口秀(talk)，每个风格不同画面背景
- 文案加固：先讲找项目难（招标网/公共资源网/政府采购网 三网又杂又散），再讲鸣儿把三网项目专业整理成档案
- 脱口秀画面去除"脱口秀"字样
- 铁律：鸣儿动作一律"找项目"；项目来源必说完整三网
"""
import os, asyncio, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts, qrcode

BASE = "D:/WorkBuddy-Projects/2026-06-07-20-59-29/promotion/pyq_samples"
FONT = "C:/Windows/Fonts/msyh.ttc"
W, H = 720, 1280
FPS = 25
clamp = lambda v: max(0, min(255, int(v)))
def f(sz): return ImageFont.truetype(FONT, sz)

# ---------- 网页二维码 ----------
_qr = qrcode.QRCode(box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
_qr.add_data("https://hndcw.com")
QR = _qr.make_image(fill_color="#2F5496", back_color="white").convert("RGB").resize((260, 260), Image.LANCZOS)

# ---------- 通用图层工具 ----------
def atext(img, x, y, s, font, rgb, alpha=255, anchor="mm"):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    dl.text((x, y), s, font=font, fill=(rgb[0], rgb[1], rgb[2], int(alpha)), anchor=anchor)
    img.alpha_composite(layer)

def top_brand_bar(img, style_tag_text=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, 74], fill=(47, 84, 150, 255))
    d.text((30, 37), "海南铎鸣 › 鸣儿·全域智能助手", font=f(28), fill=(255, 255, 255), anchor="lm")
    d.text((W - 30, 37), "hndcw.com", font=f(24), fill=(210, 220, 255), anchor="rm")
    if style_tag_text:
        tag = style_tag_text
        tw = len(tag) * 26 + 44
        d.rounded_rectangle([W - tw - 140, 16, W - 140, 58], radius=16, fill=(230, 80, 60, 255))
        d.text((W - tw // 2 - 140, 37), tag, font=f(24), fill=(255, 255, 255), anchor="mm")
    img.alpha_composite(ov)

def top_caption_line(img, text, y_offset=0, alpha=255, font_size=40):
    top_caption_block(img, text, y_offset=y_offset, alpha=alpha, font_size=font_size)

def top_caption_block(img, text, y_offset=0, alpha=255, font_size=40, max_w=640):
    if alpha <= 0:
        return
    font = f(font_size)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # 自动按宽度折行
    lines = []
    cur = ""
    for ch in text:
        test = cur + ch
        bbox = d.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    if not lines:
        return
    line_h = 72; gap = 12
    total_h = len(lines) * line_h + (len(lines) - 1) * gap
    y = 220 + y_offset
    cx = W // 2
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0] + 60
        x1, y1 = cx - tw // 2, y
        x2, y2 = x1 + tw, y1 + line_h
        d.rounded_rectangle([x1, y1, x2, y2], radius=20, fill=(25, 35, 70, int(alpha * 0.90)))
        d.text((cx, y1 + 36), line, font=font, fill=(255, 255, 255, alpha), anchor="mm")
        y += line_h + gap
    img.alpha_composite(ov)

def qr_block(img, t, dur, label="长按识别 · 找项目"):
    p = t / dur
    if p < 0.72:
        return
    a = clamp((p - 0.72) / 0.08 * 255)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, H - 360, W, H], fill=(20, 30, 60, int(a * 0.90)))
    img.alpha_composite(ov)
    cx, cy = W // 2, H - 250
    ImageDraw.Draw(img).rounded_rectangle([cx - 140, cy - 140, cx + 140, cy + 140], radius=20, fill=(255, 255, 255))
    img.paste(QR, (cx - 130, cy - 130))
    atext(img, cx, cy + 180, label, f(38), (255, 255, 255), a)
    atext(img, cx, cy + 222, "hndcw.com", f(28), (200, 210, 255), a)

def base_frame(t, dur, bg):
    return bg.copy().convert("RGBA")

# =====================================================================
# 背景 A：口播版 —— 深蓝“档案库 / 能力展示”风（专业、硬核）
# =====================================================================
def make_koubo_bg():
    # 深蓝渐变底
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    top = np.array([26, 36, 66]); bot = np.array([14, 22, 46])
    for y in range(H):
        arr[y] = top + (bot - top) * (y / H)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    # 标题栏
    d.rectangle([0, 74, W, 178], fill=(255, 255, 255))
    d.text((W // 2, 118), "鸣儿·全域智能助手", font=f(42), fill=(28, 28, 28), anchor="mm")
    d.text((W // 2, 152), "项目情报与实务顾问", font=f(24), fill=(150, 150, 150), anchor="mm")
    d.line([(0, 178), (W, 178)], fill=(60, 90, 150))
    # 三网来源 chips
    chips = [("招标网", (56, 122, 200)), ("公共资源网", (36, 160, 150)), ("政府采购网", (130, 90, 190))]
    cw = 200; gap = 24; x = (W - (cw * 3 + gap * 2)) // 2; y = 206
    for txt, col in chips:
        d.rounded_rectangle([x, y, x + cw, y + 64], radius=18, fill=col)
        d.text((x + cw // 2, y + 32), txt, font=f(30), fill=(255, 255, 255), anchor="mm")
        x += cw + gap
    # 标题：专业整理档案
    d.text((W // 2, 320), "鸣儿专业整理 · 项目档案", font=f(38), fill=(220, 230, 255), anchor="mm")
    d.text((W // 2, 362), "三网聚合 → 一键直达真实详情", font=f(26), fill=(150, 175, 230), anchor="mm")
    # 档案卡 x3
    cards = [
        ("海口市污水处理厂扩建", "金额 约1.28亿"),
        ("三亚湾生态旅游修复工程", "金额 约0.96亿"),
        ("琼海市人民医院新院区", "金额 约2.10亿"),
    ]
    detail = [("业主单位", (47, 84, 150)), ("代理机构", (47, 84, 150)),
              ("联系电话", (47, 84, 150)), ("官方附件直链", (200, 90, 60))]
    y = 410
    for name, amt in cards:
        d.rounded_rectangle([40, y, W - 40, y + 235], radius=18, fill=(245, 248, 255))
        d.text((66, y + 22), name, font=f(32), fill=(20, 20, 20))
        d.text((66, y + 70), amt, font=f(28), fill=(200, 90, 60))
        # 四要素 chips
        dx = 66; dy = y + 118
        for i, (lab, col) in enumerate(detail):
            col2 = i % 2; row = i // 2
            bx = 66 + col2 * 290; by = y + 118 + row * 48
            d.rounded_rectangle([bx, by, bx + 270, by + 40], radius=12, fill=col)
            d.text((bx + 135, by + 20), lab, font=f(24), fill=(255, 255, 255), anchor="mm")
        y += 255
    return img

# =====================================================================
# 背景 B：脱口秀版 —— 浅色“杂乱三网 → 整理档案”对比风（吐槽叙事）
# =====================================================================
def make_talk_bg():
    img = Image.new("RGBA", (W, H), (243, 245, 250, 255))
    d = ImageDraw.Draw(img)
    # 标题栏
    d.rectangle([0, 74, W, 178], fill=(255, 255, 255))
    d.text((W // 2, 118), "鸣儿·全域智能助手", font=f(42), fill=(28, 28, 28), anchor="mm")
    d.text((W // 2, 152), "项目情报与实务顾问", font=f(24), fill=(150, 150, 150), anchor="mm")
    d.line([(0, 178), (W, 178)], fill=(225, 228, 235))
    # 左：杂乱三网便利贴（灰、倾斜，表示难）
    notes = [("招标网", 120, 230, -6), ("公共资源网", 110, 380, 5), ("政府采购网", 130, 530, -4)]
    for txt, x, y, rot in notes:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.rounded_rectangle([x, y, x + 260, y + 150], radius=10, fill=(230, 232, 238, 255),
                             outline=(200, 204, 214, 255))
        od.text((x + 130, y + 75), txt, font=f(32), fill=(120, 124, 134), anchor="mm")
        img.alpha_composite(ov)
    d.text((250, 720), "每天几百条 ↓", font=f(28), fill=(170, 80, 80), anchor="mm")
    # 中：大箭头
    d.text((430, 430), "→", font=f(120), fill=(47, 84, 150), anchor="mm")
    # 右：干净鸣儿档案卡
    rx = 470
    d.rounded_rectangle([rx, 200, W - 40, 760], radius=20, fill=(255, 255, 255), outline=(47, 84, 150))
    d.rounded_rectangle([rx, 200, W - 40, 268], radius=20, fill=(47, 84, 150))
    d.text((rx + (W - 40 - rx) // 2, 234), "鸣儿档案", font=f(36), fill=(255, 255, 255), anchor="mm")
    rows = [("业主单位", "海口市水务集团"), ("代理机构", "海南某招标代理"),
            ("联系电话", "139-XXXX-XXXX"), ("官方附件", "直链可下载")]
    ry = 300
    for lab, val in rows:
        d.text((rx + 24, ry), lab, font=f(27), fill=(95, 95, 95))
        d.text((rx + 24, ry + 36), val, font=f(28), fill=(28, 28, 28))
        d.line([(rx + 16, ry + 80), (W - 56, ry + 80)], fill=(232, 235, 242))
        ry += 100
    d.text((rx + (W - 40 - rx) // 2, 800), "专业整理 · 来源可溯", font=f(26), fill=(47, 84, 150), anchor="mm")
    return img

BG_KOUBO = make_koubo_bg()
BG_TALK = make_talk_bg()

# ---------- 口播版 ----------
def render_koubo(t, dur):
    img = base_frame(t, dur, BG_KOUBO)
    top_brand_bar(img)  # 无风格标签
    d = ImageDraw.Draw(img)
    # 左下主播头像 + REC
    d.ellipse([40, H - 230, 150, H - 120], fill=(107, 79, 160))
    d.text((95, H - 175), "鸣", font=f(46), fill=(255, 255, 255), anchor="mm")
    if int(t * 2) % 2 == 0:
        d.ellipse([170, H - 212, 192, H - 190], fill=(230, 60, 60))
    d.text((205, H - 201), "REC", font=f(26), fill=(230, 80, 80))
    lines = [
        (0.00, 0.20, "我做工程，最愁找项目"),
        (0.20, 0.40, "招标网·公共资源网·政府采购网"),
        (0.40, 0.60, "鸣儿专业整理档案"),
        (0.60, 0.80, "业主·代理·电话·官方附件直链，全给齐"),
        (0.80, 1.00, "找项目，就找鸣儿"),
    ]
    p = t / dur
    for s, e, txt in lines:
        if s <= p < e:
            a = clamp((p - s) / 0.05 * 255)
            top_caption_line(img, txt, y_offset=0, alpha=a, font_size=40)
    qr_block(img, t, dur)
    return img.convert("RGB")

# ---------- 脱口秀版（无"脱口秀"字样） ----------
def render_talk(t, dur):
    img = base_frame(t, dur, BG_TALK)
    top_brand_bar(img)  # 不传 style_tag，画面无"脱口秀"字样
    lines = [
        (0.00, 0.18, "你们找项目这样："),
        (0.18, 0.42, "招标网·公共资源网·政府采购网"),
        (0.42, 0.62, "鸣儿专业整理档案"),
        (0.62, 0.82, "业主·代理·电话·官方附件直链，全排好"),
        (0.82, 1.00, "是以前没用鸣儿"),
    ]
    p = t / dur
    for s, e, txt in lines:
        if s <= p < e:
            a = clamp((p - s) / 0.05 * 255)
            top_caption_line(img, txt, y_offset=0, alpha=a, font_size=40)
    qr_block(img, t, dur, label="上鸣儿，自己找")
    return img.convert("RGB")

# ---------- 音频 / 编码 ----------
async def gen_tts(text, voice, out):
    try: os.remove(out)
    except OSError: pass
    await edge_tts.Communicate(text, voice).save(out)

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

async def main():
    koubo_text = ("我做工程，最愁找项目。招标网、公共资源网、政府采购网。用鸣儿，"
                  "把三网项目专业整理成档案——业主、代理、电话、官方附件直链，全给齐。找项目，就找鸣儿。")
    talk_text = ("你们找项目这样：招标网、公共资源网、政府采购网。用鸣儿，"
                 "把三网项目专业整理成档案——业主、代理、电话、官方附件直链，全排好。是以前没用鸣儿。")

    await gen_tts(koubo_text, "zh-CN-YunyangNeural", os.path.join(BASE, "a_koubo.mp3"))
    await gen_tts(talk_text, "zh-CN-YunxiNeural", os.path.join(BASE, "a_talk.mp3"))

    dk = get_dur(os.path.join(BASE, "a_koubo.mp3"))
    dt = get_dur(os.path.join(BASE, "a_talk.mp3"))
    print("durs koubo=%.2f talk=%.2f" % (dk, dt))

    rc1 = make_video(render_koubo, os.path.join(BASE, "a_koubo.mp3"), os.path.join(BASE, "minger_koubo_15s.mp4"), dk)
    rc2 = make_video(render_talk, os.path.join(BASE, "a_talk.mp3"), os.path.join(BASE, "minger_talk_15s.mp4"), dt)
    print("VIDEO_RC koubo=%d talk=%d" % (rc1, rc2))

    # 预览帧
    for name, rn, dur in [("koubo", render_koubo, dk), ("talk", render_talk, dt)]:
        for frac, tag in [(0.30, "mid"), (0.99, "end")]:
            frame = rn(dur * frac, dur).convert("RGB")
            frame.save(os.path.join(BASE, "v5_%s_%s.png" % (name, tag)))

if __name__ == "__main__":
    asyncio.run(main())
