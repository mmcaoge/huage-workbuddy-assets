# -*- coding: utf-8 -*-
"""
红歌 BGM 生成器 v2
- 旋律采用「义务教育教科书·音乐(简谱)」权威版本，不改编
- 音色：明亮铜管 + 弦乐 + 低音 + 军鼓/定音鼓（进行曲编制）
- v1 的"幽灵感"根因：慢起音弦乐 + 大混响 + 随机旋律 → 已全部改掉
"""
import numpy as np, wave, os

SR = 44100
OUT = r'D:/workBuddy/Delivery/workBuddy/数字人华哥.解读成片/数字人华哥解读资料/背景音乐'
os.makedirs(OUT, exist_ok=True)

# F 大调音阶（1=F）：F G A Bb C D E
F_MAJ = [65, 67, 69, 70, 72, 74, 76]
DEG_SEMI = {'I': 0, 'ii': 2, 'IV': 5, 'V': 7, 'vi': 9}

def note_midi(deg, oct_, scale):
    """deg:1-7  oct_: 0 中音 1 高音 -1 低音"""
    return scale[deg - 1] + 12 * oct_

# ---------------- 音色（v2：明亮、干脆、少混响） ----------------
def env_adsr(n, a, d, s, r):
    a_n, d_n, r_n = int(a*SR), int(d*SR), int(r*SR)
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

def lp(x, cutoff, soft=2500.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0/SR)
    att = np.ones_like(f); m = f > cutoff
    att[m] = np.exp(-(f[m]-cutoff)/soft)
    return np.fft.irfft(X*att, len(x))

def hp(x, cutoff, soft=1500.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0/SR)
    att = np.ones_like(f); m = f < cutoff
    att[m] = np.exp(-(cutoff-f[m])/soft)
    return np.fft.irfft(X*att, len(x))

def reverb(x, amount=0.07):
    out = x.copy()
    for d, g in [(0.0197, 1.0), (0.0271, 0.7), (0.0311, 0.5), (0.0437, 0.3)]:
        sh = int(d*SR)
        if sh < len(x):
            out[sh:] += g*amount*x[:-sh]
    return out

def brass(freq, dur, gain=1.0):
    """小号/圆号：明亮、起音快、合奏失谐"""
    n = int(dur*SR); t = np.arange(n)/SR
    w = np.zeros(n)
    for det in (-5, 0, 6):
        f = freq*(2**(det/1200.0))
        for k in range(1, 11):
            w += (1.0/k)**0.8 * np.sin(2*np.pi*f*k*t + k*0.25)
    w /= 10.0
    w = lp(w, 4600, soft=3000)
    e = env_adsr(n, 0.018, 0.07, 0.80, 0.12)
    return w*e*gain*0.30

def strings(freq, dur, gain=1.0):
    """弦乐：起音适中，不再拖沓"""
    n = int(dur*SR); t = np.arange(n)/SR
    vib = 1.0 + 0.003*np.sin(2*np.pi*5.6*t)
    w = np.zeros(n)
    for k in range(1, 8):
        w += (1.0/k)**1.05 * np.sin(2*np.pi*freq*k*t*vib + k*0.6)
    w /= 7.0
    w = lp(w, 3000, soft=2200)
    e = env_adsr(n, 0.05, 0.08, 0.85, 0.16)
    return w*e*gain*0.24

def bass(freq, dur, gain=1.0):
    n = int(dur*SR); t = np.arange(n)/SR
    w = np.sin(2*np.pi*freq*t) + 0.5*np.sin(4*np.pi*freq*t) + 0.22*np.sin(6*np.pi*freq*t)
    w = lp(w, 800, soft=700)
    e = env_adsr(n, 0.015, 0.10, 0.72, 0.12)
    return w*e*gain*0.40

def snare(gain=1.0):
    dur = 0.16; n = int(dur*SR); t = np.arange(n)/SR
    noise = np.random.uniform(-1, 1, n)
    noise = hp(lp(noise, 7000, 3000), 1600, 1200)
    body = 0.32*np.sin(2*np.pi*200*t)*np.exp(-t/0.04)
    e = np.exp(-t/0.055)
    return (noise*0.9 + body)*e*gain*0.32

def timpani(freq, gain=1.0):
    dur = 0.5; n = int(dur*SR); t = np.arange(n)/SR
    f = freq*(1 + 0.5*np.exp(-t/0.09))
    ph = np.cumsum(f)/SR
    w = np.sin(2*np.pi*ph) + 0.3*np.sin(4*np.pi*ph)
    e = np.exp(-t/0.20)
    return w*e*gain*0.44

def cymbal(gain=1.0):
    dur = 0.9; n = int(dur*SR); t = np.arange(n)/SR
    noise = hp(np.random.uniform(-1, 1, n), 5500, 2500)
    return noise*np.exp(-t/0.26)*gain*0.18

