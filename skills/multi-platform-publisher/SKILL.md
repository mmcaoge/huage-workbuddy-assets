---
name: multi-platform-publisher
version: 1.0.0
display_name: 多平台内容发布
display_name_en: Multi-platform Publisher
description_zh: 用 Playwright 把文章草稿自动发布到头条/搜狐/百家号/知乎/微博，覆盖 cookie 注入与草稿落库验证。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Publish article drafts to Toutiao/Sohu/Baijiahao/Zhihu/Weibo via Playwright with cookie injection.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
description: 用 Playwright 浏览器自动化把文章/草稿发布到国内内容平台（头条/搜狐/百家号/知乎/微博）。当用户要"自动发到XX平台""接XX号发布器""取cookie自动发文"时使用。覆盖 cookie 注入、编辑器填稿、UEditor 正文同步、按钮定位、草稿落库验证等已踩坑点。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
---

# 多平台内容自动发布（Playwright 浏览器自动化）

用于把生成好的文章草稿自动发布到国内平台。服务器已具备运行环境，**所有脚本在服务器跑**（本地 `D:\WorkBuddy\tmp\publisher_common\` 只是工作副本，需 scp 到服务器再 node 运行）。

## ⛔ 平台红线：正文禁留联系方式（2026-09-14 百家号封停事故 · 最高优先级）

**事故**：百家号账号被**封停**，官方弹窗原文「发布违反国家法律法规、色情低俗、**恶意营销**等」。

**根因（实锤，非推测）**：`content_library.json` **19 篇、100% 每一篇**正文结尾都挂着同一段话：
> 「加微信 18889153888（国庆），先领一份 9.9 元政策诊断，把投标前的事理顺。海南铎鸣社会调查网 · 鸣儿 · 商业情报助手。」

实测统计：每篇 **导流元素 4 处 + 价格「9.9 元」1 处**。

**必须建立的核心认知**：平台封的是**「站外导流 + 明码标价」**，**不是内容质量**。正文里出现手机号 / 微信号 / 价格，是**顶格红线**，文章写得再好也一样封。

### 发布前强制过滤清单（`content_library.json` → 模板之前）
| 元素 | 例子 | 处置 |
|---|---|---|
| 手机号 | `18889153888`、`1[3-9]\d{9}` | **删除** |
| 微信号 / 加微引导 | `加微信`、`VX:`、`加V` | **删除** |
| 价格 | `9.9 元`、`¥199` | **删除** |
| 明文外链域名 | `hndcw.com`、`http(s)://…` | 删除，或改成「主页可查」 |
| 正文外链图 | `<img src="https://…">` | 换本地上传（百家号同样拒外链图） |

### 三条必须同时记住的铁律
1. **与"对外铁律"的边界**：华哥定的「加微一律 18889153888」适用于**人工沟通 / 名片 / 门店物料**；**内容平台正文一律不留**。不冲突，是**场景区分**。
2. **三平台同源风险**：sohu / baijia / zhihu 共用同一份 `content_library.json` ⇒ **一封俱封**。改钩子必须**改内容库本身**，改单个 `template_*.json` 没用（下次生成又覆盖回来）。
3. **引流去向要换位**：内容平台只做**品牌曝光 + 搜索占位**；转化导流放到**自控阵地**（公众号 / 小程序 / 自有站）。平台内只能用平台允许的钩子（引导关注账号、@自己的号）。
4. **🛑 处置结果（2026-09-14，华哥决策）**：**三平台自动群发已整体停用**，不是"改完再发"。`crontab` 中 `5 10 * * * publish_all.sh` 已移除，留痕注释 `# [已停用 2026-09-14] 三平台自动群发（搜狐/百家号/知乎）`；crontab 备份 `automation/backups/crontab.bak_20260914_111329_stop_matrix`。**恢复前必须先清干净内容库里的联系方式与价格**，否则重启即再封。服务号发布（`oa_publish.sh` 09:45）是**自控阵地，不受影响、继续运行**。

### 「接口返回 success」≠「发布成功」
`cron_pub_matrix.log` 中出现过：`PUBLISH_RESULT {"errno":0,"errmsg":"success"}` 紧接 `FINAL_VERIFY` → **`VERIFY_RESULT_NOT_FOUND`**。
⇒ **账号受限后接口照返 success，但文章进不了后台。** 必须回后台列表按标题精确匹配实查，不能只看接口返回。
⇒ **修正后文旧结论**：曾把 `VERIFY_RESULT_NOT_FOUND` 一律解释为「文章进审核中、属预期」——该解释**仅在账号健康时**成立。若长期 NOT_FOUND 且「审核中」里也没有，应**立即怀疑账号被限制**，别继续盲发。

