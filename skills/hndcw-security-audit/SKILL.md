---
name: hndcw-security-audit
version: 1.0.0
display_name: 网站安全体检
display_name_en: Security Audit
description_zh: 网站安全体检与数据暴露面评估：敏感文件、端口、安全响应头、限流与爬虫抓取风险量化。
description_en: "Audit site security and data exposure: sensitive files, ports, headers, rate limits and scraping risk."
description: hndcw.com / hndmshdcw.com（海南社会调查网双站）的安全体检与数据暴露面评估。实测敏感文件能否被公网下载、端口是否收敛、安全响应头、限流是否缺失，并量化"我们的数据能被别人抓走多少"。当用户问「安全指数多少」「黑客容易攻击吗」「数据会不会被爬走」「有没有漏洞」「被人抓数据怎么办」时使用。
agent_created: true
---

# 双站安全体检 + 数据暴露面评估

> 一句话原则：**"目录 403"和"端口在 LISTEN"都不能作为安全结论。** 必须逐个探测具体文件路径、从公网实测端口。本项目第一轮就靠这条揪出老站两个可下载的敏感文件。

---

## 0. 前置与红线

- 服务器 `root@39.96.24.206 -p 22222`，密钥 `~/.ssh/wb_auto2`，必带 `-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null`。
- **执行环境红线**（同 `hndcw-site-health-audit`）：PowerShell 工具里禁止 `bash x.sh`（报 "Spawning a non-PowerShell shell"）、禁止出现 `%{http_code}`（报 "cmd.exe %VAR% syntax"）⇒ **固定做法：本地写脚本 → 转 LF → scp → `chmod +x` → 直接 `/tmp/x.sh` 执行**。
- 本地转 LF：`$c=[IO.File]::ReadAllText($p) -replace "`r`n","`n"; [IO.File]::WriteAllText($p,$c,(New-Object Text.UTF8Encoding($false)))`
- ⚠️ **只探测自己的资产。**
- ⚠️ **探测请求会进我们自己的 access log** —— 事后做"是否被人访问过"的判定时，必须排除 `39.96.24.206`（本机）和 UA `curl/7.61.1`。
- ⚠️ **输出里绝不打印密钥明文**：管道里加 `sed -E 's/[a-f0-9]{20,}/[REDACTED]/g'`。

---

## 1. 探测清单（照抄）

### A. 敏感文件能否被公网下载（最高优先级）

**新站 hndcw.com（Node/Express）**
```
/.env  /data/hndcw.db  /hndcw.db  /package.json  /.git/config
/config/pay-secret.json  /config/baidu.json  /config/indexnow.json
/src/server.js  /src/routes/seo.js  /scripts/intel_gen.py
/logs/  /admin  /api/  /backup.sql  /db.sqlite
```

**老站 hndmshdcw.com（迅睿CMS / PHP）**
```
/cache/data/weixin.cache          ← 公众号 appSecret 运行时缓存，最要命
/config/database.php
/backup_*.sql  （根目录散落的 MySQL dump）
/admin.php  /dayrui/  /config/  /cache/  /uploadfile/  /.env
```

逐条 `curl -s -o /dev/null -w "%{http_code}|%{size_download}|%{content_type}"`。

### B. 端口收敛
```bash
ss -tlnp | awk 'NR>1 {print $4, $6}' | sort -u          # 本地监听全景
iptables -L INPUT -n --line-numbers                      # 本机防火墙兜底
curl -s -o /dev/null -w "%{http_code}" http://<公网IP>:<port>/   # 从公网实测（关键）
```

### C. 安全响应头
```bash
curl -sI https://<域名>/ | grep -i -E "^(strict-transport|content-security|x-frame|x-content-type|referrer-policy|permissions-policy|x-powered-by|server)"
```

### D. 限流
```bash
for i in $(seq 1 20); do curl -s -o /dev/null -w "%{http_code} " https://hndcw.com/projects/list; done
grep -n -E "rateLimit|limiter|throttle|429" /www/wwwroot/hndcw.com/src/server.js
grep -n -E "limit_req|limit_conn" /www/server/panel/vhost/nginx/hndcw.com.conf
```

### E. 静态目录暴露面（找根因）
```bash
grep -n "express.static" /www/wwwroot/hndcw.com/src/server.js
```
本项目：只挂了 `path.join(__dirname,'..','public')` ⇒ **源码/数据库/config 都在 public 之外，所以全部 404**。这是"敏感路径全 404"的根因，改代码时别把 `data/` 或 `config/` 挪进 `public/`。

