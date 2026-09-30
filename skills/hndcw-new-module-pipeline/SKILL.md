---
name: hndcw-new-module-pipeline
version: 1.0.0
display_name: 网站新功能上线流水线
display_name_en: New Module Pipeline
description_zh: Node/Express/EJS/SQLite 站点新功能的设计、真实鉴权端到端验证、部署与零残留收尾。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Design, E2E-verify with real auth, deploy and clean up new modules for Node/Express/EJS/SQLite sites.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
description: 为 hndcw.com（海南社会调查网，Node/Express/EJS/SQLite/pm2）开发新功能板块，或修改既有后台/前台页面、修线上 bug 时的标准流程——设计、真实鉴权端到端验证、服务器部署与零残留收尾。含"无需密码的后台 E2E"方法（伪造 session 直连受保护路由，含 cookie 签名格式与"假通过"陷阱）、"本机 Edge + playwright-core 真浏览器验收"（真点击真截图，不装浏览器、不碰 C 盘）、"上传前本地 EJS 渲染冒烟"、"零依赖生成 xlsx 报表/导出"（手写 ZIP+OOXML，不引第三方表格库）、"提交→审核→发布"UGC 审核制度通用设计、"功能存在但用户找不到=没做"的入口可达性审计（含后台新页面必须挂进 admin 导航）、离线快照必须绝对化，以及 scp/并发编辑/EJS 注释截断/EJS 转义/bfcache/统计分母 等踩坑清单。适用于社区/法律/项目库/问卷/会员/委托方建卷等模块开发与线上问题修复。
agent_created: true
---

# hndcw.com 新模块开发部署流水线

## 触发条件
当用户要求为 `hndcw.com` 新增板块、补全 45 模块清单中的未开发项、或继续按顺序开发下一个模块时，使用本流程。

## 关键工程事实（必须先核对）

- **项目路径**：`D:/WorkBuddy-Projects/2026-06-07-20-59-29/hndcw`
- **数据库**：SQLite；`db.js` 在 **`db/db.js`**（不是 `src/db/db.js`）
- **本地 Node**：`C:/Users/琼崖纵队/.workbuddy/binaries/node/versions/22.22.2/node.exe`
- **本地服务端口**：`PORT=3100`
- **服务器**：`YOUR_SERVER_IP`，SSH 端口 `YOUR_SSH_PORT`，root，密钥 `~/.ssh/wb_auto2`，部署目录 `/www/wwwroot/hndcw.com`
- **PM2 进程名**：`hndcw`
- **部署命令链**：`tar -xzf /tmp/<pkg>.tar.gz && node db/migrate.js && node _diag/seed_<x>.mjs && pm2 restart hndcw`
- **品牌铁律**：全站显示「海南社会调查网」，不出现「铎鸣」字样
- **表单提交铁律**：前端 fetch 必须用 `URLSearchParams` 发 `application/x-www-form-urlencoded`，Express 只解析 urlencoded，`FormData` 会导致 `req.body` 为空
- **权限中间件**：`requireAuth`、`requireRole(...roles)` 在 `src/middleware/auth.js`
- **快捷登录**：`/login?as=admin|user|merchant` 用于本地测试
- **许可证闸门**：`config/license.js` 控制收费/撮合入口；当前双证关闭，只做免费信息展示，不开发支付/分账

## 标准化流程

### 1. 任务登记
创建 TaskCreate，描述：新增表、路由、视图、样式、种子、本地验证、服务器部署。

### 2. 现状摸排（并行读取）
- `db/schema.sql`（看表定义风格、找追加位置）
- 目标路由文件（如 `src/routes/community.js`、`src/routes/market.js`）
- 相关视图与 `views/partials/header.ejs`
- `public/css/brand.css`（找样式追加位置）
- 已有 `_diag/seed_*.mjs` 作为种子脚本模板

### 3. 设计与实现
按以下顺序落代码：

