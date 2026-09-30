---
name: digital-human-huage-video-template
version: 1.0.0
display_name: 数字人华哥视频模板
display_name_en: Digital Human Video Template
description_zh: 为海南铎鸣社会调查网批量生成数字人解读类短视频，含类别模板、品牌片头片尾与完整 ffmpeg 工作流。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Batch-generate digital-human short videos with category templates, branded intro/outro and a full ffmpeg workflow.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
agent_created: true
description: 当用户需要为海南铎鸣社会调查网/鸣儿商业情报助手批量生成「数字人华哥·解读」类短视频时使用。提供 6 元类别模板、片头片尾生成、数字人循环+字幕+BGM+拼接的完整 ffmpeg 工作流。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
---

# 数字人华哥·解读成片模板化流程

## 适用场景

- 为「海南社会调查网 / 海南铎鸣社会调查网 / 鸣儿·商业情报助手」生成 9:16 竖屏短视频。
- 使用 VideoGen 生成的 5 秒数字人片段，批量产出带片头、片尾、字幕、BGM 的解读成片。
- 需要保证：每个类别固定一个数字人形象、单条视频不换装、跨视频轮换。

## 核心原则

1. **六元类别 ↔ 六个数字人固定对应**，不可在一条视频内混用多个形象。
2. **片头/片尾模板化**：每类一套 5 秒片头 + 5 秒片尾，沿用「新时代的中国人」红底金字风格。
3. **单条 5 秒数字人循环**：VideoGen 单条约 5 秒，用 ffmpeg `-stream_loop` 循环铺满正片时长，成本低且不换装。
4. **字幕用 ASS 逐字卡拉 OK**：白色未读、红色已读，底部居中。
5. **片头/片尾补静默 AAC 后再 concat**：否则 ffmpeg `concat -c copy` 会丢失正片音频。

## 六元类别与数字人对应

| 类别文件夹 | 数字人形象文件 | 片尾钩子 |
|---|---|---|
| 01_招投标项目 | 01_招投标项目.mp4 | 查项目，就找鸣儿 |
| 02_供应商资质库 | 02_供应商资质库.mp4 | 看资质，就找鸣儿 |
| 03_政策红利库 | 03_政策红利库.mp4 | 领政策，就找鸣儿 |
| 04_供应链商机 | 04_供应链商机.mp4 | 找商机，就找鸣儿 |
| 05_技术服务 | 05_技术服务.mp4 | 要落地，就找鸣儿 |
| 06_投标保函 | 06_投标保函.mp4 | 办保函，就找鸣儿 |

