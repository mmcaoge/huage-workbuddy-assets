---
name: hndcw-pyq-video-promo-generator
version: 1.0.0
display_name: 朋友圈推广视频生成器
display_name_en: WeChat Moments Promo Video Generator
description: 为 hndcw.com「鸣儿」与小程序「榜上有鸣」批量生成朋友圈私域推广 15 秒竖版视频及配套文案/排期 docx。当用户要生成朋友圈推广视频、样片、口播脚本时使用。
description_zh: 批量生成朋友圈私域推广 15 秒竖版视频与配套文案排期 docx，支持多主题轮换与双产品素材分仓。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Batch-generate 15s vertical promo videos for WeChat Moments with rotating themes, voiceover scripts and schedule docx.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
---

# hndcw-pyq-video-promo-generator

为 hndcw.com「鸣儿·全域智能助手」和微信小程序「榜上有鸣」生成朋友圈私域推广的 15 秒竖版视频 + 配套文案/排期 docx。

## 能力
- 批量生成 720×1280 竖版（9:16）MP4 视频，约 12-16 秒，H.264/AAC。
- 自动生成配套封面 JPG 和每日排期/配音脚本/朋友圈文案 docx。
- 鸣儿视频：口播版（单日）+ 脱口秀版（双日）自动交替，30 天主题/城市/案例每日轮换。
- 榜上有鸣视频：7 大功能主题轮换（题库/赛事/家长端/班级擂台/错题/分享/每日精选）。

## 铁律（必须遵守）
1. **鸣儿对外动作一律说「找项目」，禁用「查项目」。**
2. **鸣儿项目来源必须完整说「招标网 / 公共资源网 / 政府采购网」，不准简化。**
3. **鸣儿数据更新用「全量更新上线」，禁用「每天几百条」等平淡说法。**
4. **每天的视频、封面、配音脚本、朋友圈文案必须都不一样。**
5. **两产品素材分仓**：
   - 鸣儿：`D:/workBuddy/Delivery/workBuddy/鸣儿.全域智能助手，朋友圈私域推广/`
   - 榜上有鸣：`D:/workBuddy/Delivery/workBuddy/榜上有鸣：朋友圈私域推广/`

## 使用方式
### 1. 鸣儿 9 月全量
```powershell
cd D:/WorkBuddy-Projects/2026-06-07-20-59-29/promotion/pyq_samples
D:/WorkBuddy/.workbuddy/binaries/python/envs/default/Scripts/python.exe _gen_v6.py
D:/WorkBuddy/.workbuddy/binaries/python/envs/default/Scripts/python.exe _gen_docx_v6.py
```
### 2. 榜上有鸣 7 天样片
```powershell
D:/WorkBuddy/.workbuddy/binaries/python/envs/default/Scripts/python.exe _gen_bang_v1.py
D:/WorkBuddy/.workbuddy/binaries/python/envs/default/Scripts/python.exe _gen_bang_docx.py
```

## 文件说明
- `_gen_v6.py`：鸣儿 30 天视频批量生成（口播/脱口秀交替、每日不同）。
- `_gen_docx_v6.py`：鸣儿排期/文案/铁律汇总 docx。
- `_gen_bang_v1.py`：榜上有鸣 7 天视频批量生成。
- `_gen_bang_docx.py`：榜上有鸣排期/文案汇总 docx。

## 依赖
- Python 3.13 managed venv
- `edge_tts`, `Pillow`, `numpy`, `qrcode`, `python-docx`
- ffmpeg 在 PATH 中可用

## 净化版 v7（华哥 2026-09-03 要求：视频广告必须「吸睛」）

### 为什么不吸睛的根因
旧 v6 视频本质是「PPT 文字卡 + 朗读」：
1. 文案是功能罗列（三网又杂又散→用鸣儿→全量更新→项目X亿），没有钩子、没有痛点反转、没有情绪。
2. 视觉是静态文字卡，没人、没场景、没动态冲击。
3. 配音是 edge-tts 默认语调，没有情绪驱动。
4. 无 BGM、无节奏卡点。

### v7 净化后铁律
1. **钩子开场**：前 3-5 秒必须抛出强痛点/冲突/悬念（如「翻烂三网，还是漏掉大单？」）。
2. **反转共情**：立即给观看者台阶——「不是你没本事，是信息被三网撕碎了」。
3. **方案证据**：鸣儿三网全量更新上线 + 今日真实数字 + 项目金额 + 业主代理电话附件直链。
4. **CTA 闭环**：结尾强引导「上 hndcw.com 找项目，长按识别」。
5. **视觉四段式**：黑底大字钩子脉冲 → 杂乱→整理对比流 → 金色大数字滚动 → 品牌蓝底二维码。
6. **配音情绪化**：用 zh-CN-YunyangNeural（稳重有力）/ zh-CN-YunxiNeural（年轻有活力），语速 +25%～+30%，靠标点断句营造节奏。
7. **BGM 垫底**：numpy 程序化 120 BPM 鼓点 loop，低音量混音到配音，卡住节奏。
8. **短视频时长控制在 15-22 秒**，完播率优先。
9. **封面取证据/大数字阶段帧**，最具冲击力。

### v7 使用方式
```powershell
# 生成 day1 净化样片（先给华哥看方向，确认后再批量）
D:/WorkBuddy/.workbuddy/binaries/python/envs/default/Scripts/python.exe D:/WorkBuddy/user-data/.workbuddy/skills/hndcw-pyq-video-promo-generator/scripts/generate_minger_pyq_video_v7.py

# 批量 30 天（待 v7 样片确认后再开启）
# 修改 generate_minger_pyq_video_v7.py 的 main() 为 1..30 循环后执行
```

## 维护
- 当前鸣儿主生成器已升级为 v7：`generate_minger_pyq_video_v7.py`。
- 如需扩展更多天数：修改 v7 `main()` 中的循环范围。
- 如需替换二维码链接：修改 v7 中的 `_qr.add_data("https://hndcw.com")`。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
