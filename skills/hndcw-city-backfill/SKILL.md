---
name: hndcw-city-backfill
version: 1.0.0
display_name: 招投标按城市补数
display_name_en: Bidding Data City Backfill
description_zh: 招投标项目库按城市/省份定向补抓历史数据，含入库体检与脏数据清洗。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Backfill bidding project data by city/province with ingestion health checks and data cleansing.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
description: 为 hndcw.com（海南社会调查网）政府招投标项目库按城市/省份定向补抓历史数据，并做入库体检与脏数据清洗。当用户提出「某某市项目太少」「补一批历史数据」「把海口三亚也补上」「数据好像不对」等需求时使用。
agent_created: true
---

# 按城市定向补抓 + 数据体检（hndcw.com）

## 适用场景
- 某个市/县在项目库里条数明显偏少，需要补历史（如「东方市怎么才 19 条」）。
- 某个省首次接入需要铺量。
- 怀疑库里有脏数据（金额离谱、日期离谱、重复条目），需要体检 + 清洗。

## 项目坐标
- 源码（本地）：`D:/WorkBuddy-Projects/2026-06-07-20-59-29/hndcw`
- 服务器：`ssh -p YOUR_SSH_PORT -i ~/.ssh/wb_auto2 -o UserKnownHostsFile=C:/Users/琼崖纵队/.ssh/known_hosts -o StrictHostKeyChecking=accept-new root@YOUR_SERVER_IP`
- 站点根：`/www/wwwroot/hndcw.com/`，生产库：`/www/wwwroot/hndcw.com/data/hndcw.db`
- 服务：`pm2 restart hndcw`
- Node：`C:/Users/琼崖纵队/.workbuddy/binaries/node/versions/22.22.2-2/node.exe`
- Python：`C:/Users/琼崖纵队/.workbuddy/binaries/python/versions/3.13.12/python.exe`

## 🔴 铁律（血的教训，不许违反）
1. **ccgp 严禁并发**。同一时刻只能有一个采集进程打中国政府采购网，页间隔 ≥2 秒。多进程猛打会触发「您的访问过于频繁，IP: xx」限流页，表现为瞬间 0 入库（页面统一 2919 字节）。
2. **不推测补造**。脏金额一律置 NULL（页面显示「公告未披露」），脏日期一律置 NULL。宁可留空也不能编一个数/一个日期。
3. **清洗必须用 `typeof()` 精确锁类型**，绝不用 `<1`、`>0` 这类条件当清洗依据——会把占 90% 的「未披露」（0/NULL）全选进去误伤。
4. **动库前先 `cp` 带时间戳备份**到 `data/hndcw.db.bak_YYYYMMDD_HHMM`，别用会滚动覆盖的同名 bak。
5. **本地 curl 走代理会返回 502**，验证本地服务必须加 `--noproxy '*'`。
6. 部署要**逐文件精确路径 scp**，不能「多源→单目录」平铺（会把 `src/routes/x.js` 落错成 `src/x.js` 致 502）。

## 流程

### 1. 先摸底（只读，别动手）
```bash
ssh ... "cd /www/wwwroot/hndcw.com && sqlite3 -header -column data/hndcw.db \"SELECT city,count(*) c FROM projects WHERE province='海南省' GROUP BY city ORDER BY c DESC LIMIT 15;\""
```

### 2. 备份
```bash
ssh ... "cd /www/wwwroot/hndcw.com/data && cp hndcw.db hndcw.db.bak_$(date +%Y%m%d_%H%M) && ls -lh hndcw.db.bak_*"
```

### 3. 串行补抓列表
`collect_city.py` 的原理：ccgp 的 `bxsearch` 同时支持 `kw=`（关键词）和 `timeType=6&start_time/end_time`（自定义时间段），两者叠加后用「城市名 + 逐月」检索，每月只要 1~2 页，比 `collect_by_month.py` 整省重抓省一个数量级的请求量。

单城市：
```bash
ssh ... 'cd /www/wwwroot/hndcw.com && PROV=海南 KW=东方 CITY=东方 MONTHS=12 PAGES_PER_MONTH=8 SLEEP=4 DB_PATH=/www/wwwroot/hndcw.com/data/hndcw.db nohup python3 -u collect_city.py > city_xx.log 2>&1 &'
```

