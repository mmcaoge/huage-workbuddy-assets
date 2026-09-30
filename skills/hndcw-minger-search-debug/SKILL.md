---
name: hndcw-minger-search-debug
version: 1.0.0
display_name: AI助手检索调试
display_name_en: AI Assistant Search Debug
description_zh: 调试 AI 招投标助手检索链路：真机复现、LLM 入参抓取、分诊与跨轮话题污染治理。
description_en: "Debug an AI bidding assistant search pipeline: live repro, LLM input capture and cross-turn pollution fixes."
agent_created: true
description: 调试 hndcw.com（海南社会调查网）「鸣儿」招投标智能助手的检索链路——用户反馈"查不到 / 查不准 / 答非所问 / 被历史话题污染"时使用。覆盖真机 HTTP 复现、DBG 抓真实 LLM 入参、分诊 40% 不调工具、跨轮 sector/keyword 污染治本、部署闭环。当用户说"鸣儿查不到""问 XX 答非所问""换了关键词还是旧结果""多轮对话后检索错乱"时触发。
---

# 鸣儿检索链路调试（hndcw.com / 招投标智能助手）

## 何时使用
- 用户反馈鸣儿「查不到」「本地库没有」「暂未找到」——但库里其实有数据。
- 多轮对话后检索被上一轮话题带偏（例如先问「演出」再问「海南省 中标」，结果仍只出演出类）。
- 问 A 类项目却答成 B 类（行业/sector 错配）。
- 改了检索/问答逻辑后，需要**真机验证**而非只看 grep 标记。

## 架构铁律（先读懂，别改错文件）
- 活跃路由 = `src/routes/minger.js`；`src/minger.js` 是死文件、无人导入，**勿改**。
- 链路：`/minger/api/ask` → `ask()`（src/agent/index.js）→ `detectIntent()`（src/agent/intent.js，本地确定性分诊）→ `buildMessages()`（读最近 6 轮历史）→ `chatWithTools(ROUTER_TOOLS)`（豆包 function calling）→ 命中 `search_projects` → `normalizeFilters(args,text)` → `runProjectSearch`（内含 `relaxedStrict` 降级链）→ 结果回给豆包写总结。
- 不调工具 → `answerModel()`（通用知识，**会编"查不到"并扣 15 积分**）。
- DB 写用 Node22 `node:sqlite`；部署服务器 `YOUR_SERVER_IP:YOUR_SSH_PORT`，私钥 `D:/.ssh_deploy/wb_auto2`（用时从 `C:/Users/琼崖纵队/.ssh/wb_auto2` 复制，用完即删），scp 大写 `-P`、ssh 小写 `-p`。

## 调试闭环（务必按序，先复现再改）

### 1. 真机复现（不要只跑模块 import）
模块级 `node` 直接 import 验证会"看起来通过"但线上仍坏。必须在服务器上跑真实 HTTP：
- 写 `/tmp/_httpN.sh`：用 `curl -c/-b` 同一个 cookie jar 连续 POST `/minger/api/ask`，模拟用户多轮对话（共享会话=跨轮污染场景）。
- 例：Q1「海南省各市县最新招演出会/音乐节/演唱会/优秀剧目的招投标公告」→ Q2「海南省 中标」，看 Q2 是否被 Q1 的 sector/keyword 污染。
- 用 `--data-binary "{\"text\":\"$1\"}"`（heredoc 内正确转义：`\"{\\\"text\\\":\\\"\$1\\\"}\"`）。

### 2. 抓真实 LLM 入参（DBG 日志）
根因常在 `normalizeFilters` 收到的 `args` 被历史污染。临时在 `searchCall` 分支插入：
```js
console.error('[DBG-NORM] text=', JSON.stringify(text), '| rawArgs=', JSON.stringify(args), '| filters=', JSON.stringify(filters));
```
重启后跑 HTTP，再 `pm2 logs hndcw --nostream | grep DBG-NORM` 看真实 rawArgs。
**典型污染证据**：`rawArgs={"province":"海南省","stage":"中标成交","sector":"文旅演出","keyword":"演出"}` 而 text="海南省 中标"——sector/keyword 都从历史带进来。

