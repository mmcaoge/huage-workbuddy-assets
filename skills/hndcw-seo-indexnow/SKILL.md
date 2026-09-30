---
name: hndcw-seo-indexnow
version: 1.0.0
display_name: SEO收录推送
display_name_en: SEO IndexNow Pusher
description_zh: 打通搜索引擎收录：排查 sitemap/robots、IndexNow 即时推送全站 URL、配置每日自动推送。
description_en: Set up sitemap/robots, push all URLs via IndexNow instantly and schedule daily auto pushes.
description: 为 hndcw.com（海南社会调查网 Node/Express）打通搜索引擎收录：排查并挂载 sitemap 路由、补 robots 声明、用 IndexNow 零成本即时推送全站 URL、配每日自动推送。当用户提出「怎么让搜索引擎收录」「流量太少」「sitemap 404」「提交百度/Google/Bing」「让 AI 搜索抓到」等需求时使用。
agent_created: true
---

# hndcw.com 搜索引擎收录打通（sitemap + IndexNow）

## 何时用
- 用户抱怨"没流量""没人来""搜不到我们"
- 需要让 15 万项目页 / 4.8 万企业页 / 政策页进入 Google、Bing、百度、AI 搜索（ChatGPT/Perplexity）
- 站点改版后重新提交收录

## 核心事实（2026-09-14 实证）
- 项目根：`/www/wwwroot/hndcw.com`；PM2 应用名 `hndcw`，端口 3000。
- SSH：`ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/wb_auto2 -p 22222 root@39.96.24.206`
- scp 同样参数（大写 `-P`）。**Bash 里必须 `dangerouslyDisableSandbox:true`**，且本地路径用 Windows 形式 `D:/WorkBuddy/tmp/xxx`。
- sitemap 模块：`src/routes/seo.js`（index + static + policies + projects 分片，6 小时内存缓存）。
- **头号坑：路由写了但没挂载。** 必须检查 `src/server.js` 里有无 `app.use('/', seoRouter)`，且必须在 **404 兜底之前**。（历史上 `/sitemap`、`/rights-statement` 都踩过同一坑。）
- robots.txt 是**硬编码在 server.js** 里的（不是文件），改它要改 server.js。

## 标准流程

### 1. 先诊断（不要凭印象）
```
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/sitemap.xml   # 应 200
curl -s http://127.0.0.1:3000/robots.txt                                     # 应含 Sitemap:
grep -n -i 'seo\|sitemap' src/server.js                                      # 看是否挂载
grep -n -E "router\.(get|use)\(" src/routes/seo.js                           # 看定义了哪些端点
```
再核对 **sitemap 里列的 URL 是否真实 200**（提交死链会扣分）。注意 curl 中文 URL 必须 `%` 编码，否则误报 400。

### 2. 挂载 + 补 robots（改 server.js）
```js
import seoRouter from './routes/seo.js';
...
app.use('/', seoRouter);          // 必须在 404 兜底前
```
robots 里加：
```js
'Allow: /\n' + '\n' + 'Sitemap: https://hndcw.com/sitemap.xml\n'
```
改完 `node --check src/server.js && pm2 reload hndcw`。

### 3. sitemap 内容增强
`STATIC_PAGES` 里只放**已验证 200** 的公开页（`/`、`/minger`、`/suppliers`、`/policies`、`/projects/map`、`/knowledge`、`/guarantee`、`/market/tech`、`/owners`、`/legal`、`/disclaimer`、`/rights-statement`）。
⚠️ `/projects` 是 302（重定向到 /），**不要放进 sitemap**。
政策详情走 `/sitemap-policies.xml`（`select id from policies where status=1`）。

