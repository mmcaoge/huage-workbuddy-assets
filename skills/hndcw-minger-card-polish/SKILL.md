---
name: hndcw-minger-card-polish
version: 1.0.0
display_name: AI助手卡片装扮
display_name_en: AI Assistant Card Polish
description_zh: 装扮 AI 助手的项目结果卡与对话界面，覆盖模板双份同步、回归测试与上线冒烟闭环。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Polish an AI assistant result cards and chat UI with dual-template sync, regression and smoke tests.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
description: 装扮/修改 hndcw.com 鸣儿（政府招投标智能助手）的项目结果卡与对话界面。当用户提出「装扮鸣儿」「鸣儿卡片加个 xxx」「鸣儿这里显示不对」「项目卡样式/顺序/字段调整」「鸣儿回答文案改一下」等需求时使用。覆盖 EJS+JS 双份同步、回归测试、上线冒烟的完整闭环。
agent_created: true
---

# 鸣儿装扮流程（hndcw.com）

鸣儿是 hndcw.com 的门面——**首页 `https://hndcw.com/` 是 302 → `/minger`**，所以鸣儿的每处视觉/文案改动都是高优先级。

## 一、代码位置（改前必读）

| 位置 | 文件 | 说明 |
|---|---|---|
| 卡片结构（服务端直出历史卡） | `views/minger/chat.ejs` 第 65~90 行 `history.forEach` | **EJS 顶层** |
| 卡片结构（JS 动态卡） | `views/minger/chat.ejs` `cardHtml(c, n)` / `addCard(c, i)` | **JS 一份** |
| 徽章配色 | `stageCls()` / `moneyCls()` | **EJS 顶层与 JS 各写一份，改一处必须改两处** |
| 样式 | `public/css/minger.css` | `.pcard` / `.pc-t` / `.pc-r` / `.pc-n` / `.pc-fz` |
| 回答话术 | `src/agent/index.js` `scopeText` 组装处（约 395~420 行） | |
| 意图解析 | `src/agent/intent.js` | |
| 指代/翻页 | `src/agent/index.js` `resolveReferral()` + `src/agent/memory.js` | |
| 卡片字段 | `src/agent/search.js` `toCard(p)` | |

## 二、三条不可违背的约束

### 1. 卡片序号必须与后端对齐
后端 `memory.js` 的 `focusCard()` 取 `cards[n-1]`（**n 从 1 起**）；前端卡序是 `i+1`。
**改任一边都要同步另一边**，否则用户说「第二个」会指错卡。
多卡才标号（`cards.length >= 2`），单卡不标（「①」单独出现反而是干扰）。

### 2. 🔴 EJS 注释里不能出现 `<%= %>` / `<%-` 字面文本
会被 EJS 当开标签 → `Could not find matching close tag for "<%-"` → **整页 500**（已踩）。
要写注释用 `<% /* ... */ %>`，且注释**正文**里也不能出现 `<%` 序列。

### 3. `views/404.ejs` 必须存在
`src/routes/articles.js` 会 `render('404')`。缺了这个视图，访问不存在的资讯时
Express 抛 `Failed to lookup view "404"` → **错误处理器自己再崩一次，用户看到 500 而不是 404**。

## 三、改动闭环（按顺序做，别跳）

### 步骤 1：改代码
EJS 顶层 + JS 动态 + CSS 三处一起改。改完立刻搜一遍：`grep -n "旧标记" views/minger/chat.ejs` 确认两处都改到。

### 步骤 2：跑回归测试
```bash
cd D:/WorkBuddy-Projects/2026-06-07-20-59-29/hndcw
node tmp/tpl_card3.mjs
```
该测试直接渲染 `chat.ejs` 的 `#stream` 区块（用正则从模板里抠出来），覆盖：
序号 ①②③ 不冒 ④ / 单卡不标号 / 业主行渲染 / 「未披露」降灰 `pc-none` / 锁定卡不给白送 /
`fuzzy` 只出现在补位卡 / 无 HTML 转义 / 无残留 EJS 标签。**共 14 项，改卡片结构后必跑。**
新增卡片字段时往这个文件里补断言。

> 注意：整页渲染需要 `isLogin/referralUrl/user/tab` 等 locals，单独渲染 `chat.ejs` 会报
> `isLogin is not defined`。所以测试只抠 stream 区块，**不要渲染整页**。

