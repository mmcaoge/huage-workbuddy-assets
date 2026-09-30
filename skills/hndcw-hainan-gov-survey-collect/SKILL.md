---
name: hndcw-hainan-gov-survey-collect
version: 1.0.0
display_name: 海南政务采购公告采集
display_name_en: Hainan Gov Procurement Collector
description_zh: 采集海南省政府网站群全品类政府采购公告，按国家标准品目打标，支持站群外县市检索接口。
description_en: Collect Hainan government procurement announcements with national category tagging and multi-site search.
description: 为 hndcw.com 采集海南省政府网站群**全品类政府采购公告**（A 货物 / B 工程 / C 服务三级品目），按国家标准子类别打标（cat_code/cat_name），或按任意主题关键词采集。含**站群外 6 个独立县市的检索接口**（开普云 search5 / 拓尔思 IGS）、采集→过滤→分类→入库→**联系方式补全**全链路脚本 + 周采集定时，以及过滤/分类规则铁律与一堆接口逆向坑。分类器 `category_taxonomy.cjs` / `tax_classify.py` 为单一真源（A01–A09/B01–B08/C01–C23，约 36 类）。**采完必须跑联系方式补全**——站上原有补全脚本全部硬编码 ccgp 过滤，政府站记录会整块缺联系方式。当用户说「采集某某类项目」「补一批社会调查/满意度/演出赛事/物业养老项目」「让鸣儿能查到XX类项目」「加上 C20 文化体育娱乐类筛选」「挂个定期采集」「公告没有电话/联系方式」时使用。
agent_created: true
---

# 海南政府网站群 · 主题类项目采集（hndcw.com）

## 适用场景
- 「全面采集社会调查类项目」「海南各市县政府的满意度/民意/残疾人状况/旅游/公共服务监测调查项目」
- 「让鸣儿能查到 XX 类项目」（多因库里该 sector 无数据）
- 需要按**任意主题关键词**（不限于社会调查）抓海南各政府网站的公告

## 项目坐标
- 服务器：`ssh -i ~/.ssh/wb_auto2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p YOUR_SSH_PORT root@YOUR_SERVER_IP`
- 站点根：`/www/wwwroot/hndcw.com/`；生产库 `data/hndcw.db`；脚本落 `tools/`
- **scp 必须大写 `-P`**；本地 Windows 源路径加 `MSYS_NO_PATHCONV=1`

## 当前覆盖（2026-09-17 全量打通）
站群 SSI 44 站（含 18 个市县的政府门户 + 省厅局）+ 站群外 6 个独立系统市县 = **海南 19 个市县中 18 个**；
省厅局侧覆盖发改/财政/审计/统计/卫健/教育/旅文/市场监管/知识产权/林业/农业农村等。
唯一缺口是**三沙市**（`sansha.hainan.gov.cn` 长期不可达，非接口问题，已明确不采集）。

### 全品类扩展（2026-09-17 落地）
采集范围从「仅社会调查」扩成「**全品类政府采购公告**」，并用 A/B/C 三级品目打标。库内 `projects`：
- 总行 **185,622**；其中 **115,063 行带真实标准子类别 `cat_code`**（A01–A09/B01–B08/C01–C23 约 36 类），
  **70,532 行 `cat_code` 为空**（仅分到 `industry` 大类、未命中具体子类），27 行仍为 NULL。
- 本轮**新增全品类公告 14,839 条**（全量过滤后落库）。
- 按大类：`A 货物 21,884` / `B 工程 33,426` / `C 服务 59,753` / `空 70,532`。
- 子类 Top（节选）：C13 工程咨询 21,481 / C02 信息技术 15,227 / B01 房屋建筑 10,956 / B02 市政 9,458 /
  C08 商务服务 8,278 / C21 公共管理社保 7,478 / A04 医疗设备 6,732 / B07 装修修缮 6,076 /
  C20 文化体育娱乐 424。
- `industry`（A/B/C/其他）+ `sector`（旧 24 值）+ `cat_code`/`cat_name`（标准子类）**三列并存**，鸣儿与前端均可按 cat_code 过滤。
- 旧 `sector='社会调查'` 数据（扩品类前口径，约 937 条）仍保留，未被覆盖。

## 🔴 第一铁律：先验证数据源，别假设

本次实测三个源，结论**与直觉相反**，三者互补而非替代：

| 源 | 结论 | 证据 |
|---|---|---|
| **ccgp（中国政府采购网）** | ❌ 对本类项目不可用 | 海南 zone 下"满意度调查"标题 **0 条**（全国 183）；全文 17 条**全是正文顺带提及**（评标办法/代理费"比选"），非项目 |
| **ggzy.hainan.gov.cn（省公共资源交易平台）** | ⚠️ 只覆盖一部分 | 全品类 224,802 条，但"残疾人基本状况""公共服务监测""旅游满意度"检索**为 0** |
| **海南省政府网站群**（*.hainan.gov.cn + 省厅局站） | ✅ **真正的发布渠道** | 比选/遴选/征集公告发在各政府网"公示公告"栏；实测旅文厅旅游满意度调查比选、知识产权局社会满意度调查、多市县残疾人基本状况调查 |

**规律**：`比选/遴选/询价` 这类小额服务采购**不发在交易平台**，只发在**各政府网站**。凡"交易平台搜不到"的主题，先去政府网站群试。

⚠️ **ccgp 时间窗有上限**：`timeType=6` 自定义范围**最大约 1 年**（730 天直接返回"找到 0"，400 天结果被截断）。
用超长窗口得到"0 条"时，先怀疑窗口而不是"没数据"。

## 站群统一检索接口（TRS/IGS 内核，SSI）
```
GET https://db.hainan.gov.cn/igs/front/search.jhtml
    ?code=460cba3871804a4f8f696b6429e0fa08   ← 必需！缺它直接 HTTP 500
    &searchWord=<关键词>  &siteId=<站点号>  &pageSize=<n>  &pageNumber=<1 基>
    [&position=TITLE]               ← 只匹配标题：精度大幅提升
    [&orderby=time&timeOrder=desc]  ← 时间倒序：先拿最新（找可投项目）
```
返回：`{"page":{"content":[{url,title,trs_time,content,trs_site,GROUPNAME,filenum}],"total":"N"}}`
（`content` 带 `<em>` 高亮，入库前要剥掉）

