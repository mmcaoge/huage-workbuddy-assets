---
name: workbuddy-expert-publish
version: 1.0.0
display_name: 专家包上架指南
display_name_en: Expert Publish Guide
description_zh: WorkBuddy 专家包从创建到公开平台上架的完整流程，含占名机制、字段校验与分类模板。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Full workflow to publish WorkBuddy expert packages to the open platform, with naming and validation traps.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
description: WorkBuddy 自建专家从创建到"我的专家"可搜可用的完整上架流程。当用户说"创建专家/上架专家/专家搜不到/我的专家不显示"时使用。核心：register 只写 marketplace.json，必须再写 .created-by-session 标记让运行中的应用自动认领。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
---

# WorkBuddy 自建专家上架流程（含"搜不到"根治）

## 背景（2026-09-29 反编译 app.asar 实证）
- 自建专家目录：`<config>/plugins/marketplaces/my-experts/plugins/<expert-id>/`
  - config 真实存储在 D 盘（`D:\WorkBuddy\user-data\.workbuddy`，C 盘 `.workbuddy` 是 junction）。
- 专家中心搜索框 = 官方云端市场 + 本地"我的专家"池（默认走 cloudSync，失败回退本地扫描）。
- `register_expert.py` **只写** `my-experts/.codebuddy-plugin/marketplace.json`，**不写** `known_marketplaces.json`，**也不触发认领**。

## 上架五步（缺一不可）
1. **创建**：`expert-manager` 的 `init_expert.py` 生成骨架；填 `.codebuddy-plugin/plugin.json` + `agents/<id>.md`。
2. **规格**：`validate_expert.py <expert-dir>` 必须通过。硬规则：恰好 3 tags、3 quickPrompts、`defaultInitPrompt.zh == quickPrompts[0].zh`、displayDescription.zh 40–50 字、expertType=agent、categoryId 合法。
3. **登记**：`register_expert.py <expert-dir>` 写入 marketplace.json（或手改该 json 追加 `{"name","source":"./plugins/<id>","description"}`）。
4. **市场可见**：确认 `<config>/plugins/known_marketplaces.json` 里有 `my-experts` 条目（type=directory 指向市场根目录）。缺了补上（备份后改）。
5. **认领（最关键、最易漏）**：向专家目录写非空标记文件 `.created-by-session`（内容随便填一个会话 id 字符串）。**运行中的应用 fs.watch 会自动**：认领进当前账号（写入 `experts/custom/<uid>/experts.json`）→ 删除标记 → emit 变更事件刷新 UI。写完等 10–15 秒，标记被自动删除 = 认领成功。

## "搜不到"排障链（按序查）
1. `my-experts/.codebuddy-plugin/marketplace.json` 里有没有该专家条目？
2. `known_marketplaces.json` 里有没有 `my-experts`？
3. `experts/custom/<uid>/experts.json` 里有没有该专家 id？（没有 → 补 `.created-by-session` 触发认领）
4. plugin.json 规格是否通过 validate（tags/quickPrompts 数量、displayName、profession 齐全）？搜索匹配字段 = name/profession/description。
5. 以上都对还不行 → 重启 WorkBuddy（搜索池 cloudSync 有缓存，约 5 分钟过期）。