1. **数据表**：在 `db/schema.sql` 末尾追加 `CREATE TABLE IF NOT EXISTS ...` 与索引。使用自增主键、TEXT 字段、status 状态字段、created_at/updated_at。
2. **路由**：在对应 router 文件末尾、`export default router;` 之前新增路由。含列表/筛选、新增(GET/POST)、详情，必要时含接单/报名/提交等动作路由。
3. **视图**：在 `views/` 新增 `.ejs`。保持与现有页面一致：`<%- include('partials/header', {BRAND, title:'...'}) %>`、`page-hero-blue`、`page-wrap`、`<%- include('partials/footer') %>`。
4. **入口**：在 `views/community.ejs` hub 或 `partials/header.ejs` 导航加入口。
5. **样式**：在 `public/css/brand.css` 追加模块专属类名（如 `.nh-*`、`.ca-*`），保持蓝色品牌色系。
6. **种子**：在 `_diag/` 新增 `seed_<module>.mjs`，使用 `import { getDb } from '../db/db.js';`，先查数量已满足则跳过，保证幂等。

### 4. 本地验证
```bash
cd /d/WorkBuddy-Projects/2026-06-07-20-59-29/hndcw
node db/migrate.js
node _diag/seed_<module>.mjs
PORT=3100 C:/Users/琼崖纵队/.workbuddy/binaries/node/versions/22.22.2/node.exe src/server.js
```
- `curl` 验证列表/详情/新增页面状态码
- 登录测试：`curl -c cookie.txt "http://127.0.0.1:3100/login?as=user"`
- 提交测试：用 `--data-urlencode` 发 POST
- Playwright 截图：保存到 `_diag/shot_<module>_<page>.png`

### 5. 服务器部署
```bash
cd /d/WorkBuddy-Projects/2026-06-07-20-59-29/hndcw
rm -f ../hndcw_<module>.tar.gz
tar -czf ../hndcw_<module>.tar.gz src views public db _diag package.json package-lock.json
scp -P YOUR_SSH_PORT -i ~/.ssh/wb_auto2 -o StrictHostKeyChecking=no ../hndcw_<module>.tar.gz root@YOUR_SERVER_IP:/tmp/
ssh -p YOUR_SSH_PORT -i ~/.ssh/wb_auto2 -o StrictHostKeyChecking=no root@YOUR_SERVER_IP "cd /www/wwwroot/hndcw.com && tar -xzf /tmp/hndcw_<module>.tar.gz && node db/migrate.js && node _diag/seed_<module>.mjs && pm2 restart hndcw"
```
部署后立刻服务器本地冒烟：
```bash
ssh ... "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/<new-path>"
```

### 6. 收尾
- 更新 `C:/ProgramData/WorkBuddy/chromium-env/1tz6mf1/WorkBuddy/2026-06-07-20-59-29/.workbuddy/memory/MEMORY.md` 的模块进度表与总数
- 追加到当日 `2026-08-19.md`（或当天日期）工作日志
- TaskUpdate 标记任务完成
- 用 `present_files` 呈现 Playwright 截图

## 常见坑