- **必须逐站点指定 `siteId`，不传 500**。枚举 1~250 实测 **44 个活跃站点**（81~250 全空，不用再试）。
  站点清单见 `scripts/collect_survey_gov.py` 的 `SITES`。
- 词表设计：**用完整短语，不要用单字/宽词**（"调查"在儋州全文命中 9869 条全表噪音）。
- 精度对比（儋州）：`满意度调查` 标题 **12** 条 vs 全文 560 条；`残疾人基本状况` 标题 9 vs 全文 2721。

### 站群外「独立系统」县市（已全部打通，2026-09-17）
海口、三亚、文昌、五指山、乐东、昌江、三沙**不在站群内**（独立 CMS）。前 6 个已接入
（`scripts/collect_survey_indep.py`），**三沙 `sansha.hainan.gov.cn` 长期不可达，暂不采集**。

**如何找到这些站的接口（可复用套路）**：抓首页 → 找搜索 `<form>` 的 `action` 或搜索按钮绑定的 JS
→ 顺藤摸到 `/search5/search/s` 或 `/irs/front/search`。**siteCode 就写在首页表单的 hidden input 里**
（如 `<input name="siteCode" value="4690050001">`），不要按行政区划规律猜（猜的会返回"未找到站点信息"）。

| 站点 | 系统 | 接口 / 参数 |
|---|---|---|
| 文昌 | 开普云 search5 | `POST https://wenchang.hainan.gov.cn/search5/search/s` |
| 五指山 | 开普云 search5 | `POST https://wzs.hainan.gov.cn/search5/search/s` |
| 乐东 | 开普云 search5 | `POST https://ledong.hainan.gov.cn/search5/search/s` |
| 昌江 | 开普云 search5 | `POST https://changjiang.hainan.gov.cn/search5/search/s` |
| 三亚 | 开普云 search5（**独立搜索域**） | `POST https://search.sanya.gov.cn/search/s` |
| 海口 | **拓尔思 IGS**（另一套系统） | `POST http://www.haikou.gov.cn/irs/front/search`（**JSON body**） |

**siteCode**：文昌 `4690050001`、五指山 `4690010001`、乐东 `4690270001`、昌江 `4690260001`、
三亚 `4602000035`（省级总站是 `4600000001`）。

**开普云 search5**（4 个 hainan 子域 + 三亚）
```
POST {host}/search5/search/s    （三亚为 {host}/search/s，无 search5 前缀）
body: siteCode / searchWord / column='' / uc=1 / left_right_index='' / pageSize / pageNum
返回: {"siteName":..., "searchResultAll":{"total":N,"searchTotal":[{title,url,pubDate,content,siteName}]}}
```
- 参数取自检索页内联 JS：`var param = {'siteCode':…,'searchWord':…,'column':…,'uc':1,'left_right_index':…}`
- 分页参数是 **`pageNum`**；`title` 带 `<span>` 高亮，要剥。
- 该系统的 `ctx` 定义在 `/search5/static/common/config.js`：`ctx = protocol//host/search5/`。

**海口 拓尔思 IGS**（`/irs-c-web/search.shtml` 页 + webpack 打包的 `search.js`）
```
POST http://www.haikou.gov.cn/irs/front/search   Content-Type: application/json
body: {"code":"17d1d69fedf","dataTypeId":"259","searchWord":W,
       "pageNo":1,"pageSize":50,"searchBy":"all","orderBy":"relevance"}
返回: {"success":true,"data":{"pager":{"total":N},
        "middle":{"listAndBox":[{"type":"DATA","data":{title,url,time,content,source}}]}}}
```
- ⚠️ **`searchBy` + `orderBy` 必填**，缺任一个只回 59 字节的
  `{"success":false,"msg":"排序方式不能为空！"}`（**不是 HTTP 错误码，容易误判成"接口不通"**）。
- `code`/`dataTypeId` 来自搜索页 URL；`pageSize` 10/20/30/50 都正常。
- 海口索引含大量**新闻报道**（`source` 是「海口晚报」「中国新闻网」），靠 `survey_filter.py` 兜掉。

## 全品类采集管线（A/B/C 三级品目，2026-09-17 起）

把"只采社会调查"扩成"全品类政府采购公告 + 标准子类别打标"。流程：

```
collect_gov_all.py         站群 SSI 44 站 × 全品类词表（标题检索）→ data/gov_all_raw.jsonl
collect_survey_indep.py    站群外 6 独立县市；设 GOV_ALL=1 即切到全品类词表（同接口，换关键词）
survey_filter_all.py       ★ 规则过滤 + 分类打标：写 industry / cat_code / cat_name，输出 gov_all_filtered.jsonl
import_gov_all.py          写 projects（source_url 幂等；dm_code 从 DM-琼-{年}-{6位} 续接）
backfill_cat.cjs           ★ 全量回填：对库中既有 185k 行用修正后分类器重跑 cat_code（含 '其他' 重判 A/B/C）
```

⚠️ `collect_survey_indep.py` 默认仍是"社会调查"词表；**全品类补采要带 `GOV_ALL=1`**（或把词表换成全品类版），否则只补社会调查。

### 分类单一真源（两份口径必须一致）
- `tools/category_taxonomy.cjs` —— Node CommonJS 版（`require` 版，供 backfill / 前端 `src/agent/*` 用）。
- `tools/tax_classify.py` —— Python 版（供 `survey_filter_all.py` 用）。
- 两者共享同一份 `TAX` 数组（A01–A09 / B01–B08 / C01–C23，约 36 类）+ `classifyTop()`(A/B/C/其他) + `classifyCat()`(cat_code)。
  **改分类规则只改这两处，且必须同步改两处**（曾因只改 py 漏改 cjs 导致前后端口径不一）。

### 分类骨架（华哥给定，重点赛道）
- **A 货物**：A01 通用设备 / A02 专用设备 / A04 医疗设备 / A05 家具 / A06 车辆 / A09 软件无形资产 …
- **B 工程**：B01 房屋建筑 / B02 市政 / B03 水利 / B04 公路 / B05 生态修复 / B07 装修修缮 …
- **C 服务（重点关注）**：C02 信息技术 / C08 商务服务(会展·宣传片·招商推介·资产评估·社会调查·法律顾问) /
  C13 工程咨询管理(勘察·设计·监理·造价) / C18 教育(研学·课后) / C19 医疗卫生 / **C20 文化体育娱乐(演出·音乐节·赛事·展览)** /
  C21 公共管理社会保障(环卫·物业·养老·应急)。