### 4. IndexNow 即时推送（零成本、免站长账号）
1. 生成 key 并落地：
```
KEY=$(openssl rand -hex 16)
echo -n $KEY > public/$KEY.txt          # 公网必须能 HTTPS 取到
printf '{"key":"%s","keyLocation":"https://hndcw.com/%s.txt"}' $KEY $KEY > config/indexnow.json
curl -s -o /dev/null -w '%{http_code}\n' https://hndcw.com/$KEY.txt   # 必须 200
```
2. 推送脚本 `scripts/indexnow_push.py`（支持 `--days N` / `--all` / `--limit N`，每批 1 万，POST 到 `https://api.indexnow.org/indexnow`）。
3. 首次全量：`python3 scripts/indexnow_push.py --all` → 150,718 条 / 16 批 / 全 200。
4. cron 每日推新增：
```
10 9 * * * cd /www/wwwroot/hndcw.com && PYTHONIOENCODING=utf-8 /usr/bin/python3 scripts/indexnow_push.py --days 3 >> logs/indexnow.log 2>&1
```

### 5. 站长平台「站点验证」（百度/Google/Bing 都要走这一步）
1. **验证文件放哪**：网站根目录 = `public/`（`server.js` 的 `express.static` 指向它），直接 `scp` 进去即可，公网 `https://hndcw.com/<文件名>` 就能访问，**不用碰宝塔**。
2. ⚠️ **百度 `baidu_verify_codeva-<code>.html` 的文件内容不是文件名！** 新版 codeva 格式里放的是一串**独立的 32 位十六进制哈希**（例：文件名 `baidu_verify_codeva-BIsU2OiV53.html`，内容 `417b224b227d6354f590a3d09962f3fe`）。**永远要用户下载原件、原样 scp 上传，不要凭文件名推算内容**（推算必报「验证文件的内容错误」）。
   - 拿到用户下载的原件后：`scp "D:/Downloads/<文件名>.html" root@...:/www/wwwroot/hndcw.com/public/`（直接传原件，逐字节一致）。
   - 校验：服务器与公网回读的 `md5sum` 必须等于本地原件。
3. ⚠️⚠️ **头号坑：宝塔 nginx 全局开了 `proxy_cache`**（`/www/server/nginx/conf/proxy.conf` 里 `proxy_cache cache_one;`，被 `nginx.conf` 的 http 块 include）。**凡是带 `Cache-Control: public` 的响应都会被 nginx 缓存**，于是"文件已替换、公网还返回旧内容"，表现为百度报「验证文件的内容错误」，且**直连 `127.0.0.1:3000` 是新内容、走域名却是旧内容**。
   - 诊断三连：
     ```
     curl -s http://127.0.0.1:3000/<文件>            # 新内容 → 说明应用没问题
     curl -s https://hndcw.com/<文件>                # 旧内容 → 说明 nginx 缓存
     nginx -T | grep proxy_cache                     # 确认 proxy_cache cache_one
     grep -rl "<文件名>" /www/server/nginx/proxy_cache_dir   # 找到缓存条目
     ```
   - 清缓存：`grep -rl "<文件名>" /www/server/nginx/proxy_cache_dir | xargs -r rm -f`
   - **根治**（`src/server.js` 的 `express.static({ setHeaders })` 开头加）：
     ```js
     const p = (res.req && res.req.path) || '';
     if (/^\/(baidu_verify_|MP_verify_|sogou_verify_|BingSiteAuth|google[0-9a-fA-F]+)/.test(p)) {
       res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
       return;
     }
     ```
     `no-store` 会同时绕开 nginx `proxy_cache` 与浏览器缓存。
   - 改完 `node --check src/server.js && pm2 reload hndcw`，再连打两次域名确认都是新内容。
   - **推论**：以后凡"改了 public/ 下同名文件但不生效"，先怀疑这个 nginx 缓存。（实测缓存里**不含 HTML 页面**，只缓存带 `public` 的静态资源与 `/api/share-card`，所以动态页不受影响。）
4. 百度选域名时**填裸域 `hndcw.com`**（sitemap 全是裸域；百度把 www 与裸域当两个独立站点）。百度弹「建议添加带 www 的主站」要**点「仍然继续」**。
5. 验证文件（`baidu_verify_*` / `MP_verify_*`）**验证通过后必须长期保留**，清理 `public/` 时要排除它们。

