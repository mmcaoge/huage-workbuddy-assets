// 伪造管理员会话 + 逐路由计时（定位慢点）。用完自行清理会话。
import { DatabaseSync } from 'node:sqlite';
import { createHmac, randomBytes } from 'node:crypto';

const SECRET = 'hndcw-session-secret-' + (process.env.SESSION_SECRET || 'dev');
const db = new DatabaseSync('/www/wwwroot/hndcw.com/data/sessions.db');
const sid = 'lat' + randomBytes(6).toString('hex');
db.prepare('INSERT OR REPLACE INTO sessions (sid,sess,expired) VALUES (?,?,?)')
  .run(sid, JSON.stringify({ cookie: { expires: new Date(Date.now() + 3600000).toISOString(), httpOnly: true, path: '/', sameSite: 'lax' }, uid: 16 }), Date.now() + 3600000);
db.close();
const cookie = 's:' + sid + '.' + createHmac('sha256', SECRET).update(sid).digest('base64').replace(/=+$/, '');
const BASE = 'http://127.0.0.1:3000';

const urls = [
  ['/', false],
  ['/admin/questionnaire', true],
  ['/admin/questionnaire/1/export?format=template', true],
  ['/admin/questionnaire/1/export?format=xlsx', true],
  ['/admin/questionnaire/1/export?format=csv', true],
];
for (const [u, auth] of urls) {
  const t0 = Date.now();
  try {
    const ctl = new AbortController();
    const tm = setTimeout(() => ctl.abort(), 120000);
    const r = await fetch(BASE + u, { headers: auth ? { cookie: 'connect.sid=' + cookie } : {}, redirect: 'manual', signal: ctl.signal });
    clearTimeout(tm);
    const buf = Buffer.from(await r.arrayBuffer());
    console.log(`${u}  => ${r.status}  ${Date.now() - t0}ms  ${buf.length}B  ${(r.headers.get('content-type') || '').split(';')[0]}`);
  } catch (e) {
    console.log(`${u}  => ERR ${Date.now() - t0}ms  ${e.name}: ${e.message}`);
  }
}
// 清理
const db2 = new DatabaseSync('/www/wwwroot/hndcw.com/data/sessions.db');
db2.prepare('DELETE FROM sessions WHERE sid=?').run(sid);
const left = db2.prepare("SELECT COUNT(*) c FROM sessions WHERE sid LIKE 'brandtest%' OR sid LIKE 'lat%'").get();
db2.close();
console.log('残留测试会话:', left.c);