- **中文 SQL 字符串必须用单引号**：SQLite 中 `"待接单"` 会被当成列名，引发 `no such column`。
- **tar 包输出路径**：必须放在 `../hndcw_<x>.tar.gz`，不能放在 `_diag/` 下，避免递归打包自身。
- **服务器解压不生效**：tar 解压后务必 `ls -la` 检查关键文件时间戳，必要时重新 `tar -xzf`。
- **端口占用**：本地 3100 被旧进程占用时，用 PowerShell `Stop-Process` 杀进程，Git Bash `taskkill` 可能失败。
- **CSS 网格**：社区 hub 的 `.cm-hub-cats` 已改为 `repeat(auto-fit, minmax(150px,1fr))`，增加模块会自动换行。
- **scp 必须大写 `-P`**：`scp -p YOUR_SSH_PORT` 会把端口当本地文件（`stat local "YOUR_SSH_PORT"` 报错）；ssh 用的小写 `-p` 不能混用。反向地，Windows 本地源路径要配 `MSYS_NO_PATHCONV=1` + `D:/...` 形式，否则 `/d/...` 被 Windows scp 拒绝。两类命令分开执行。
- **同一文件严禁并行发多个 Edit**：工具可能返回 success 但内容被静默回退（曾一次发 7 个 Edit，3 处丢失，直接导致线上 `is not defined` 500）。同一文件一律串行单条 Edit，改完用 `grep -c` 逐项核对再上传。
- **EJS `<%= %>` 会对已转义字符串二次转义**：把 JSON 塞进 HTML 属性必须用 `<%- %>` 输出，否则引号变成 `&amp;quot;`，前端 `JSON.parse` 必然失败。
- **EJS 模板引用未定义变量 = 运行时 500**（编译期查不出）；新增模板变量必须确认对应 route 的 `render` 已传参。
- **新增题型/状态枚举必须在所有循环里显式排除**：统计/CSV/表格的 `else` 兜底分支会吞掉新类型（分节标题曾被当普通题渲染出空饼图）。统一 `var AQ = questions.filter(q => q.type !== 'section')` 并替换全部引用。
- **后台页面必须显式 `Cache-Control: no-store`**：否则浏览器 bfcache 会在点「返回」时还原旧页面，表现为"按钮点了没反应"（已真实误判一次）。
- **SQLite `LIKE` 对 ASCII 不区分大小写**：清理临时数据用 `GLOB 'qa*'` 复核，`LIKE 'qa%'` 会命中真实用户 session 造成误判。
- **验证脚本放 `/tmp` 时 `require('ejs')` 解析不到站点 node_modules**：须放站点目录内运行、用完即删；`node --check` 也须在含 `"type":"module"` 的 package.json 目录下执行才能正确解析 ESM。
- **单值状态枚举别硬塞进两态模型**：问卷 `status` 是三态（`published` 收集中 / `draft` 草稿=从未发布 / `closed` 已下线）。曾把"下线"也写成 `draft`，导致列表里全显示「草稿」，这正是用户判定"下线是摆设"的成因之一。新增状态前先看模板里是否已预留分支。
- **统计里「有效份数」不能用"能转成数字"来判断**：`computeStats` 曾写 `if(!isNaN(num)){sum+=num;n++}`，于是文字选项的单选题 `Number('咨询响应')=NaN` → `n=0` → 页面显示「单选 · 有效 0 份」且各选项占比一律 `0%`（实际有票）。评分/NPS 因答案本身就是数字才一直正常，所以这个 bug 藏得很深、只有文字选项单选才暴露。正解：`n++` 只代表"该题有一次有效作答"，数字求和单独留给 rating/nps。**后台 `src/routes/questionnaire.js` 与委托方 `src/routes/client.js` 各有一份同源 `computeStats`，必须一起改。**
- **SSH 偶发 `Permission denied (publickey)` 不是密钥坏了**：同一条密钥上一条命令成功、下一条就失败，多为连接抖动（并发发起多条 ssh 时更常见）。正确反应是**重试 + 把 ssh 调用串行化**，不要怀疑密钥、更不要重配。
- **EJS 注释正文里不能出现 EJS 的结束标记**：`<%# ... %>` 注释以**第一个** `%>` 结束。首版把用法示例写进注释（含 `<%= s.id %>`），内层 `%>` 把注释提前截断 → `Could not find matching close tag for "<%#"` → 引用它的页面**成片 500**。`node --check` 查不出来（这是模板层问题，不是 JS 语法），只能靠部署后 curl 抓页面才发现。注释里描述用法时不要带可执行的模板标记。

## 修线上 bug 的排障顺序（先证伪，别急着改代码）

用户说"某按钮是摆设 / 点了没用"时，先分清是**后端坏了**还是**体验断了**，再动手：

1. **查 nginx 访问日志，确认请求是否到达服务器**
   `grep -hE "POST /admin/<x>" /www/wwwlogs/hndcw.com.log | tail -20`
   - 有 `POST ... 302` → 请求到了、后端也执行了 → 问题在**前端体验**（跳错页 / 缓存 / 状态语义没变化）。
   - 完全没有记录 → 前端没绑事件，或被 CSS/JS 拦截。
2. **查数据库真实状态**，确认是否落库：`sqlite3 data/hndcw.db "SELECT id,status,updated_at FROM xxx"`。已落库 ⇒ 后端没问题。
3. **验证功能实际效果**（如"下线后公开链接是否真失效"）：`curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/q/<code>`。
4. 三者交叉即可定位。

真实案例：`下线` 后端完全正常（状态已落库、公开链接已 404），但 `POST` 后 302 跳到**详情页**，用户按返回时 bfcache 还原旧列表 → 看着像没生效（用户连点了 5 次）。修法 = 原地 AJAX 更新本行 + 重定向回列表页 + `no-store` + 三态语义。

## 后台 & 委托方页面：真实鉴权 E2E（无需密码）

受 `requireRole('admin'|'client')` 保护的页面无法匿名验证。不要退化成"只 render 模板 mock"，可以**直接造一条合法会话**，对生产做真实 HTTP 断言：