### 6. 百度普通收录 API 推送（IndexNow 不覆盖百度！）
- **百度不认 IndexNow**，必须走自己的推送 API；IndexNow 只覆盖 Bing / Yandex / Seznam / Naver。
- 脚本 `scripts/baidu_push.py`（URL 生成与 `indexnow_push.py` 同源：静态页 + `policies status=1` + `projects status=1/dm_code` 非空）。参数：
  - `--only projects|policies|static`（默认 `projects`，按 `id desc` 取**最新**的；`static` 共 12 条，`policies` 248 条）
  - `--days N`（默认 1）/ `--limit N`（默认 **10**，对齐新站配额）
  - `--dry-run`：只打印待推 URL，**不消耗配额** —— 调参/验证必用
  - `--all`：**必须同时显式给 `--limit`**，否则脚本报错退出（防止误跑烧光配额、被百度降权）
  - **推送台账** `config/baidu_pushed.json`：记录"已成功推送"的 URL，每次推送前过滤 → 杜绝重复提交（百度会因重复提交**下调 API 权限**）。只有 HTTP 200 才记台账。
- 配置 `config/baidu.json`（`chmod 600`）：`{"site":"https://hndcw.com","token":"<准入密钥>"}`
  - `site` 存完整 URL（用于拼待推 URL）；**推给百度时只取 host**。
  - 密钥在百度「普通收录 → API提交」页面。⚠️ **该页面没有复制按钮**，token 就藏在「接口调用地址」那行 URL 的 `token=` 后面 —— 让用户在那页按 `Ctrl+A`→`Ctrl+C`→粘贴发来即可。
  - ⚠️⚠️ **token 大小写敏感**：实测 OCR 读成 `YyXL5HPndMoZYJib`，**真值是 `YyXL5HPndMOzYJIb`**（差在 `o→O`、`z→Z`、`i→I`）。靠截图/肉眼**必错**，一定要用户复制文本。
- ⚠️⚠️ **头号坑：百度官方文档的示例本身是错的。** 文档写 `site=https://xxx.com`，照抄必返
  `{"error":400,"message":"site init fail"}`。**`site` 参数只能填纯域名 `hndcw.com`，绝不能带 `http(s)://`。**
  ```python
  host = urllib.parse.urlparse(site).netloc or site          # hndcw.com
  endpoint = 'http://data.zz.baidu.com/urls?site=%s&token=%s' % (host, token)
  ```
- 用 **http**（不是 https）：`data.zz.baidu.com` 的 SSL 证书有兼容性问题。
- **单批上限 2000 条**（IndexNow 是 1 万，别混）。批间 `sleep 1`。
- 返回语义：`{"remain":N,"success":N,"not_same_site":[],"not_valid":[]}` = 成功。错误码：

  | 码 | message | 含义 |
  |---|---|---|
  | 400 | `site init fail` | **site 带了协议头**（最常见，改纯域名即可） |
  | 400 | `site error` | 站点未在站长平台验证 |
  | 401 | `token is not valid` | 密钥不对 —— **别用截图 OCR 取密钥**，`l/I/1`、`o/0`、`S/5`、`b/6` 极易读错，必须让用户**复制文本**发来 |
  | 400 | `only 2000 urls are allowed once` | 单批超 2000 |
  | 400 | `over quota` | 超当日配额 |
  | 404 | `not found` | 接口地址写错 |

- **配额铁律（实测）**：2026-09-14 首次推送返回 `{"remain":7,"success":3}` —— **新站全天配额只有 10 条**（推满 10 条后 `remain:0`）。配额由百度按"该站新产生的有价值链接量"动态分配，随站点质量提升而放宽。
  - ⇒ **15 万页面的收录主力是 sitemap，不是 API。** API 只用于把"当天最新/最关键的少量页面"优先送进去。
  - ⇒ 重复提交旧链接会浪费配额**且被下调 API 权限**，故脚本内置台账去重。
- cron 与 IndexNow **错开时间**（IndexNow 已占 09:10）：
  ```
  20 9 * * * cd /www/wwwroot/hndcw.com && PYTHONIOENCODING=utf-8 /usr/bin/python3 scripts/baidu_push.py --days 1 --limit 8 >> logs/baidu.log 2>&1
  ```
  （`--limit 8` 给 10 条日配额留 2 条余量；`/usr/bin/python3` 已实测可跑，脚本只用标准库。）