### 步骤 3：本地起服务冒烟
本机无 `pgrep`；本地 curl **默认走代理会返回 502**，必须 `--noproxy '*'`；
起→测→kill 要放在**同一条 Bash 命令**里（否则会话结束进程被回收）：
```bash
(PORT=3055 node src/server.js > tmp/smoke.log 2>&1 & echo $! > tmp/smoke.pid) ; sleep 4 ; \
curl -s --noproxy '*' -o tmp/m_out.html -w "HTTP %{http_code}\n" http://127.0.0.1:3055/minger ; \
kill $(cat tmp/smoke.pid) 2>/dev/null ; grep -i "error" tmp/smoke.log | head -5
```
⚠️ 输出文件写 `tmp/`（D 盘项目内），**不要写 `/tmp`**（Git Bash 下 grep 读不到）。
ℹ️ 本地库只有几百条样本，检索结果不代表线上；**本地只验证渲染与报错，不验证命中数**。

### 步骤 4：部署
逐文件精确 scp 到**服务器项目根目录**（`/www/wwwroot/hndcw.com/tmp/` **不存在**，传过去会 `dest open ... Failure`）：
```bash
SSHOPT="-i ~/.ssh/wb_auto2 -o UserKnownHostsFile=C:/Users/琼崖纵队/.ssh/known_hosts -o StrictHostKeyChecking=accept-new"
scp -P YOUR_SSH_PORT $SSHOPT views/minger/chat.ejs  root@YOUR_SERVER_IP:/www/wwwroot/hndcw.com/views/minger/chat.ejs
scp -P YOUR_SSH_PORT $SSHOPT public/css/minger.css   root@YOUR_SERVER_IP:/www/wwwroot/hndcw.com/public/css/minger.css
scp -P YOUR_SSH_PORT $SSHOPT src/agent/index.js      root@YOUR_SERVER_IP:/www/wwwroot/hndcw.com/src/agent/index.js
ssh -p YOUR_SSH_PORT $SSHOPT root@YOUR_SERVER_IP "pm2 restart hndcw"
```
切忌「多源→单目录」平铺 scp，会把 `src/routes/x.js` 落错成 `src/x.js` 致 502。

### 步骤 5：线上验证（服务器上 curl 也要 `--noproxy '*'`）
```bash
ssh -p YOUR_SSH_PORT $SSHOPT root@YOUR_SERVER_IP "cd /www/wwwroot/hndcw.com && \
curl -s --noproxy '*' -o /dev/null -w 'minger HTTP %{http_code}\n' https://hndcw.com/minger && \
curl -s --noproxy '*' https://hndcw.com/css/minger.css | grep -c '新标记' && \
pm2 logs hndcw --lines 20 --nostream 2>/dev/null | grep -i error | tail -5"
```
`/minger` 应 200，CSS 里能 grep 到新类名，error log 无新增。

### 步骤 6：提交
```bash
git add -A && git commit -q -m "..." && git log --oneline -1
```
提交后用 `git log --oneline -1` 复核（曾经报 "no changes added" 但实际已提交，别重复提交）。

## 四、已有的装扮成果（别重复造）

- **阶段徽章**：招标金 `st-bid` / 中标成交青 `st-win` / 更正变更蓝 `st-chg` / 废标终止红 `st-dead` / 单一来源 `st-solo` / 磋商谈判询价 `st-talk`
- **预算层次**：有金额用 `--gold2`，「公告未披露」走 `.pc-none` 降灰
- **序号徽章** `.pc-n`：多卡才标，与后端 `cards[n-1]` 对齐
- **沾边标记** `.pc-fz`：放宽条件补位的卡渲染「沾边 · 放宽条件补的，不是精确命中」
- **鸣儿头像动效**：AI 消息弹入 `avPop` / 思考点头 `avNod` / 首屏浮动 `hiFloat`，带 `prefers-reduced-motion:reduce` 降级
- **一键追问 chip**：换一批 / 〈城市〉更多 / 怎么投标，**纯规则零 token**

## 五、鸣儿已有的后端能力（前端没做好 = 能力空转）

`resolveReferral()` 已支持（零 token、不查库）：
「第二个／第3条／第5家」「最新的」「预算最大的」「这家采购人还发过别的项目吗」
「再来/再找/更多/换一批」（按 `minger_search_context` 翻页并排除已展示的 dm_code）。

**教训**：序号指代后端早就好了，但前端卡片三年没有序号，用户根本数不出来——
**改前端前先确认后端能力是否已被前端暴露出来**。

## 六、清理

一次性诊断脚本**挪进** `/www/wwwroot/hndcw.com/_archive_tmp/`（**挪不删，留底**）。
保留 `title_audit.py`（改标题规则要用）与全部 `collect_*.py` / `clean_*.py`。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