---

## 运行环境（服务器 YOUR_SERVER_IP）
- SSH：`ssh -i ~/.ssh/wb_auto2 -p YOUR_SSH_PORT root@YOUR_SERVER_IP`（本沙箱需 `dangerouslyDisableSandbox: true`）
- Node v22.23.2，系统 chromium：`/usr/bin/chromium-browser`，playwright-core 在 `/www/wwwroot/automation/publisher_common/node_modules/`
- 脚本目录：`/www/wwwroot/automation/publisher_common/`
- Cookie 真源：`/www/wwwroot/automation/config/platform_auth.json`（`chmod 600`），结构 `{平台:{cookie, note, updated_at}}`，cookie 为整行 `a=1; b=2; ...` 字符串
- `browser_helper.js` 提供 `launch()`（chromium headless + `--no-sandbox`）+ `parseCookies(str, domain)`（按 `;` 拆分 → 统一 domain，如 `.baidu.com`）

## 关键套路（每个平台都这样起手）
1. `launch()` → `ctx.addCookies(parseCookies(auth.X.cookie, '.域名'))` 注入登录态
2. 进发布页 → 等编辑器就绪（轮询 30–40s，百家号 CDN 极慢）→ 填标题 → 填正文 → 点真实发布/存草稿按钮
3. **验证**：重开草稿/已发布列表，确认标题+正文都落库（不只是 DOM 里有）

## 🔴 已踩死坑（必看，否则白跑）
- **Baijiahao/百家号 UEditor 没有 `window.UE` 全局**（`typeofUE === "undefined"`）。所有 `UE.instants` / `UE.getEditor().setContent()` 全部无效！正文必须进 `iframe#ueditor_0`：
  ```js
  const ifr = document.getElementById('ueditor_0');
  const doc = ifr.contentDocument, body = doc.body;
  body.focus();
  doc.execCommand('selectAll', false, null);
  doc.execCommand('insertHTML', false, html);   // 触发 UEditor 内部同步
  body.dispatchEvent(new Event('input', { bubbles: true }));
  ```
  仅 `body.innerHTML = html` 替换会写进 DOM 但不进表单状态 → 草稿正文为空、占位符"请输入正文"不消失、列表查 0 条。
- **按钮定位**：收集候选元素时，**优先 `button/a/[role="button"]`**，再退到文本最短者。之前误点嵌套 `<span>删除/存草稿</span>` 不触发 React handler，导致"已保存"只是自动保存提示、草稿没真生成。
- **点真实按钮后判断落库**：草稿模式点"存草稿"后 URL 会变出 `article_id=18...` 即落库成功；验证时按该 id 重开编辑页读 `iframe#ueditor_0` body，确认标题+正文都在、占位符消失。
- **搜狐/Quill 编辑器**：用 `document.execCommand('insertText', false, html)` 填 `.ql-editor`（不是 input）。
- **知乎/zhuanlan.zhihu.com/write 用 Draft.js**：标题是 `<textarea>`；正文是 `div.public-DraftEditor-content`（contenteditable），按段落逐个 `insertText` + 一次 `Enter` 换行即可正确同步 Draft.js 状态并触发自动存草稿。
  ```js
  const editor = document.querySelector('.public-DraftEditor-content');
  editor.click(); editor.focus();
  for (const para of paragraphs) {
    document.execCommand('insertText', false, para);
    await new Promise(r => setTimeout(r, 200));
    editor.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true }));
    await new Promise(r => setTimeout(r, 200));
  }
  ```
- **头条(mp.toutiao.com)走纯 API**：需 `a_bogus` 反爬签名，用开源生成器 Node+jsdom 调 `window._U._u` 生成，再 POST `/mp/agw/article/publish` 存草稿。头条是纯 API、搜狐/百家必须 Playwright，两条路线并存。
- **草稿清理**：
  - 百家号：按标题精确匹配，用 `span[class*="data2action_actions_delete"]` 真实点击 + 确认"确定"；别误删账号既有草稿。
  - 知乎：从创作中心内容管理页 `https://www.zhihu.com/creator/manage/creation/article` 定位标题行 → 点"更多" → "删除" → "确认"；比文章页/动态页更稳。
  - **微博（weibo.com）**："···更多"菜单**不是 `<button>`**，是 `DIV[class*="_more"]`（如 `woo-pop-wrap _more_1v5ao_27`）；删除项是 `div/span` 含"删除"文字（非 button）。流程：定位测试卡 → 点 card 内 `div[class*="_more"]` → 菜单点"删除" → 确认弹窗"确定"。脚本 `weibo_delete.js`。
