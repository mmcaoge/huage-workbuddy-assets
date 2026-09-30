// 单位名清洗真源 —— 关键样本回归（本地跑，不需要数据库）
// 用法：node tools/test_unitName.mjs
import { cleanUnitName, unitKey, looksLikeUnit } from '../src/lib/unitName.js';

const CASES = [
  // ---- 历史 13 层 CASE 那条路径剥不干净的真实值（本次修复的核心目标）----
  ['天津市政府采购中心 公开招标公告', '天津市政府采购中心'],
  ['天津市政府采购中心 中标公告', '天津市政府采购中心'],
  ['天津市政府采购中心 更正公告', '天津市政府采购中心'],
  ['江西省机电设备招标有限公司 公开招标公告', '江西省机电设备招标有限公司'],
  ['宁夏回族自治区政府采购中心 公开招标公告', '宁夏回族自治区政府采购中心'],
  ['中央国家机关政府采购中心 询价公告', '中央国家机关政府采购中心'],
  // ---- 无空格粘连 ----
  ['烟台润城工程项目管理有限公司公开招标公告', '烟台润城工程项目管理有限公司'],
  ['某某招标代理有限公司竞争性磋商公告', '某某招标代理有限公司'],
  // ---- 多层粘连（最多剥 4 轮）----
  ['某代理机构 中标公告 中标公告', '某代理机构'],
  ['某代理机构 中标公告 中标公告 更正公告', '某代理机构'],
  // ---- HTML 实体 ----
  ['&nbsp; 徐瑞杰', '徐瑞杰'],
  ['&nbsp;&nbsp;海南省招标中心&nbsp;', '海南省招标中心'],
  ['A&amp;B 招标代理有限公司 中标公告', 'A&B 招标代理有限公司'],
  // ---- 整串就是后缀的脏数据：刻意保留原值，不能剥成空 ----
  ['其他公告', '其他公告'],
  ['公告', '公告'],
  // ---- 短值保护：剥完短于 4 字就停，刻意保留原值 ----
  // 剥成「海口」会让一个 2 字残缺名冒充单位上榜单；保留原值同样不理想，但符合
  // 「不制造新语义」的原则 —— 这类脏数据应由采集侧修，不该在展示层猜。
  ['海口 中标公告', '海口 中标公告'],
  // ---- 不该被误改的正常名 ----
  ['海南铎鸣市场调查有限公司', '海南铎鸣市场调查有限公司'],
  ['海南社会调查网', '海南社会调查网'],
  ['三亚市自然资源和规划局', '三亚市自然资源和规划局'],
  // ---- 空值 ----
  ['', ''],
  [null, ''],
  [undefined, ''],
  ['   ', ''],
];

let fail = 0;
console.log('=== cleanUnitName 回归 ===');
for (const [input, want] of CASES) {
  const got = cleanUnitName(input);
  const ok = got === want;
  if (!ok) fail++;
  const J = (x) => (JSON.stringify(x) === undefined ? String(x) : JSON.stringify(x));
  console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${J(input).slice(0, 46).padEnd(48)} -> ${J(got).slice(0, 34)}${ok ? '' : '   want ' + J(want)}`);
}

console.log('\n=== 幂等性（clean(clean(x)) === clean(x)） ===');
let idemFail = 0;
for (const [input] of CASES) {
  const a = cleanUnitName(input);
  const b = cleanUnitName(a);
  if (a !== b) { idemFail++; console.log(`  FAIL ${JSON.stringify(input)} : ${JSON.stringify(a)} -> ${JSON.stringify(b)}`); }
}
console.log(idemFail ? `  ${idemFail} 个不幂等` : '  ✓ 全部幂等');

console.log('\n=== unitKey（空则退回原值） ===');
for (const [input] of [['其他公告'], ['', ''], ['  ', '']]) {
  console.log(`  ${JSON.stringify(input)} -> ${JSON.stringify(unitKey(input))}`);
}

console.log('\n=== looksLikeUnit ===');
for (const v of ['海南大学', '其他公告', '公告', 'A1', '12345', '海南铎鸣市场调查有限公司']) {
  console.log(`  ${String(looksLikeUnit(v)).padEnd(5)} ${v}`);
}

console.log(`\n结果：${fail === 0 && idemFail === 0 ? '全部通过 ✓' : `失败 ${fail} 项 + 幂等 ${idemFail} 项`}`);
process.exit(fail === 0 && idemFail === 0 ? 0 : 1);