---

## 2. 判据铁律（防误报 / 防漏报）

| 现象 | 不能下的结论 | 正确判据 |
|---|---|---|
| 目录返回 403 | ❌ "目录安全" | **老站 `/cache/` 403，但 `/cache/data/weixin.cache` 是 200** ⇒ 403 只表示禁止列目录，**必须逐个探测具体文件** |
| `ss` 显示 `0.0.0.0:18888` | ❌ "面板暴露在公网" | 宝塔 18888 有 iptables `DROP` 兜底（只放行 `127.0.0.1` + `183.254.33.0/24`）；888/3000 靠**云安全组**拦 ⇒ **必须从公网 IP 实测，`HTTP=000` 才是不可达** |
| 敏感路径返回 404 | ✅ 真安全 | 看**响应体大小是否一致**：新站全是 `404\|11838~11878\|text/html`（统一 404 页）⇒ 真不存在。若某条 200 且大小异常 ⇒ 命中 |
| robots.txt 里有 `Disallow` | ❌ "已防护" | **只拦搜索引擎，拦不住真人，且等于给攻击者指路**。绝不当安全措施 |

---

## 3. 本项目已确认的问题（2026-09-14）

| 级别 | 位置 | 现象 | 修复 |
|---|---|---|---|
| 🔴 高 | 老站 `/cache/data/weixin.cache` | **200 可下载**，明文含公众号 appid/appsecret/token/aeskey | ✅ **已修复 2026-09-14**：nginx `deny all`（见 §4，改后 403） |
| 🔴 高 | 老站根目录 `backup_news_person_*.sql` | **200 可下载**（161KB/121KB MySQL dump） | ✅ **已修复 2026-09-14**：`mv` 出 web 根（见 §4，改后 404） |
| ⚠️ 中 | 双站 | **零限流**：`server.js` 无 rate-limit、nginx 无 `limit_req`；`/projects/list` 连打 20 次全 200 | 加限流（§5） |
| ⚠️ 中 | 老站 | **无任何安全响应头** | nginx 补 HSTS/CSP/DENY/nosniff |
| ⚠️ 低 | 新站 | `x-powered-by: Express` 泄露技术栈 | `app.disable('x-powered-by')` |
| ✅ | 新站 | 敏感路径全 404 + 安全头齐全（HSTS/CSP/DENY/nosniff/Referrer-Policy/Permissions-Policy） | — |
| ✅ | 服务器 | 888/3000 公网不可达、MySQL 只听 127.0.0.1、宝塔 18888 有 iptables 兜底、fail2ban 在跑 | — |

---

## 4. 修复：nginx deny（零中断、可秒回滚）

```nginx
# 放在 server 块内、location / 之前（正则 location 按出现顺序首个匹配生效，必须排在静态资源块前面）
location ~* \.(sql|cache|bak|env|ini)$ { deny all; }
location ~* ^/(cache|config)/ { deny all; }
```

> 2026-09-14 **实际部署于 `hndmshdcw.com.conf`**（迅睿 PHP 站）：原配置仅 deny `.env`，补上上述两段。`.sql|.cache|.bak` 用扩展名正则（**路径无关**，覆盖所有子目录里的同类文件，如 `_reorg_bak_*/cache/data/weixin.cache` 也一并 403）；`^/(cache|config)/` 兜底目录。另把根目录两个 `backup_news_person_*.sql` `mv` 到 `/www/backups/old_site_sql/`（不删除）。

**验证证据（改后实测）**：

| 项 | 改前 | 改后 |
|---|---|---|
| `/cache/data/weixin.cache` | 200 | **403** |
| `_reorg_bak/.../weixin.cache` | 200 | **403** |
| `backup_news_person_*.sql` | 200 | **404**（已移走） |
| 任意 `.bak`/`.cache` 文件 | 可下载 | **403** |
| 老站首页 / 文章页 | 200 | **200** |
| 新站 hndcw.com / `/healthz` | — | **200 / ok**（独立 vhost 不受影响） |

**回滚**：`cp /www/server/panel/vhost/nginx/hndmshdcw.com.conf.bak_20260914_143431_p0sec /www/server/panel/vhost/nginx/hndmshdcw.com.conf && /www/server/nginx/sbin/nginx -s reload`