### 分类器踩过的坑（修过，备忘）
1. **物业被错分 C19**：C19 的 `妇幼` 在 TAX 里先于 C21 的 `物业` 命中 ⇒ 把 **C21 移到 C19 之前**（靠前优先）。
2. **招商推介落到"其他"**：顶层正则无 `招商|推介` ⇒ `SVC_STRONG` 加 `招商|推介`。
3. **批前公示被错分 C（服务）**：`建设工程规划许可证批前公示` 含"规划"被 `SVC_STRONG` 判 C，但实为工程 ⇒ 加
   `FORCE_B = 规划许可证|批前公示|住宅楼|商住楼|商业楼|厂房|楼宇`，`classifyTop` 中 `ENG_RE 且 FORCE_B` → 强制返回 B。
4. **NO-CAT 缺口**（生态修复/海堤/推介活动/物品采购无匹配）：B05 加 `生态保护修复|保护修复|海岸带|生态治理`、
   B03 加 `海堤|堤坝`、C08 加 `推介活动|评估`、GOODS_RE 加 `物品`。NO-CAT 从 2524→2320。

### cat_code 如何流到前台与鸣儿
- **前台**：`src/routes/projects.js` 的 `/list` 支持 `?top=A|B|C`（大类）+ `?cat=C20`（标准子类）；列表页加"大类 / 标准子类别"双下拉（`CAT_GROUPS` 常量）；卡片元信息显示 `cat_code` 蓝徽章。
- **鸣儿**：`src/agent/intent.js` 的 `CAT_KEYWORDS`（口语→cat_code，约 36 条）**优先**于旧 `SECTOR_KEYWORDS`；
  `src/agent/search.js` 的 `buildWhere` 加 `cat_code=?` / `cat_code LIKE ?(catTop%)`；`src/agent/index.js` 放宽链在降级时一并清掉 `catCode/catTop`；
  `src/agent/llm.js` 的 `search_projects` 工具 schema 加 `catCode`（原 `sector` 标"旧版"）。
- 前端/鸣儿参数名对照：`top`=大类首字母(A/B/C)，`cat`/`catCode`=完整子类码(如 C20)。

## 周采集调度（`scripts/survey_weekly.sh`）
全链路：站群采集 → 独立县市采集 → 合并过滤 → 入库 → 刷新汇总表。crontab：
```
0 7 * * 1 cd /www/wwwroot/hndcw.com && bash tools/survey_weekly.sh
```
⚠️ **时段选择的坑**：这台服务器 cron 极密集 —— `collect_region` **全天 24 小时每 20 分钟**
（21 省轮转）写一次 hndcw 库，另有 clean_winner / collect_details / collect_incremental /
refresh_stats 等多个写入任务，**不存在完全空闲时段**（我先按"02:30 空闲"和"07:00 空闲"两次判断都错，
因为 `crontab -l | head -30` 把后半段截掉了 —— **看 cron 一定要看全，别用 head 截**）。
所以时段只是"相对较轻"，**真正的并发安全靠 SQLite WAL + `busy_timeout=30000`**
（`import_survey.py` 已设，与既有 `collect_incremental` 并发场景相同）。脚本里那段"检测到
collect_region 就等 60s"只是轻量避让，**不要把它当正确性依赖**。

**幂等**：`import_survey.py` 用 `SELECT source_url FROM projects` 做去重，重跑只会补差集；
采集器用 `data/*_raw.jsonl` 的 url 集自去重，**可无脑重跑**。

**`--no-backup` 必须加**：默认每次入库都 `shutil.copy2` 整个库（600MB+），
周采集每周一次会把磁盘吃光（服务器仅剩 28G）。回滚依据改为：本次 `dm_code` 区间 + `data/survey_weekly/filtered_*.jsonl` 存档。


## 🔴 采完必做：政府站记录的联系方式补全（`tools/collect_gov_contacts.py`）

**这是本项目最容易漏的一步，漏了前台档案页会整块显示「原公告未公开详细联系方式」。**

### 根因（2026-09-17 华哥反馈「全都没有电话」时查出）
站上原有的三个补全脚本，取数 SQL **全部硬编码了 ccgp 过滤**：
| 脚本 | 取数条件 |
|---|---|
| `collect_details.py` | `source_url LIKE '%ccgp.gov.cn%'` |
| `collect_details_p0.py` | `source_url LIKE '%ccgp.gov.cn%'` |
| `enrich_detail.py` | `source_name='中国政府采购网'` |

⇒ **政府网站群来源的记录（hainan.gov.cn 等）从建库起就不在任何补全任务的取数范围内**，
`owner_contact / agent_contact / contact_name / contact_phone / owner_address / agent_address` 恒为空。
实测：全库 ccgp 169,832 条有联系方式 168,932 条（99.5%）；
**非 ccgp 715 条有联系方式 0 条（0%）**。

前端 `src/routes/projects.js` 的 `hasContact` = 上述 6 个字段任一非空；
为 false 时 `views/project_detail.ejs` 与 `views/minger/print.ejs` 直接跳过联系方式块
（打印视图表现为章节号从「一」跳到「三」，**二、采购人与代理机构**整节消失）。

### ⚠️ 不是「公告没写」，是「没人去抓」
抽样 40 条 hainan.gov.cn 社会调查公告：**35% 正文含真实项目联系电话**
（如「受理单位：海南省监狱管理局 该项目采购小组 联系电话：0898-65785545」、
「联系人：符芳玉；联系电话：13976590613」），55% 只有网站页脚举报电话，10% 抓取失败。
⚠️ 但也**不能靠已存的 `raw_content` 提取** —— 那是搜索接口返回的 <300 字摘要，
690/715 条不含任何联系信息，必须回源抓详情页。

### 三条铁律（踩过才知道）
1. 🔴 **先切页脚再提取**。政府站页脚含「网站违法和不良信息举报电话」「政府综合服务热线」
   「开发维护：海南信息岛技术服务中心 联系电话：0898-12315」等，**不切掉必然把举报电话写成项目电话**。
   做法：用强标记（`违法和不良信息举报`/`举报邮箱`/`政府网站标识码`/`政府综合服务热线`/`公安备案号`/
   `公网安备`/`ICP备`/`网站地图`）找**最早出现位置**截断；强标记未命中才用弱标记（`主办单位：`/`技术支持：`）兜底。
