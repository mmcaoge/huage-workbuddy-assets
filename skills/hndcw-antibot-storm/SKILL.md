---
name: hndcw-antibot-storm
version: 1.0.0
display_name: 反爬风暴处置
display_name_en: Anti-bot Storm Response
description_zh: 网站反复 504/整站卡死的标准诊断与反爬风暴处置：CPU 定位、504 分布、UA 统计与限流封锁。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: "Diagnose recurring 504s and bot storms: CPU profiling, 504 distribution, UA stats, blocking and throttling."— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
description: hndcw.com 反复 504/整站卡死的标准诊断与反爬风暴处置流程。当用户反馈"网站打不开/504/后台白屏/进不去"时使用。覆盖 node 单线程 CPU 打满、V8 profiler 定位 native 热点、nginx 504 时间分布、爬虫 UA 统计、UA 硬闸+网段封锁+全站限流模板。
---

# hndcw 504 / 整站卡死标准处置（2026-09-29 实战沉淀）

## 事故史（同类根因已复发 3 次）
- 09-17：/owners 查询串抓取陷阱（meta-externalagent 高频扫）
- 09-27：node 匿名内存 26h 涨到 2.5GB → swap 抖死（加 900M 保险丝）
- 09-29：Meta 爬虫风暴（meta-webindexer/meta-externalagent + 伪 Chrome）刷 /projects/ 详情页 → 单线程 CPU 99.9% → 全站 504

## 标准诊断链（按序执行，勿跳步）
1. **内存还是 CPU？** `free -h; pm2 list`：
   - node mem 逼近 900M → 内存泄漏路径（重启 + /api/mem + heapsnapshot 追）
   - mem 正常但 %CPU 高 → 爬虫风暴/native 烧（本次流程）
2. **线程级确认**：`top -H -b -n1 -p $(pm2 pid hndcw)`。只有主线程烧 = JS/native 主线程问题；libuv worker 烧 = zlib/crypto。
3. **JS 还是 native？** V8 CPU profiler 采样：
   ```
   kill -USR1 <pid>   # 开 inspector（默认 127.0.0.1:9229）
   curl -s http://127.0.0.1:9229/json/list   # 拿 webSocketDebuggerUrl
   # node22 内置全局 WebSocket，CDP: Profiler.enable → setSamplingInterval(1000) → start → 8s → stop
   # 统计 samples 按 callFrame 聚合：(idle) 占大头 + JS 无热点 = CPU 烧在 native（node:sqlite 同步 C++）
   ```
   ⚠️ profiler 只采 JS 主线程，native 帧不会出现为函数名，"(idle) 多但 top 显示 CPU 满"本身就是 native 证据。
4. **504 时间分布**：`grep 'upstream timed out' /www/wwwlogs/hndcw.com.error.log | awk '{print $1,$2}' | cut -d: -f1,2 | sort | uniq -c | tail -48`
   - 每分钟数百条 = 爬虫风暴；集中在采集时段(0-10/18-4 点) = python 写锁阻塞同步 SQLite。
5. **UA/路径/IP 三统计**（tail -20000 即可）：
   ```
   UA:   awk -F'"' '{print $6}' | sort | uniq -c | sort -rn | head -10
   路径: awk '{print $7}' | cut -d'?' -f1 | sed 's|/projects/.*|/projects/*|' | sort | uniq -c | sort -rn
   IP:   awk '{print $1}' | sort | uniq -c | sort -rn | head -10
   ```
   常见敌方 UA：meta-webindexer / meta-externalagent / facebookexternalhit（Meta）；伪造 Chrome 无 bot 标识；57.141.x = Meta AS32934 网段。
6. **为什么旧防护失效（勿重复踩）**：单 IP 限流被几十个爬虫 IP 稀释；60s 微缓存对"每 URL 只爬一次"无效；单请求 54ms × 上千 QPS = 2 核必然打满。**结论：必须 UA/网段层硬闸，不能只靠限速和缓存。**

## 反爬硬闸模板（已落地 hndcw.com.conf，备份 *.bak_before_antibot_20260929）
```nginx
# http 级（conf 文件顶部）
map $http_user_agent $bad_bot {
    default 0;
    ~*meta-webindexer 1;  ~*meta-externalagent 1;  ~*facebookexternalhit 1;
    ~*facebookcatalog 1;  ~*semrushbot 1;  ~*ahrefsbot 1;  ~*mj12bot 1;
    ~*dotbot 1;  ~*dataforseo 1;  ~*serpstatbot 1;
}
limit_req_zone $binary_remote_addr zone=all_pages:10m rate=10r/s;

# server 块
if ($bad_bot) { return 403; }
deny 57.141.0.0/16;   # Meta 官方爬虫网段网络层兜底

# location / 兜底限流（真人 10r/s + burst 40 不受影响）
limit_req zone=all_pages burst=40 nodelay;
limit_req_status 429;
```
- 改 conf 必须：备份 → `nginx -t` → `-s reload`；robots.txt 在 `src/server.js`（robotsBlock/bots 数组），改后 `node --check` + `pm2 reload hndcw --update-env`。
- robots.txt 原则：**只具名放行**百度/谷歌/Bing/AI 爬虫；Meta 系全域 Disallow。勿再"欢迎"高频商业爬虫。

## 验证清单
```
curl -A 'meta-webindexer UA'  → 403
curl -A 'Baiduspider'         → 200（SEO 不伤）
curl -A 'Googlebot'           → 200
curl -A '普通 Chrome UA'      → 200 且 <100ms
3 分钟后 504 计数 = 0；node %CPU < 20%
```

## 修复脚本模式
复杂 conf/server.js 修改用**本地 Write python 脚本 + scp 上传执行**（备份 assert 锚点），绝不 ssh 内联多层引号（必炸）。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