- **SPA 路由**：百家号要点首页"发布作品" div 触发前端路由跳 `/builder/rc/edit`，直接 goto 编辑页会被重定向/卡死。
- **搜狐（mp.sohu.com）发布链路（2026-09-11 实跑验证 ✅）**：
  - 流程：`goto content/list`（搜狐会重定向到 `contentManagement` 工作台）→ 点"发布内容" → 等 `.ql-editor` → 填标题/正文 → `insertImage(CDN url)` 插 4 图 → 点"发布" → 原创声明选"无需声明" → 点"上传图片"(filechooser 拦截，`setInputFiles` 本地 `cover_branded.png` 作封面) → 逐个选下拉(分类/属性/栏目) → 点"确定" → 内容管理页 `titleFound:true` 即成功。
  - **搜狐正文图接受外链 CDN**（`https://hndcw.com/p1.png` 等，`insertImage` 直接成功），**与百家号相反**——百家号会因 errno:20040084 拒外链图。所以搜狐正文图不必改本地上传；但封面仍走本地上传（与统一标准一致）。
  - **去重护栏必须用「独立浏览器预检」（sohu_dedupe_precheck.js），不能用同 context 第二页查重**：在发布器主流程里 `ctx.newPage()` 开第二页去查重，会让主页面 SPA 编辑器打不开（页面变空白，`.ql-editor` 永不出现）。改用单独 `launch()` 一个浏览器查重，exit 1=重复 / 0=可发；`publish_all.sh` 里先跑预检，重复则跳过。

## 微博文章发布器结论（2026-09-11 实跑验证，重要）
- **核心结论**：微博文章（card.weibo.com/article/v5/editor）**不适合自动化**，已从 publish_all.sh 自动群发移除，改由人工手动发布。
- **验证码定位**：编辑器本身（写文章 / 填标题 / 正文 / 存草稿）零验证码；但点「下一步」进入发布设置时，页面重定向到 `https://security.weibo.com/captcha/geetest?key=...`，显示「请先验证身份 / 请按语序依次点击文字」——geetest 点序验证码，自动化无法绕过。**最终「发布」因此永远走不到**。
- **「保存草稿」路径（仅能存、不能发）**：编辑器 footer 有「保存草稿」BUTTON（精确文本 `保存草稿`），点击**不触发验证码**，URL 变 `...#/draft/<id>` 即落库。但两个硬伤：
  1. **草稿自动续写污染**：每次打开编辑器都自动 resume 同一个草稿（同 id），自动化重跑会把新内容**拼接追加**到旧草稿正文（实测单次跑出 1923 字拼接垃圾），无法干净覆盖。
  2. **本地图上不去**：正工具栏图片按钮（class `W_ficon ficon_e_image`）点击后**不出现 `input[type=file]`**（dump 得 `fileInputs:[]`），编辑器走微博图库而非本地上传，Playwright `setInputFiles`/filechooser 均失效。
- **删除脏草稿（已验证）**：草稿箱列表项 `div.list-item` → 点卡片内 `i.item-more`（class `item-more hover:text-primary`）→ 弹出菜单点「删除」→ 二次确认弹窗点「确定」→ 计数 `草稿箱 (N/30)` 归零。脚本 `weibo_delete_draft.js`。
- **决策**：微博由人工手动发布（草稿需手动过 geetest）。自动化只保证搜狐/百家/知乎三家稳定跑通；微博、头条（禁言）均不碰。

## 百家号发布器 v2 关键修复（2026-09-11 实跑验证 errno:0）
旧版 `baijia_publish.js`（pilot1–pilot13）一直 `VERIFY_NOT_FOUND`，根因两类，现已修复并实跑 `errno:0`、封面 `cover_source:"upload"`、标题匹配：

1. **最终提交按钮真相（最重要）**：百家号编辑页**没有**“确认并发布/确认发布/发表/提交”这类按钮。真实提交 = 封面设好后**再次点击**编辑器里的“发布” BUTTON（`cheetah-btn cheetah-btn-primary`，文本精确 `发布`）→ 直接触发 `POST /pcui/article/publish`，**没有独立确认弹窗**。旧脚本搜“确认并发布”永不命中。
   - 第一次点“发布”只打开发布面板（popover）；设好封面后**第二次**点“发布”才是真提交。