2. 🔴 **宁缺勿滥**。举报/投诉/纪检/信访/12315/12345 类上下文一律拒绝（`REJECT_CTX`）；
   只在正文出现裸电话时才要求落在 `采购人|业主|受理单位|遴选人|我局|服务中心` 语境里。
   **假联系方式比没有联系方式更糟。**
3. 🔴 **地址要二次清洗，且判据不能一把梭**。裸正则会把「…292号**邮政编码**」「…中心和**2026年8月31日**」
   「**及联系方式（一）材料递交邮寄地址**」整段吞进来。必须按 `ADDR_STOP` 截尾 + 形状校验。
   同理姓名要做黑名单（`姓名|手机号|电话|联系|方式|单位|部门|及地址|或个人|签字…`），
   否则会存进「姓名及手机号」「联系人及地址」这种占位词。

   **地址形状判据的演进（三次才对，别重走）**：
   | 版本 | 判据 | 结果 |
   |---|---|---|
   | v1 | `(省\|市\|县\|区\|路\|号\|楼…)` 一个大集合 | **太松** ——「海南大田国家级自然**保护区**管理局」靠"保护区"的"区"蒙过去 |
   | v2 | 必须**同时**有「行政区划字」+「门牌字」 | **太紧** —— 把「海府路36号银都大厦402室」这种不带城市前缀的合法地址也杀了 |
   | v3 ✅ | **只要有门牌类字**「路\|街\|道\|巷\|镇\|乡\|村\|号\|栋\|幢\|座\|楼\|层\|室\|苑\|院\|园\|大厦\|广场\|大道\|大街」 | 正确：既排除「…管理局/统计局/委员会」这类机构名，又保住无城市前缀的地址 |

   另两个实测坑：
   - **先摘尾部序号、再去尾部标点**。顺序反了会把「…农业审批室**3.**」的"."先吃掉、只剩裸数字"3"，
     而裸数字**不能**删（「…高美仕楼3座501」是合法门牌尾）。
   - **超长优先砍括号补充说明**：政府站常写「…D栋18楼（18A1801-18B1802）3」，括号是房号细化、
     后面还跟个列表序号，整段超长；砍括号保住主干。

### 抓完必跑一次离线复洗
抓取侧的正则会随实测样本不断加严，早期批次写进去的脏值要统一收口：
```bash
DRY=1 python3 tools/clean_gov_contacts.py   # 先看会改什么
python3 tools/clean_gov_contacts.py         # 落库
python3 tools/clean_gov_contacts.py         # 再跑一次应为「0 改动」= 已收敛
```
⚠️ 复洗脚本里**绝不能**为了"以后重抓"把 `detail_fetched_at` 置 NULL（我第一版就是这么写的）——
约一半政府站公告原文本来就没有项目联系电话，置 NULL 等于让下一轮把它们全抓一遍、零新增。
正确方向是反过来：给「确无联系方式」的记录**补上**水位。

### 本次实测结果（715 条，作为下次的精度基线）
处理 715 → **补到 289 条（40%）**，无命中 384，抓取失败 42。
分字段：联系电话 289、采购人联系 201、联系人姓名 158、联系地址 111。
复洗：地址改写 23 + 作废 5，姓名作废 3（作废全是机构名/残段，判废正确）。
对照基线：ccgp 侧有联系方式占比 **99.2%**。

### 字段落位
- `contact_name` / `contact_phone` ← 公告里的「联系人 / 联系电话」（= 前端「项目联系人」行）
- `owner_contact` ← 仅当电话语境指向**采购人/业主/受理单位/遴选人**且**不含**`代理|项目管理有限公司|咨询有限公司`
  时才写（避免把代理机构电话记成采购人电话）
- `owner_address` ← 清洗后的地址
- `detail_fetched_at` ← 无论命中与否都打水位，避免重复抓
- **只填空字段，绝不覆盖已有值**

### ⚠️ 两个必须有的实现细节
1. **回抓水位 `REFETCH_DAYS`（默认 30 天）**：待补集合不能只按「字段为空」筛。
   约一半政府站公告原文本来就没有项目电话（实测），若不加水位，这些记录**每周都从头重抓一遍、零新增**，
   白烧时间还反复骚扰政府网站。这与 ccgp 的 `collect_details.py` 是同一个坑。
2. **SQL 里含 `'%ccgp.gov.cn%'`，绝不能再用 `%` 做字符串格式化** —— `%c` 会被当成转换符直接炸
   （`not enough arguments for format string`）。要用字符串拼接插值。

### 调度与规模
```bash
45 7 * * 1 cd /www/wwwroot/hndcw.com && SLEEP=1.0 /usr/bin/python3 -u tools/collect_gov_contacts.py >> logs/gov_contacts.log 2>&1
```
放在 `survey_weekly.sh`（周一 07:00 起、约 11 分钟）之后，让当周新入库的政府站记录当天就补上。
715 条单轮约 15 分钟（SLEEP=1.0，实测约 50 条/分钟）。

### 上线前的备份规矩（改库前必做）
```python
# 1) 一致性快照 —— ⚠️ 服务器 python3 是 3.6：
#    sqlite3.Connection.backup 是 3.7+ 才有（AttributeError）；
#    VACUUM INTO 该环境也报 near "INTO": syntax error。
#    → 退化方案：PRAGMA wal_checkpoint(TRUNCATE) 之后 shutil.copy2
# 2) 回滚档：把「本次会动的行」的原值 dump 成 rollback_rows.json
```
产出 `data/_bak_govcontact_<时间戳>/`：整库快照（约 660MB）+ `rollback_rows.json`。
**改完必须验证该目录公网 404**（`curl -o /dev/null -w '%{http_code}' …/hndcw.db` → 404）。

## 可投标池正文补全（`tools/enrich_biddable.py`，2026-09-17 上线）

**症状**：后台「可投标」点进详情页字段全空 —— 业主单位显示成站点名（"琼海市人民政府网"）、
投资额「金额未披露」、投标截止「—」、联系方式无。
**根因**：`monitor_tenders_daily.py` 只做**标题级**采集（它拿到的 `content` 就是检索接口的短摘要，实测约 175B），
**公告正文从未抓取** → 池内 `budget_amount=0`、`key_dates=0`、`raw_content` 空。
前端模板（`project_detail.ejs`）本身完备，**缺的纯粹是数据**，不要去改模板。

**做法**：按 `source_url` 抓正文 → 结构化抽取 → 回写主库 → 打 `body_fetched_at` 水位
（**抓失败也打水位**，否则死链每轮都重试）。