交付根目录：`D:\workBuddy\Delivery\workBuddy\数字人华哥.解读成片\`

## 工作流

### Step 1：准备资料

确保资料库已就位：
- `数字人华哥解读资料/数字人形象/`：6 个 mp4，按上表命名。
- `数字人华哥解读资料/技能工具/gen_intro_outro_v3.py`：生成片头片尾。
- `数字人华哥解读资料/技能工具/gen_category_video.py`：生成完整成片。
- `D:/workBuddy/tmp/digital_human/msyh.ttc`：中文字体。
- `D:/workBuddy/tmp/digital_human/bgm.wav`：背景音乐。

### Step 2：生成/更新六套片头片尾

运行：

```
python 数字人华哥解读资料/技能工具/gen_intro_outro_v3.py
```

会在每个类别文件夹生成 `片头.mp4` 和 `片尾.mp4`。

### Step 3：生成正片

编辑 `gen_category_video.py` 里的 `CFG`：
- `folder`：类别文件夹名
- `voice`：完整配音文件路径（VideoGen 原生音或 edge-tts/mp3）
- `lines`：文案列表，每项 `(句子, 时长秒)`
- `out_name`：成片输出文件名

运行：

```
python 数字人华哥解读资料/技能工具/gen_category_video.py
```

脚本自动完成：数字人循环 → 烧字幕 → 混 BGM → 拼片头片尾。

## 关键技术点

- **循环数字人**：`ffmpeg -stream_loop -1 -i avatar.mp4 -t <voice_dur>`。
- **ASS 字幕路径**：ass 文件和字体放同一目录，`ass='文件名.ass':fontsdir='.'`，避免 Windows 盘符冒号解析问题。
- **混音 BGM**：主音 100% + BGM 15%，`amix=inputs=2:duration=first`。
- **拼接**：用 `filter_complex concat=n=3:v=1:a=1`，给无音频的片头片尾先补 `anullsrc` 静音音轨。
- **输出规格**：1080×1920（9:16）、h264 + aac、44.1kHz 双声道、yuv420p。

## 背景音乐（红歌原曲演奏版）

- 华哥定调：**红歌是国民音乐，没有版权问题；红歌不能篡改**。因此必须用原版红歌旋律，而不是"红歌风格原创改编"。
- ⚠️ **曲谱铁律**：旋律必须依据**官方教材简谱**——义务教育教科书《艺术·音乐（简谱）》人教 2012 版 / 苏少 2024 版。
  - 网上红歌简谱绝大多数是**图片**；文字版多为 **AI 伪造**（音符与时值全错），照抄即篡改，一律不采信。
  - 可靠检索式：`<歌名> 简谱 1= 2/4 教材`（命中 ima.qq.com wiki 收录的教材 PDF 解析文本）。
- 已完成：`背景音乐/03_政策红利库_歌唱祖国.wav` —《歌唱祖国》1=F 2/4 中速壮大行进地，王莘词曲，教材原谱，57.9s，BPM 104。
- 其余 5 首（01/02/04/05/06）须逐首核对教材原谱后补做；未配时 `pick_bgm` 自动回退到《歌唱祖国》。
- 生成脚本 `scripts/gen_red_bgm_v2.py`（纯 numpy，无需 scipy；FFT 滤波 + 轻混响）。
- ⚠️ `scripts/gen_red_bgm.py` 是 v1 随机旋律版，被批为「幽灵音乐」，**已废弃勿用**。
- **"幽灵感"根因与修复**（务必遵守）：
  - 随机生成旋律（无歌唱性）→ 改用教材原谱旋律
  - 慢起音弦乐 attack 0.16 → 改 0.05
  - 大混响 0.22 → 改 0.07
  - 整小节长音和声 → 保留但音量压到 0.42、起音加快
  - 音符首尾相接无间隙 → 留 12% 间隙，节奏更干脆
- 混音音量（脚本顶部常量 `BGM_MAIN_VOL` / `BGM_HEAD_VOL`，华哥嫌小已调大过一档）：正片 **0.14**、片头/片尾 **0.26**。参考电平：人声 mean -29.4dB，BGM 0.14 时 mean -32.4dB（低于人声约 3dB，听得清又不压人声）。要再调直接改这两个常量重跑。

## ⚠️ 必须避开的坑

1. **音轨必须是「纯正片原声」，不能是整条成片的音轨。**
   从参考成片（如 ep2）提取的整条音轨包含它自己的片头静音（约 5s）和片尾静音（约 4s）。
   直接当正片语音用，会导致主片开头 5 秒和结尾 4 秒**没声音但数字人嘴在动**——这是被明确投诉过的缺陷。
   排查方法：`ffmpeg -i voice.m4a -af "silencedetect=noise=-40dB:d=0.3" -f null -` 看静音区间。
   修复方法：按静音区间截取纯语音段（如 `-ss 5.17 -t 25.12`）另存为 clean 音轨再使用。
2. **片头/片尾也要铺 BGM**（0.26 音量），否则正片有音乐、片头片尾死寂，听感断裂。
3. 字幕时长须与实际语音总长一致，用等分法（总时长 ÷ 句数）对齐。
4. ASS 字幕与字体必须同目录，用 `fontsdir='.'`，否则 Windows 盘符冒号会被 ffmpeg 解析错。
5. 片头/片尾无音轨时，直接 `concat -c copy` 会丢掉正片音频；必须补音轨或改用 `filter_complex concat`。

## 已知限制

- VideoGen 单条约 5 秒，循环后嘴型会重复，与参考视频同路。
- VideoGen 输出右下角自带「视频由AI生成」水印，参考视频可接受。
- 数字人性别与配音声线必须一致（男数字人用男声）。

## 资源文件

- `scripts/gen_intro_outro_v3.py`：生成 6 套片头片尾。
- `scripts/gen_category_video.py`：通用成片生成脚本。
- `references/使用说明.txt`：详细目录结构与出片流程。
- `references/数字人视频品牌片头片尾规范.md`：品牌铁律。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