- 顺带可补「搜索展现 → 站点属性」：**主体备案号**按第 8 节的格式规则填写（⚠️ **不带 `-N` 后缀**），再点「**关联主体**」认领主体 —— 百度明示关联后"有机会快速进入搜索权益"。
- ⚠️ 本机沙箱里 `curl`/`Invoke-WebRequest` 打 `hndcw.com` 常返回 **size=0**（只有头没有体），会误判"站点挂了"。**判断线上是否正常，一律 ssh 到服务器内部 curl。**

### 7. 百度 sitemap 提交的三个铁律（2026-09-14 实测）
- **① 绝对不能提交「索引型」sitemap。** 官方原文：「索引型 sitemap 文件不予处理，**且若存在索引型 sitemap，将不允许提交新文件**，需删除索引型 sitemap 后再尝试提交数据」。
  - `https://hndcw.com/sitemap.xml` 是 `sitemapindex`（**索引型**）⇒ **只给 Google/Bing/IndexNow 用，永远不要填进百度那个输入框。**
  - 为此新增**非索引型扁平单文件** `https://hndcw.com/sitemap-baidu.xml`（改 `src/routes/seo.js`）：
    静态页 12 + 政策 248 + **最新 40,000 条**项目 = **40,260 条 / 7.06 MB / 生成约 1.0s**，实测 HTTP 200、`<urlset>` 格式。
  - 实测每条约 **184 字节** ⇒ `BAIDU_PROJECT_LIMIT = 40000` 对应约 7.4MB，给 10MB 上限**留足余量**。改这个常量时必须重算体积。
- **② 单文件上限**：最多 **50,000 个网址**且 **< 10MB**，格式 `txt` 或 `xml`。
- **③ 新站有「1-4 周观察期」，期间 sitemap 提交额度强制为 0**：页面显示「今日提交上限：0 条 / 今日提交余额：0 条」，**输入框与提交按钮被 `disabled`**（这就是"填不进去"的真相）。
  - 同时**保留「存量文件上限：1 条」**，目的是让站长**提前备好合规文件**，观察期一结束即可提交。
  - **这不是故障、不是资质问题、不是站点降权**，是百度对新站的标准风控观察机制。
  - 应对：填**主体备案号**（**不带 `-N`**，详见第 8 节） + 点「**关联主体**」认领（平台原话"填写站点的主体备案号，可以提高每日提交上限"）→ **然后等**。
  - ⚠️ **不要反复提交、不要频繁改后台信息、不要提申诉**（14 天内的新站申诉无效）。
  - 配额由"站点资源质量 / 用户价值 / 稀缺权威"综合评估；想提升可关注**平台 VIP 俱乐部**申请。
- 死链提交同理：同样有配额、同样禁止索引型、且「每次最多可提交 20 条文件地址」。

### 8. 百度「主体备案号」字段：格式 + 填不进的两个原因（2026-09-14 实测）
- ⚠️⚠️ **头号坑：这个字段不能带 `-N` 后缀。**
  - 字段问的是**主体备案号**（一个主体唯一，形如 `京ICP备12345678号`），而 `-1`/`-2`/`-5` 属于**网站备案号**的网站序号（形如 `京ICP备12345678号-5`）。
  - 依据：百度智能云官方《基本概念》——「**主体备案号**：一个主体只可存在唯一的主体备案号…常见格式 京ICP备12345678号；**网站备案号**：…常见格式 京ICP备12345678号-1、-2」；boke112 教程亦写「**主体备案号是不带-1之类的哦**」。
  - ⇒ 本站正确填法：**`琼ICP备2022013998号`**（去掉 `-5`）。带 `-5` 填会报红字「**暂未查到您网站的备案信息**」。
  - 对照：本站主体 `铎鸣市场调查(海南)有限公司` → 主体号 `琼ICP备2022013998号`；`hndmshdcw.com` 网站号 `…号-3`、`hndcw.com` 网站号 `…号-5`（**页脚挂 `-5` 是合规的，不要改页脚**）。
