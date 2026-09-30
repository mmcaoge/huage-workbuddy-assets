---
name: hndcw-branded-xlsx-export
version: 1.0.0
display_name: 品牌Excel导出
display_name_en: Branded XLSX Export
description_zh: 生成品牌化 Excel/CSV 导出，含零依赖 OOXML 生成器与隐蔽坑位避雷。
description_en: Produce branded Excel/CSV exports with a zero-dependency OOXML generator and pitfall guide.
description: 为 hndcw.com（海南社会调查网 Node/Express）做「鸣儿独家」品牌化的 Excel/CSV 导出，或修改 src/lib/xlsx.js 零依赖 OOXML 生成器时使用。含品牌版式规格、嵌入 logo、打印页码设置、以及一个极隐蔽的坑（漏写 sheetViews 会让 Excel 把行高按 2/3 渲染、长文本被截），并给出「openpyxl 解析 → Excel COM 真开 → PDF 转图目测 → 线上 HTTP 真下载」四段验证链。当用户说「把模板做成鸣儿独家的」「导出的表太丑/没品牌」「报表加 logo」「导出文字被截断」「行高不对」时使用。
agent_created: true
---

# hndcw.com 品牌化 xlsx 导出（鸣儿独家）

> 一句话原则：**自写 OOXML 的坑不在"能不能打开"，而在"Excel 渲染出来和你以为的不一样"。凡是行高/列宽/打印相关，必须用 Excel COM 读回真值，不能只看文件里的属性。**

---

## 0. 文件与部署坐标

- 生成器 `src/lib/xlsx.js`（零依赖：手写 ZIP + 最小 OOXML，不引第三方表格库，线上不加依赖）。
- 版式层 `src/lib/survey-export.js`（四个产物：答卷报表 xlsx / 模板清单 xlsx / 模板 JSON / 原始 CSV；`sendSurveyExport()` 给后台 `qAdmin` 与委托方 `/client/surveys/:id/export` 共用）。
- 品牌常量在 `survey-export.js` 顶部 `BRAND_X`（手工与 `config/brand.js` 对齐；**热线用 `0898-36356507`**，别用手机号）。
- 配色：深蓝 `#1A1A4D`、靛紫 `#4B0082`、道奇蓝 `#1E90FF`、金 `#FFD700`。
- logo：`public/images/logo-round.png`（失败回退 `minger-192.png`，再失败**退化为无图版式**，绝不让导出整体失败）。

---

## 1. 版式规格（三 sheet 统一：品牌头 4 行 + 数据 + 品牌尾 3 行）

| 区块 | 内容 |
|---|---|
| r1 | 深蓝 `#1A1A4D` 横幅，**A 列留白给浮动 logo**，B 起写「海南社会调查网 · 鸣儿商业情报助手」18pt 金色，行高 40 |
| r2 | 副行「鸣儿独家 ▪ 文档类型 ▪ 传递民意·践行价值」，行高 19 |
| r3 | 问卷标题，行高 26 |
| r4 | 2.5pt 细金分隔行 |
| r5 | meta 行（问卷类型 / 份数 / 导出时间 / 域名），行高 17 |
| r6 | 表头：靛紫底 + 金字（`HEAD_GOLD`）或深底白字，行高 28 |
| 数据 | 斑马纹（`ZEBRA`）；长文本行高由 `fitHeight(vals, widths)` 按 `estLines()` 估算自动加高（上限 150） |
| 尾部 | 3 行：金口号「传递民意·践行价值 ▪ 本件由 … 独家生成」/「微信搜一搜「鸣儿·商业情报助手」｜调查热线 0898-36356507｜hndcw.com」/「铎鸣市场调查(海南)有限公司 ｜ 琼ICP备2022013998号-5 ｜ 口径说明」 |

实现要点：`brandHead(NC, docLabel, title, metaLines)` + `brandFoot(...)` 两个共用函数，别三个 sheet 各写一份（会慢慢跑偏）。

---

## 2. ⚠️⚠️ 头号坑：漏写 `<sheetViews>` → Excel 把行高按 2/3 缩放