### 🔴 三条必踩坑（都真实踩过）
1. **`budget_amount` 单位是「万元」**（`src/util/format.js` 有明确注释；≥10000 万元自动显示为「亿元」）。
   写成「元」会让 5 万元显示成「5 亿元」。误写后的幂等订正：
   ```sql
   UPDATE projects SET budget_amount=ROUND(budget_amount/10000.0,4)
   WHERE biddable=1 AND budget_amount>=1000;   -- 订正后值 <1000，重跑不再命中
   ```
2. **政府公告的采购人是「无冒号跨行表格」**：正文形如「一、采购单位\n白沙黎族自治县残疾人联合会」。
   直接匹配 `采购人[:：]值` 会全军覆没。正解：先构造**压平单行文本**（`re.sub(r'\s+',' ',head)`），
   再匹配 `(?:采购人|采购单位|招标人|采购方|委托单位)(?:信息|名称)?\s*(?:名\s*称)?\s*[:：]?\s*(候选)`
   —— **冒号必须可选** —— 然后用机构名白名单校验候选，取第一个通过的。
3. **机构名识别必须用白名单尾词**，否则标题兜底会产出「关于新安家园」「…及可行」这类垃圾：
   尾词只留 `管理局|管理站|管委会|办事处|办公室|委员会|联合会|协会|中心|集团|公司|医院|学校|学院|研究院|检察院|法院|监狱|戒毒所|政府|局|厅|委|院|站|所|处|署`；
   **绝不放单字 `园/台/馆/校/社/队/行/会`**（会命中「家园 / 平台 / 网站 / 银行」）。
   另：候选含数字一律丢弃；以「关于 / 公告 / 通知 / 项目 / 本次」开头一律丢弃。
   采购人只出现在标题里时用标题推断兜底（取「关于」之前片段，再退化为首个机构名），优先级低于正文抽取。

### 字段映射（写库前必对）
`owner_unit`=业主单位、`investor`=采购代理机构、`budget_amount`（**万元**）、
`key_dates` JSON `{get_file, bid_deadline, open_time, signup_deadline}`、`project_code`、
`contact_name`、`contact_phone`、`owner_address`、`qualification`、`raw_content`、`summary`。

⚠️ **前端展示是分层的**：「投资额 / 业主单位 / 行业」在免费区可见；
**「投标截止 / 开标时间 / 资格要求 / 联系方式」在 `canFull` 积分解锁区内**（`project_detail.ejs` 的 `if (canFull)`）。
所以**匿名 curl 验证会判为 MISS，属正常**。验证走管理员会话：
`sessions.db` 取 `uid=16` 的 sid → `connect.sid=s:<sid>.<HMAC-SHA256(sid,'hndcw-session-secret-dev') base64 去=>`。

### 调度与实测基线
```bash
20 7 * * * cd /www/wwwroot/hndcw.com && WORKERS=6 python3 -u tools/enrich_biddable.py >> logs/enrich_biddable.log 2>&1
```
接在 07:00 监测之后，新标当天即有详情。
池 1016 条实测：正文 **831**、业主单位 **538**、电话 **648**、投标截止 **294**、预算 **229**、资格 **320**；
`WORKERS=10` 跑 877 条约 457s；抓取失败 46 条（个别站点反爬/超时）。

## 可投标池业务线过滤（`tools/classify_biddable.py`，2026-09-18 上线）

**为什么需要**：`biddable=1` 只表示监测脚本判的「可直接参与」（门槛低），
**不代表铎鸣干得了**。实测 1017 条里工程类 212、货物类 254，还有大量
「遴选招标代理／预算编制／监理单位」的中介类公告（业主在找中介，不是找投标人）
和「中选结果／成交公告」的已结束公告 → 华哥点进去全是废标。

### 判定逻辑（排除优先 + 能力线白名单，宁缺毋滥）
1. 命中 `EX_DONE`（中选结果/成交公告/中标公示/废标/流标/征求意见/线索征集） → 0「已结束」
2. 命中排除词（中介类 + 工程货物类） → 0「排除:xxx」
3. 命中能力线白名单 → 1（记 `fit_reason=类别(命中词)`）
4. 都不命中 → 0「未命中能力线」

能力线 5 类：调查统计 / 评估测评 / 数据信息化 / 咨询研究 / 民生服务。
判定依据写进 `fit_reason`，后台列表每行可见，便于人工复核放行。

### 字段与消费端
```sql
ALTER TABLE projects ADD COLUMN bid_fit INTEGER DEFAULT 0;   -- 1=能力线内可投
ALTER TABLE projects ADD COLUMN fit_reason TEXT;             -- 判定依据
```
- `src/routes/admin.js` 的 `/biddable`：默认 `biddable=1 AND bid_fit=1`，`?all=1` 看全量，传 `fitTotal/allTotal/showAll`
- `views/admin/biddable.ejs`：说明区加切换按钮、表头加「匹配判定」列、分页保留 `&all=1`
- **`tools/monitor_tenders_daily.py` 入库时必须同步打标**（`_CB.classify(title)`），否则次日新标又变噪声

### 实测基线（2026-09-18，池 1017 条）
能力线内 **171**（16.8%）/ 剔除 846：中介+工程货物 380、未命中 346、已结束 120。
排除类抽检 20 条**零误杀**。
⚠️ `EX_DONE` 首轮漏了「中选公告／关于确定／评选结果」等结果型写法，导致已结束标混进池 —— 已补。
**改词表后必须全量重跑分类**（`python3 tools/classify_biddable.py`），否则旧标签残留。

## 投标状态分层（`bid_status`，2026-09-18 上线）

**口径（华哥定调）**：`可投标 = 现在真能投的 = 能力线内 + 截止未过`；
其余全部项目**照旧留在总库**，一条不删，只是不进这个池。

| 状态 | 判定 | 后台默认 |
|---|---|---|
| `live` 在投期 | `bid_deadline[:10] >= 今天(北京时区)` | ✅ 默认视图 |
| `unknown` 待确认 | 抽不到 `bid_deadline` | 需点原公告核对 |
| `expired` 已截止 | 截止 < 今天 | 复盘用 |

后台 `/admin/biddable?st=live|unknown|expired|all`、`?all=1` 总库全量。
实现要点：`admin.js` 里**全量取回 biddable=1 后在 JS 算状态再切片分页**
（`key_dates` 是 JSON 字符串，SQL 不好比日期；1017 条量级内存过滤足够）。

