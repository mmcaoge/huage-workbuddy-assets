// 项目「三件套」：详情 / 地址 / 电话 —— 全站单一真源
// 用途：把鸣儿完整档案里已有的详情、地址、电话能力抽成通用组件，
//       供后台可投标池、项目详情页、鸣儿卡片共用，避免各处各写一套取值与脱敏规则。
// 约定：任何页面展示这三样，都必须调 buildTrio()，不得自己拼字段。

const PHONE_RE = /(?:1[3-9]\d{9}|0\d{2,3}-?\d{7,8}|\d{3,4}-?\d{7,8})/;

function clean(v) {
  return String(v == null ? '' : v).replace(/\s+/g, ' ').trim();
}

// 脱敏：未解锁/游客只给可辨识的骨架，保留转化钩子
export function maskPhone(v) {
  const d = String(v || '').replace(/[^\d]/g, '');
  if (!d) return '';
  if (d.length >= 11) return d.slice(0, 3) + '****' + d.slice(-4);
  if (d.length >= 7) return d.slice(0, 3) + '****' + d.slice(-2);
  return d.slice(0, 2) + '****';
}

export function maskAddr(v) {
  const s = String(v || '').trim();
  if (!s) return '';
  if (s.length <= 6) return s.slice(0, 2) + '…';
  // 保留到区县级，门牌号隐去
  return s.slice(0, Math.min(10, s.length)) + '…（完整地址需解锁）';
}

/**
 * 构建三件套。
 * @param {object} p 项目行（数据库原始字段）
 * @param {object} opts { masked: 是否脱敏 }
 * @returns {{detail:object, address:object, phone:object}}
 */
export function buildTrio(p, opts = {}) {
  const masked = !!opts.masked;
  p = p || {};

  // ① 详情：官方公告原文 + 站内档案页
  const raw = clean(p.raw_content || p.content || '');
  const detail = {
    ok: !!(p.source_url || raw.length > 100),
    url: p.source_url || '',
    local: p.dm_code ? '/projects/' + encodeURIComponent(p.dm_code) : '',
    len: raw.length,
    brief: raw ? raw.slice(0, 70) : '',
  };

  // ② 地址：采购单位 > 代理机构 > 中标单位（谁最有用谁优先）
  let addrFrom = '';
  let addr = '';
  if (clean(p.owner_address)) { addr = clean(p.owner_address); addrFrom = '采购单位'; }
  else if (clean(p.agent_address)) { addr = clean(p.agent_address); addrFrom = '代理机构'; }
  else if (clean(p.bid_address)) { addr = clean(p.bid_address); addrFrom = '中标单位'; }
  const address = { ok: !!addr, text: addr, from: addrFrom };

  // ③ 电话：项目联系人 > 采购单位 > 代理机构 > 中标单位
  let phoneFrom = '';
  let phone = '';
  let phoneName = clean(p.contact_name);
  if (clean(p.contact_phone)) { phone = clean(p.contact_phone); phoneFrom = '项目联系人'; }
  else if (clean(p.owner_contact)) { phone = clean(p.owner_contact); phoneFrom = '采购单位'; }
  else if (clean(p.agent_contact)) { phone = clean(p.agent_contact); phoneFrom = '代理机构'; }
  else if (clean(p.bid_contact)) { phone = clean(p.bid_contact); phoneFrom = '中标单位'; }

  // 兜底：联系人字段里夹带了号码（如「张三 13800138000」），拆出来
  if (!phone) {
    const blob = [p.owner_contact, p.agent_contact, p.bid_contact, p.contact_name].map(clean).join(' ');
    const m = blob.match(PHONE_RE);
    if (m) { phone = m[0]; phoneFrom = '公告联系信息'; }
  }
  // 号码字段里夹了姓名（如「张三13800138000」），姓名单独拆出
  if (phone && !phoneName) {
    const nm = String(phone).replace(PHONE_RE, '').replace(/[^\u4e00-\u9fa5]/g, '').trim();
    if (nm.length >= 2 && nm.length <= 4) phoneName = nm;
  }
  if (phone) {
    const m = String(phone).match(PHONE_RE);
    phone = m ? m[0] : phone;
  }
  const phoneOut = { ok: !!phone, text: phone, name: phoneName, from: phoneFrom };

  if (masked) {
    if (address.ok) address.text = maskAddr(address.text);
    if (phoneOut.ok) phoneOut.text = maskPhone(phoneOut.text);
    if (detail.ok) detail.brief = '';
  }
  return { masked, detail, address, phone: phoneOut };
}

/** 三件套齐备度：返回 0-3，用于列表排序/筛选「信息全的先投」 */
export function trioScore(t) {
  return (t.detail.ok ? 1 : 0) + (t.address.ok ? 1 : 0) + (t.phone.ok ? 1 : 0);
}

export default { buildTrio, trioScore, maskPhone, maskAddr };