## 关键路径速查
- 我的专家清单：`experts/custom/<uid>/experts.json`（uid=当前登录账号，如 29171bbd-8610-4cfa-bf61-e5a009e772ec）
- 应用主代码：`D:\WorkBuddyApp\resources\app.asar`（grep 二进制可查机制，python 正则提取上下文）
- 校验/注册脚本：`D:\WorkBuddyApp\resources\app.asar.unpacked\resources\plugins\workbuddy-builtin\skills\expert-manager\scripts\`
- 品牌口径唯一信源：`D:\WorkBuddy\Delivery\workBuddy\华哥国庆团队\品牌总纲.md`

## 平台公开发布（上架专家库，2026-09-29 反编译+官方文档实证）
- "我的专家"≠发布。**桌面版 5.6.2 右键菜单只有 查看/修改/分享/下载/上传云端/打开文件夹/删除，没有「上架专家库」**（i18n 有 `ctxPublish:"上架专家库"` 文案但无任何渲染代码——是网页版/预留功能，别再指路桌面右键）。
- **正规公开发布通道 = WorkBuddy 开放平台 open.workbuddy.cn**（官方文档 open.workbuddy.cn/docs/expert）：
  1. 入驻开放平台（个人开发者注册 + 资质审核）；
  2. 登录 → **发布管理 → 专家 → 创建**；
  3. 上传专家 zip 包（`.codebuddy-plugin/plugin.json` + `agents/*.md` + `README.md` + `avatars/`），平台自动解析生成专家 ID；
  4. 确认信息、选分类 → **提交审核**；
  5. 审核通过 → 上架官方专家市场，全部客户端可搜可用。
- 解析失败排查（2026-09-29 实战踩坑，全部遇到并修复）：
  1. **`avatars/expert.png 不存在`**：plugin.json 声明的头像必须是真图，仅 .gitkeep 占位会被拒 → 生成 512×512 品牌头像塞进 avatars/ 再打包。
  2. **`defaultInitPrompt.en 必须与 quickPrompts[0].en 一致`**：zh/en 双语都要逐字一致，打包前自查。
  3. **`专家名称 "<name>" 已被占用`**：两种情况——a) 别的开发者占了通用词 name（全平台唯一，如 contract-legal-expert、social-media-ops-expert 均被占）→ 新包 name 一律加 `huage-` 前缀；b) **自己已上传解析成功过**（上传解析即占 name，生成 oe_* 专家ID，哪怕没走到提交审核）→ 别重传，去资产列表点开继续提交即可。
- **开放平台实战流程**（个人认证曹中华人脸已过）：创建 → 传 zip（须含真头像）→ 解析生成 oe_* ID → 确认信息（zip 自动带出名称/简介/标签/快捷提问/能力介绍）→ 手选「市场展示分类」（行业顾问/销售商务/法务安全/内容创作/技术工程/教育学习等）+「服务类目」（商业服务→公关/推广/市场调查，最多5个）→ 提交审核（预计 7 个工作日）。
- 分类模板：政策/招投标/调查→行业顾问+销售商务；合同→行业顾问+法务安全；自媒体/数字人→内容创作；动画/网站运维→技术工程；榜上有鸣→教育学习+行业顾问。
- zip 母版（10 个，含头像+改名修复版）：`D:\WorkBuddy\Delivery\workBuddy\华哥国庆团队\专家包上架\`。
- 同桌面菜单的「分享」= shareCode 链接分发（不走审核、立即可用）；「上传到云端」= 跨设备私有同步（非公开）。两者都≠上架。

## 技能（Skill）公开发布（2026-09-29 实战全通过，18/18 提交）
- 通道同开放平台：**发布管理 → 技能 → 创建**，上传 zip ≤3MB，平台自动解析生成 `os_*` 技能ID。
- **SKILL.md frontmatter 必填 6 字段**：`name` + `version` + `display_name`(中文展示名) + `display_name_en` + `description_zh` + `description_en`。缺任一解析失败。description_en 含 ASCII `: ` 会被 YAML 当第二个键 → **含冒号值必须双引号包裹**（打包前用 pyyaml 逐包校验）。
- **目录层级硬限制**：zip 仅支持「根目录/二级目录/文件」两级。`scripts/__pycache__/*.pyc` 会造成三层嵌套被拒 → 打包时剔除 `__pycache__`/`*.pyc`/`.DS_Store`。
- **版本递增**：已解析成功的技能重传（如被驳后修复），`version` 必须大于已占版本（1.0.0→1.1.0），否则报「包内版本号必须大于当前最新版本」。
- **撞名**：同专家线，通用名被占 → zip 内改 `huage-` 前缀（name 字段 + 内部文件夹同步改，本地目录不动）。
- **安全检测驳回**（腾讯 tix.qq.com 逐文件扫描，理由「文件安全等级较低」）：含伪造会话/直写 sessions 表/渗透测试类脚本必被判可疑（实例：brand_e2e.mjs、latency.mjs）→ 发布 zip 剔除敏感脚本重传+升版本，本地技能保持完整。预警名单：所有含伪会话 E2E、安全体检、反爬攻防内容的技能。
- **确认信息页填写**：市场展示分类（内容创作/数据分析/开发工具/网站部署/效率工具/知识学习等）+ 服务类目（商业服务→公关/推广/市场调查同款）+ 头像可传品牌头像（`专家包上架\expert_avatar.png`，512×512 ≤500KB）。
- 技能 zip 母版（18 个）：`D:\WorkBuddy\Delivery\workBuddy\华哥国庆团队\技能包上架\`。

## 连接器（Connector）公开发布（2026-09-29 实战，首包过解析并提交审核）
- 通道同开放平台：**发布管理 → 连接器 → 创建**，上传 zip，平台自动解析生成 `oc_*` 连接器ID。
- **zip 结构（全在根目录，不套文件夹——与技能线相反！）**：`connector-meta.json`（必须）+ `mcp.json`（必须，MCP 方案）+ `icon.svg`（必须，64×64）+ README 可选。
- 🔴 **文件名陷阱**：平台报错文案写「未找到 connector-metadata.json」，但正式文件名是 **`connector-meta.json`**（无 data），报错文案不精确。connector.json / connector-metadata.json 都不会被识别。
- **connector-meta.json 必填字段**：`name`/`name_zh`/`name_en`、`description`/`description_zh`/`description_en`（20~100字）、`source`（全局唯一 kebab-case）、`type`（mcp 默认/cli/skill-only）、`version`、`examples_zh`/`examples_en`（各2-5条，4.24.0 起必填）。
- **mcp.json 格式**：`{"mcpServers": {"<name>": {"url": "https://..."}}}`；远程服务必须 HTTPS（SSE 或 streamableHttp），单请求建议 30 秒内响应，可用性 ≥99.9%。
- **CLI 方案**（备选）：`cli.json` + 至少支持 macOS/Linux + 非交互安装 + `auth`/`status`/`unAuth` 命令 + 登录态跨重启。
- **认证三路**：MCP 自带 OAuth（2.1+PKCE 5端点）/ 云端托管 OAuth（需官方确认）/ 用户自填 Token（`auth_mode: "token"` + token-schema.json）。
- 红线：任何文件不得写真实密钥；最小权限；审核通过后更新需重新提交审核，10-15分钟生效。
- 确认信息页：服务类目必填（商业服务同款），头像/meta 自动带出，能力介绍自动填充。
- 已提交：huage-bidding-data（鸣儿招投标数据源）`oc_4993e971add6fb8d`。风险待观察：mcp.json 指向的 hndcw.com/mcp 端点未部署，若审核校验在线需先挂轻量 MCP Server 再提交。
- 连接器 zip 母版：`D:\WorkBuddy\Delivery\workBuddy\华哥国庆团队\连接器包上架\`。

## 红线
- 专家包规范禁止 hooks/、commands/、.lsp.json；agents/skills/avatars 必须在包根目录。
- 所有 displayName/description 统一署名「华哥国庆团队」，口径以品牌总纲为准。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