```js
// session 存在独立库 data/sessions.db（不是 data/hndcw.db）
// 密钥默认值 'hndcw-session-secret-dev'（server.js 未设 SESSION_SECRET 时）
const { DatabaseSync } = require('node:sqlite');
const crypto = require('node:crypto');
const sdb = new DatabaseSync('/www/wwwroot/hndcw.com/data/sessions.db');
const sid = 'qaE2E' + Date.now().toString(36);           // 可识别前缀，便于清理
sdb.prepare('INSERT INTO sessions (sid,sess,expired) VALUES (?,?,?)').run(sid,
  JSON.stringify({ cookie: { expires: new Date(Date.now() + 3600e3).toISOString(),
                             path: '/', httpOnly: true, secure: true, sameSite: 'lax' },
                   uid: 16 }),                            // uid=16 = admin（曹中华）
  Date.now() + 3600e3);
const sig = crypto.createHmac('sha256', 'hndcw-session-secret-dev')
                  .update(sid).digest('base64').replace(/=+$/, '');
const COOKIE = 'connect.sid=' + encodeURIComponent('s:' + sid + '.' + sig);
// 之后用 http.request 带 Cookie 头访问 127.0.0.1:3000 即可
// （cookie 的 secure 标志只影响 Set-Cookie，不影响服务端解析）
```

配套要点：
- `uid` 由 `SELECT id,username,role FROM users WHERE role='admin'` 取得；会话里存的键是 `uid`（见 `src/middleware/auth.js`）。
- ⚠️ **cookie 只能放 `'s:' + sid + '.' + 签名`，绝不能把 JSON 塞进去**。`cookie-signature` 的 `unsign` 取 `input.slice(0, lastIndexOf('.'))` 当作 sessionID，所以签名对象**只有 sid**；sessionID 必须**恰好等于 sessions 表的 `sid` 主键**。2026-09-17 连错两次：先写成 `s:<sid>.<base64(JSON)>.<sig>`，后又漏了密钥前缀只写 `'dev'` —— 两者都表现为"怎么都登录不上"。
- 密钥真源：`src/server.js` 是 **`secret: 'hndcw-session-secret-' + (process.env.SESSION_SECRET || 'dev')`**。别只取 `'dev'`。
- 关于"默认密钥算不算漏洞"：**不能远程利用**。因为 `saveUninitialized: false`，sessionID 必须在 `sessions` 表里存在才会被当作已登录；伪造 cookie 只能靠**写库**，而那需要服务器权限。所以这套伪造法之所以可行，前提正是我们能用 SSH + sqlite 写 store。生产环境的 `SESSION_SECRET` 建议设置（纵深防御），但不必当成在线可利用的洞去救火——设置它会让所有人（含用户自己）重新登录。
- ⚠️⚠️ **最容易骗过自己的坑：断言不能只看状态码**。会话无效时受保护页返回 `302 → /login`，而 urllib/curl 默认**跟随重定向**，最终拿到的是**登录页的 200** —— `assert status == 200` 会"假通过"。必须同时断言页面内容（如 `'问卷中心' in html`），或者用**不跟随重定向**的 opener 断言 `302 + Location:/login`。同理，"管理员已登录"这类前置条件也要用内容断言，否则后面所有步骤的失败都会被误判。
- 双模接口（AJAX / 原生表单）**两条路径都要断言**：`Accept: application/json` → JSON 原地更新；`Accept: text/html` → `302 + session flash`。
- `flash` 要验证"**读后即清**"：第一次 GET 有横幅、第二次 GET 无。
- 脚本 `finally` 删除该 sid；清理后用 `GLOB`（区分大小写）复核，避免 `LIKE` 误判。
- **清理后要自证**：再用旧会话访问受保护页应回到 302。这一条同时证明"会话真的是鉴权凭据"。
- ⚠️ **别把临时脚本写进网站根目录**：`/www/wwwroot/hndcw.com/` 下的 `*.py` / `*.mjs` / `*.cjs` 实测不可公网下载（只有 `/public` 被静态服务，根目录脚本返回 404），但 scp 上去的脚本必须用完即删，别留在根目录（那里已积压了 40 多个历史采集脚本）。
- **截图留证的首选是真浏览器直连生产站**（见下节「真浏览器 E2E」）。离线 HTML 快照只能当留档，**不能当验收物**——2026-09-17 就因快照里残留根相对路径，被用户点出 `NoSuchKey` 并判"你还是没有跑通"。真要留离线快照，**只注入 `<base href="https://hndcw.com/">` 是不够的**：base 只让 CSS/JS 加载成功，**点击站内链接仍会被预览器当成它自己的路径**（`href="/admin/x"` → `/page/<id>/0/admin/x` → NoSuchKey）。必须把 `href|src="/..."`、CSS 里 `url(/...)`、以及 **JS 字符串里的 `'/api/...'`** 全部改写成绝对域名，并**放弃 iframe 聚合页**（`./快照/x.html` 在预览器里同样不可靠）。改完必须用浏览器以 `file://` 逐个自检：正文文本 >100 字、`document.styleSheets` 已加载、失败请求 0、无残留根相对路径。