2. **`errno:20040084 当前图片链接异常` 根因**：发布 API **拒绝正文里的外部 http(s) 图与 data: URI 图**。旧脚本把 `https://hndcw.com/footer_brand.png`（实际 404）塞进正文 → 必失败。修复 = 正文用 `stripExternalImgs()` 剥离所有外链/dataURI `<img>`，封面改用**本地图** `setInputFiles` 上传（路径如 `/www/wwwroot/hndcw.com/public/sohu_baijia_cover.png`），5 要素钩子用**文字**版。
3. **封面上传链路（v12 验证）**：点封面 slot `div.FeEditorApp-_93c3fe2a3121c388-item` → 开 `cheetah-modal` → `setInputFiles` 到**非 editor 内的 file input**（在 `input[type=file]` 列表里找 parent 链不含 `editor-outter-wrapper|ueditor|edui` 的那个，通常 idx 1）→ 点 `div.cheetah-modal button.cheetah-btn-primary` 含“确定”。
4. **UEditor 正文插图（>3 图标准）暂不可靠**：工具栏“插入图片”按钮是 `edui-for-insertimag`，但其图库弹窗 Playwright 点击极不稳定（v4 开过一次，v5–v7 全 `NONEDITOR_INPUT_IDX -1` 失败）。**正文插图自动化先放下**，用文字版 5 要素钩子替代；>3 图标准待后续攻 UEditor 图库弹窗。
5. **终检 `VERIFY_RESULT NOT_FOUND` 分两种情况，别一律当"预期"**：账号**健康**时，发文成功 → 文章进"审核中"，不在默认 `rc/content` 列表，属正常，需查"审核中" tab 或等审核通过。账号**受限/被封**时，接口照样返 `errno:0` 但文章根本进不了后台 ⇒ **连续 NOT_FOUND 且"审核中"也查无，就是账号出问题的信号**（2026-09-14 百家号封停即为此形态）。

### 发布器统一标准（五平台通用，防封号）
- 正文 >300 字 + >3 图（百家号暂用文字钩子替代图钩子）；各平台正文**必须差异化**（用户已因重复内容被封/警告）。
- 尾部固定 5 要素文字钩子：`海南社会调查网 hndcw.com ｜ 海南铎鸣社会调查网 hndmshdcw.com ｜ 传递民意·践行价值 ｜ 鸣儿·找项目 ｜ 榜上有鸣`。
- **所有平台封面/插图一律用本地上传图，禁止塞外链图**（errno:20040084 类错误跨平台通用：发布 API 普遍拒外链图）。
- 发布窗口 10:00–11:30；去重护栏（按标题精确匹配，已发则跳过）。

## 当前进度
- ✅ 头条（纯 API a_bogus，当前被禁言 30+7 天，禁言期内不碰，解禁前需补差异化+去重+禁外链图）
- ✅ 搜狐（Playwright）
- ⛔ 百家号（Playwright，2026-09-11 v2 修复 errno:0）—— **2026-09-14 账号被封停**，官方判定「恶意营销」，实因正文含「加微信 18889153888 + 9.9 元」。**恢复发布的前提：先把内容库里的联系方式与价格彻底清干净**，否则重启即再封。
- ✅ 知乎（Playwright，专栏 Draft.js 编辑器，publish/draft/删除均验证通过）
- ⚠️ 微博（文章流 card.weibo.com/article **无法自动发布**：点「下一步」触发 geetest 验证码「请按语序依次点击文字」，自动化无法绕过；「存草稿」可零验证码保存，但编辑器会自动续写同一草稿导致内容拼接污染，且正文图片按钮不暴露 file input（本地图上不去）。结论：**微博走人工手动发布**，已移出 publish_all.sh 自动群发。短微博（weibo.com 首页框）可发但不符合 >300字+>3图 标准，不纳入。）

⚠️ **现状校正（2026-09-11，重要）**：机械发布链路五家均通，但**内容质量护栏此前没兜住 → 已踩封号/警告坑**：用户反馈搜狐/知乎发了几条都是同样信息、微博发了两条短微博、头条发了 4 条同样信息 → 头条已被禁言 30+7 天，其余平台重复内容警告。
**必须统一补全三层护栏再放量**：① 正文差异化（同主题各平台改写，禁止原样复制）；② 去重（按标题精确匹配，已发跳过）；③ 本地图（禁外链图，见 errno:20040084）。
**微博**：文章流无法自动发布（geetest 验证码在「下一步」拦截），已移出自动群发，由人工手动发布；其账号里若存在自动化残留草稿，用 `weibo_delete_draft.js` 清（点卡片 `i.item-more` → 删除 → 确定）。

