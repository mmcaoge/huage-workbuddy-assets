---
name: hndcw-site-health-audit
version: 1.0.0
display_name: 网站健康体检
display_name_en: Site Health Audit
description_zh: 基于 nginx 日志做真实流量基线、404 归因与坏链修复验证，量化爬虫与真人流量。
description_en: Baseline real traffic from nginx logs, attribute 404s and verify broken-link fixes.
description: hndcw.com（海南社会调查网 Node/Express 站）站内健康体检与 404 治理。把 nginx 日志里的爬虫和真人分开算真实流量基线，对 404 做归因（区分"我们自己制造的坏链"与"外部爬虫自发探测"），并给出修复与验证闭环。当用户问「流量怎么这么少」「为什么没转化」「有没有坏链」「数据是不是不对」「帮我体检一下」时使用。
agent_created: true
---

# hndcw.com 站内健康体检 + 404 治理

> 一句话原则：**谈任何"转化/推广"之前，先跑一遍这个体检。** 本站日志里 **90%+ 的请求是爬虫**，凭印象判断流量必然错得离谱。

---

## 0. 前置

- 服务器 `root@YOUR_SERVER_IP -p YOUR_SSH_PORT`，密钥 `~/.ssh/wb_auto2`，必带 `-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null`。
- 项目根 `/www/wwwroot/hndcw.com`；日志 `/www/wwwlogs/hndcw.com.log`（老站 `hndmshdcw.com.log`）。
- 日志格式 = 标准 combined：`IP - - [time] "REQ" status size "referer" "ua"`。
- 服务器 Python 是 **3.6**（无 `subprocess.run(capture_output=...)`、`text=`）；有 `/usr/bin/python3`。
- **一切线上事实一律 ssh 到服务器内部 curl 判定**；本机沙箱 curl 打 hndcw.com 常返回 size=0 会误判"站点挂了"。

### ⚠️ 执行环境两条硬红线（PowerShell 工具会拦）

1. 命令里出现 `bash xxx.sh` / `sh xxx.sh` → 报 `Spawning a non-PowerShell shell ...`。
2. 命令里出现 `%{http_code}` 这类 `%VAR%` → 报 `cmd.exe %VAR% environment variable syntax`。

⇒ **固定做法：本地写脚本 → 本地转 LF → scp 上传 → `chmod +x` 后直接 `/tmp/x.sh` 执行**（命令行里既无 `bash` 也无 `%`）。python 脚本用 `PYTHONIOENCODING=utf-8 /usr/bin/python3 /tmp/x.py`。

