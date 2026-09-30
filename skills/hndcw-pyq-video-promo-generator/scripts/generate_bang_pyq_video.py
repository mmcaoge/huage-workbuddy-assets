# -*- coding: utf-8 -*-
r"""榜上有鸣 朋友圈私域推广视频 v1（华哥 2026-09-02）
- 每天视频/图片/脚本/文案都不一样
- 主题轮换：题库/赛事/家长端/班级擂台/错题/分享/每日精选
- 输出到 D:\workBuddy\Delivery\workBuddy\榜上有鸣：朋友圈私域推广
"""
import os, asyncio, subprocess, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts

SRC_BASE = "D:/WorkBuddy-Projects/2026-06-07-20-59-29/promotion/pyq_samples"
OUT_BASE = "D:/workBuddy/Delivery/workBuddy/榜上有鸣：朋友圈私域推广"
FONT = "C:/Windows/Fonts/msyh.ttc"
W, H = 720, 1280
FPS = 25
clamp = lambda v: max(0, min(255, int(v)))
def f(sz): return ImageFont.truetype(FONT, sz)

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def gradient_bg(top_rgb, bot_rgb):
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    top = np.array(top_rgb); bot = np.array(bot_rgb)
    for y in range(H):
        arr[y] = top + (bot - top) * (y / H)
    return Image.fromarray(arr)

def wrap_text(text, font, max_w):
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

# ---------- 通用图层 ----------
def top_bar(img, title="榜上有鸣"):
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, 74], fill=(0, 132, 255, 255))
    d.text((30, 37), "海南铎鸣 › " + title, font=f(28), fill=(255,255,255), anchor="lm")
    d.text((W - 30, 37), "搜一搜：榜上有鸣", font=f(24), fill=(220,240,255), anchor="rm")
    img.alpha_composite(ov)

def caption_block(img, text, y_offset=0, alpha=255, font_size=40, max_w=640):
    if alpha <= 0:
        return
    font = f(font_size)
    lines = wrap_text(text, font, max_w)
    if not lines:
        return
    line_h = 70; gap = 10
    y = 120 + y_offset
    cx = W // 2
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    for line in lines:
        bbox = d.textbbox((0,0), line, font=font)
        tw = bbox[2] - bbox[0] + 56
        x1, y1 = cx - tw//2, y
        x2, y2 = x1 + tw, y1 + line_h
        d.rounded_rectangle([x1,y1,x2,y2], radius=18, fill=(20,40,70,int(alpha*0.92)))
        d.text((cx, y1+35), line, font=font, fill=(255,255,255,alpha), anchor="mm")
        y += line_h + gap
    img.alpha_composite(ov)

