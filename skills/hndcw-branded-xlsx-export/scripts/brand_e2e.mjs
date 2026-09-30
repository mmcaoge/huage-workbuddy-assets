// 线上 E2E：伪造管理员/委托方 session → 直接请求导出路由 → 校验 4 种产物的响应头与内容
// 用完即删（会话行 + 临时文件），不留残留。
import { DatabaseSync } from 'node:sqlite';
import { createHmac, randomBytes } from 'node:crypto';
import { writeFileSync, mkdirSync } from 'node:fs';

const SECRET = 'hndcw-session-secret-' + (process.env.SESSION_SECRET || 'dev');
const BASE = 'http://127.0.0.1:3000';
const OUT = '/tmp/brandcheck';
mkdirSync(OUT, { recursive: true });

// express-session + cookie-signature：s:<sid>.<base64(hmac-sha256(sid))>（去掉 = 与 /+= 之类尾字符）
function sign(sid) {
  const mac = createHmac('sha256', SECRET).update(sid).digest('base64').replace(/=+$/, '');
  return 's:' + sid + '.' + mac;
}

const db = new DatabaseSync('/www/wwwroot/hndcw.com/data/sessions.db');
const sids = [];
function forge(uid, tag) {
  const sid = 'brandtest' + tag + randomBytes(6).toString('hex');
  const sess = {
    cookie: { originalMaxAge: 86400000, expires: new Date(Date.now() + 86400000).toISOString(), httpOnly: true, path: '/', sameSite: 'lax' },
    uid,
  };
  db.prepare('INSERT OR REPLACE INTO sessions (sid, sess, expired) VALUES (?,?,?)')
    .run(sid, JSON.stringify(sess), Date.now() + 86400000);
  sids.push(sid);
  return sign(sid);
}

async function hit(url, cookie, save) {
  const r = await fetch(BASE + url, { headers: { cookie: 'connect.sid=' + cookie }, redirect: 'manual' });
  const ct = r.headers.get('content-type') || '';
  const cd = r.headers.get('content-disposition') || '';
  const buf = Buffer.from(await r.arrayBuffer());
  if (save) writeFileSync(OUT + '/' + save, buf);
  return { status: r.status, ct, cd, size: buf.length, buf };
}

// 只读校验 xlsx：ZIP 结构 + 图片 + 品牌文字（用 node 自带 zlib 手工解 ZIP 太麻烦，直接查特征字节）
function checkXlsx(buf) {
  const s = buf.toString('latin1');
  const hasZip = buf[0] === 0x50 && buf[1] === 0x4b;
  const hasSheetViews = s.includes('<sheetViews>');
  const hasMedia = s.includes('xl/media/image1.png');
  const hasStyle = s.includes('1A1A4D') || s.includes('FFD700');
  return { hasZip, hasSheetViews, hasMedia, hasStyle };
}

const surveys = db.prepare ? null : null;
const adminSid = forge(16, 'adm');
const results = [];
const CASES = [
  ['/admin/questionnaire/1/export?format=xlsx', 'admin_1_report.xlsx', '答卷报表'],
  ['/admin/questionnaire/1/export?format=template', 'admin_1_tpl.xlsx', '模板清单'],
  ['/admin/questionnaire/1/export?format=template-json', 'admin_1_tpl.json', '模板JSON'],
  ['/admin/questionnaire/1/export?format=csv', 'admin_1_raw.csv', '原始CSV'],
  ['/admin/questionnaire/25/export?format=template', 'admin_25_tpl.xlsx', '模板清单(含分节)'],
  ['/admin/questionnaire/25/export?format=xlsx', 'admin_25_report.xlsx', '答卷报表(含分节)'],
];
for (const [url, save, label] of CASES) {
  const r = await hit(url, adminSid, save);
  const extra = save.endsWith('.xlsx') ? JSON.stringify(checkXlsx(r.buf)) : '';
  results.push(`${label.padEnd(18)} ${String(r.status).padEnd(4)} ${r.ct.split(';')[0].padEnd(38)} ${String(r.size).padStart(8)}B  ${r.cd}`);
  if (extra) results.push(`   结构: ${extra}`);
}

// 委托方路径：clientdemo 账号 id
let clientNote = '';
try {
  const main = new DatabaseSync('/www/wwwroot/hndcw.com/data/hndcw.db', { readOnly: true });
  const u = main.prepare("SELECT id,username FROM users WHERE username='clientdemo'").get();
  if (u) {
    const mid = main.prepare("SELECT id,title,owner_id,review_status,status FROM surveys WHERE owner_id=?").get(u.id);
    if (mid) {
      const csid = forge(u.id, 'cli');
      const r1 = await hit(`/client/surveys/${mid.id}/export?format=template`, csid, 'client_tpl.xlsx');
      results.push(`${'委托方模板'.padEnd(18)} ${String(r1.status).padEnd(4)} ${r1.ct.split(';')[0].padEnd(38)} ${String(r1.size).padStart(8)}B  ${r1.cd}`);
      results.push(`   结构: ${JSON.stringify(checkXlsx(r1.buf))}  (survey ${mid.id} ${mid.title})`);
      clientNote = `clientdemo uid=${u.id} survey=${mid.id}`;
    } else clientNote = 'clientdemo 名下无问卷';
  } else clientNote = '无 clientdemo 账号';
  main.close();
} catch (e) { clientNote = '委托方检查跳过: ' + e.message; }

// 未登录必须被拦（防伪造会话掩盖鉴权 bug）
const rNo = await fetch(BASE + '/admin/questionnaire/1/export?format=xlsx', { redirect: 'manual' });
results.push(`\n未登录访问           ${rNo.status} (期望 302/403)`);

// 清理会话
for (const s of sids) db.prepare('DELETE FROM sessions WHERE sid=?').run(s);
db.close();
results.push(`\n已清理伪造会话 ${sids.length} 条；${clientNote}`);
results.push('样本目录 /tmp/brandcheck/');
console.log(results.join('\n'));