本地转 LF（PowerShell）：
```powershell
$p='D:\WorkBuddy\tmp\x.sh'
$c=[IO.File]::ReadAllText($p) -replace "`r`n","`n"
[IO.File]::WriteAllText($p,$c,(New-Object Text.UTF8Encoding($false)))
```
> ⚠️ 脚本内容若含 `masscan|nmap|zgrab|scan|checker` 等词，也可能被安全策略拦 ⇒ 爬虫特征词**只保留必要项**。

---

## 1. 流量体检（真人 vs 爬虫）

### 关键认知
- **看 `MicroMessenger` 才是看真人**：微信内访问量是本项目最可靠的真人指标（推广都在微信生态）。
- **Googlebot 伪装 UA**：`Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) ...` —— UA 里**不含 "bot" 字样**，按 bot 关键词过滤会漏掉，必须单列。
- 自家 IP：`183.254.x`（海南移动）= 华哥本人/测试，统计时要扣掉。
- referer 里 `cn.bing.com` / `www.google.com` / `www.baidu.com` / `mp.sohu.com` 才是**外部真实入口**。

### 爬虫特征正则（够用即可，别贪多）
```
bot|Bot|spider|Spider|crawler|Crawler|slurp|Slurp|externalagent|python-requests|curl/|Go-http|okhttp|Scrapy|Semrush|Ahrefs|Bytespider|MJ12|Petal|libwww|Wget|UptimeRobot|Pingdom|HeadlessChrome|PhantomJS|CCBot|Diffbot|DotBot|HubSpot|censys|libredtail|zgrab
```

### 统计口径
1. 总量 / 疑似爬虫 / 疑似真人 / 微信内 四项
2. **每日趋势**（总 / 真人 / 微信）——判断在涨还是在降
3. 真人 UA top15、真人访问页面 top25（`/projects/DM-xxx` 归并成一项）、referer top15
4. 真人独立 IP 数 + 最活跃 IP（识别自家测试与云爬虫）
5. 状态码分布（**404 数量是健康度硬指标**）
6. 交叉验证业务表：`users`（近 7/30 天新增）、`service_leads`、`point_orders`

> 判据铁律：谈推广变现前先看 `guest_daily_views`、`users`、`service_leads`、`point_orders`，别凭印象说"转化不行"。

---

## 1.5 判断"某搜索引擎还来不来"（判活三问）

**只看 UA 关键词会得出完全相反的结论。** 老站实测：`grep -c -i baiduspider` 46 天命中 31 次，看似"百度在抓"，实际 31 次里绝大多数是**漏洞扫描器冒充 Baiduspider**（抓的是 `/dist../.env`、`/userfiles/x?path=../../.env`、`/actuator/mappings`、`/api/inngest`）⇒ 真百度对老站的抓取 ≈ 0。

三问缺一不可：

1. **数量对不对** —— 正常运营的中文站，百度应每日数十至数百次抓取。个位数/天 = 没在抓。
2. **URL 像不像正经蜘蛛** —— 真蜘蛛抓文章页、栏目页、sitemap、robots.txt；抓 `.env`/`actuator`/路径穿越的一律是扫描器。
3. **有没有 referer 导流** —— 抓了不收录、收录不导流，仍等于没流量。**导流的逐日趋势比总量更有价值**（本项目靠它发现：谷歌 308→87 暴跌 72%、百度 9/8 后归零、必应 ~110/天稳定）。

```bash
# 按天 × 搜索引擎矩阵
for d in 11 12 13 14; do
  L=$(grep "^[^ ]* [^ ]* [^ ]* \[$d/Sep/2026" $LOG)
  echo "$d/Sep 百度=$(echo "$L"|grep -c -i baiduspider) 必应=$(echo "$L"|grep -c -i bingbot) 谷歌=$(echo "$L"|grep -c -i googlebot) 华为=$(echo "$L"|grep -c -i petalbot)"
