import subprocess, os, math
from PIL import Image, ImageDraw, ImageFont

FF = r'D:/ffmpeg/extracted/ffmpeg-N-125472-g97cbffe917-win64-gpl/bin/ffmpeg.exe'
FT = r'D:/workBuddy/tmp/digital_human/msyh.ttc'
OUT = r'D:/workBuddy/Delivery/workBuddy/数字人华哥.解读成片'
W, H = 1080, 1920

def font(sz): return ImageFont.truetype(FT, sz)

def bg():
    return Image.new('RGB', (W, H), (185, 30, 30))

def tc(draw, text, y, fnt, fill):
    w = draw.textlength(text, font=fnt)
    draw.text(((W - w) / 2, y), text, font=fnt, fill=fill)

# 六个元类别配置
CATS = [
    ('01_招投标项目',   '招投标项目',   '一句话查全国项目',           '查项目，就找鸣儿'),
    ('02_供应商资质库', '供应商资质库', '中标企业画像 · 资质 · 业绩', '看资质，就找鸣儿'),
    ('03_政策红利库',   '政策红利库',   '自贸港申报指南',             '领政策，就找鸣儿'),
    ('04_供应链商机',   '供应链商机',   '甲方乙方关系',               '找商机，就找鸣儿'),
    ('05_技术服务',     '技术服务',     'AI 落地代申报',              '要落地，就找鸣儿'),
    ('06_投标保函',     '投标保函',     '替代保证金 · 释放资金',       '办保函，就找鸣儿'),
]

BRANDS = ['海南社会调查网', '海南铎鸣社会调查网', '鸣儿·商业情报助手', '榜上有鸣', '新时代的中国人']

def draw_intro1(d):
    # 片头画面1：大栏目名 + 口号
    tc(d, '新时代的中国人', 520, font(96), (255, 215, 0))
    tc(d, '传递民意 · 践行价值', 720, font(54), (255, 235, 160))
    tc(d, '主办：海南社会调查网', 1300, font(38), (255, 255, 255))
    tc(d, '协办：海南铎鸣社会调查网', 1360, font(38), (255, 255, 255))
    tc(d, '出品：榜上有鸣', 1420, font(38), (255, 255, 255))
    tc(d, '总编辑：曹中华', 1480, font(38), (255, 255, 255))

def draw_intro2(d, cat_name, tagline):
    # 片头画面2：华哥解读 + 类别 + 定位语
    tc(d, '华哥 · 解读', 560, font(80), (255, 215, 0))
    tc(d, '· ' + cat_name + ' ·', 720, font(72), (255, 255, 255))
    tc(d, tagline, 900, font(44), (255, 235, 180))

def draw_outro1(d, action):
    # 片尾画面1：值得关注 + 动作句
    tc(d, '值得关注', 560, font(96), (255, 215, 0))
    tc(d, action, 740, font(64), (255, 255, 255))

def draw_outro2(d):
    # 片尾画面2：五品牌 + 软钩子 + 口号
    tc(d, '五大品牌', 420, font(42), (255, 215, 0))
    y = 520
    for b in BRANDS:
        tc(d, b, y, font(42), (255, 255, 255))
        y += 70
    tc(d, '微信搜一搜：鸣儿·商业情报助手', 1180, font(44), (255, 235, 160))
    tc(d, '传递民意 · 践行价值', 1300, font(42), (255, 215, 0))

def img_to_mp4(png_path, mp4_path, t=2.5, fade_out=True):
    fade = f',fade=t=out:st={t-0.4}:d=0.4' if fade_out else ''
    cmd = f'{FF} -y -loop 1 -i "{png_path}" -t {t} -r 25 -pix_fmt yuv420p -vf "fade=t=in:st=0:d=0.4{fade}" -an "{mp4_path}"'
    subprocess.run(cmd, shell=True, check=True)

for folder, cat_name, tagline, action in CATS:
    cat_dir = os.path.join(OUT, folder)
    os.makedirs(cat_dir, exist_ok=True)

    # 片头两帧
    img = bg(); d = ImageDraw.Draw(img); draw_intro1(d)
    p1 = os.path.join(cat_dir, '_intro_1.png'); img.save(p1)
    img = bg(); d = ImageDraw.Draw(img); draw_intro2(d, cat_name, tagline)
    p2 = os.path.join(cat_dir, '_intro_2.png'); img.save(p2)

    m1 = os.path.join(cat_dir, '_intro_1.mp4')
    m2 = os.path.join(cat_dir, '_intro_2.mp4')
    img_to_mp4(p1, m1, 2.5)
    img_to_mp4(p2, m2, 2.5)

    # concat 片头
    lst = os.path.join(cat_dir, '_intro_list.txt')
    with open(lst, 'w', encoding='utf-8') as f:
        f.write(f"file '{m1.replace(chr(92), '/')}'\n")
        f.write(f"file '{m2.replace(chr(92), '/')}'\n")
    intro_out = os.path.join(cat_dir, '片头.mp4')
    subprocess.run(f'{FF} -y -f concat -safe 0 -i "{lst}" -c copy "{intro_out}"', shell=True, check=True)

    # 片尾两帧
    img = bg(); d = ImageDraw.Draw(img); draw_outro1(d, action)
    o1 = os.path.join(cat_dir, '_outro_1.png'); img.save(o1)
    img = bg(); d = ImageDraw.Draw(img); draw_outro2(d)
    o2 = os.path.join(cat_dir, '_outro_2.png'); img.save(o2)

    m_o1 = os.path.join(cat_dir, '_outro_1.mp4')
    m_o2 = os.path.join(cat_dir, '_outro_2.mp4')
    img_to_mp4(o1, m_o1, 2.5)
    img_to_mp4(o2, m_o2, 2.5)

    lst2 = os.path.join(cat_dir, '_outro_list.txt')
    with open(lst2, 'w', encoding='utf-8') as f:
        f.write(f"file '{m_o1.replace(chr(92), '/')}'\n")
        f.write(f"file '{m_o2.replace(chr(92), '/')}'\n")
    outro_out = os.path.join(cat_dir, '片尾.mp4')
    subprocess.run(f'{FF} -y -f concat -safe 0 -i "{lst2}" -c copy "{outro_out}"', shell=True, check=True)

    print(folder, '片头', os.path.getsize(intro_out)/1024/1024, 'MB', '片尾', os.path.getsize(outro_out)/1024/1024, 'MB')

print('ALL INTRO/OUTRO v3 done')