## 上传前先本地把模板渲染一遍（拦住"运行期 500"）

`node --check` 只查 JS 语法，**查不出 EJS 里的运行时 ReferenceError**；EJS 注释截断更会成片 500（见下文踩坑清单）。所以在 `scp` 之前先本地跑一次渲染冒烟：

```js
// D 盘装 ejs（别装 C 盘）：npm i ejs
import ejs from 'ejs';
import { readFileSync } from 'node:fs';
// 用线上真实数据喂模板（可从服务器 sqlite 导出 survey/questions/responses 存成 dump.json），
// 并按"各状态枚举"各渲染一遍（如审核状态 pending / approved / rejected 都要过一遍）
ejs.render(readFileSync('views/admin/questionnaire.ejs', 'utf8'), data,
           { filename: 'views/admin/questionnaire.ejs', root: 'views' });
```

- 需要把**服务端 `res.locals` 注入的全局**一起喂进去，否则会误报失败：`config/brand.js` 的 **`BRAND`**（`_foot.ejs` 用到）、`app.locals.fmtBJ` / `fmtDate`。
- 需要 `include` 的局部文件（`_head` / `_foot` / `partials/export_modal`）要在本地按同样的目录层级摆好。
- ⚠️ 带 include 的模板失败时，`e.message` 可能只显示"某模板:行号"，真正原因在**栈的更深处**。2026-09-17 就因只打印 `e.message.split('\n')[0]` 而误判成"自己的代码有问题"，实际只是测试台没喂 `BRAND`。要么打印 `e.stack`，要么直接看 `e.message` 全文。
- 纯语法层面可先用 `ejs.compile(src)` 逐个文件快速扫一遍，比完整渲染快。

## 上传后必须复核的三件事（部署闭环）

1. `grep -c <关键新标识> <每个上传的文件>` —— 确认上传的确实是新版本（scp 静默失败过）。
2. 服务端 `node --check` 每个改动的 `.js`。
3. `pm2 restart` 后**看错误日志的"最新时间"**，别被历史报错骗了：`/root/.pm2/logs/hndcw-error.log` 里会长期留着以前的事故栈，重启时因为写入 SQLite 的 `ExperimentalWarning` 而刷新文件 mtime，看起来像"刚出错"。判断新错误的办法是看行号/内容是否指向本次改动，或先记下当前行数再对比。



真实案例：问卷系统建卷能力 100% 可用，但用户（管理员）反馈"**没有建模版的地方**"。根因不是功能缺失，是**入口只写给了委托方角色**：

## 功能"存在"但用户找不到 = 没做（入口可达性审计）

真实案例：问卷系统建卷能力 100% 可用，但用户（管理员）反馈"**没有建模版的地方**"。根因不是功能缺失，是**入口只写给了委托方角色**：

- `views/questionnaire_list.ejs` 里建卷按钮的条件是 `user.role==='client'` → 管理员反而看不到；
- 管理员唯一能点的 CTA 是「申请建卷权限」→ `/apply` → 页面底部「已有账号？直接登录」→ `/login`（已登录则跳 `/user/center`）→ **用户中心一个问卷入口都没有** ⇒ 死循环。

铁律：
1. **任何"按角色开放的能力"都要在每个入口处按角色分流**，不能只写 `=== 'client'`。统一模式：
   `admin → /admin/<module>`；`client → /client`；其余 → 公开页或申请页。
   入口至少覆盖三处：**公开列表页顶部 CTA、用户中心侧边菜单、用户中心卡片位**（再加 header/tabbar 更佳）。
