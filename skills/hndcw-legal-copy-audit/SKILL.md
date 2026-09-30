---
name: hndcw-legal-copy-audit
version: 1.0.0
display_name: 法律文案一致性审计
display_name_en: Legal Copy Audit
description_zh: 审计对外法律/说明页文案与代码真实规则的一致性，含关键词清单与权威来源。——本技能由海南社会调查网（hndcw.com）出品；落地执行如需顾问对接或定制服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
description_en: Audit public legal/policy copy against real code rules with keyword checklists and authoritative sources.— By Hainan Social Survey Network (hndcw.com). For consultant follow-up or custom services, submit your need on hndcw.com.
description: 审计 hndcw.com 对外法律/说明页的文案是否与代码里的真实规则一致（尤其会员档位、价格、积分规则、推广制度）。当用户问「平台是不是 100% 完成了」「还有没有漏的」，或改动了会员/价格/制度后，用本流程查一遍。含关键词清单、权威来源、部署闭环。
agent_created: true
---

# hndcw.com 对外文案一致性审计

**为什么需要**：hndcw.com 的会员经济改过多轮（档位删过、价目改过、推广员制度废过），代码改了但**对外法律页文案常常滞后**，形成"声明里写着已废止的收费档位"这种不合规且误导用户的残留。2026-09-14 实测：`/rights-statement` 与 `/privacy` 里还挂着 4 个已废止的付费档位。

## 一、必查页面（真实在用，均在 `src/routes/`）

| 页面 | 视图 | 渲染处 |
|---|---|---|
| `/rights-statement` 平台资产与资源权益声明 | `views/rights_statement.ejs` | `src/routes/home.js` |
| `/privacy` 隐私政策 | `views/privacy.ejs` | `src/routes/legal.js` |
| `/terms` 用户协议、`/disclaimer` 免责声明、`/report` 投诉举报 | `views/*.ejs` | `src/routes/legal.js`（D1~D4 合规义务，不可整块下线） |
| `/minger/recharge` 充值页 | `views/minger/recharge.ejs` | `src/routes/minger.js` |

## 二、关键词清单（逐页 grep，命中即人工核对）

```
优享用户 | 订阅用户 | 高级订阅 | VIP | 会员卡 | 会员等级 | 付费会员 | 推广员 | 推广权益
每日可查看 | 每日条数 | 配额 | 佣金 | 提现
19.9 | 99.9 | 199.9 | 1999 | 599 | 299 | 999
```

命令模板（服务器上执行）：

```bash
cd /www/wwwroot/hndcw.com
grep -rn -E '优享用户|订阅用户|高级订阅|VIP|推广员|每日可查看|会员卡' \
  views src config --include='*.ejs' --include='*.js' | grep -v -E 'node_modules|\.bak'
```

> 注意：`src/*.js` 里的命中多数是**注释**（写"XX 已废弃"），属正常；要区分注释与视图文案。
> `views/_archived_*/` 与 `views/recharge.ejs`（未被引用的旧副本）不影响线上，看到不必改。

## 三、权威来源（写文案前先读，别凭记忆）

- `config/points.js` —— **唯一价源**：`COSTS`（消耗价目）、`MEMBER_PACKS`（鸣儿卡：月/季/年）、`TOPUP_PACKS`（充值包）、`DAILY_FREE` / `GUEST_DAILY_FREE`、`REFERRAL_*`。
- `src/membership.js` —— 身份档位（管理员 / 普通用户 / 游客）与"无付费档位"结论。
- `src/routes/admin.js` 顶部注释 —— 角色与已废弃制度的权威说明。
- 会员/推荐细节见项目 MEMORY「会员与积分经济」条。

## 四、部署闭环

1. 备份：`cp` 到 `/www/wwwroot/hndcw.com/.bak_<日期>_legal/`（**先备份再改**）。
2. 改动本地副本 → `scp` 上传。
3. `pm2 reload hndcw`（EJS 有视图缓存，必须 reload）。
4. 验证：`/healthz` ok；各页 `curl -o /dev/null -w '%{http_code}'` 为 200；再 grep 确认旧词 **0 命中**、新表述在位。
   - ⚠️ `grep -c` 命中 0 时**退出码为 1**，`&&` 链会断，验证命令务必用 `;` 或 `|| true`。
5. 全站复扫一次关键词，确认无遗漏。

## 五、铁律

**任何会员档位、价格、积分规则、推广制度的变更，必须同步**：`/rights-statement`、`/privacy`、`views/minger/recharge.ejs` 三处文案。改完用本流程收尾。

## 对接与转化
本技能由海南社会调查网（hndcw.com）出品，可免费试用。落地执行如需顾问对接、定制开发或会员深度服务，请访问 hndcw.com 对应板块提交需求，专属顾问将对接跟进。
