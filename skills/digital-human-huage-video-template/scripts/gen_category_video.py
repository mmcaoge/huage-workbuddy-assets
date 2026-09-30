import subprocess, os, re, shutil, glob

FF = r'D:/ffmpeg/extracted/ffmpeg-N-125472-g97cbffe917-win64-gpl/bin/ffmpeg.exe'
FFP = r'D:/ffmpeg/extracted/ffmpeg-N-125472-g97cbffe917-win64-gpl/bin/ffprobe.exe'
FT = r'D:/workBuddy/tmp/digital_human/msyh.ttc'
BASE = r'D:/workBuddy/Delivery/workBuddy/数字人华哥.解读成片'
BGM_DIR = os.path.join(BASE, '数字人华哥解读资料/背景音乐')

# 配乐音量（华哥要求「调大一点点」：正片 8%->14%，片头片尾 15%->26%）
BGM_MAIN_VOL = 0.14
BGM_HEAD_VOL = 0.26

def pick_bgm(folder):
    """按类别前缀选配乐。暂无专属配乐时，回退到已确认的《歌唱祖国》（教材原谱）"""
    hits = sorted(glob.glob(os.path.join(BGM_DIR, folder[:2] + '_*.wav')))
    if hits:
        return hits[0]
    fallback = sorted(glob.glob(os.path.join(BGM_DIR, '*歌唱祖国*.wav')))
    if fallback:
        return fallback[0]
    allf = sorted(glob.glob(os.path.join(BGM_DIR, '*.wav')))
    return allf[0] if allf else None

# 按类别填写：文件夹名、数字人文件名（在 数字人形象/ 下）、语音、文案、输出名
CFG = {
    'folder': '03_政策红利库',
    # ⚠️ 必须用「纯正片原声」：ep2_voice.m4a 是整条 ep2 成片的音轨，
    # 含 5.18s 片头静音 + 4s 片尾静音，直接用会导致主片首尾没声音。
    # ep2_voice_clean.m4a = 截取 5.17s~30.29s 的纯正片语音（25.12s）。
    'voice':  r'D:/workBuddy/tmp/digital_human/ep2_voice_clean.m4a',
    'lines': [
        ('大家好，我是华哥。今天解读海南自贸港双十五税收优惠。', 5.024),
        ('第一，鼓励类产业企业减按15%征收企业所得税。', 5.024),
        ('第二，高端紧缺人才个人所得税实际税负超过15%的部分免征。', 5.024),
        ('在海南做实业、引人才，税赋更轻、成本更低。', 5.024),
        ('关注海南铎鸣社会调查网，找鸣儿帮你一对一梳理落地。', 5.024),
    ],
    'out_name': '政策红利库_双十五税解读.mp4',
}

def run(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        raise RuntimeError('CMD failed: ' + str(cmd)[:200])
    return r

def fmt(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(lines, durations):
    events = []
    cum = 0.0
    for (line, dur) in zip(lines, durations):
        # 逐字 Karaoke
        chars = [c for c in line if c.strip() or c == ' ']
        n = max(len(chars), 1)
        sec = dur / n
        k_text = ''
        pos = 0
        for ch in line:
            if ch == ' ':
                k_text += ' '
            else:
                k_text += f'{{\\k{int(sec*100)}}}{ch}'
                pos += 1
        events.append(f"Dialogue: 0,{fmt(cum)},{fmt(cum+dur)},Default,,0,0,0,,{k_text}")
        cum += dur

    return f"""[Script Info]
Title: category_subs
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,56,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,60,60,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(events)}
"""

def main(cfg):
    folder = cfg['folder']
    cat_dir = os.path.join(BASE, folder)
    avatar = os.path.join(BASE, '数字人华哥解读资料/数字人形象', folder + '.mp4')
    intro = os.path.join(cat_dir, '片头.mp4')
    outro = os.path.join(cat_dir, '片尾.mp4')
    final = os.path.join(cat_dir, cfg['out_name'])

    # 1) 语音时长
    voice_dur = float(subprocess.run([FFP, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', cfg['voice']],
        capture_output=True, text=True).stdout.strip())

    # 2) 循环数字人铺到 voice 时长
    loop_mp4 = os.path.join(cat_dir, '_main_loop.mp4')
    run([FF, '-y', '-stream_loop', '-1', '-i', avatar, '-t', str(voice_dur),
         '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', loop_mp4],
        capture_output=True, text=True)

    # 3) ASS 字幕
    lines = [l for l,_ in cfg['lines']]
    durs = [d for _,d in cfg['lines']]
    ass_path = os.path.join(cat_dir, '_subs.ass')
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(build_ass(lines, durs))

    # 4) 合并视频 + 语音 + 字幕
    # 字体和 ass 放同目录，用 fontsdir='.' 避免盘符冒号问题
    font_local = os.path.join(cat_dir, 'msyh.ttc')
    if not os.path.exists(font_local):
        shutil.copy2(FT, font_local)
    main_sub = os.path.join(cat_dir, '_main_sub.mp4')
    ass_name = os.path.basename(ass_path)
    run([FF, '-y', '-i', loop_mp4, '-i', cfg['voice'], '-filter_complex',
         f"[0:v]ass='{ass_name}':fontsdir='.'[v];[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a]",
         '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '128k', main_sub],
        cwd=cat_dir, capture_output=True, text=True)

    # 5) 混 BGM（红歌纯音乐，不压人声）
    bgm = pick_bgm(folder)
    main_mix = os.path.join(cat_dir, '_main_mix.mp4')
    run([FF, '-y', '-i', main_sub, '-i', bgm, '-filter_complex',
         f'[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a0];[1:a]volume={BGM_MAIN_VOL}[a1];[a0][a1]amix=inputs=2:duration=first[a]',
         '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', main_mix],
        capture_output=True, text=True)

    # 6) 片头/片尾铺 BGM（与主片同一首配乐，听感连贯），再拼接
    def dur(p):
        return float(subprocess.run([FFP, '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', p],
            capture_output=True, text=True).stdout.strip())

    intro_a = os.path.join(cat_dir, '_intro_a.mp4')
    outro_a = os.path.join(cat_dir, '_outro_a.mp4')
    for src, outp in [(intro, intro_a), (outro, outro_a)]:
        t = dur(src)
        run([FF, '-y', '-i', src, '-i', bgm, '-filter_complex',
             f'[1:a]volume={BGM_HEAD_VOL},atrim=0:{t},asetpts=PTS-STARTPTS,'
             f'aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a]',
             '-map', '0:v', '-map', '[a]', '-shortest',
             '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-b:a', '128k', outp], capture_output=True, text=True)

    run([FF, '-y',
         '-i', intro_a, '-i', main_mix, '-i', outro_a,
         '-filter_complex',
         '[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]',
         '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-ar', '44100', '-ac', '2', final],
        capture_output=True, text=True)

    print('DONE', final)

if __name__ == '__main__':
    main(CFG)