2. **申请类页面必须识别"已具备权限者"**：已登录且角色已达标时，不要继续渲染申请表单，改为提示「无需重复申请」+ 直达后台按钮，并让底部链接不再出现「直接登录」。
3. **`requireRole('client')` 不含 admin** ⇒ 管理员访问 `/client` 会 403。给管理员指路时一律指向 `/admin/*`，**不要擅自放宽角色门禁**（E2E 要断言 403 仍然成立）。
4. 验收必须走"**用户实际点击路径**"，不能只断言路由 200。先 `grep -rnE 'href="/q"' views/` 看目标页到底被谁链到——`/q`（问卷列表）当时只有 3 处次级链接，一级导航与用户中心全无入口，这才是"找不到"的真相。
4b. **后台新建的页面必须同时挂进后台导航**：`views/admin/_head.ejs` 的 `.admin-nav` 是唯一的一级入口。2026-09-17 发现 `/admin/clients`（委托方申请审核）建好了却**没进导航**，用户只能手输网址，等于没有。凡是新增 `/admin/*` 页面，都要在 `.admin-nav` 里加一项。
5. 顺手做**窄屏可用性**：后台 `views/admin/_head.ejs` 的 `.admin-nav` 有 11 个栏目，窄屏会换行成一堵墙；加 `@media (max-width:820px)` 让它 `flex-wrap:nowrap;overflow-x:auto`。
6. 注意路由语义容易混：`/survey` 是调查服务**销售页**（`survey.js`），真正的问卷列表在 **`/q`**（`questionnaire.js` 的 `qPublic.get('/')`）。别把入口指向错页。

## 「提交 → 审核 → 发布」类需求的通用设计（UGC 上线审核）

2026-09-17 委托方问卷审核落地的模式，后续做"政策/活动/商家/帖子需审核"一律照此：

1. **审核状态独立成一个字段，别硬塞进 `status`**。`status`（draft/published/closed）管"是否对外可见"，`review_status`（none/pending/approved/rejected）管"平台是否放行"。两者正交，否则"已过审但暂时下线"这种状态无法表达。
2. **平台自建内容免审**（`owner_type='admin'` 直接 approved），只对第三方 UGC 设卡，不然管理员自己也被挡。
3. ⚠️ **内容一改就作废审核结论**：已 approved/rejected 的记录，内容一旦变更即回 `pending`；若原本 `published`，同时置 `closed` 暂停对外。否则可以送一份无害内容过审、再偷换成违规内容上线——这是这类制度最容易漏的洞。
4. **闸门放在服务端，不只放前端**：前端按钮置灰只是体验，真正拦住的是发布路由里的 `canPublish()` 判定（E2E 要直接 POST 打这个路由断言被拒）。
5. **送审即通知管理员**（复用 `notifyAdminLead`），并给用户一个可见的"审核中"状态页；否则队列没人看、用户以为卡死而反复提交。申请类还要做**同联系方式 pending 去重**。
6. 幂等迁移：新列用 `ALTER TABLE ... ADD COLUMN` 逐个 try/catch；**首次加列时把存量数据回填为 approved**，避免新制度上线把老数据全部锁死。

## 真浏览器 E2E（本机 Edge + playwright-core，零 C 盘污染）

用户说"你还是没跑通"时，他要的是**看得见的真实点击**，不是 curl 状态码，也不是离线快照。**不要再下结论"Playwright 要装到 C 盘所以违规"** —— 本机已有 Edge，playwright-core 只是纯 JS 库，装 D 盘即可，不需要下载任何浏览器。

```bash
mkdir -p /d/workBuddy/tmp/e2e && cd /d/workBuddy/tmp/e2e
export npm_config_cache=/d/workBuddy/tmp/npm-cache     # 不重定向会写 C 盘 npm cache
"C:/Users/琼崖纵队/.workbuddy/binaries/node/versions/22.22.2-3/npm.cmd" i playwright-core@1.49.1
```

```js
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';
const browser = await chromium.launch({ executablePath: EDGE, headless: true });
const ctx = await browser.newContext({ viewport:{width:1440,height:1000}, ignoreHTTPSErrors:true });
await ctx.addCookies([{ name:'connect.sid', value:RAW_COOKIE,   // 未编码的 s:<sid>.<sig>
                        domain:'.hndcw.com', path:'/', httpOnly:true, secure:true, sameSite:'Lax' }]);
```