### 截止日期离线重抽（`tools/reextract_dates.py`）
**不联网，秒级**，只对库里已有 `raw_content` 重抽。首轮抽取率仅 29%，根因：
`enrich_biddable.py` 用 `get_text('|')` 逐单元格切分，政府公告 HTML 表格把日期切碎成
「1、时间：202」+「6年9月15日」+「至」→ 普通正则全落空。三招修复：
1. **数字粘连** `glue()`：`(\d)[\s|　]+(\d)` → `\1\2`，拼回 `2026年9月15日`
2. **标准句式优先**：`PAT_BEFORE_SUBMIT` 匹配政府采购固定写法
   「并于2026年09月15日15:30（北京时间）前提交响应文件」—— 覆盖率最高的单一模式
3. 区间「A至B」取右端、无年份按发布年推断、「公告之日起 N 个工作日」add_workdays 推算

效果：31 → **59** 条有明确截止。剩余 112 条是公告本身未写明（网页正文只有「见附件」），
**如实标 unknown，绝不编造日期**；下一步可攻附件下载解析（PDF/docx）。

### 改词表后的标准动作
```bash
DRY=1 python3 tools/classify_biddable.py      # 预演看分布 + 能力线内样例
python3 tools/classify_biddable.py            # 正式写库（全量重刷，幂等）
```
改 admin.js / ejs / monitor 前先 `cp` 到 `data/_bak_fit/`（本轮已建该备份目录）。

## 脚本清单（`scripts/` ↔ 服务器 `tools/`，两边 md5 必须一致）
```
survey_topics.py            ★ 检索词表【单一真源】—— 两个采集器都 import 它，改词表只改这一处
                               （两个采集器同时 defined TOPICS 会导致改一处漏一处）
collect_survey_gov.py       站群 SSI：44 站 × 34 词 标题检索 → data/survey_gov_raw.jsonl
collect_survey_indep.py     站群外独立县市：6 站（3 种接口）→ data/survey_indep_raw.jsonl
                              支持 ONLY=haikou,wenchang / MAX_PAGE / PAGE_SIZE / SLEEP / WORKERS
survey_filter.py            规则过滤，RAW 支持**逗号分隔多来源**（两来源合并后跨源 url 去重）
                              实测：站群 8452 + 独立 3393 + 补跑 ≈ 12627 条 → 679 条
import_survey.py            写 projects（先 --dry-run 预演；周采集加 --no-backup）
                              province='海南省'  industry='服务'  sector='社会调查'
survey_weekly.sh            周采集全链路（采集→过滤→入库→刷汇总），crontab 每周一 07:00
collect_gov_contacts.py     ★ 政府站记录·联系方式补全（见上一节，crontab 每周一 07:45）
                              覆盖全部非 ccgp 记录，不限社会调查；SLEEP/LIMIT/DRY/REFETCH_DAYS 可调
clean_gov_contacts.py       ★ 补全后的**离线复洗**（不联网，只对已存值做纯字符串复洗，幂等）
                              `import collect_gov_contacts` 复用 clean_addr / NAME_BAD，规则单一真源
                              抓完必跑一次；DRY=1 先预演。跑完应"0 改动"（= 已收敛）
enrich_biddable.py          ★ 可投标池正文补全（详见「可投标池正文补全」节，crontab 每日 07:20）
                              抓 source_url → 抽取 owner/预算(万元)/截止/联系/资格 → 回写 + body_fetched_at 水位
                              DRY=1 预演只打印；LIMIT / WORKERS 可调
classify_biddable.py        ★ 可投标池业务线过滤（详见同名章节）—— 打 bid_fit/fit_reason
trio.js（src/lib/）          ★ 三件套：详情/地址/电话 —— 全站单一真源（详见「三件套」节）
                              排除优先 + 5 类能力线白名单；DRY=1 预演；改词表后全量重刷即可
                              被 monitor_tenders_daily.py import，入库即打标
reextract_dates.py          ★ 投标截止日期离线重抽（不联网秒级，详见「投标状态分层」节）
                              数字粘连 + 「XX前提交响应文件」标准句式 + 区间/相对日期
                              DRY=1 预演；SCOPE=fit(默认)|all
build_delivery_xlsx.py      交付 Excel 生成器（本地跑，读 tmp/hn1.json + filtered_*.jsonl → 品牌版式 xlsx）

全品类新增（2026-09-17）：
collect_gov_all.py          站群 SSI 全品类采集（分类词表）→ data/gov_all_raw.jsonl
collect_survey_indep.py     设 GOV_ALL=1 → 独立县市也走全品类词表（同接口换关键词）
survey_filter_all.py        ★ 全品类过滤 + 分类打标（industry/cat_code/cat_name）→ data/gov_all_filtered.jsonl
import_gov_all.py           全品类入库（source_url 幂等；dm_code 续接 DM-琼-{年}-{6位}）
backfill_cat.cjs           ★ 全量回填 cat_code：对库中既有行用修正后分类器重跑（含 '其他' 重判 A/B/C）
category_taxonomy.cjs      ★ 分类单一真源（node require 版）：TAX + classifyTop/classifyCat/classify
tax_classify.py            ★ 分类单一真源（py 版，survey_filter_all.py 调用）；与 .cjs 口径必须一致
```
典型单次全量耗时：站群 44 站 ≈ 10–15 分钟；独立 6 站 ≈ 5–8 分钟；过滤+入库 < 1 分钟。
入库后**必须**刷汇总表：`node tools/refresh_stats.mjs`（前台 `sector` 筛选读 `stats_group`）。

⚠️ **两个采集器的 `ONLY` 环境变量语义不同**（站群是 siteId 整数、独立县市是站点 key 字符串），
所以**独立采集器绝不能 `from collect_survey_gov import TOPICS`** —— 那会让主模块顶层
`ONLY = [int(x) ...]` 解析 `ONLY=haikou` 直接 ValueError 崩掉。词表已抽到 `survey_topics.py` 解决。