# ---------------- 曲谱（教材简谱，不改编） ----------------
# 《歌唱祖国》 1=F 2/4 中速 壮大行进地  王莘词曲
# 格式：(音级, 八度, 拍数)
GECHANG_ZUGUO = [
    (5,0,1.5),(5,0,0.5),   # 5.  5    五星
    (1,0,1.0),(5,0,1.0),   # 1   5    红旗
    (3,0,1.0),(1,0,1.0),   # 3   1    迎风
    (5,0,1.5),(6,0,0.5),   # 5.  6    飘
    (5,0,1.0),(5,0,0.75),(5,0,0.25),  # 5 5. 5  扬，胜利
    (1,1,1.0),(1,1,1.0),   # i   i    歌声
    (6,0,0.75),(5,0,0.25),(4,0,0.5),(6,0,0.5),  # 6. 5 4 6  多么响亮
    (5,0,2.0),             # 5  -
    (5,0,1.0),(5,0,0.75),(5,0,0.25),  # 歌唱我
    (6,0,1.0),(6,0,1.0),   # 6 6  们
    (2,0,1.0),(2,0,0.75),(2,0,0.25),  # 亲爱的
    (5,0,1.5),(4,0,0.5),   # 5. 4  祖国，
    (3,0,1.0),(5,0,0.75),(5,0,0.25),  # 从今
    (5,0,1.0),(5,0,0.75),(6,0,0.25),  # 走向繁
    (5,0,0.5),(4,0,0.5),(3,0,0.5),(2,0,0.5),  # 荣富
    (1,0,2.0),             # 强
]
# 每小节和弦（16 小节，2/4）
GCZG_CHORDS = ['I','I','I','I','V','V','V','I',
               'I','I','IV','IV','V','V','V','I']

def render_song(name, melody, chords, scale, bpm, bars_per_repeat, repeats,
                drum='march', seed=7):
    rng = np.random.default_rng(seed)
    spb = 60.0/bpm
    total_beat = sum(d for _,_,d in melody) * repeats
    total = int((total_beat*spb + 2.5)*SR)
    mix = np.zeros(total)

    def place(sig, beat, g=1.0):
        i = int(beat*spb*SR)
        if i < 0 or i >= total: return
        end = min(i+len(sig), total)
        mix[i:end] += sig[:end-i]*g

    # 打击乐（按拍循环）
    nbars = int(total_beat/2) + 1
    for b in range(nbars):
        if drum == 'march':
            place(snare(1.0), b*2 + 1.0)
            place(snare(0.5), b*2 + 1.5)
            place(timpani(98.0), b*2 + 0.0)
        elif drum == 'broad':
            place(timpani(98.0), b*2 + 0.0)
        if b % 4 == 0:
            place(cymbal(0.8), b*2)

    # 低音（每小节根音 + 五音）
    for b in range(nbars):
        deg = chords[b % len(chords)]
        root = scale[0] + DEG_SEMI[deg]
        place(bass(root - 24, 1.0*spb*0.9), b*2 + 0.0, 0.95)
        place(bass(root - 24 + 7, 1.0*spb*0.9), b*2 + 1.0, 0.7)

    # 和声（弦乐，每小节长音，起音快不拖沓）
    for b in range(nbars):
        deg = chords[b % len(chords)]
        root = scale[0] + DEG_SEMI[deg]
        quality = [0, 4, 7] if deg in ('I','IV','V') else [0, 3, 7]
        for iv in quality:
            place(strings(root + iv, 2.0*spb*0.92), b*2 + 0.0, 0.42)

    # 主旋律（重复 repeats 次）
    seg_beats = sum(d for _,_,d in melody)
    for r in range(repeats):
        off = r*seg_beats
        beat = off
        for (deg, oc, d) in melody:
            f = note_midi(deg, oc, scale)
            # 高八度叠加让旋律更挺拔
            place(brass(f, d*spb*0.88), beat, 1.0)
            place(brass(f*2, d*spb*0.88), beat, 0.22)
            place(strings(f, d*spb*0.88), beat, 0.30)
            beat += d

    # 混音：混响大幅降低，避免空灵
    wet = reverb(mix, 0.07)
    mix = mix*0.90 + wet*0.10
    fade = int(1.0*SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix/peak*0.89
    # 无缝循环
    xl = int(1.0*SR)
    head = mix[:xl].copy()
    mix[-xl:] = mix[-xl:]*np.linspace(1, 0, xl) + head*np.linspace(0, 1, xl)

    l = mix
    r = np.concatenate([mix[60:], np.zeros(60)])
    st = np.stack([l, r], axis=1)
    st /= max(np.max(np.abs(st)), 1e-9)
    st *= 0.89
    pcm = (st*32767).astype('<i2')
    p = os.path.join(OUT, name + '.wav')
    with wave.open(p, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f'{name}.wav  {len(mix)/SR:.1f}s  {os.path.getsize(p)/1024/1024:.2f}MB')

if __name__ == '__main__':
    # 《歌唱祖国》→ 03 政策红利库
    render_song('03_政策红利库_歌唱祖国', GECHANG_ZUGUO, GCZG_CHORDS,
                F_MAJ, bpm=104, bars_per_repeat=16, repeats=3, drum='march', seed=7)
    print('DONE')