多城市（**必须串行**，参考 `tmp/run_cities.sh`）：
```bash
#!/bin/bash
cd /www/wwwroot/hndcw.com || exit 1
export DB_PATH=/www/wwwroot/hndcw.com/data/hndcw.db
export PROV=海南 MONTHS=12 PAGES_PER_MONTH=8 SLEEP=4
for C in 海口 三亚 儋州 澄迈; do
  echo "===== START $C $(date '+%F %T') ====="
  KW=$C CITY=$C python3 -u collect_city.py
  echo "===== END $C $(date '+%F %T') ====="
  sleep 15
done
echo "===== DETAILS $(date '+%F %T') ====="
WHERE_FILT="city IN ('海口市','三亚市','儋州市','澄迈县')" LIMIT=0 SLEEP=0.3 python3 -u collect_details.py
echo "===== ALL DONE $(date '+%F %T') ====="
```
每个市约 8-10 分钟（含限流退避）。脚本自带耐心退避（60/120/300/600/900s）与开工前解封探测，被限流不用干预。

**注意城市规范名**：脚本内 `canon_city()` 会把「东方」规范成「东方市」。若库里同时存在短名和全名，检索会漏，需统一：
```sql
UPDATE projects SET city='东方市' WHERE province='海南省' AND city='东方';
```

### 4. 补详情（预算/联系人/电话/附件）
```bash
ssh ... 'cd /www/wwwroot/hndcw.com && WHERE_FILT="city='"'"'东方市'"'"'" LIMIT=0 SLEEP=0.3 nohup python3 -u collect_details.py > df_details.log 2>&1 &'
```
`WHERE_FILT` 支持任意 SQL 片段，多城市用 `city IN (...)`。

### 5. 体检（补完必做）
四查：
```sql
-- 重复标题
SELECT count(*) FROM (SELECT title FROM projects WHERE city LIKE '%东方%' GROUP BY title HAVING count(*)>1);
-- 空标题/无日期
SELECT sum(title IS NULL OR length(title)<6), sum(publish_date IS NULL) FROM projects WHERE city LIKE '%东方%';
-- 金额类型分布（出现 text 即为污染）
SELECT typeof(budget_amount) tp, count(*) c FROM projects GROUP BY tp;
-- 日期合法性（非法/越界）
SELECT count(*) FROM projects WHERE publish_date IS NOT NULL AND (
  publish_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
  OR substr(publish_date,6,2) NOT BETWEEN '01' AND '12'
  OR substr(publish_date,9,2) NOT BETWEEN '01' AND '31'
  OR publish_date < '2000-01-01' OR publish_date > date('now'));
```

### 6. 清洗（本地写 .sql 文件 → scp → `sqlite3 data/hndcw.db < file`）
**绝不用 ssh heredoc 写 SQL**——引号会被转义搞坏（踩过：整段 SQL 变成无意义字符）。

金额清洗：
```sql
UPDATE projects SET budget_amount=NULL WHERE typeof(budget_amount)='text';
UPDATE projects SET budget_amount=NULL WHERE typeof(budget_amount) IN ('integer','real') AND budget_amount>1000000;
UPDATE projects SET budget_amount=NULL WHERE budget_amount=0;
```
日期清洗：
```sql
UPDATE projects SET publish_date=NULL WHERE publish_date IS NOT NULL AND (
  publish_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
  OR substr(publish_date,6,2) NOT BETWEEN '01' AND '12'
  OR substr(publish_date,9,2) NOT BETWEEN '01' AND '31'
  OR publish_date < '2000-01-01' OR publish_date > date('now'));
```

### 7. 堵源头（清洗后必须同步改采集脚本，否则白洗）
- 金额：`collect_province.py` 的 `safe_amount()`（含中文丢弃 + 上限 100 亿元）、`collect_details.py` 的 `float()` + 范围校验。
- 日期：`collect_province.py` 的 `valid_date()`（正则 → 年份区间 → `datetime()` 构造器校验真实日历日 → 不晚于今天+31 天）。

### 8. 验证检索链路
```bash
ssh ... 'cd /www/wwwroot/hndcw.com && node --input-type=module -e "
import { searchProjectsStrict } from \"./src/agent/search.js\";
const r = searchProjectsStrict({province:\"海南省\", city:\"东方\"}, 5);
r.forEach((p,i)=>console.log((i+1)+\". \"+p.publish_date+\" \"+p.title.slice(0,30)));
" 2>&1 | grep -v Experimental'
```
再用 `extractFilters` 验证口语问法能解析出正确的 city/keyword。

## 已知坑
- **ccgp 分页重复**：结果不足一页时 `page_index=2/3` 会把首页那几条原样再返回。列表脚本按「整页无新增即 break」规避；Node 端 `src/agent/ccgp.js` 按 `url+title` 双 Set 去重。
- **WAF 403**：详情页不带浏览器 UA + Referer 会 403，`collect_details.py` 已带。
- **限流页识别**：返回体约 2919 字节且含「访问过于频繁」，不是正常结果。
- 大省（辽/粤/冀）日更 100+ 条，超出分页上限，近 20 天实际只能采到最近 7-10 天；小省才能采满。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