## 🔴 过滤规则铁律（本次最大教训）
**绝不能用「调查 / 测评 / 评估 / 统计 / 监测」单词匹配**。实测会误收：
「遥感调查」「田长制巡田外业调查」「国土日常变更调查」「网络安全等级保护测评」
「广播电视发射塔安全检测评估」「专职人民调解员选聘」。
必须用**组合短语（对象词 + 动作词）**：
```python
r'满意度(调查|测评|评价|评估|监测|回访|指数)'
r'(群众|公众|市民|居民|社会|服务|游客|企业|市场主体)满意度'
r'残疾人.{0,10}(状况|需求|信息|就业|服务).{0,8}(调查|核查|采集|评估|监测|摸底)'
r'旅游(统计|满意度|服务质量|调查|监测|数据)'
r'公共服务.{0,8}(质量|满意度|监测|评价|评估|调查|水平)'
r'(第三方|社会|绩效|需求|服务质量|政策)评估'
```
另需**硬排除**三类高发噪音（各占总量的很大比例）：
1. **单位自查公示** —— 东方市一家 100+ 条「XX单位关于 2025 年度预算绩效自评情况的公示」，**不是采购项目**；
2. **实物采购伪装** —— 琼中「统计调查和法治宣传纪念品采购」；
3. **生态/生物调查** —— 保亭「水生植物覆盖度调查」。

规则演进（可作精度标尺）：单词版 192 条（大量误收）→ 组合短语版 759 条 → 去自评等噪音后 **655 条**。

## 字段对齐（写 projects 前必查现网取值）
```sql
SELECT DISTINCT city FROM projects WHERE province='海南省';      -- 看命名风格
SELECT DISTINCT sector FROM projects;                           -- 看二级标签
```
- ⚠️ **`city` 必须对齐现网既有写法**：现网用简写「**保亭黎族自治县**」「**琼中黎族自治县**」，
  **不是**官方全称「保亭黎族苗族自治县」。写全称 → 同一县两种写法 → 前台筛选/统计分裂。
- `dm_code` 格式 `DM-{省简称}-{年}-{6位流水}`，续号：
  `SELECT MAX(CAST(substr(dm_code,11) AS INTEGER)) FROM projects WHERE dm_code LIKE 'DM-琼-%'`
- `sector` 标签已由 `src/collect/normalize.js:102` 定义：`['社会调查', /社会调查|民意|普查|调研|统计调查/]`
  —— **鸣儿的"社会调查"分类早就在，只是没数据**；采集前先查该标签再决定是否新增。

## 验证闭环（缺一不可）
```bash
# 1) 库内
sqlite3 data/hndcw.db "SELECT count(*) FROM projects WHERE sector='社会调查' AND status=1;"
# 2) 前台 —— 公开列表是 /projects/list
curl -s 'https://hndcw.com/projects/list?sector=社会调查' | grep -o '共 [0-9]* · [0-9]*省'
# 3) 鸣儿 —— 参数名是 text（不是 q！传错会回"请先说说你要查什么"）
curl -s -X POST https://hndcw.com/minger/api/ask -H 'Content-Type: application/json' \
     -d '{"text":"儋州市残疾人状况调查项目"}'
# 4) 联系方式（补全后必查）—— 走打印视图，它不受 unlocked 限制
curl -s "https://hndcw.com/minger/project/DM-%E7%90%BC-2026-005486/print" | grep -o '二、采购人与代理机构'
# 5) 全品类 cat_code（扩品类后必查）—— 前台按大类/子类过滤 + 鸣儿 catCode
curl -s 'https://hndcw.com/projects/list?top=C'  | grep -o '共 [0-9]* · [0-9]*省'   # 应≈ 59753
curl -s 'https://hndcw.com/projects/list?cat=C20' | grep -o '共 [0-9]* · [0-9]*省'  # 文化体育娱乐≈ 424
node -e "const {DatabaseSync}=require('node:sqlite');const db=new DatabaseSync('data/hndcw.db'); \
console.log('with_cat', db.prepare(\"SELECT COUNT(*) c FROM projects WHERE cat_code IS NOT NULL AND cat_code<>''\").get().c, '/', \
db.prepare('SELECT COUNT(*) c FROM projects').get().c);"   # 应≈ 115063 / 185622
```
⚠️ **`/projects` 是管理员页**（`adminOrMinder`），游客 302 回首页是**设计行为，不是 bug**；公开入口是 `/projects/list`。
⚠️ **验联系方式一定要走 `/minger/project/:dm/print`** —— 档案页 `/projects/:dm` 的
`hasContact` 带 `unlocked` 前置条件（`src/routes/projects.js:293`），游客看不到，
直接 curl 档案页会误判成"没补上"。打印视图那条（`:370`）没有 `unlocked` 门。
判断成功的标志：打印视图出现「**二、采购人与代理机构**」节且含「采购人联系方式 / 项目联系人 / 联系电话」——
补全前该节**整节消失**，章节号直接从「一」跳到「三」。

## 交付
导出 Excel（含"项目清单 + 统计概览"双 sheet）：
`D:\workBuddy\Delivery\workBuddy\海南社会调查类项目清单\海南各市县社会调查类项目清单_YYYYMMDD.xlsx`

生成方式（**每轮采集后重建，勿手写**）——两步：
```bash
# 1) 服务器导出 DB 行 → 本地 D:/workBuddy/tmp/hn1.json
ssh … 'cd /www/wwwroot/hndcw.com && node -e "
const {DatabaseSync}=require(\"node:sqlite\");
const db=new DatabaseSync(\"data/hndcw.db\");
const rows=db.prepare(\"SELECT dm_code,title,city,owner_unit,publish_date,stage,source_name,source_url
  FROM projects WHERE sector=? AND province=? ORDER BY publish_date DESC, dm_code DESC\").all(\"社会调查\",\"海南省\");
require(\"fs\").writeFileSync(\"/tmp/hn1.json\", JSON.stringify(rows));"'
# 2) 本地跑生成器（表头版式/列宽/冻结/统计块都在脚本里）
python scripts/build_delivery_xlsx.py
```
⚠️ **`projects` 表字段名**：是 `owner_unit`（不是 `owner`），**没有 `keyword` 列**
（"命中特征"来自 `data/survey_weekly/filtered_*.jsonl` 的 `hit` 字段，按 `url` 对齐）。
⚠️ **地区判定别用 `r'(市|县)'` 裸匹配来源站名** ——「海南省**市场**监督管理局」会被误判成市县站
（本次 5 条省级记录被错标"(未识别)"）。必须拿**真实市县名清单**去比。