要点：
- **每页都要记录证据**：`response.status()`、`page.on('pageerror')`、`page.on('console', m=>m.type()==='error')`，外加 `fullPage` 截图。"零报错"要来自监听器，不能靠肉眼。
- **真点按钮，不看代码**：定位到目标行 `page.locator('tr',{hasText:'<code>'}).locator('button.js-pub-btn').click()`，然后断言三件事——行内状态文本变了、toast（`#qToast`）有文案、`page.url()` **没有跳走**（这是"原地 AJAX 生效"的核心证据），并抓 `page.on('response')` 里的 POST 状态码。
- **表单页三个坑**：评分 / NPS 是 `<button>` 而不是 radio（只 `check()` radio 会漏答，进度停在 3/5）；算术验证码形如 `7 + 8 = ?` 出现在题面文本里，要正则解析后回填；提交按钮常被浮层挡住使 `click()` 30s 超时，用 `click({force:true})` 兜底。
- **闭环才算跑通**：发布 → 前台可见 → 访客填写 → 提交入库 → 后台答卷 +1 → 图表渲染 → CSV 导出，一条链走完再截图交付。
- 真机提交会**顺带触发管理员微信提醒**（服务端日志 `[notify] 已推送管理员微信提醒 ok`），可当通知链路的免费验证。
- 收尾零残留：删本地脚本目录、删服务器 `/tmp/*.py`、删伪造 session 行（删除后再访问受保护页应回到 302/登录页，以此自证清干净）。

## 导出 / 报表类功能：零依赖生成 xlsx

用户说"导出的模板你还没有设计"时，通常不是要格式转换，而是**要一份能直接交付客户的报表**（有标题、有统计、有版式），裸 CSV 一定被打回。做法：

**1. 不要引第三方表格库**（`src/lib/xlsx.js` 约 11KB 即可自足）：
- 手写 ZIP（STORE 不压缩 + 256 项 CRC32 查表）、`[Content_Types].xml`、`_rels/.rels`、`xl/workbook.xml`、`xl/_rels/workbook.xml.rels`、`xl/styles.xml`、`xl/worksheets/sheetN.xml`。
- 字符串用 `t="inlineStr"` + `<is><t xml:space="preserve">`，省掉 sharedStrings。
- 关键顺序：`cols` 在 `sheetData` 之前，`mergeCells` 在 `sheetData` 之后；冻结窗格用 `<sheetView><pane ySplit= topLeftCell= state="frozen"/>`。
- 日期直接写字符串（自行做 UTC→北京时间），避免日期序列号与 numFmt 的坑。

**2. 报表内容按「两张表」组织**：Sheet1 明细（第 1 行合并大标题、第 2 行类型/份数/导出时间、第 3 行表头并冻结、其后逐份数据）；Sheet2 统计分析（每题一块：题目标题底纹行 → 有效份数/平均分/NPS 摘要 → 选项|票数|占比表格）。矩阵题按行展开，填空题逐条列原文。

**3. 逻辑与路由分离**：产物构造 + 响应头统一放 `src/lib/survey-export.js` 的 `sendSurveyExport(req,res,survey,questions,responses)`；**admin 与委托方两条路由各只剩 3 行**（取数 + 权限 + 调用），避免同源代码各写一份后漂移。

**4. 入口用弹窗而不是下拉**：后台表格外层是 `overflow-x:auto` 容器，绝对定位的下拉会被裁切。组件做成 `views/partials/xxx_modal.ejs`，页面只放一个 `class="js-exp-btn" data-id data-title` 的按钮 + 页尾 include 一次。

**5. 中文文件名**：同时给 `filename="ascii.xlsx"` 与 `filename*=UTF-8''<encodeURIComponent(中文名)>`，浏览器优先用后者。

**6. 验证必须验到"文件本身能打开"**：`node --check` 只能证明语法，证明不了 ZIP/OOXML 正确。用 D 盘 venv 的 openpyxl 读一遍（`/d/WorkBuddy/.workbuddy/binaries/python/envs/default/Scripts/python.exe`，缺则 `pip install openpyxl`，并把 `PIP_CACHE_DIR` 指向 D 盘），断言 sheet 名、关键单元格、冻结窗格与合并区域。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