**症状**：文件里明明写 `ht="37"`，Excel 实际按 **24.7pt** 渲染 → 两行文字的第二行被下一行的填充盖住，看起来就是"行高不够 / 文字被截断"。改多大数字都没用，因为你在跟一个 2/3 的缩放系数搏斗。

**根因**：工作表 XML 里没有 `<sheetViews>` 时，Excel（16.0 实测）不把 `ht` 当点数用。原来代码只在 `freezeRow` 存在时才写 `sheetViews`，所以**冻结窗格的表正常、其他表全错** —— 极容易被误判成"个别 sheet 的样式问题"。

**正解**（`sheetXml()` 里）：

```js
const pane = sheet.freezeRow
  ? `<sheetViews><sheetView workbookViewId="0"><pane ySplit="${sheet.freezeRow}" topLeftCell="A${sheet.freezeRow+1}" activePane="bottomLeft" state="frozen"/><selection pane="bottomLeft" activeCell="A${sheet.freezeRow+1}" sqref="A${sheet.freezeRow+1}"/></sheetView></sheetViews>`
  : `<sheetViews><sheetView workbookViewId="0"/></sheetViews>`;   // ← 不冻结也必须写
```

**定位手法（决定性，务必照做）**：`openpyxl` 只能读 XML 原值（永远"正确"，永远看不出这个坑）；必须用 **Excel COM 读回**：

```python
ws.Rows(52).RowHeight   # 文件写 37 → 这里读回 24.7 就是中招
```

**对照实验结论**（已做过，别重复）：只注入 `<sheetFormatPr>` 无效；注入 `<sheetViews>` 立刻 37.0 正常。

---

## 3. 其余 OOXML 硬规矩（每条都踩过）

1. **`headerFooter` 里的裸 `&` 非法** → `&L/&C/&R/&P` 必须转义成 `&amp;L/&amp;C/...`，Excel 解析后还原为控制码。漏了 → Excel / openpyxl 直接报「文件损坏」。
2. **元素顺序**：`sheetPr → dimension → sheetViews → cols → sheetData → mergeCells → printOptions → pageMargins → pageSetup → headerFooter → drawing`，顺序错了报「文件损坏」。
3. **嵌图必须同时补关系文件** `xl/drawings/_rels/drawingN.xml.rels`（`r:embed="rId1"` → media），并写 sheet 的 `xl/worksheets/_rels/sheetN.xml.rels`；`oneCellAnchor` 用默认命名空间 `xdr:wsDr`（openpyxl 才认）。形状 30×30pt、锚点 `col0,row0`、left 4.5 / top 5.2 与横幅留白格对齐。
4. **打印**：不设页面设置时宽表打印/导 PDF 会被右侧截断。加 `<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>` + `<pageSetup paperSize="9" orientation="landscape" fitToWidth="1" fitToHeight="0"/>`，页数实测 7 → 4/5。
5. **列宽单位与行高单位不同**：`col width` 是"字符宽"，`row ht` 是磅；`- 1.5` 的可用宽余量是经验值（略保守，宁可多留一行高度也别截字）。

---

## 4. 验证链（四段，缺一段都可能漏掉渲染层问题）

本地临时区建议 `D:/workBuddy/tmp/qbrand`；Python 用 **D 盘 venv**（已含 openpyxl / pywin32 / pymupdf）：
`D:/WorkBuddy/.workbuddy/binaries/python/envs/default/Scripts/python.exe`
（**别用 `D:/workBuddy/user-data/.workbuddy/binaries/python/envs/default`，那个没装这些包**）

