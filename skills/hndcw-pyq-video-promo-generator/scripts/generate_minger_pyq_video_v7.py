# -*- coding: utf-8 -*-
r"""鸣儿·全域智能助手 朋友圈推广视频 v7（净化版 · 华哥 2026-09-03）
净化目标：让视频真正「吸睛」，而不是 PPT 配朗读。
核心改造：
  1. 文案 = 钩子驱动结构：痛点开场 → 反转共情 → 三网方案 → 数字证据 → 扫码CTA
  2. 视觉 = 动态冲击：黑底大字钩子脉冲 / 杂乱→整理对比流 / 金数滚动 / 二维码CTA
  3. 配音 = 情绪化 edge-tts（活力男声 + 标点停顿 + 语速提气）
  4. 音频 = numpy 程序化 BGM 卡点垫底，混音到配音
先跑 day1 做样片，确认方向后改 main() 批量。
"""
import os, asyncio, subprocess, json, math, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import edge_tts

SRC_BASE = "D:/WorkBuddy-Projects/2026-06-07-20-59-29/promotion/pyq_samples"
OUT_BASE = "D:/workBuddy/Delivery/workBuddy/视频广告净化测试"
ensure = lambda p: os.makedirs(p, exist_ok=True)
FONT = "C:/Windows/Fonts/msyh.ttc"
W, H = 720, 1280
FPS = 25
clamp = lambda v: max(0, min(255, int(v)))
def f(sz): return ImageFont.truetype(FONT, sz)
def ease(t): return t * t * (3 - 2 * t)  # smoothstep