- **若去掉后缀仍报同错** ⇒ 次因：百度备案库从工信部同步有 **1–4 周延迟**，新备案/刚做完主体变更的域名查不到。三条路：
  - A（推荐）：等 2–3 周重填。
  - B：**反馈中心 → 网站支持 → 站点属性 → 备案号填写**，附**工信部备案查询截图**（`beian.miit.gov.cn` 查域名）+ 站点链接 + 备案号 + 问题截图，约 2 天通过。
  - C：不管它 —— 该项只影响"sitemap 每日提交上限"和主体关联权益，**不影响收录本身**。
- **与「sitemap 上限 0 条」是两件独立的事**：后者是新站 1–4 周观察期，前者是备案库同步。
- ⚠️ **不要浪费时间在免费 ICP 查询接口上**：2026-09-14 实测 vvhan / uomg / leafone / 比特 / apihz 公共 key **全部失效或限流**，`icp.chinaz.com` 是 JS 渲染抓不到数据（对已知已备案域名同样返回"暂无数据"，**做不了对照**）。
  - ⇒ 要权威结论只有两条：**让用户自己在 `beian.miit.gov.cn` 查并截图**，或**看百度平台自己的返回**。

### 9. AI 搜索可见性：canonical + JSON-LD + llms.txt + 放行 AI 爬虫（2026-09-14 铺设）

目标升级：不只"被搜索引擎收录"，而是让 15 万项目 / 4.8 万企业数据成为 **AI 回答问题时直接引用的源**。

**(1) 规范域名：www → 裸域 301**
```nginx
server {                # 80
    listen 80;
    server_name hndcw.com www.hndcw.com;
    return 301 https://hndcw.com$request_uri;   # ⚠️ 不能写 $host，否则 www 会被留在 www
}
server {                # 新增独立 www 块，443 再兜一层
    listen 443 ssl http2;
    server_name www.hndcw.com;
    ssl_certificate /etc/letsencrypt/live/hndcw.com/fullchain.pem;
    return 301 https://hndcw.com$request_uri;
}
```
配置在 `/www/server/panel/vhost/nginx/hndcw.com.conf`。`openssl x509 -noout -text | grep DNS:` 确认 SAN 含 `www.hndcw.com` 就**不用换证**。

**(2) canonical 全站化** —— `src/server.js` 全局中间件：
```js
app.use((req, res, next) => {
  res.locals.BRAND = BRAND;
  const origin = process.env.SITE_ORIGIN || 'https://hndcw.com';
  res.locals.siteOrigin = origin;
  const p = req.path && req.path !== '/' ? req.path.replace(/\/+$/, '') : '/';
  res.locals.canonicalUrl = origin + p;   // 强制裸域、剥 query、剥尾斜杠
  next();
});
```
⚠️⚠️ **头号坑：hndcw.com 有两套 head 模板，改一处必漏。**
- `views/partials/header.ejs`（约 70 页 include）
- `views/minger/_head.ejs`（**首页 `views/minger/chat.ejs` 唯一 include 的是它**；另覆盖 policy_list / policy_detail / projects_map / projects_list / suppliers_list / knowledge / guarantee / market_tech）
- 症状：改完 header.ejs，`curl -s https://hndcw.com/ | grep -c canonical` 仍是 0。
- 另有 7 个页面自带 `<head>`，用脚本注入；**注入前断言该文件 `</head>` 恰好出现 1 次**，否则会插错位置。
- ⚠️ `/projects` 是 **302**（`adminOrMinder` 权限门槛）⇒ 其 canonical / JSON-LD 一律用 **`/projects/list`**。

**(3) JSON-LD 分层**

| 范围 | 类型 |
|---|---|
| 全站（两套 head 模板） | `WebSite` + `SearchAction`、`Organization` |
| 列表/索引页 | `CollectionPage`（`/policies`、`/projects/list`、`/knowledge`）、`Dataset`（`/projects/map`、`/suppliers`） |
| 详情页 | `GovernmentService`（政策详情，标题动态）、`BreadcrumbList` |
| 服务页 | `Service`（`/guarantee`、`/market/tech`） |
| 数据说明页 | `FAQPage` + `Dataset` + `BreadcrumbList` |