### 自动群发差异化落地（prepare_daily.js v2，2026-09-11 修复）
- **旧坑**：原 `prepare_daily.js` 只生成**一份** `template_article.json`，三平台（搜狐/百家号/知乎）发**完全相同**内容 → 仍踩「同文多发」封号风险。
- **修复**：`prepare_daily.js` 改为按三平台**错位偏移**（`OFFSETS={sohu:4,baijia:5,zhihu:0}`）各选一篇不同文章，写 `template_sohu.json / template_baijia.json / template_zhihu.json`；`publish_all.sh` 分别用对应文件发布。`publish_state.json` 新增 `platform_history` 记录近 7 天各平台标题，选稿时自动避开近期已发。
- **固定尾注钩子集中化**：`prepare_daily.js` 内 `HOOK_TEXT` 统一 5 要素，生成模板时若文章本身不含「榜上有鸣」则自动追加到 text/html/weibo_text 末尾，保证每篇都带满 5 要素防封号模板（此前库里文章只含 2 要素）。
- **调试**：`node prepare_daily.js --dry --date 2026-09-12` 只打印当天三平台选题、不写任何文件；`node prepare_daily.js` 真实运行（cron 10:05 调用）。
- **cron**：`5 10 * * * publish_all.sh`（落在 10:00–11:30 窗口内）。
- **三平台每天不同文章示例（周六 2026-09-12）**：搜狐=政策红利(idx2) / 百家号=工商注册(idx3) / 知乎=系统运维(idx5)。

## 内容供给：内容库扩容（content_library.json）—— 2026-09-14

⚠️ **分发的真实瓶颈不是模板、不是链路，是"没内容可发"。**

实测 `publisher_common/content_library.json` 原仅 **7 篇**，而 `prepare_daily.js` 按周几 + 偏移量选稿 ⇒ **一周就循环完一整轮**，于是三平台反复发同样内容 —— 这就是此前"同文多发 → 头条禁言 30+7 天、其余平台警告"的**根因**（不是编辑器问题，也不是护栏没写）。

- **诊断口径**：`node -e "console.log(require('./content_library.json').length)"`。**篇数 < 20 就先扩容，不要再调发布器**。
- **扩容工具**：`/www/wwwroot/hndcw.com/scripts/intel_gen.py` —— 读站点 `data/hndcw.db` 生成**真实数据驱动的情报型文章**。比通用软文更抗"重复内容"判定，且自带导流价值。
  - 4 类生成器：① **区域招标情报**（`X省最新招标情报：本周新增 N 个政府项目` —— 7 天新增 + 行业 top3 + 阶段 top3 + 地市 top3）；② **区域中标榜**（`bid_winner` 聚合 top5）；③ **惠企政策清单**（最新 6 条）；④ **阶段风险文**（17% 项目会「更正」或「终止」，投标前先看这几点）。
  - **字段必须严格对齐现有库**：`domain / title / wordcount / cover / images / images_local / hook_cdn / hook_local / html / text / weibo_text` —— 少一个发布器就可能静默出错。生成后做一次字段完整性校验。
  - 配图：段间插 `p1/p2/p3.png`、末尾插 `hook.png`（走站点 CDN，同搜狐可用的外链图策略）。
  - 用法：`PYTHONIOENCODING=utf-8 /usr/bin/python3 scripts/intel_gen.py --apply --limit 4`（不加 `--apply` 即 dry-run）。`--apply` 按标题去重 + 自动备份原库为 `content_library.json.bak_intel_<ts>`。
  - cron（**与既有任务错峰**，避让 09:10 IndexNow / 09:20 百度推送 / 09:30 oa_gen / 09:45 oa_publish）：
    ```
    35 9 * * 1 cd /www/wwwroot/hndcw.com && PYTHONIOENCODING=utf-8 /usr/bin/python3 scripts/intel_gen.py --apply --limit 4 >> logs/intel_gen.log 2>&1
    ```
- ⚠️ **两个生成器坑**：
  1. 行业维度 SQL **必须过滤 `其他/其它/未知/空`**，否则标题会写成"其他（1965 个）"这种对外不可用的句子。
  2. 生成器外层若写成 `for kind in kinds`，**第一个生成器会吃满 limit**（实测 10 篇全是区域文）⇒ 必须改为**按省轮次的 `while` 循环**，每轮产出 region + winner + policy + stage 混合。
- **回归验证**：`node prepare_daily.js --dry --date <未来日期>` —— dry-run **只打印选题、不写任何文件**，不会污染 `publish_state.json` 与三个 `template_*.json`。确认三平台各选中不同文章才算通过。

## 对外铁律（华哥 2026-09-10 明确）
- 对外物料/文案**一律不提"AI"**，以「国庆/华哥」人设 + 行业口碑背书；加微一律 18889153888；单位名报「海南铎鸣社会调查网」不报工商主体。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