# ---------- 二维码 ----------
import qrcode
_qr = qrcode.QRCode(box_size=10, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
_qr.add_data("https://hndcw.com")
QR = _qr.make_image(fill_color="#2F5496", back_color="white").convert("RGB").resize((240, 240), Image.LANCZOS)

def atext(img, x, y, s, font, rgb, alpha=255, anchor="mm"):
    if alpha <= 0 or not s: return
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((x, y), s, font=font, fill=(rgb[0], rgb[1], rgb[2], int(alpha)), anchor=anchor)
    img.alpha_composite(layer)

def wrap_text(text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        test = cur + ch
        if ImageDraw.Draw(Image.new("RGBA", (1,1))).textbbox((0,0), test, font=font)[2] > max_w and cur:
            lines.append(cur); cur = ch
        else: cur = test
    if cur: lines.append(cur)
    return lines

# =====================================================================
# 30 天内容库（沿用 v6 主题/城市/项目，保证"每天不同"铁律）
# =====================================================================
THEMES = [("市政工程","水务/道路/管网"),("医疗卫生","医院/诊所/设备"),("教育科研","学校/实验室/信息化"),
          ("生态环保","污水处理/固废/绿化"),("交通运输","公路/桥梁/港口"),("农业农村","灌溉/产业/基础设施"),
          ("文化旅游","景区/场馆/文创"),("能源电力","光伏/储能/电网"),("信息化","政务/大数据/安防"),("房建住宅","保障房/公共建筑")]
CITIES = ["南昌","银川","天津","郑州","济南","呼和浩特","成都","杭州","广州","武汉","海口","乌鲁木齐","西安","南京","长沙","合肥","福州","南宁","贵阳","昆明","拉萨","兰州","西宁","石家庄","太原","沈阳","长春","上海","重庆","北京"]
PROJECTS = [("{}市污水处理厂扩建工程","1.28"),("{}湾生态廊道修复项目","0.86"),("{}人民医院新院区建设","2.10"),
            ("{}市智慧交通管理平台","0.45"),("{}新区中小学新建工程","0.92"),("{}市垃圾分类处理中心","0.63"),
            ("{}海岸带综合整治工程","1.55"),("{}市公共卫生临床中心","1.80"),("{}现代农业产业园配套","0.78"),
            ("{}市文体中心升级改造","1.12"),("{}新能源充电设施一期","0.38"),("{}市数字政府云平台","0.55"),
            ("{}保障性租赁住房项目","1.65"),("{}市供水管网改造工程","0.72"),("{}渔港经济区基础设施","1.05"),
            ("{}市康养综合体建设","1.35"),("{}河流域生态修复","0.96"),("{}市冷链物流园建设","0.88"),
            ("{}高新技术产业孵化园","1.45"),("{}市应急指挥中心","0.42"),("{}古城文化旅游区改造","0.68"),
            ("{}市第二福利院迁建","0.52"),("{}港区航道疏浚工程","1.20"),("{}市消防站建设工程","0.34"),
            ("{}基层医疗卫生机构","0.48"),("{}市农村公路提升工程","0.60"),("{}工业互联网平台","0.50"),
            ("{}市殡仪馆改扩建","0.40"),("{}水库除险加固工程","0.74"),("{}市人才公寓装修改造","0.36")]

def day_content(day):
    theme, sub = THEMES[(day-1) % len(THEMES)]
    city = CITIES[(day-1) % len(CITIES)]
    tmpl, amt = PROJECTS[(day-1) % len(PROJECTS)]
    return {"day":day,"theme":theme,"sub":sub,"city":city,"project":tmpl.format(city),"amount":amt,
            "update_count": 120 + (day*17) % 380}

# =====================================================================
# 净化文案：钩子驱动 5 段结构（痛点→反转→方案→证据→CTA）
# =====================================================================
HOOK = [
    "翻烂三网，还是漏掉大单？",
    "找项目仨月，真项目没摸到？",
    "同行拿到单，你还在刷网页？",
    "三网又杂又散，头都大了？",
    "不是没项目，是你刷不到！",
]
REVERSE = "不是你没本事，是信息被三网撕碎了。"
PLAN = "招标网、公共资源网、政府采购网——鸣儿三网全量更新上线，专业整理成档案。"
EVIDENCE = "今日更新 {n} 条，{project} 金额约 {amt} 亿，业主代理电话附件直链全给齐。"
CTA = "上 hndcw.com 找项目，长按识别。"

def script(day, ctx):
    hook = HOOK[(day-1) % len(HOOK)]
    ev = EVIDENCE.format(n=ctx["update_count"], project=ctx["project"], amt=ctx["amount"])
    style = "koubo" if day % 2 == 1 else "talk"
    if style == "koubo":
        voice = "zh-CN-YunyangNeural"; rate = "+30%"
    else:
        voice = "zh-CN-YunxiNeural"; rate = "+27%"
    full = "{h}{rv}招标网、公共资源网、政府采购网，鸣儿三网全量更新上线，整理成档案。{ev}{cta}".format(
        h=hook, rv=REVERSE, ev=ev, cta=CTA)
    return full, voice, rate, style, hook

# =====================================================================
# 动态视觉：4 阶段（HOOK / CONTRAST / EVIDENCE / CTA）
# =====================================================================
def bg_hook(t, dur, hook):
    """黑底红黄大字脉冲"""
    p = t / dur
    img = Image.new("RGBA",(W,H),(8,8,12,255))
    d = ImageDraw.Draw(img)
    # 顶部细光条
    d.rectangle([0,0,W,6], fill=(220,60,60))
    # 脉冲缩放（基于开场进度）
    k = ease(min(1, p/0.35))
    scale = 0.86 + 0.18*k
    # 钩子文字分行
    lines = wrap_text(hook, f(54), 600)
    line_h = 78; total = len(lines)*line_h
    y0 = H*0.40 - total/2
    glow = (255, 70, 70) if (int(t*2)%2==0) else (255,200,90)
    for i,line in enumerate(lines):
        y = y0 + i*line_h
        atext(img, W//2, y, line, f(int(54*scale)), glow, 255)
    # 副标
    atext(img, W//2, H*0.74, "—— 这不是你一个人的困局", f(30), (160,160,175), 230)
    return img

def bg_contrast(t, dur, ctx):
    """白底：左三网乱 / 右鸣儿档案齐，箭头流动"""
    img = Image.new("RGBA",(W,H),(244,246,250,255))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,90], fill=(47,84,150))
    atext(img, W//2, 45, "找项目，为什么累？", f(40), (255,255,255), 255)
    # 左：三网乱（灰色堆叠小字）
    lx = 40
    for i,src in enumerate(["招标网","公共资源网","政府采购网"]):
        y = 150 + i*150
        d.rounded_rectangle([lx,y,lx+280,y+120], radius=14, fill=(228,230,236), outline=(200,204,214))
        d.text((lx+140,y+60), src, font=f(34), fill=(120,124,134), anchor="mm")
        # 模拟杂乱小字
        for j in range(4):
            d.text((lx+20, y+18+j*22), "····· ····· ·····", font=f(18), fill=(180,184,194))
    # 中：流动箭头
    ax = 340 + 14*math.sin(t*3)
    d.text((ax, 420), "➜", font=f(90), fill=(47,84,150), anchor="mm")
    # 右：鸣儿档案齐（整齐卡）
    rx, rw = 380, W-380-40
    d.rounded_rectangle([rx,150,rx+rw,150+520], radius=18, fill=(255,255,255), outline=(47,84,150), width=3)
    atext(img, rx+rw//2, 185, "鸣儿项目档案", f(36), (47,84,150), 255)
    rows = [("业主单位", ctx["city"]+"相关单位"),("代理机构","专业招标代理"),
            ("联系电话","139-XXXX-XXXX"),("官方附件","直链下载")]
    ry = 240
    for lab,val in rows:
        d.rounded_rectangle([rx+16,ry,rx+rw-16,ry+54], radius=10, fill=(245,248,255), outline=(47,84,150))
        d.text((rx+28, ry+27), lab, font=f(22), fill=(47,84,150), anchor="lm")
        d.text((rx+150, ry+27), val, font=f(22), fill=(28,28,28), anchor="lm")
        ry += 66
    atext(img, rx+rw//2, 690, "专业整理 · 来源可溯", f(26), (47,84,150), 255)
    return img

def bg_evidence(t, dur, ctx):
    """深色：金色大数字滚动"""
    p = (t-dur*0.55)/(dur*0.25)
    img = Image.new("RGBA",(W,H),(14,20,42,255))
    d = ImageDraw.Draw(img)
    atext(img, W//2, 200, "今日全量更新上线", f(34), (210,220,255), 255)
    # 数字滚动 0 → update_count
    n = int(min(1,max(0,p)) * ctx["update_count"])
    atext(img, W//2, 330, "{}".format(n), f(120), (255,205,90), 255)
    atext(img, W//2, 430, "条真实项目情报", f(30), (210,220,255), 255)
    # 项目 + 金额
    atext(img, W//2, 600, ctx["project"], f(32), (255,255,255), 255)
    atext(img, W//2, 680, "金额约 {} 亿".format(ctx["amount"]), f(56), (255,120,90), 255)
    atext(img, W//2, 780, "业主·代理·电话·附件直链 全给齐", f(26), (200,210,235), 255)
    return img

def bg_cta(t, dur, ctx):
    """品牌蓝底：二维码 + 上 hndcw.com"""
    p = (t-dur*0.80)/(dur*0.20)
    a = clamp(p/0.15*255)
    img = Image.new("RGBA",(W,H),(20,34,70,255))
    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,90], fill=(47,84,150))
    atext(img, W//2, 45, "找项目，上鸣儿", f(42), (255,255,255), 255)
    cx, cy = W//2, int(H*0.52)
    d.rounded_rectangle([cx-130,cy-130,cx+130,cy+130], radius=18, fill=(255,255,255))
    img.paste(QR, (cx-120, cy-120))
    atext(img, cx, cy+170, "长按识别 · 找项目", f(40), (255,255,255), a)
    atext(img, cx, cy+218, "hndcw.com", f(30), (200,210,255), a)
    return img

def render_frame(t, dur, ctx, hook):
    p = t/dur
    if p < 0.25:      return bg_hook(t, dur, hook)
    elif p < 0.55:    return bg_contrast(t, dur, ctx)
    elif p < 0.80:    return bg_evidence(t, dur, ctx)
    else:             return bg_cta(t, dur, ctx)

# =====================================================================
# 程序化 BGM（numpy 轻量 loop，120BPM 卡点）
# =====================================================================
def gen_bgm_wav(path, dur, sr=22050):
    beats = int(dur*2)  # 120 BPM → 2 beat/s
    n = int(dur*sr)
    sig = np.zeros(n, dtype=np.float32)
    # 低音 kick
    for b in range(beats):
        s0 = int(b*sr/2)
        for i in range(int(0.12*sr)):
            if s0+i < n:
                env = math.exp(-i/(0.12*sr)*6)
                sig[s0+i] += 0.5*env*math.sin(2*math.pi*60*(i/sr))
    # 轻 pad 和声（根音 + 五度）
    for i in range(n):
        tt = i/sr
        sig[i] += 0.06*math.sin(2*math.pi*196*tt) + 0.05*math.sin(2*math.pi*294*tt)
    sig = np.clip(sig, -1, 1)
    with open(path,"wb") as wf:
        wf.write(b"RIFF"); wf.write(struct.pack("<I", 36+len(sig)*2)); wf.write(b"WAVE")
        wf.write(b"fmt "); wf.write(struct.pack("<IHHIIHH",16,1,1,sr, sr*2,2,16))
        wf.write(b"data"); wf.write(struct.pack("<I", len(sig)*2))
        wf.write((sig*32767).astype(np.int16).tobytes())

# =====================================================================
# TTS + 混音
# =====================================================================
async def gen_tts(text, voice, out, rate="+8%"):
    try: os.remove(out)
    except OSError: pass
    for _ in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(out); return
        except Exception:
            await asyncio.sleep(0.6)
    raise RuntimeError("tts fail")

def get_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",path],capture_output=True,text=True)
    return float(r.stdout.strip())

def mix_bgm(tts_mp3, bgm_wav, out):
    subprocess.run(["ffmpeg","-y","-i",tts_mp3,"-i",bgm_wav,
                    "-filter_complex","[1:a]volume=0.16[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0",
                    out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def make_video(render, audio, out, dur):
    total = int(dur*FPS)+1
    cmd = ["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s","%dx%d"%(W,H),"-r",str(FPS),
           "-i","-","-i",audio,"-c:v","libx264","-pix_fmt","yuv420p","-preset","fast","-crf","23",
           "-c:a","aac","-shortest","-movflags","+faststart",out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for i in range(total):
        p.stdin.write(render(i/FPS, dur).tobytes())
    p.stdin.close(); p.wait()

async def generate_day(day, style="auto", out_dir=OUT_BASE):
    ensure(out_dir)
    ctx = day_content(day)
    full, voice, rate, st, hook = script(day, ctx)
    date_str = "09_{:02d}".format(day)
    audio_path = os.path.join(SRC_BASE, "v7_a_{}.mp3".format(date_str))
    bgm_path  = os.path.join(SRC_BASE, "v7_bgm_{}.wav".format(date_str))
    mixed     = os.path.join(SRC_BASE, "v7_mix_{}.mp3".format(date_str))
    video_path= os.path.join(out_dir, "minger_v7_{}_{}.mp4".format(date_str, st))
    cover_path= os.path.join(out_dir, "minger_v7_{}_{}_cover.jpg".format(date_str, st))
    await gen_tts(full, voice, audio_path, rate)
    dur = get_dur(audio_path)
    gen_bgm_wav(bgm_path, dur)
    mix_bgm(audio_path, bgm_path, mixed)
    # 重测时长用混音后
    dur = get_dur(mixed)
    make_video(lambda t,d: render_frame(t,d,ctx,hook), mixed, video_path, dur)
    render_frame(dur*0.65, dur, ctx, hook).convert("RGB").save(cover_path, quality=95)
    print("DAY {} {} dur={:.2f}s -> {}".format(day, st, dur, video_path))
    return {"day":day,"style":st,"theme":ctx["theme"],"city":ctx["city"],"project":ctx["project"],
            "amount":ctx["amount"],"update_count":ctx["update_count"],"copy":full,"video":video_path,"cover":cover_path,"duration":dur}

async def main():
    # 样片：先跑 day1（市政工程/海口/污水厂1.28亿）做对比验证
    info = await generate_day(1, out_dir=OUT_BASE)
    print(json.dumps(info, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