def bottom_cta(img, t, dur):
    p = t / dur
    if p < 0.72:
        return
    a = clamp((p - 0.72) / 0.08 * 255)
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, H-280, W, H], fill=(20,35,60, int(a*0.92)))
    img.alpha_composite(ov)
    atext(img, W//2, H-190, "微信搜一搜：榜上有鸣", f(40), (255,255,255), a)
    atext(img, W//2, H-130, "小程序 · 答题竞赛 · 266 万题库", f(28), (200,220,255), a)
    atext(img, W//2, H-80, "让孩子爱上学习", f(32), (255,210,100), a)

def atext(img, x, y, s, font, rgb, alpha=255, anchor="mm"):
    if alpha <= 0 or not s:
        return
    layer = Image.new("RGBA", (W,H), (0,0,0,0))
    dl = ImageDraw.Draw(layer)
    dl.text((x,y), s, font=font, fill=(rgb[0],rgb[1],rgb[2],int(alpha)), anchor=anchor)
    img.alpha_composite(layer)

# ---------- 每日内容 ----------
THEMES = [
    ("海量题库", "266 万精选题目，覆盖小初高全学科"),
    ("赛事系统", "日赛/周赛/月赛/期赛/年赛，天天有挑战"),
    ("家长端", "孩子答题成绩实时看，学习进度一手掌握"),
    ("班级擂台", "班级 PK、组队闯关，学习也能很燃"),
    ("错题挑战", "错题反复练，举一反三补弱项"),
    ("分享挑战", "邀请好友一起答，边玩边学赢奖励"),
    ("每日精选", "每天 10 道精选题，养成答题好习惯"),
]

def day_content(day):
    theme, desc = THEMES[(day - 1) % len(THEMES)]
    return {"day": day, "theme": theme, "desc": desc}

COPY_TEMPLATES = [
    "孩子做题没兴趣？试试榜上有鸣！{theme}，{desc}。微信搜一搜：榜上有鸣，让孩子爱上答题。",
    "别让孩子只刷短视频了。榜上有鸣{theme}，{desc}。每天 10 分钟，答题涨知识。搜一搜：榜上有鸣。",
    "【{theme}】{desc}。榜上有鸣，把学习变成一场有趣的比赛。微信搜一搜：榜上有鸣。",
    "很多家长已经在用了。榜上有鸣{theme}，{desc}。边玩边学，成绩看得见。搜一搜：榜上有鸣。",
    "孩子学习成绩上不去？榜上有鸣{theme}，{desc}。用游戏化方式激发学习动力，搜一搜：榜上有鸣。",
    "今天开始，让学习不一样。榜上有鸣{theme}，{desc}。微信搜一搜：榜上有鸣，免费体验。",
    "不补课、不逼学，榜上有鸣{theme}，{desc}。每天答几题，知识自然涨。搜一搜：榜上有鸣。",
]

def make_copy(day, ctx):
    return COPY_TEMPLATES[(day - 1) % len(COPY_TEMPLATES)].format(**ctx)

def pyq_copy(day, ctx):
    return "【榜上有鸣 · {}】{} 微信搜一搜：榜上有鸣，让孩子爱上答题。#榜上有鸣".format(ctx["theme"], ctx["desc"])

# ---------- 视觉模板 ----------
def make_bg_hero(ctx, palette="blue"):
    palettes = {
        "blue": ((0,100,200),(0,60,140)),
        "green": ((0,140,120),(0,80,70)),
        "purple": ((100,60,180),(60,30,120)),
        "orange": ((230,120,30),(180,70,10)),
        "teal": ((0,130,150),(0,75,90)),
        "pink": ((210,70,130),(140,30,80)),
        "yellow": ((220,170,0),(160,110,0)),
    }
    top, bot = palettes.get(palette, palettes["blue"])
    img = gradient_bg(top, bot)
    d = ImageDraw.Draw(img)
    # 大主题
    d.text((W//2, 280), ctx["theme"], font=f(72), fill=(255,255,255), anchor="mm")
    d.text((W//2, 370), ctx["desc"], font=f(28), fill=(230,245,255), anchor="mm")
    # 数字强调
    if ctx["theme"] == "海量题库":
        d.text((W//2, 560), "266", font=f(120), fill=(255,210,80), anchor="mm")
        d.text((W//2, 700), "万道精选题", font=f(40), fill=(255,255,255), anchor="mm")
    elif ctx["theme"] == "赛事系统":
        d.text((W//2, 580), "日/周/月/期/年", font=f(50), fill=(255,210,80), anchor="mm")
        d.text((W//2, 680), "五大赛事不停歇", font=f(40), fill=(255,255,255), anchor="mm")
    elif ctx["theme"] == "家长端":
        d.text((W//2, 580), "实时看成绩", font=f(52), fill=(255,210,80), anchor="mm")
        d.text((W//2, 680), "学习进度一手掌握", font=f(36), fill=(255,255,255), anchor="mm")
    elif ctx["theme"] == "班级擂台":
        d.text((W//2, 580), "班级 PK", font=f(60), fill=(255,210,80), anchor="mm")
        d.text((W//2, 680), "组队闯关更带劲", font=f(38), fill=(255,255,255), anchor="mm")
    elif ctx["theme"] == "错题挑战":
        d.text((W//2, 580), "举一反三", font=f(60), fill=(255,210,80), anchor="mm")
        d.text((W//2, 680), "错题反复练，弱项变强项", font=f(34), fill=(255,255,255), anchor="mm")
    elif ctx["theme"] == "分享挑战":
        d.text((W//2, 580), "邀请好友", font=f(60), fill=(255,210,80), anchor="mm")
        d.text((W//2, 680), "边玩边学赢奖励", font=f(38), fill=(255,255,255), anchor="mm")
    else:
        d.text((W//2, 580), "每日 10 题", font=f(60), fill=(255,210,80), anchor="mm")
        d.text((W//2, 680), "养成答题好习惯", font=f(38), fill=(255,255,255), anchor="mm")
    return img

def make_bg_cards(ctx, palette="blue"):
    accent_map = {"blue":(0,132,255),"green":(0,160,120),"purple":(120,70,200),"orange":(240,130,30),"teal":(0,150,170),"pink":(220,80,140),"yellow":(220,170,0)}
    accent = accent_map.get(palette, (0,132,255))
    img = Image.new("RGBA", (W,H), (247,249,252,255))
    d = ImageDraw.Draw(img)
    # 顶部标题区
    d.rectangle([0,74,W,220], fill=accent)
    d.text((W//2,140), ctx["theme"], font=f(48), fill=(255,255,255), anchor="mm")
    d.text((W//2,190), ctx["desc"], font=f(24), fill=(230,245,255), anchor="mm")
    # 三张功能卡
    cards = [
        ("266 万题库", "小初高全学科覆盖"),
        ("五大赛事", "日周月期年不间断"),
        ("家长端", "成绩实时看得见"),
    ]
    y = 280
    for t, s in cards:
        d.rounded_rectangle([60,y,W-60,y+140], radius=18, fill=(255,255,255), outline=accent, width=2)
        d.rounded_rectangle([60,y,140,y+140], radius=18, fill=accent)
        d.text((100,y+70), t[:2], font=f(40), fill=(255,255,255), anchor="mm")
        d.text((170,y+50), t, font=f(32), fill=(28,28,28), anchor="lm")
        d.text((170,y+95), s, font=f(24), fill=(100,100,100), anchor="lm")
        y += 170
    return img

BG_MAKERS = [make_bg_hero, make_bg_cards]

def caption_schedule(text):
    parts = text.replace("。", "|").replace("，", "|").replace("；", "|").split("|")
    parts = [p.strip() for p in parts if p.strip()]
    n = len(parts)
    seg = 1.0 / n
    return [(seg*i, seg*(i+1), p) for i,p in enumerate(parts)]

def render_frame(t, dur, bg, captions, ctx, show_caption=True):
    img = bg.copy().convert("RGBA")
    top_bar(img)
    p = t / dur
    if show_caption:
        for s,e,txt in captions:
            if s <= p < e or (p >= 1.0 and e >= 0.99):
                a = clamp((p-s)/max(0.03,(e-s)*0.25)*255)
                caption_block(img, txt, alpha=a, font_size=38)
                break
    bottom_cta(img, t, dur)
    return img.convert("RGB")

# ---------- 音频/编码 ----------
async def gen_tts(text, voice, out, rate="+8%"):
    try: os.remove(out)
    except OSError: pass
    last_err = None
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(out)
            return
        except Exception as e:
            last_err = e
            await asyncio.sleep(0.5 * (attempt+1))
    raise last_err

def get_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",path], capture_output=True, text=True)
    return float(r.stdout.strip())

def make_video(render, audio, out, dur):
    total = int(dur*FPS)+1
    cmd = ["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s","%dx%d"%(W,H),
           "-r",str(FPS),"-i","-","-i",audio,"-c:v","libx264","-pix_fmt","yuv420p",
           "-preset","fast","-crf","23","-c:a","aac","-shortest","-movflags","+faststart",out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(total):
        frame = render(i/FPS, dur)
        p.stdin.write(frame.tobytes())
    p.stdin.close(); p.wait()
    return p.returncode

async def generate_day(day):
    ensure_dir(OUT_BASE)
    ctx = day_content(day)
    copy_text = make_copy(day, ctx)
    pyq = pyq_copy(day, ctx)
    palette = ["blue","green","purple","orange","teal","pink","yellow"][(day-1)%7]
    bg = BG_MAKERS[(day-1)%len(BG_MAKERS)](ctx, palette)
    captions = caption_schedule(copy_text)
    date_str = "09_{:02d}".format(day)
    audio_path = os.path.join(SRC_BASE, "bang_a_{}.mp3".format(date_str))
    video_path = os.path.join(OUT_BASE, "bang_{}.mp4".format(date_str))
    cover_path = os.path.join(OUT_BASE, "bang_{}_cover.jpg".format(date_str))
    await gen_tts(copy_text, "zh-CN-XiaoxiaoNeural", audio_path)
    dur = get_dur(audio_path)
    def render(t,d):
        return render_frame(t,d,bg,captions,ctx)
    rc = make_video(render, audio_path, video_path, dur)
    # 封面：无字幕
    frame = render_frame(dur*0.5, dur, bg, captions, ctx, show_caption=False)
    frame.save(cover_path, quality=95)
    print("BANG DAY {} dur={:.2f}s rc={}".format(day, dur, rc))
    return {"day":day,"date_str":date_str,"theme":ctx["theme"],"copy":copy_text,"pyq":pyq,"video":video_path,"cover":cover_path,"duration":dur}

async def main():
    days = []
    for day in range(1, 31):  # 9 月全量 30 天
        days.append(await generate_day(day))
    with open(os.path.join(OUT_BASE, "bang_september_plan.json"), "w", encoding="utf-8") as f:
        json.dump(days, f, ensure_ascii=False, indent=2)
    print("DONE 30 days bang ->", OUT_BASE)

if __name__ == "__main__":
    asyncio.run(main())