**(4) robots.txt 放行 AI 爬虫**：19 个具名 UA 段，显式放行 `GPTBot / OAI-SearchBot / ChatGPT-User / ClaudeBot / Claude-Web / PerplexityBot / Applebot(-Extended) / Bytespider / meta-externalagent / Amazonbot / DuckDuckBot / YisouSpider`，同时保留 `/admin`、`/user/`、`/account`、`/api/`、`/minger/api/` 的 Disallow。

**(5) llms.txt 三件套**（llmstxt.org 约定，路由在 `src/routes/seo.js`）
- `/llms.txt`（约 2.1KB）：站点信息 + 主办单位 + 备案号 + **实时 `counts()` 数据量** + 主要页面 + 引用规范。
- `/llms-full.txt`（约 64KB）：额外附最近 100 条项目 + 300 条政策的 Markdown 链接清单。
- `/about/data`：数据说明页（来源 / 字段口径 / 更新机制 / 8 条 FAQ / 引用规范）。⚠️ **FAQ 正文与 FAQPage JSON-LD 必须共用同一份 `faqs` 数组**，否则两处口径会漂。
- 三个新页都要进 `STATIC_PAGES`（sitemap）并手动推一次 IndexNow。

**验证（一条命令回归）**
```bash
for u in / /policies /projects/map /suppliers /about/data; do
  echo -n "$u  "; curl -s https://hndcw.com$u | grep -o 'rel="canonical" href="[^"]*"' | head -1
done
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' https://hndcw.com/llms.txt
curl -s https://hndcw.com/robots.txt | grep -c 'User-agent'
```
（本机沙箱 curl 打域名常返回 size=0 ⇒ **一律 ssh 到服务器内部跑**。）

## 踩过的坑（务必照做）
- **⚠️ sitemap / 推送脚本必须过滤非法 `dm_code`，否则等于主动把 404 喂给搜索引擎**（2026-09-14 实测）：日志里 bingbot 反复抓 `/projects/DM-?-2026-000295`（`?` 会截断路径）与 `/projects/DM-%C3%A8%E2%80%B9%C2%8F-...`（UTF-8 被按 Latin-1 误解码的乱码）全部 404。
  - 根因：`encodeURI(dm_code)` **不编码 `?`**；库里也可能存在乱码 code。
  - 修法（`src/routes/seo.js`）：`validDmCode()` + `DM_OK_SQL`，**所有**取项目的查询都要套（`countProjects` / `sliceProjects` / `newestProjects` / 任何推送脚本），过滤 `? # % / 空格` 与 `À-ÿ` 乱码区段；否则分片数与内容不一致。
  - 详见技能 `hndcw-site-health-audit`（站内健康体检 + 404 治理）。
- **⚠️ PowerShell 调 `ssh` 传命令时引号会被吞掉**：`echo "20 9 * * * ..."` 到达远端变成 `echo 20 9 * * * ...`，于是 `*` 被 **glob 展开成一堆文件名**、`>>` 重定向到意外路径。**危险场景是写 crontab** —— 会把整个目录的文件名塞进定时任务。
  - ⇒ 传命令时**尽量不用引号**（`echo ===A===`、`cat f`、`head -4` 这类都安全）。
  - ⇒ 必须含引号/特殊字符的内容（如 crontab 整行），**写成文件 `scp` 上去再 `cat` 拼接**，**绝不在命令行里 `echo "..." >>`**。
- **改 crontab 的安全姿势**：
  ```
  crontab -l > /tmp/ct.txt
  cat /tmp/newline.txt >> /tmp/ct.txt     # newline.txt 由本地写好 scp 上来，LF 行尾
  crontab /tmp/ct.txt
  ```
  改完必须 `crontab -l | grep -c .`（比对行数）+ `tail -3`（看新行）+ `grep -c <关键字>`，确认没写脏、旧行没丢。