**三条关键注意**：
1. ⚠️ **nginx `deny` 只挡 HTTP，不影响 PHP 运行时读文件**（PHP 读 `weixin.cache` 走文件系统）⇒ 公众号功能不受影响。改完必须实测：首页/文章页 200 + `weixin.cache` 磁盘文件仍在 + 新站 /healthz ok。
2. 改前备份：`cp hndmshdcw.com.conf{,.bak_$(date +%Y%m%d_%H%M%S)_sec}`，然后 `nginx -t` 通过才 `reload`（`nginx -t` 失败则脚本自动回滚、不 reload）。
3. 若某 `location` 已被其他规则匹配，注意 `deny` 的优先级；必要时用 `location ^~` 提升。

---

## 5. 限流模板（Express）

```js
// src/server.js，挂路由之前
const hits = new Map();
app.use((req, res, next) => {
  const ip = req.headers['x-forwarded-for']?.split(',')[0]?.trim() || req.ip;
  const now = Date.now();
  const rec = hits.get(ip) || { n: 0, t: now };
  if (now - rec.t > 60000) { rec.n = 0; rec.t = now; }
  rec.n++; hits.set(ip, rec);
  if (rec.n > 120) return res.status(429).send('请求过于频繁');
  next();
});
```
> 注意：`hndcw` 跑在 nginx 反代后，**必须用 `x-forwarded-for` 才拿得到真实 IP**（`req.ip` 会是 127.0.0.1）。内存 Map 重启即清空，够用；量大再换 Redis。

---

## 6. 数据暴露面评估（"别人会不会抓走我们的数据"）

**算法**：
1. 分片数：`curl -s $SITE/sitemap.xml | grep -c "<loc>"`
2. 总量：拉每个分片 `grep -c "<loc>"`（本项目 16 片 ≈ **150,557 条项目 URL 全公开**）
3. 页面鉴权：`curl -s -o /dev/null -w "%{http_code}" $SITE/projects/list`
4. 限流：连打 20 次看是否 429（本项目全 200）
5. 对比自家采集姿势：`grep -n -E "SLEEP|CONCURREN|TIMEOUT" collect_region.py`

**本项目结论模板**（可直接复用表述）：
> 我们抓别人的数据要**单进程 + 每页间隔 ≥3 秒 + 怕被封 IP**；别人抓我们**不用怕任何东西** —— 没有限流、没有 UA 校验、无需登录，而 `/sitemap.xml` 还主动把 15 万条 URL 的完整目录递了出去。一台机器一天就能全量拉走。这是"为 SEO 开放"与"防批量抓取"的**固有矛盾**，不能靠关掉 sitemap 解决（那会同时失去搜索流量），只能靠"限流 + 分批 + 详情页轻校验"折中。

---

## 7. 验证闭环（改完必跑）

```bash
# a) 敏感文件：期望 403 或 404（不再是 200）
curl -s -o /dev/null -w "%{http_code}\n" https://hndmshdcw.com/cache/data/weixin.cache
curl -s -o /dev/null -w "%{http_code}\n" https://hndmshdcw.com/backup_news_person_20260806115329.sql
# b) 站点与文章页仍正常
curl -s -o /dev/null -w "%{http_code}\n" https://hndmshdcw.com/
curl -s -o /dev/null -w "%{http_code}\n" https://hndmshdcw.com/yaowen/1132.html
# c) 公众号功能仍正常（证明 deny 没伤到运行时读缓存）
#    发一条测试图文或看后台微信模块是否报 40125
# d) 新站主服务未受影响
curl -s http://127.0.0.1:3000/healthz     # {"ok":true}
```

---

## 8. 踩过的坑

- ⚠️ **别把"我们页面公开"当漏洞**：项目详情页公开是**产品设计**（要让搜索引擎收录），不是缺陷。真正的风险来自"公开 + 无鉴权 + 无限流 + sitemap 全量"四者叠加。
- ⚠️ **分析"是否被人访问过"前先清污染**：本轮自查产生的 curl 记录会混进日志（`backup_news_person` 全日志 5 条全是自查），不排除本机 IP 会得出"已被下载"的错误结论。
- ⚠️ **老站是迅睿CMS，路径有行业标准形态**（`/cache/data/weixin.cache`、`/dayrui/`、`/config/database.php`）⇒ 攻击者**不需要猜**，扫标准字典就能命中。这类"框架标准路径"必须优先排查。
- ⚠️ 老站 `.sql` 备份是**历史遗留**（2026-08-06 建的），别只删新的、忘了翻根目录还有几个。
- ⚠️ 宝塔面板端口是 **18888 不是 8888**（8888 那台是别的服务/已被 DROP）；888 是 nginx 的另一个监听口。
