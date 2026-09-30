---
name: hndcw-contextual-share-card
version: 1.0.0
display_name: 上下文分享卡片
display_name_en: Contextual Share Card
description_zh: 生成带项目/板块上下文的分享二维码品牌卡片。
description_en: Generate branded QR share cards carrying project or section context.
agent_created: true
description: 为 hndcw.com（Node/Express/EJS/SQLite）生成带上下文的分享二维码品牌卡片。当用户需要让分享卡按项目/功能/板块显示名称和简介时使用。
---

# hndcw.com 上下文分享卡片

## 适用场景

- 用户反馈：分享二维码在不同项目/功能下都长一样、不带简介。
- 需要新增某个板块的分享入口，且分享卡要一眼看出是什么内容。

## 核心改动点

1. **后端 `src/routes/share.js`**
   - `/api/share-card` 接收 `url`、`title`、`desc`、`tag` 四个查询参数。
   - `makeBrandCardBuffer(url, {title, desc, tag})` 渲染 800×800 PNG：
     - 顶部小站名（海南社会调查网）
     - 彩色板块标签（如「建设项目」「工程维权」）
     - 大标题（项目/功能名，最多 2 行）
     - 简介（最多 3 行）
     - 中心嵌 logo 二维码
     - CTA「微信扫一扫，查看详情」+ 短网址
   - 保留 `/api/qrcode` 作为纯二维码接口。
   - 字体注册兼容 Linux（Noto/WQY）与 Windows（Microsoft YaHei/SimHei）。

2. **前端 `public/js/share.js`**
   - `openShare(url, title, desc, tag)` 把上下文参数拼进 `/api/share-card?v=3`。
   - `.btn-share` 点击时读取 `data-title` / `data-desc` / `data-tag`。
   - `renderBrandCards()` 对 `img.brand-card-img` 一律按 `data-url/title/desc/tag` 重建卡片图。
   - 弹窗标题显示「分享：xxx」，图片加 loading 状态。

3. **视图中的分享按钮**
   - 给 `.btn-share` 加 `data-desc` 和 `data-tag`。
   - 示例（项目详情）：
     ```ejs
     <a class="btn btn-sm btn-ghost btn-share share-act"
        data-title="<%= p.title %>"
        data-tag="建设项目"
        data-desc="<%= ('采购人：'+(p.owner_unit||'—')+' ｜ 地区：'+((p.province||'')+(p.city||''))+' ｜ 阶段：'+(p.stage||'—')).replace(/"/g,'「').replace(/\n/g,' ') %>">
       📤 分享此项目
     </a>
     ```
   - 自由文本字段必须做 `replace(/"/g,'「').replace(/\n/g,' ')`，防止 HTML 属性断裂。
   - 已有板块标签对应：建设项目、工程维权、资讯速递、供需对接、综合平台、邀请好友。

4. **常驻/浮动分享按钮（如右下角 `fab-share`）**
   - 移动端改造后浮动按钮非常显眼，**不能写死 `data-title/data-tag/data-desc`**，否则任何页面点击都只显示站名。
   - 方案：去掉固定 data，由 `public/js/share.js` 在点击时通过 `pageCtx()` 动态取当前页上下文（`document.title` 第一段 + 按 pathname 推断板块 + h1 文本简介）。`
   - 具体实现参考：
     ```js
     function pageCtx() {
       var raw = document.title || '';
       var title = raw.indexOf(' - ') > 0 ? raw.split(' - ')[0] : raw;
       var tag = '综合平台';
       var p = location.pathname;
       if (p.indexOf('/projects') === 0) tag = '建设项目';
       else if (p.indexOf('/news') === 0 || p.indexOf('/article') === 0) tag = '资讯速递';
       else if (p.indexOf('/legal') === 0) tag = '法律服务';
       else if (p.indexOf('/market') === 0 || p.indexOf('/merchant') === 0) tag = '企业集市';
       else if (p.indexOf('/community') === 0) tag = '社区互助';
       else if (p.indexOf('/disputes') === 0) tag = '工程维权';
       else if (p.indexOf('/supply') === 0) tag = '供需对接';
       else if (p.indexOf('/user') === 0 || p.indexOf('/account') === 0) tag = '用户中心';
       var desc = '';
       var h1 = document.querySelector('h1');
       if (h1 && h1.textContent) desc = h1.textContent.trim().replace(/\s+/g, ' ').slice(0, 60);
       return { title: title, tag: tag, desc: desc };
     }
     // click handler 中：btn.dataset.title || ctx.title 等
     ```

5. **用户中心品牌卡**
   - 把 `img.brand-card-img` 的 `src` 去掉，改为 `data-url` / `data-title` / `data-desc` / `data-tag`。
   - 让 `renderBrandCards()` 统一渲染，避免内联 URL 不带上下文。

## 部署与验证

- 上传文件：`src/routes/share.js`、`public/js/share.js`、相关 `.ejs` 视图。
- 服务器执行 `pm2 restart hndcw`。
- 验证：
  - `curl /api/share-card?url=...&title=...&desc=...&tag=...` 返回 HTTP 200 PNG，中文正常。
  - 真实详情页 HTML 中能看到 `data-tag` 与 `data-desc`。
  - **必须真实点击两个入口**：页面内的"📤 分享此项目"按钮 + 右下角常驻浮动"分享"按钮，确认弹窗卡片都显示当前项目/功能名与板块标签（不能只 curl 后端）。
  - 在首页点击浮动分享按钮，应显示首页标题/综合平台；在详情页点击，应显示项目名/建设项目。

## 注意

- 卡片缓存 `Cache-Control: public, max-age=300`；如需强制刷新，前端 URL 加 `&v=3`（或递增版本号）。
- 后端字体注册失败时会用回退字体；生产服务器确保有 `NotoSansCJK` 或 `wqy-zenhei`。