### 3. 四类根因与治本
1. **分诊模型非确定性不调工具（约 40% 翻车）**：豆包 `tool_choice:'auto'` 有时直接走通用知识编"查不到"。→ 在 `ask()` 末端加强制闸门：`if (GOAL_INTENTS.has(det.intent) && !isHowTo && !LOCATION_Q.test(text)) return legacyRoute(...)`。
2. **即便调了工具也 0 命中**：模型自加 `stage=招标公告`/`industry=服务` 从不被放宽。→ `relaxedStrict` 增 WIDE 档（`{stage:null,industry:null,industryHint:null}`）。
3. **跨轮 sector 污染**：`f.sector` 写成 `String(a.sector || _secFromText)` 会保留 LLM 历史 sector。→ 改为 **只认当前句**：`f.sector = _secFromText`（当前句能识别行业词则用之，否则 null，绝不继承 LLM 历史 sector）。
4. **跨轮 keyword 污染（最隐蔽）**：原守卫只在词数>3 时过滤，且 `_kept.length ? _kept : _toks` 在无匹配时**回退保留历史词**。→ 改为：
   ```js
   const _t = String(text || '');
   const _toks = String(a.keyword).replace(/\s+/g,' ').trim().split(' ').filter(Boolean);
   const _kept = _toks.filter((t) => _t.includes(t)).slice(0, 3);
   f.keyword = _kept.length ? _kept.join(' ').slice(0, 40) : null;
   ```
   **只保留当前句里真实出现的词；一个都不在→整体丢弃，绝不回退。**
5. **把历史库存说成「近期」（2026-09-17 治本）**：searchCall 命中后喂给模型的 `summary` 行**不含发布日期**（只有 title/area/stage/money/owner/dm），模型看到「已按时间倒序」就把 2024 年的老公告总结成「近期有N个」。→ 两处修：① summary 行补 `｜发布日期 ${c.date}`；② tool 消息注入北京今天（`new Date(Date.now()+8*3600e3).toISOString().slice(0,10)`）+ 时效铁律：**近90天内才可称「近期」；超3个月必须写明年份按「历史公告」表述；5条中无近90天新增时第一句必须直说「近90天无新增公告，以下为历史库存」**。
6. **relaxedStrict 从不放宽 city（2026-09-17 治本）**：模型偶发把「海口市琼山区」拆成 `city=琼山区`→规整成 `琼山`，而库 city 列只有地级市口径（`海口市`）→ 全部降级档都 AND 上 city 必然 0 命中 → 误入 ccgp 实时查兜底错说「本地库没有」。→ 在 tries 链尾补两档：`{...filters, city: null}`（保 sector/keyword）与 `{...filters, city: null, keyword: null, days: null}`。降级文案会如实说「精确匹配没有、以下是相近公告」。

### 4. 改文件与部署
- ⚠️ **Edit 工具大块改动会部分回滚** → 用 Python io 读写（见 `scripts/patch_server_file.py`）做精确字符串替换 + 断言校验。
- 改完先在服务器 `cp` 备份 `/tmp/bakN_index_*.js`，再覆盖 `src/agent/index.js`（scp `-P YOUR_SSH_PORT` 逐文件精确绝对路径到 `/www/wwwroot/hndcw.com/`）。
- `node --check src/agent/index.js` 语法校验 → `pm2 restart hndcw` → `pm2 info hndcw` 确认 online / unstable restarts 0。
- 移除 DBG 行后**必须再跑一次 HTTP 两轮复验**确认修复（见 references/debug_workflow.md）。

## 验证清单（全部过才算完）
- [ ] Q1（带行业词）→ 正确返回该行业结果
- [ ] Q2（换话题，如「海南省 中标」）→ 返回**全省全行业**，不被 Q1 污染
- [ ] 当前句 keyword 在文本中 → 保留；不在 → 丢弃（无回退）
- [ ] 分诊模型不调工具时 → 走 legacyRoute 兜底，不编"查不到"、不误扣积分
- [ ] pm2 进程 online，error log 空，DBG 行已移除

## 常见坑
- 只 grep 标记判定"已修复"会误判（曾经踩过）——**必须真机 HTTP 复验**。
- `src/minger.js`（根目录）是死文件，改它无效。
- pm2 莫名重启多为**外部人为 `pm2 restart`**（宝塔/并发会话），非崩溃；restarts 计数高但 unstable restarts=0 即正常。
- SAFE_DELETE 会拦截 `rm` 删 D:/.ssh_deploy 私钥 → 用 PowerShell `icacls /reset` + `Remove-Item -Force`。

## Resources
- `scripts/patch_server_file.py`：服务器 JS 文件精确补丁工具（备份+替换+断言）。
- `references/debug_workflow.md`：DBG 日志插入 / HTTP 复验脚本模板 / 部署闭环示例。