验证（缺一不可）：openpyxl 读回 + **Excel COM 真开**（`win32com.client.Dispatch('Excel.Application')`）
+ 导 PDF → pymupdf 转 PNG 目测。行高抽检：`ws.Rows(1..3).RowHeight` 应等于脚本设定值（30/22/26），
若被压成 2/3 说明 OOXML 缺 `sheetViews`（见技能 `hndcw-branded-xlsx-export`）。

## 🔴 服务器操作坑（都是实测踩出来的）
- `pkill -f <脚本名>` 会**匹配到 ssh 自身命令行把自己杀掉**（输出全空、后续命令不执行）。
  改用：`S=脚本名; ps -ef | grep "$S.py" | grep -v grep | awk '{print $2}' | xargs -r kill -9`
- 采集用 `setsid nohup ... < /dev/null &`，否则 ssh 断开可能带走子进程。
- 政府站请求要克制：站级并发 5、`SLEEP=0.35`，单站内串行。
- **服务器 python3 是 3.6**：`subprocess.run(..., capture_output=True)` 会 `TypeError`（3.7+ 才有）。
  用 `subprocess.check_output([...])`；要传 stdin（如写 crontab）用
  `check_output("crontab -", shell=True, input=text.encode())`。
- ⚠️ **`ThreadPoolExecutor` 里的异常会被静默吞掉**：`submit` 后不取 `future.result()`，
  线程里崩了你也只看到"这个站新增 0 条"，**误判成接口正常但无数据**。
  必须 `for fu in as_completed(futs): try: fu.result() except: traceback.print_exc()`。
  （本次海口站就是这样"只请求 1 次、新增 0 条、无报错"躲过一轮排查。）
- ⚠️ **`clean_text` 要做类型兜底**：个别接口把 `title`/`content` 返回成 dict/list，
  `re.sub` 直接 `expected string or bytes-like object` 崩掉整站。开头加
  `if not isinstance(s, str): s = '' if s is None else str(s)`。
- ⚠️ **scp 会静默覆盖服务器上的在线补丁**：在服务器直接改好脚本、之后又 scp 本地旧版上来，
  改动就没了（本次把 `from survey_topics import TOPICS` 覆盖回旧写法，`ONLY` 又崩）。
  **规矩：改动一律先落本地 `scripts/`，再 scp；或改完服务器立刻回同步本地。**
  收尾前跑一次双侧 `md5sum` 对齐（见"脚本清单"）。
- 清临时文件：服务器 `/tmp/*.py` 与本地 `D:/workBuddy/tmp` 任务完成即清。

## 三件套：详情 / 地址 / 电话（`src/lib/trio.js`，2026-09-18 上线）

华哥定调：鸣儿完整档案里已有的「详情、地址、电话」三样能力，要抽成通用三件套，
铺到后台可投标池与项目详情页，一处取全、不必翻完整档案。

### 单一真源铁律
任何页面展示这三样，**必须调 `buildTrio(p, {masked})`**，禁止自己拼字段（否则脱敏与来源优先级会各写一套）。

```js
import { buildTrio, trioScore } from '../lib/trio.js';   // 注意：routes/ 下是 ../lib，不是 ../../
const t = buildTrio(row, { masked: !full });
// → { masked, detail{ok,url,local,len,brief}, address{ok,text,from}, phone{ok,text,name,from} }
```

取值优先级（谁最有用谁优先）：
- 地址：采购单位 `owner_address` > 代理机构 `agent_address` > 中标单位 `bid_address`
- 电话：项目联系人 `contact_phone` > 采购单位 `owner_contact` > 代理 `agent_contact` > 中标 `bid_contact`
- 兜底：字段里夹带号码（「张三 13800138000」）用 `PHONE_RE` 拆；号码里夹姓名也拆回 `phone.name`

### ⚠️ 脱敏是变现红线
游客/未解锁看到的是骨架：`089****8676`、`海南省海口市美兰区海…（完整地址需解锁）`，
且**脱敏态不渲染复制按钮与 `tel:` 链接**（否则游客复制一堆星号，体验崩）。
后台（admin）全显示。`trioScore(t)` 返回 0-3，可用于「信息全的先投」排序。

### 接入点
- `src/routes/admin.js` /admin/biddable：SQL 加 9 个字段，`all.forEach` 里 `r.trio = buildTrio(r)`
- `views/admin/biddable.ejs`：项目标题后一列「三件套：详情 / 地址 / 电话」（colspan 11→12）
- `src/routes/projects.js` + `views/project_detail.ejs`：hero 下方三件套卡，`masked: !full`
- 复制能力：`.js-copy` + `data-copy` 属性，clipboard 失败降级 `execCommand('copy')`

### 实测（2026-09-18）
能力线内 171 条：地址 95、电话 133、联系人 128。游客视角零泄露（已验证）。

## 鸣儿能力情报补抽（`tools/reextract_qual.py`，2026-09-18 上线）

华哥反馈「项目详情页鸣儿的能力情报没接上」。诊断结论：**不是前端问题，是抽取没跑全**——
`evaluation`（评分标准）全库 **0 条**、`purchase_items`（采购标的）**从未有脚本写过**、
`qualification` 漏抽 85 条（比选类公告写「五、申报单位条件」「参选条件」「报价人资格」，
而 enrich 的 RE_QUAL 只认「资格要求/资格条件」）。

脚本离线补抽三块（幂等，只补空字段）：资格要求 / 评分标准 / 采购标的（JSON `[{name,qty,budget}]`）。
用法：`DRY=1 python3 tools/reextract_qual.py`（预演）· `DM=xxx` 单条调试 · `SCOPE=fit` 只跑能力线内。

### 实测（2026-09-18，池 1017）
资格要求 374→488、评分标准 0→160、采购标的 0→366。目标页四块情报卡全部渲染。

### ⚠️ 三个正则坑（都踩了）
1. **章节编号前是句号**：`……1月。\n三、项目实施内容及要求`，分隔字符类必须含 `。，,；;：` 与 `\s`。
2. **编号后夹修饰词**：「三、**项目**实施内容」——词表要求紧邻会漏，需加 `.{0,6}?` 容错。
3. **词表词出现在正文句子里**（"经营范围涵盖本次项目实施内容"）会被误当标题
   → 采购标的锚点必须要求**章节编号形态**，否则抽出来全是资质证照句子。
   再用 `BAD_ITEM`（营业执照/具备/职称/资金来源…）过滤条目，宁缺毋滥。

### 关联
`reextract_dates.py` 的 `glue()`（数字粘连）必须复用，否则 HTML 表格切碎的文本拼不回来。