1. **样本生成**：`test_gen.mjs` —— 用**线上真实问卷结构**（ssh 到服务器 dump `surveys` + `survey_responses` 到 `dump.json`）+ 合成作答，覆盖长表 / 含分节 / 全题型（矩阵·下拉·日期）/ 零答卷四类。别只测自己造的干净数据。
2. **结构校验**：openpyxl 逐 sheet 打印 `max_row × max_column`、图片数、合并数、前 6 行、尾 3 行、`row_dimensions[n].height`；失败数必须 0。
3. **真机渲染**：pywin32 直连 Excel COM —— 逐个 `Workbooks.Open`（ReadOnly）、读 `Shapes`、`Range('B1').Interior.Color / Font.Color / Font.Size`、**`Rows(n).RowHeight` 与 ht 对比**、`ExportAsFixedFormat(0, pdf)`；再用 pymupdf 转 PNG **目测**（这一步才看得见"被下一行盖住的第二行"）。
   - 校验值：B1 填充 `5052954 = 0x4D1A1A = #1A1A4D`；字色 `55295 = 0xFFD700`；字号 18；横幅行高 40。
   - ⚠️ Excel COM 要 ASCII 文件名（中文路径/名易出问题），先拷成 `case1.xlsx`。
4. **线上 E2E**：伪造管理员会话 + `fetch` 直打 `/admin/questionnaire/:id/export?format=xlsx|template|template-json|csv`，**并把真实下载产物取回本地再跑一遍 2+3**（证明线上返回的字节就是品牌版式）。委托方路径 `/client/surveys/:id/export` 也要测。

**伪会话公式**（连错会"假通过"，务必照抄）：密钥 = `'hndcw-session-secret-' + (process.env.SESSION_SECRET || 'dev')`；cookie = `s:<sid>.<base64(hmac_sha256(secret, sid)) 去掉尾部 '='>`；store 表 `data/sessions.db` 的键是**裸 sid**，`sess` = `{"cookie":{"expires":"..."},"uid":<数字>}`，`expired` 是**毫秒时间戳**。管理员 uid = 16（曹中华）。断言要看**页面内容**，不能只看状态码。

---

## 5. 部署与收尾

```bash
# 备份 → 上传 → 语法 → 重启 → 线上验证
ssh ... "cd /www/wwwroot/hndcw.com && mkdir -p _bak_brand_YYYYMMDD && cp -a src/lib/xlsx.js src/lib/survey-export.js _bak_brand_YYYYMMDD/"
MSYS_NO_PATHCONV=1 scp -i ~/.ssh/wb_auto2 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P YOUR_SSH_PORT \
  xlsx.js survey-export.js root@YOUR_SERVER_IP:/www/wwwroot/hndcw.com/src/lib/
ssh ... "cd /www/wwwroot/hndcw.com && node --check src/lib/xlsx.js && node --check src/lib/survey-export.js && pm2 restart hndcw"
```

- **scp 必须大写 `-P`**；本地 Windows 源要 `MSYS_NO_PATHCONV=1`。
- 上传后比对 `md5sum`（本机 vs 服务器）再重启，避免半截文件上线。
- 收尾：删 `/tmp` 脚本与样本目录、删伪造会话（自证 `SELECT COUNT(*) ... = 0`）、`pm2 save`。
- 交付目录：`D:\workBuddy\Delivery\workBuddy\hndcw 鸣儿独家问卷模板\`（真实产物 + 预览 PNG）。

---

## 6. 本技能自带脚本（`scripts/`，直接拷到 `D:/workBuddy/tmp/<任务名>/` 用）

| 脚本 | 用途 |
|---|---|
| `test_gen.mjs` | 样本生成：读 `dump.json`（线上真实问卷结构）→ 造 9 份产物，覆盖长表/分节/全题型/零答卷 |
| `check_xlsx.py` | openpyxl 严格解析：结构 / 图片 / 合并 / 行高 / 首尾行 |
| `verify_excel.py` | Excel COM 真开 + **行高回读对比** + `Shapes`/B1 配色 + 导 PDF |
| `brand_e2e.mjs` | 线上 E2E：伪会话 + 4 种导出格式真下载 + ZIP 结构断言 |
| `latency.mjs` | 逐路由耗时探针（部署前后对比用，附带伪会话自清理） |

跑之前先把线上的 `surveys`/`survey_responses` dump 成 `dump.json`（见 `hndcw-site-health-audit` 技能的 ssh 坐标）。
