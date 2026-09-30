# -*- coding: utf-8 -*-
"""
红歌风格原创进行曲 BGM 生成器
- 纯原创旋律（大调进行曲风格），无版权风险
- 编制：铜管 + 弦乐 + 低音 + 军鼓/镲/定音鼓
- 输出 6 首，对应 6 元类别
"""
import numpy as np, wave, os, math

SR = 44100
OUT = r'D:/workBuddy/Delivery/workBuddy/数字人华哥.解读成片/数字人华哥解读资料/背景音乐'
os.makedirs(OUT, exist_ok=True)

def m2f(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))

def env_adsr(n, sr, a, d, s, r):
    a_n, d_n, r_n = int(a*sr), int(d*sr), int(r*sr)
    s_n = max(n - a_n - d_n - r_n, 0)
    e = np.concatenate([
        np.linspace(0, 1, a_n, endpoint=False) if a_n else np.array([]),
        np.linspace(1, s, d_n, endpoint=False) if d_n else np.array([]),
        np.full(s_n, s),
        np.linspace(s, 0, r_n) if r_n else np.array([]),
    ])
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]

def fft_lowpass(x, cutoff, soft=3000.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    att = np.ones_like(f)
    mask = f > cutoff
    att[mask] = np.exp(-(f[mask] - cutoff) / soft)
    return np.fft.irfft(X * att, len(x))

def fft_highpass(x, cutoff, soft=2000.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    att = np.ones_like(f)
    mask = f < cutoff
    att[mask] = np.exp(-(cutoff - f[mask]) / soft)
    return np.fft.irfft(X * att, len(x))

def reverb(x, amount=0.25):
    out = x.copy()
    for d, g in [(0.0297, 1.0), (0.0371, 0.8), (0.0411, 0.65), (0.0437, 0.5), (0.0532, 0.35)]:
        sh = int(d * SR)
        if sh < len(x):
            out[sh:] += g * amount * x[:-sh]
    return out

# ---------- 音色 ----------
def brass(freq, dur, gain=1.0):
    """铜管/小号：丰富谐波 + 合奏失谐 + 明亮"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    w = np.zeros(n)
    # 3 个略微失谐的振荡器模拟合奏
    for det in (-4, 0, 5):  # cents
        f = freq * (2 ** (det / 1200.0))
        for k in range(1, 10):
            w += (1.0 / k) ** 0.85 * np.sin(2 * np.pi * f * k * t + k * 0.3)
    w /= 9.0
    w = fft_lowpass(w, 2600 + 1200, soft=2500)
    e = env_adsr(n, SR, 0.035, 0.10, 0.78, 0.18)
    return w * e * gain * 0.30

def strings(freq, dur, gain=1.0):
    """弦乐：慢起音 + 颤音 + 柔和"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.4 * t)
    w = np.zeros(n)
    for k in range(1, 8):
        w += (1.0 / k) ** 1.1 * np.sin(2 * np.pi * freq * k * t * vib + k * 0.7)
    w /= 7.0
    w = fft_lowpass(w, 2200, soft=2000)
    e = env_adsr(n, SR, 0.16, 0.12, 0.82, 0.28)
    return w * e * gain * 0.26

def bass(freq, dur, gain=1.0):
    """低音大号/贝斯"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.45 * np.sin(4 * np.pi * freq * t) + 0.2 * np.sin(6 * np.pi * freq * t)
    w = fft_lowpass(w, 700, soft=800)
    e = env_adsr(n, SR, 0.02, 0.15, 0.7, 0.15)
    return w * e * gain * 0.38

def snare(gain=1.0):
    """军鼓"""
    dur = 0.19
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.random.uniform(-1, 1, n)
    noise = fft_highpass(noise, 1400, soft=1200)
    noise = fft_lowpass(noise, 6500, soft=3000)
    body = 0.30 * np.sin(2 * np.pi * 195 * t) * np.exp(-t / 0.045)
    e = np.exp(-t / 0.062)
    return (noise * 0.85 + body) * e * gain * 0.34

def timpani(freq, gain=1.0):
    """定音鼓"""
    dur = 0.55
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.55 * np.exp(-t / 0.10))
    w = np.sin(2 * np.pi * np.cumsum(f) / SR)
    w += 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    e = np.exp(-t / 0.22)
    return w * e * gain * 0.42

def cymbal(gain=1.0):
    """镲"""
    dur = 1.1
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.random.uniform(-1, 1, n)
    noise = fft_highpass(noise, 5200, soft=2500)
    e = np.exp(-t / 0.30)
    return noise * e * gain * 0.20

# ---------- 作曲 ----------
# 大调音阶半音偏移
MAJ = [0, 2, 4, 5, 7, 9, 11]

def chord_notes(root, quality):
    """返回和弦音 MIDI（三和弦）"""
    if quality == 'maj':
        return [root, root + 4, root + 7]
    if quality == 'min':
        return [root, root + 3, root + 7]
    if quality == 'dom':
        return [root, root + 4, root + 7, root + 10]
    return [root, root + 4, root + 7]

PROGRESSIONS = {
    'A': [('I', 'maj'), ('V', 'maj'), ('vi', 'min'), ('IV', 'maj')],   # 经典红歌
    'B': [('I', 'maj'), ('IV', 'maj'), ('V', 'maj'), ('I', 'maj')],    # 正格终止
    'C': [('I', 'maj'), ('vi', 'min'), ('IV', 'maj'), ('V', 'maj')],   # 五十年代风
    'D': [('I', 'maj'), ('V', 'maj'), ('IV', 'maj'), ('I', 'maj')],
}

DEGREE_SEMI = {'I': 0, 'ii': 2, 'iii': 4, 'IV': 5, 'V': 7, 'vi': 9}

RHYTHMS = [
    [1.0, 1.0, 1.0, 1.0],
    [1.5, 0.5, 2.0],
    [0.5, 0.5, 1.0, 2.0],
    [2.0, 1.0, 1.0],
    [1.0, 0.5, 0.5, 2.0],
    [2.0, 2.0],
    [0.5, 0.5, 0.5, 0.5, 2.0],
    [1.0, 1.0, 2.0],
]

def build_melody(key_root, prog, bars, rng, octave=0):
    """生成红歌风格旋律：强拍和弦音、级进与跳进结合、句尾长音"""
    notes = []  # (start_beat, dur_beat, midi)
    beat = 0.0
    prev = None
    for b in range(bars):
        deg, qual = prog[b % len(prog)]
        root = key_root + DEGREE_SEMI[deg]
        ch = chord_notes(root, qual)
        pool = [c for c in ch] + [c + 12 for c in ch[:2]]
        rhy = RHYTHMS[rng.integers(0, len(RHYTHMS))]
        # 每 4 小节乐句结尾用长音
        if b % 4 == 3:
            rhy = [2.0, 2.0]
        for d in rhy:
            if d + beat > bars * 4:
                break
            # 强拍（小节第一拍）优先跳进到根音或五音
            if abs(beat % 4) < 1e-6:
                cand = [root, root + 7, root + 12]
            else:
                cand = pool
            if prev is not None:
                # 限制跳进不超过八度，尽量靠近前音
                cand = sorted(cand, key=lambda c: abs(c - prev))[: max(1, len(cand) // 2 + 1)]
            midi = int(cand[rng.integers(0, len(cand))]) + 12 * (1 + octave)
            notes.append((beat, d, midi))
            prev = midi
            beat += d
        # 补齐到小节线
        beat = (b + 1) * 4.0
    return notes

def render(track_notes, chords, bpm, drum_style, seed, total_bars):
    """合成整首"""
    rng = np.random.default_rng(seed)
    spb = 60.0 / bpm
    total_beat = total_bars * 4.0
    total = int((total_beat * spb + 2.0) * SR)
    mix = np.zeros(total)

    def place(sig, start_beat):
        i = int(start_beat * spb * SR)
        if i < 0 or i >= total:
            return
        end = min(i + len(sig), total)
        mix[i:end] += sig[: end - i]

    # 打击乐
    for b in range(total_bars):
        # 军鼓 pattern（进行曲：2、4 拍重音 + 弱起装饰）
        if drum_style == 'march':
            for off in (1.0, 3.0):
                place(snare(0.95), b * 4 + off)
            place(snare(0.45), b * 4 + 3.5)
            place(timpani(m2f(36)), b * 4 + 0.0)
            place(timpani(m2f(43)), b * 4 + 2.0)
        elif drum_style == 'light':
            place(snare(0.5), b * 4 + 2.0)
            place(timpani(m2f(36)), b * 4 + 0.0)
        elif drum_style == 'broad':
            place(timpani(m2f(36)), b * 4 + 0.0)
        if b % 4 == 0:
            place(cymbal(0.8), b * 4)

    # 低音 + 和声 + 旋律
    for (deg, root, qual) in chords:
        pass

    return mix

def compose(name, key_root, prog_key, bpm, bars, drum_style, seed,
             octave=0, lead='brass', harm=True, pad_oct=0):
    rng = np.random.default_rng(seed)
    prog = PROGRESSIONS[prog_key]
    spb = 60.0 / bpm
    total_beat = bars * 4.0
    total = int((total_beat * spb + 2.5) * SR)
    mix = np.zeros(total)

    def place(sig, start_beat, gain=1.0):
        i = int(start_beat * spb * SR)
        if i < 0 or i >= total:
            return
        end = min(i + len(sig), total)
        mix[i:end] += sig[: end - i] * gain

    # 1) 打击乐
    for b in range(bars):
        if drum_style == 'march':
            place(snare(0.95), b * 4 + 1.0)
            place(snare(1.0), b * 4 + 3.0)
            place(snare(0.42), b * 4 + 3.5)
            place(timpani(m2f(36)), b * 4 + 0.0)
            place(timpani(m2f(43)), b * 4 + 2.0)
        elif drum_style == 'light':
            place(snare(0.55), b * 4 + 2.0)
            place(timpani(m2f(36)), b * 4 + 0.0)
        else:  # broad
            place(timpani(m2f(36)), b * 4 + 0.0)
        if b % 4 == 0:
            place(cymbal(0.85), b * 4)

    # 2) 低音（每小节根音 + 五音）
    for b in range(bars):
        deg, qual = prog[b % len(prog)]
        root = key_root + DEGREE_SEMI[deg]
        place(bass(m2f(root - 24), 2.0 * spb * 0.92), b * 4 + 0.0, 0.95)
        place(bass(m2f(root - 24 + 7), 2.0 * spb * 0.92), b * 4 + 2.0, 0.75)

    # 3) 和声弦乐长音
    if harm:
        for b in range(bars):
            deg, qual = prog[b % len(prog)]
            root = key_root + DEGREE_SEMI[deg]
            ch = chord_notes(root, qual)
            for c in ch:
                place(strings(m2f(c + 12 * pad_oct), 4.0 * spb * 0.96), b * 4 + 0.0, 0.5)

    # 4) 主旋律
    mel = build_melody(key_root, prog, bars, rng, octave)
    for (sb, db, midi) in mel:
        f = m2f(midi)
        dur = db * spb * 0.94
        if lead == 'brass':
            place(brass(f, dur), sb, 1.0)
            place(strings(f, dur), sb, 0.35)
        else:
            place(strings(f, dur), sb, 1.0)
            place(brass(f, dur), sb, 0.30)

    # 5) 混响 + 淡入淡出 + 归一化
    wet = reverb(mix, 0.22)
    mix = mix * 0.82 + wet * 0.18
    fade = int(1.2 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.89
    # 无缝循环：尾部与头部交叉淡化
    xl = int(1.0 * SR)
    head = mix[:xl].copy()
    mix[-xl:] = mix[-xl:] * np.linspace(1, 0, xl) + head * np.linspace(0, 1, xl)

    # 立体声（轻微展宽）
    l = mix
    r = np.concatenate([mix[80:], np.zeros(80)])
    stereo = np.stack([l, r], axis=1)
    stereo /= max(np.max(np.abs(stereo)), 1e-9)
    stereo *= 0.89

    pcm = (stereo * 32767).astype('<i2')
    path = os.path.join(OUT, name + '.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    dur_s = len(mix) / SR
    print(f'{name}.wav  {dur_s:.1f}s  {os.path.getsize(path)/1024/1024:.2f}MB')

# ---------- 六元类别配乐 ----------
# (名称, 主音MIDI, 和声进行, BPM, 小节数, 鼓风, 种子, 八度, 主奏)
PIECES = [
    ('01_招投标项目_奋进进行曲', 60, 'B', 116, 22, 'march', 11, 0, 'brass', True, 0),
    ('02_供应商资质库_团结力量', 62, 'A', 108, 20, 'march', 23, 0, 'brass', True, 0),
    ('03_政策红利库_祖国颂', 65, 'C', 96, 18, 'broad', 37, 0, 'strings', True, 0),
    ('04_供应链商机_希望田野', 67, 'A', 120, 22, 'light', 53, 0, 'brass', True, 0),
    ('05_技术服务_实干先锋', 69, 'B', 124, 22, 'march', 71, 0, 'brass', True, 0),
    ('06_投标保函_深情祖国', 62, 'C', 88, 18, 'broad', 97, 0, 'strings', True, 0),
]

for (nm, key, pk, bpm, bars, ds, sd, oc, ld, hm, po) in PIECES:
    compose(nm, key, pk, bpm, bars, ds, sd, oc, ld, hm, po)

print('ALL BGM DONE')
