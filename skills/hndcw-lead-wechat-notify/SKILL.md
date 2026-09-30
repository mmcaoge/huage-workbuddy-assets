---
name: hndcw-lead-wechat-notify
version: 1.0.0
display_name: 线索微信通知
display_name_en: Lead WeChat Notify
description_zh: 为留资表单接入微信模板消息提醒管理员，含 openid 获取验证与部署闭环。
description_en: Wire lead form submissions to WeChat template-message alerts with openid verification and deploy loop.
description: 为 hndcw.com 的留资表单接入「提交 → 微信模板消息提醒管理员」。当用户提出「XX 也要微信通知管理员」「线索没人看」「加个提醒」等需求时使用。含 notify.js 复用方式、模板字段对齐、https.request chunked 大坑、openid 获取与验证、新增链路的部署闭环。
agent_created: true
---

# 线索提交 → 微信提醒管理员（hndcw.com）

## 一、现状（已上线，勿重造）

| 链路 | 入口 | lead_type |
|---|---|---|
| 投标保函 | POST `/guarantee/submit` | 投标保函 |
| 技术服务咨询 | POST `/market/consult` | 技术服务咨询 |
| 政策咨询 | POST `/policies/consult` | 政策咨询 |

三者均：校验入参 → 落 `service_leads` → 调 `notifyAdminLead(...)`。

## 二、三层结构

1. `config/notify.js`：两个值 `adminOpenid` / `templateId`（可用环境变量 `ADMIN_OPENID` / `ADMIN_TEMPLATE_ID` 覆盖）。
   - 现用：openid `o4qzr5-lpP77lcBjPFVp5wTsnZVo`（华哥/曹中华），模板 `MG6jdBAE_05ulStrr9-eQzhGNAuHLY2GS5sSDsS7IjA`（公众号「万能表单**客服**通知」）。
   - 备用：`XuTHyJjPwjlxe9NWD1GuKAIf5M-lL4IEKPc9XRed7qc`（「万能表单**用户**通知」，给客户本人发回执）。
2. `src/notify.js`：`notifyAdminLead({ title, name, phone, content, remark, time })`，**best-effort**——未配置直接 skip，异常全吞，绝不阻塞入库主流程。
3. 调用方：入库成功后 `notifyAdminLead({...}).catch(() => {})`。

## 三、四个必踩的坑

1. **`https.request` 发送会返回空 body**：未设 `Content-Length` 走 chunked，微信返回 `{}`，日志看着像"发了但没反应"（误判成 `errcode` 为 0）。**必须用 Node 内置 `fetch`**。
2. **模板字段必须完全对齐**：多/少一个都报 `47003 argument invalid`。现用模板 6 字段 = `first / keyword1客户姓名 / keyword2客户手机 / keyword3提交时间 / keyword4表单项目 / remark`，与 `notify.js` 参数一一对应。
3. **截图抄 template_id 必错**：`l/I/0/O/S` 等易混字符 OCR 常读错 → `40037 invalid template_id`。**一律用接口拉取**：
   `GET https://api.weixin.qq.com/cgi-bin/template/get_all_private_template?access_token=...`
4. **`service_leads.name` 存的是联系人姓名**（不是公司名），清测试数据时别按公司名 DELETE。

## 四、拿管理员 openid（不用问用户要）

1. 查本站库：`select id,username,openid from users where openid!=''`。
2. 用 `cgi-bin/user/get` 拉关注者列表，确认该 openid 在列表内（不在 = 未关注，发不出去）。
3. 库里没有时，让用户在微信里走一次本站 OAuth 登录即可落库。

## 五、新增一条链路的步骤

1. 路由顶部 `import { notifyAdminLead } from '../notify.js';`
2. 落 `service_leads`（带 `lead_type` + `extra` JSON）→ 调 `notifyAdminLead({ title, name, phone, content, remark, time }).catch(() => {})`
3. 部署闭环：备份 → `scp` → `node --check` → `pm2 reload hndcw` → POST 实测 → `pm2 logs hndcw --lines 30 --nostream | grep -i notify` 看到 `已推送管理员微信提醒 ok` → 清理测试数据。
4. 前端表单用 `fetch` POST 后 toast 提示，不要整页提交（与站内暗色风格一致）。

## 六、前置依赖（不通先查这里）

公众号 appSecret 一旦失效/重置，**提醒、语音 JS-SDK、OAuth 全废**（微信支付不受影响，它用商户 API key/证书）。appSecret 在服务器有**四处**存储、必须同步，见项目 MEMORY「微信凭证」条目。另：语音还需公众号后台「JS 接口安全域名」含 `hndcw.com`。