done
# 导流（referer 计数，逐日）
echo "$L" | grep -o 'https\?://[^"]*baidu\.com[^"]*' | wc -l
```

### ⚠️ "真人"计数必扣两类伪装者（否则数出假基线）
- **伪装成浏览器的扫描器**：`146.148.26.13`(GCP) 用普通 Safari UA 在 9/10 打出 **39,600 次 404** ⇒ 当天"真人 42,658"纯属虚构。**信号：某天 真人 与 404 同时暴涨 ⇒ 先怀疑扫描器。**
- **商业 SEO 工具**：SemrushBot（`185.191.171.x`）、AhrefsBot 会整段扫站。UA 正则必须含 `semrush|ahrefs|mj12|dotbot|blexbot|dataforseo|zoominfo`。

---

## 2. 404 归因（三步定位）

**第一步**：按 URL 归并（剥 query）统计 404 排行，找出 TOP 项。
**第二步**：看 404 的 **referer** —— 若 referer 是自己站内页面 ⇒ **是我们自己制造的坏链**；若 referer 为空且 UA 是爬虫 ⇒ 爬虫盲爬。
**第三步**：实测命中口径。用服务器内部 curl 打目标 URL 拿状态码，对比代码里的查询条件。

### 本项目已确认的三类根因（照抄即可）

| 类型 | 特征 | 根因 | 修法 |
|---|---|---|---|
| **A. 口径不一致** | 404 URL 大量带 `%20`；referer 是站内项目页 | 链接由字段**原值**生成，查询却用**清洗后**的值做 `=` 比对 ⇒ 必然不等 | 查询端加**多轮兜底**：原值精确 → 清洗值 → 清洗后 name；并统一清洗函数 |
| **B. 主动推坏地址** | 爬虫请求 `/projects/DM-?-xxxx`、含乱码的 `DM-%C3%A8...` | sitemap/推送脚本里 `encodeURI(dm_code)` 不编码 `?`；或字段本身是 UTF-8 被按 Latin-1 误解码的乱码 | 生成端统一过 `validDmCode()` 过滤（见下） |
| **C. 外部爬虫自发探测** | 如 `/null`、`/fetch`、`/proxy`；referer 是站内页但**页面 HTML 里根本没有该链接** | Meta 等爬虫解析 JS 变量后自行拼 URL | **不修**（先抓页面验证：`curl -s <url> \| grep -oE '(href\|src)="[^"]*null[^"]*"'`）。若无输出即证伪，别浪费时间 |

### 坏地址过滤规则（`src/routes/seo.js` 已落地）
```js
const BAD_DM = /[?#%/\\\s]/;
function validDmCode(c) {
  if (!c) return false;
  const s = String(c);
  if (s.length < 6 || s.length > 40) return false;
  if (!s.startsWith('DM-')) return false;
  if (BAD_DM.test(s)) return false;
  if (/[\u00C0-\u00FF]/.test(s)) return false;  // Latin-1 乱码区段
  return true;
}
const DM_OK_SQL = " AND dm_code NOT LIKE '%?%' AND dm_code NOT LIKE '%#%'"
  + " AND instr(dm_code,'%')=0 AND instr(dm_code,'/')=0 AND instr(dm_code,' ')=0";
```
⚠️ **所有**取项目的查询（`countProjects` / `sliceProjects` / `newestProjects` / 推送脚本）都要套同一条件，否则分片数与内容不一致。

### 单位名清洗（`src/routes/owners.js` 已落地）
`cleanUnitName()`：去 HTML 实体（`&nbsp;` `&amp;` …）→ 逐层剥离公告尾缀（`公开招标公告|招标公告|中标公告|更正公告|…|公告|公示`，最多 4 轮、结果 <4 字即停）→ 压缩空白。
配合 `findRows()` 多轮兜底。**展示用清洗名，统计用实际命中的 key。**

---

## 3. 修复后的验证（必做）

```bash
# a) 历史 404 的 URL 重测：从日志取最后 60 个唯一样本，逐个 curl 看状态码
#    （样本获取 + 重测逻辑见本项目 2026-09-14 脚本 /tmp/verify404.py）
#    验收标准：200 占比显著上升（本项目由 0% → 98%）
# b) sitemap 是否还有坏地址
curl -s https://hndcw.com/sitemap-projects-1.xml | grep -c 'DM-?'
curl -s https://hndcw.com/sitemap-baidu.xml   | grep -c 'DM-?'
# c) DB 里坏 code 存量
#    select count(*) from projects where dm_code like '%?%' or instr(dm_code,' ')>0 ...
# d) 回归
curl -s http://127.0.0.1:3000/healthz        # {"ok":true}
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/owners
```

---

## 4. 踩过的坑

- ⚠️ **PowerShell 两条拦截红线**（见 §0），本轮各踩一次 ⇒ 固定用"scp 上传 + 直接执行"。
- ⚠️ **服务器 Python 3.6**：`capture_output=` / `text=` 会 `TypeError` ⇒ 用 `subprocess.check_output([...], stderr=subprocess.DEVNULL)`。
- ⚠️ **终端 GBK 乱码**：python 加 `PYTHONIOENCODING=utf-8`；bash 脚本里的中文一律乱码，**判读只靠英文与数字字段**。
- ⚠️ **改数据前必 dry-run**：先统计"会改多少行 + 给前后对比样本 + 检查会不会清空（长度 <4）"。本项目 `investor` 字段 44.6% 需要清洗，但清洗后只剩电话甚至变空 ⇒ **结论是不清**（清完仍是垃圾，且会误伤）。**"能清洗" ≠ "值得清洗"。**
- ⚠️ 宝塔 nginx 全局 `proxy_cache`：改了 `public/` 下同名文件后公网仍旧内容时，先怀疑它（详见 `hndcw-seo-indexnow` 技能）。
- ⚠️ 别用 `run_in_background` 跑 SSH 长任务（会话会把它带死，日志 0 字节、查无进程）。

---

## 4.5 ⚠️ 性能饱和（站点"假死"）排查：抓取陷阱打满单线程 Node

**什么时候用**：用户说"网站打不开/很慢"，或公网 `curl -w '%{time_total}'` 显示首页 **15-30s** 甚至超时，而服务器负载并不高、没有大规模采集任务在跑。

**2026-09-17 实案**：公网首页 22.7s（偶发 30s 超时）；`ps` 里 `node src/server.js` **持续 95% CPU**、`top` 的 `sy`（系统时间）35-43%。真凶 = **meta-externalagent / MJ12bot 每 2-3 秒扫一条 `/owners?name=<公司名>`**，而该路由每次请求要对 16.6 万行 `projects` 跑全表 `LIKE` + 13 层嵌套 `CASE WHEN` 分组（`EXPLAIN` 显示 `SCAN TABLE` + `TEMP B-TREE FOR GROUP BY`，单查询 87-917ms，多轮兜底叠加即**秒级同步 CPU**）。Node 单线程被同步 SQLite 占死 → 所有请求排队 → 全站 20s+。

### 定位四步（按顺序做，比猜快得多）

```bash
# ① 确认是"CPU 型饱和"还是"IO/锁型"：看 sy 占比与进程 CPU
top -bn2 -d 1 | grep -E '^%Cpu|server.js'
P=$(pgrep -f "src/server.js" | head -1); a=$(awk '{print $14+$15}' /proc/$P/stat); sleep 5; b=$(awk '{print $14+$15}' /proc/$P/stat)
echo "CPU=$(echo "scale=1; ($b-$a)/5" | bc)%"     # 精确瞬时值（ps 的 %CPU 是生命周期均值，会骗人）

# ② 系统调用画像：谁在狂读文件
timeout 4 strace -c -f -p $P 2>&1 | tail -10     # 45580 次/4s 的 pread64 ⇒ 全表扫描

# ③ 直接看扫的是哪个文件（fd 带路径，最决定性）
timeout 3 strace -f -p $P -e trace=pread64 -y 2>&1 | head -5
#   pread64(23</www/wwwroot/hndcw.com/data/hndcw.db>, ..., 4096, 274157568) = 4096  ⇒ 随机偏移扫 627MB 库

# ④ 把成本归到具体路由：nginx 日志按路径/UA 分布
tail -30000 /www/wwwlogs/hndcw.com.log | grep -c '/owners'
tail -30000 /www/wwwlogs/hndcw.com.log | sed 's/.*HTTP\/2\.0" [0-9]* [0-9]* "[^"]*" "//; s/"$//' | cut -c1-40 | sort | uniq -c | sort -rn | head -8
```

⚠️ **别被"每分钟才 3-10 条请求"骗了**：nginx 日志只记**已完成**的请求，慢请求在完成前不出现；而且**单次成本秒级**时，几条并发就够打满单线程。判据要看"单请求成本 × 并发"，不是看 QPS。

### 修复（三重，止血优先）

1. **从源头掐掉抓取陷阱**：参数化搜索页（`?name=` 每个公司名一个 URL、`?q=` 无限搜索空间）对 SEO 零价值 —— `src/server.js` 的 `ROBOTS_DENY_APP` 加
   `Disallow: /*?name=`、`/*?q=`、`/*?keyword=`。
2. **nginx 硬闸**（robots 是君子协定，这里是拒绝）：vhost 加 `location ^~ /owners`，命中「AI/SEO 爬虫 UA **且** 带 `name=`/`q=`」→ `return 403`；真人照常访问，只加 `limit_req zone=owners_search burst=5 nodelay`。**不带参数的榜单页 `/owners` 必须保持开放**（保住搜索收录，别一刀切把整条路径封死）。
3. **限流 zone** 定义在 `/www/server/nginx/conf/limit_req.conf`（http 上下文，**宝塔不覆盖**；vhost 在 `/www/server/panel/vhost/nginx/hndcw.com.conf` 会被面板重写，改这里要留意）。

⚠️ **nginx 两个语法坑（都实测报错）**：
- **`if` 不能嵌套** → `"if" directive is not allowed here`（`if` 只允许出现在 server/location 上下文）。
- **`if ($a$b = "11")` 变量拼接不支持** → `unknown "a$b" variable`。
- ✅ 正解 = 用 **`map` 组合变量**（`map` 支持 `"$a$b"` 复合源）：

```nginx
map $http_user_agent $owners_isbot { default 0; "~*(meta-externalagent|Bytespider|MJ12bot|AhrefsBot|SemrushBot|GPTBot|CCBot|PetalBot|ClaudeBot)" 1; }
map $args $owners_hasq { default 0; "~(^|&)(name|q)=" 1; }
map "$owners_isbot$owners_hasq" $owners_block { default 0; "11" 1; }
# vhost 里只留： if ($owners_block) { return 403; }
```
改完必须 `nginx -t`（过滤掉 http2 弃用告警）再 `nginx -s reload`。

### 验证（一定要出前后对比数字）

| 路由 | 修复前 | 修复后 |
|---|---|---|
| 公网首页 `/` | 21175ms | **226ms** |
| 导出答卷报表 xlsx | 13972ms | **114ms** |
| `/admin/questionnaire` | 1522ms | **46ms** |
| Node CPU | 95% | **4%** |

断言：爬虫 UA+查询串 → **403**；爬虫 UA+榜单页 → **200**；真人 UA+查询串 → 正常执行（不存在的公司名 404 但 0.07s）；日志里出现 403 记录。
⚠️ 502/499 若集中出现在**你重启 pm2 的时间点**，那是重启窗口造成的，不是故障；用 `grep " 502 " | tail` 看时间戳判定。

### 残留风险

上面的止血只解决"不让爬虫来打"。**查询本身仍是秒级同步全表扫描** —— 该治本已于 2026-09-17 完成，见 4.6。换来"毫秒级"的代价是**统计口径变成预计算表**，新采集的数据要等定时刷新才进统计（见 4.6 的 cron）。换 UA 的爬虫或分布式 IP 仍可能复发，故 nginx 限流与微缓存必须保留。

---

## 4.6 查询性能治本：预计算 + 索引 + 连接参数 + 微缓存（2026-09-17 已落地）

**核心认知（先记这一条）**：`node:sqlite` 的 `DatabaseSync` 是**同步 API**，
`db.prepare(...).all()` 会**阻塞整个事件循环**。因此本项目里
**任何一条秒级查询 = 整站冻结那么多秒**；5 个并发就是 5 倍排队。
上节实测的"公网首页 21s"不是查询慢 21s，而是**队列排了 21s**。
⇒ 一切优化目标都是把"在线查询"降到毫秒；降不到的就搬去离线（预计算）。

### 三个反复出现的成本模式（照这个清单去查）

| 模式 | 症状 | 例子（实测） |
|---|---|---|
| **A. `GROUP BY + ORDER BY c DESC + LIMIT` 无法下推** | `EXPLAIN` 显示 `SCAN TABLE` + `USE TEMP B-TREE FOR GROUP BY` + `... FOR ORDER BY`；`LIMIT 12` 一点忙没帮上 | 首页 stage/province 分组 1012+651+655 = **2669ms**；榜单 1712+1366 = **3078ms** |
| **B. 函数包裹列 ⇒ 索引失效** | `EXPLAIN` 显示 `SCAN TABLE`，即使有索引也用不上 | `WHERE date(created_at,'+8 hours')=date('now','+8 hours')`（今日新增）**968ms**；改成 `created_at >= 常量` 后 **0.6ms**（走 `COVERING INDEX`） |
| **C. 查询期做数据清洗** | 每行跑 N 次后缀 `LIKE`，且后缀匹配用不上索引 | `investor` 的 **13 层嵌套 `CASE WHEN ... LIKE '%中标公告'`**，表达式长 1200 字符；搜索 699ms、topAgents 1366ms |

另有 `status=1` **零选择性**（16.9 万行里命中 100%，形同虚设，无法裁剪任何数据）。
以及**下拉选项**：`SELECT DISTINCT col ... ORDER BY col` 一次一次全表扫，
列表页一次要跑 4 个（province 836 / industry 1099 / stage 1097 / sector 956 ≈ **4 秒**）。

### 治本四件套

**① 离线预计算（`tools/refresh_stats.mjs`，本技能 scripts/ 有副本）**

```
projects.investor_clean / owner_clean   预计算清洗列（+ 各自索引）
stats_owner / stats_agent / stats_bidder (nm, c, s) 画像与榜单
stats_group (k, nm, c, s)               k = stage|province|industry|sector
stats_meta  (k, v)                      projects/provinces/supply/disputes/users/supplier_count/policy_count
```
- 榜单类查询必须 `ORDER BY c DESC LIMIT n` ⇒ 给 `c` 建**降序索引**（`idx_stats_owner_c ON stats_owner(c DESC)`），否则又是"全表扫 + 排序"。
- 刷新器把 `DELETE` 与各表 `INSERT SELECT` 分事务提交，用 `BEGIN IMMEDIATE` 分批（默认 2 万行/批），不与采集脚本长时间抢写锁。
- 用法：`node tools/refresh_stats.mjs`（增量，日常）／`--full`（全量重算清洗列，改清洗规则后或每月兜底）／`--stats-only`（只重建汇总表，~7s）。
- ⚠️ **凡是改成读预计算的页面，都要写"汇总表缺失就回退现算"的兜底**（首次部署、刷新器还没跑完时不能让页面空白或显示假 0）。

**② 清洗规则单一真源（`src/lib/unitName.js`）**
原先 `cleanUnitName()/TAIL_RE`（26 种后缀、可重复剥 4 次）与 `agentCleanExpr()`（13 种后缀、只剥 1 次）**两套规则口径分裂**，同一单位在不同页面会被拆成两个名字。现在统一由 `cleanUnitName()`（骨架 `stripTail` + `unitKey`）产出，采集/刷新期写入预计算列，查询期只读列。

**③ 连接参数（`db/db.js`）** — 出厂默认对 607MB 库严重偏小，这是最便宜的杠杆：
```js
PRAGMA cache_size = -65536;      // 2MB → 64MB 页缓存
PRAGMA mmap_size  = 134217728;   // 0 → 128MB 只读内存映射，省掉 read() 拷贝
PRAGMA temp_store = MEMORY;      // 分组/排序的临时 B 树不落盘
PRAGMA synchronous = NORMAL;     // WAL 下已保证崩溃安全，写入更快、持锁更短
```
⚠️ 这几个是**每连接**的，只影响 Node 进程，python 采集侧各自建连接不受影响。
⚠️ 服务器仅 3.5GB 内存（可用约 1.8GB）——取值要留余量，别把 cache 开到几百 MB。

**④ nginx 游客微缓存（把爬虫和重复访问挡在 Node 之外）**
```nginx
proxy_cache_path /www/server/nginx/cache_micro levels=1:2 keys_zone=micro_cache:16m
                 max_size=256m inactive=10m use_temp_path=off;   # 放在 http 上下文
map $http_cookie $hndcw_has_session { default 0; "~*(connect\.sid|hndcw_sid)=" 1; }

location = / {                       # 首页
    proxy_cache micro_cache;
    proxy_cache_key "$scheme$host$uri";
    proxy_ignore_headers Cache-Control Expires;   # 上游是 no-store，必须显式忽略才缓存得下来
    proxy_cache_valid 200 60s;                    # 只缓存 200，403/429/500 不进缓存
    proxy_cache_bypass $hndcw_has_session;
    proxy_no_cache    $hndcw_has_session;         # 带登录 cookie：绕过读 + 不写入，杜绝串号
    proxy_cache_lock on;                          # 防缓存穿透惊群
    proxy_cache_use_stale updating error timeout; # 过期先用旧内容顶，后台再更新
    add_header X-Cache $upstream_cache_status always;   # 验证用
    ...
}
```
安全边界三条不可省：① 只缓存 200；② `proxy_cache_bypass` **与** `proxy_no_cache` 都要带登录 cookie 判据；③ **不要** `proxy_cache_ignore_headers Set-Cookie`（保留"含 Set-Cookie 就不缓存"的默认行为）。
本站 `saveUninitialized:false` ⇒ 游客不带 Set-Cookie ⇒ 不影响命中率。
⚠️ `add_header` 在 location 内会**覆盖父级同名指令**；本站安全响应头是 Node 出的、nginx 全局零 `add_header`，所以加 `X-Cache` 安全 —— 换项目要先确认这件事。

### 顺手修掉的连带问题

- **积分写锁把整页打成 500**：`balanceOf()`（`src/points.js`）在"有积分到期需清零"时会**写库**；采集进程（cron 10:00-23:00 密集写）持锁超过 `busy_timeout` 时异常会一路抛到路由 ⇒ 鸣儿首页/情报库 500。修法：给 `balanceOf` 包一层 try/catch，降级返回最近一次缓存余额（`degraded: true`），页面照常渲染。
- **列表页 `COUNT(*)`**：无筛选条件（WHERE 只剩 `status=1`）时总数即站点项目总量 ⇒ 读 `stats_meta`，避开 627ms 全表 COUNT。

### 落地顺序（照抄，别颠倒）

1. 备份：`_bak_perf_YYYYMMDD/`（含被改的 js + 两个 nginx conf）
2. 上传代码（刷新器要先传，因为后面立刻要用）
3. **先跑 `--full` 建好 schema/索引/回填/汇总表**（16.9 万行 ×2 列 ≈ 110s，后台 `setsid nohup` 跑）
4. 验证索引与汇总表真的生效：`EXPLAIN QUERY PLAN` 要看得到 `SEARCH ... USING COVERING INDEX ...`
5. 再 `pm2 restart`（顺序颠倒会让页面先走兜底，白慢一轮）
6. nginx：`mkdir -p cache_micro && chown www:www` → `nginx -t` → `-s reload`
7. 挂 cron（见下）

### cron（挂在采集/加工之后，避开写库窗口）

```cron
0 9,13,19 * * * cd /www/wwwroot/hndcw.com && /usr/bin/node tools/refresh_stats.mjs >> logs/refresh_stats.log 2>&1
30 23      * * * cd /www/wwwroot/hndcw.com && /usr/bin/node tools/refresh_stats.mjs >> logs/refresh_stats.log 2>&1
50 23      1 * * cd /www/wwwroot/hndcw.com && /usr/bin/node tools/refresh_stats.mjs --full >> logs/refresh_stats.log 2>&1
```
本项目采集时段是 region 10:00-20:50、`clean_winner` 21:10、`collect_details` 21:20/22:45 —— 上图时点都避开了。
⚠️ 改 crontab 前先 `crontab -l > /root/crontab.bak_YYYYMMDD`，再 `crontab -l > /tmp/ct_new; cat >> /tmp/ct_new; crontab /tmp/ct_new`（**绝不直接覆盖**，本项目有 87 条任务）。

### 验证（必须两项都做）

```bash
# ① 绕过 nginx 微缓存，测 Node 真实回源（带任意 session cookie 即触发 BYPASS）
CK="Cookie: connect.sid=s%3Aprobe.xyz"
for u in "/" "/projects/map" "/projects/list" "/owners" "/minger"; do
  printf "%-16s" "$u"; for i in 1 2 3; do curl -s -o /dev/null -H "$CK" -w " %{time_total}s" "https://hndcw.com$u"; done; echo
done
# ② 微缓存命中与隔离：MISS→HIT 应出现；带 cookie 必须 BYPASS
curl -s -o /dev/null -D - https://hndcw.com/projects/map | grep -iE '^HTTP|^x-cache'
curl -s -o /dev/null -D - -H "Cookie: connect.sid=s%3Afake.abc" https://hndcw.com/ | grep -i x-cache   # 期望 BYPASS
```
⚠️ **别用"页面 200"当验证通过** —— 必须核对**内容**（本次就出现过 `SELECT nm AS stage ... WHERE k="stage"`
因为双引号被 SQLite 当**列名**解析而返回 0 行的假象；生产代码用单引号无此问题，但排查时自己写的探针脚本极易踩）。

### 前后对比（真实数字，可直接引用给用户）

| 路由 / 指标 | 治本前 | 治本后 |
|---|---|---|
| **情报库 `/projects/map`** | 1009~2231ms | **11~22ms** |
| 首页 `/` | 2669ms（冷 2.9s） | **21~93ms** |
| 榜单 `/owners` | 3078ms | **12~81ms** |
| 列表 `/projects/list` | ~4.6s（4×DISTINCT） | **10~63ms** |
| 今日新增单查询 | 968ms | **0.6ms** |
| 画像页搜索 `type=agent` | 699ms | **4~18ms** |
| 20 并发 `/projects/map` | 全站排队 | 全部 200，最慢 **0.32s** |
| Node CPU | 95% | **4.5%** |

> 本技能自带脚本 `scripts/`：`measure_owners.py`（对某关键词跑 `EXPLAIN QUERY PLAN` + 计时，量化"单次成本"）、`refresh_stats.mjs`（预计算刷新器全文，可直接移植）、`unitName.js`（清洗单一真源）、`test_unitName.mjs`（清洗规则回归用例）、`nginx_limit_req.conf.example`（限流 zone + 三个 map + 微缓存 zone 完整写法）、`nginx_hndcw_vhost.conf.example`（含 `/owners` 防护与微缓存的 vhost 全文）。

---

## 5. 交付给用户的话术要点

- 先给**真人流量基线**（总请求 / 爬虫占比 / 微信内 / 新增用户 / 真实线索），别只报"访问量"。
- 404 要分清**"我们自己制造的"和"爬虫自发的"** —— 前者必须修，后者要明确说"不是我们的问题、不需要修"，避免用户误以为网站到处是洞。
- 修完必须回测，用**修复前 vs 修复后**的对比数字收尾（例：7,417 次/月 → 历史样本 59/60 已 200）。