- **IndexNow 首次返 `403 SiteVerificationNotCompleted`**：属正常，等公网 key 文件可访问后**重试即 200**。
- **别用 `run_in_background` 跑 SSH 长任务**：会话会把它带死（日志 0 字节、查无进程）。全量推送**前台跑**，16 批约 18 秒。
- **Bash 引号**：多层嵌套引号极易 `unexpected EOF`。宁可分两条命令，或把 python 写到本地文件再 scp 上传执行（推荐）。注意本机 Bash 环境 `PATH` 常坏（`ls`/`mkdir`/`head`/`dirname` 全部 not found），**优先用 PowerShell 工具**。
- 「查不到文件里的 appsecret/appid」≠ 没用：老站把微信配置存在 **DB + 磁盘缓存**，文件 grep 抓不到。
- **平台密钥/ID 一律要用户复制文本**，不要靠截图 OCR：已两次踩坑（模板 template_id、百度 token）。
- **⚠️ 批量注入 EJS 要用"断言式脚本"，而且本机别用 Python**：注入前逐个断言目标文件 `</head>` **恰好出现 1 次**（本次 9 文件全 `OK`、`BAD=0`）再动手，否则会插到 head 之外。另：**本机 Python 批处理脚本会静默无输出**（exit 0、零打印、文件未生成）⇒ 改写 Node 版，并**把日志显式写入文件再 Read 验证**，不要依赖 stdout。
- **⚠️ 动 head 之前先数清有几套模板**：hndcw.com 是 `views/partials/header.ejs` + `views/minger/_head.ejs` 双套，另有 7 页自带 `<head>`。只改一套 → 部分页面 canonical/description 为空（**首页走的就是 `_head.ejs`**）。canonical 这类全站变量放在 `app.use` 中间件里，别塞进单路由。

## 需要用户配合的部分（无法自动化）
- **百度搜索资源平台** ziyuan.baidu.com：站点验证 ✅（2026-09-14 通过）→「API提交」准入密钥已配 ✅（2026-09-14）→「**sitemap**」标签提交 `https://hndcw.com/sitemap-baidu.xml`（**不是** `sitemap.xml`，见第 7 节）—— 但**新站 1-4 周观察期内额度为 0**，需先填主体备案号（**不带 `-N`**，见第 8 节）+ 关联主体，再等观察期结束。
- **Google Search Console** / **Bing Webmaster Tools**：验证后提交同一个 sitemap。
- 三者都只需做一次，之后靠 sitemap + IndexNow 自动运转。

## 验证清单
- [ ] `/sitemap.xml` 200 且为 sitemapindex
- [ ] `/sitemap-projects-1.xml` 返回 10000 条 `<loc>`
- [ ] `/sitemap-policies.xml` 248 条
- [ ] `/robots.txt` 含 `Sitemap:`
- [ ] IndexNow 推送 HTTP 200（非 403）
- [ ] `crontab -l | grep indexnow` 有记录
- [ ] 百度推送：`python3 scripts/baidu_push.py --limit 3` 返回 `http=200` 且 body 含 `remain`
- [ ] 百度推送 cron `crontab -l | grep baidu` 有记录
- [ ] `/healthz` 仍 ok（改动没破坏主服务）
- [ ] `www.hndcw.com` 任意路径 301 → `https://hndcw.com$request_uri`
- [ ] 首页 + `/policies` `/projects/map` `/suppliers` `/about/data` 均含 `rel="canonical"`，且为**裸域、无 query、无尾斜杠**
- [ ] `/llms.txt`、`/llms-full.txt`、`/about/data` 均 200（新页已进 sitemap 并推过一次 IndexNow）
- [ ] `/robots.txt` 含 19 个 `User-agent`（含 GPTBot / PerplexityBot / ClaudeBot）且含 `Sitemap:`
- [ ] 首页 HTML 含 `application/ld+json`，`@type` 含 `WebSite`
- [ ] `/projects` 的 canonical 指向 `/projects/list`（**不是** `/projects`，后者 302）
