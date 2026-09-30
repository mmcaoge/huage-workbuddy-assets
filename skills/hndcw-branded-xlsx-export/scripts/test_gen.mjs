// 本地样本生成：用线上真实问卷结构 + 合成作答，检验「鸣儿独家」版式在长表/全题型下的表现
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { buildAnswerReportXlsx, buildTemplateXlsx, buildTemplateJson, buildCsv } from './survey-export.js';

const dump = JSON.parse(readFileSync('dump.json', 'utf8'));
mkdirSync('out', { recursive: true });

const rnd = (n) => Math.floor(Math.random() * n);
const pick = (arr) => arr[rnd(arr.length)];
const TEXTS = [
  '整体体验不错，响应速度可以再快一些。',
  '希望能提供更详细的分析报告附件。',
  '对接人很专业，问题解释得清楚。',
  '建议增加线上进度查询功能。',
  '价格如果再灵活些会更好。',
  '交付时间比预期提前了一天，满意。',
];
const CONTACTS = ['', '13800001111', '', '13900002222', '', '', '13700003333', ''];

// 按题型合成一份作答
function synthAnswers(questions) {
  const a = {};
  for (const q of questions) {
    if (q.type === 'section') continue;
    if (q.type === 'rating') { a[q.id] = String(1 + rnd(q.max || 5)); continue; }
    if (q.type === 'nps') { a[q.id] = String(rnd(11)); continue; }
    if (q.type === 'single' || q.type === 'dropdown') { a[q.id] = pick(q.options || ['其他']); continue; }
    if (q.type === 'multiple') {
      const opts = (q.options || []).filter(() => Math.random() < 0.45);
      a[q.id] = opts.length ? opts : [(q.options || ['其他'])[0]];
      continue;
    }
    if (q.type === 'text') { a[q.id] = pick(TEXTS); continue; }
    if (q.type === 'date') { a[q.id] = '2026-09-' + String(1 + rnd(17)).padStart(2, '0'); continue; }
    if (q.type === 'matrix') {
      const o = {};
      (q.rows || []).forEach((_, ri) => { o[String(ri)] = pick(q.options || ['满意']); });
      a[q.id] = o; continue;
    }
  }
  return a;
}

function synth(survey, questions, n, startId) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const d = new Date(Date.UTC(2026, 8, 3 + (i % 14), 1 + rnd(12), rnd(60), rnd(60)));
    out.push({
      id: startId + i,
      survey_id: survey.id,
      contact: pick(CONTACTS),
      answers: JSON.stringify(synthAnswers(questions)),
      created_at: d.toISOString(),
    });
  }
  return out;
}

const base = 'https://hndcw.com';

/* ① 真实问卷：政务服务满意度调查（1 份真实 + 21 份合成，验证长表斑马与统计占比） */
{
  const { survey, responses } = dump['1'];
  const qs = JSON.parse(survey.questions || '[]');
  const all = [...responses, ...synth(survey, qs, 21, 9001)];
  writeFileSync('out/01_答卷报表_政务服务满意度调查.xlsx', buildAnswerReportXlsx(survey, qs, all, base));
  writeFileSync('out/02_问卷模板_政务服务满意度调查.xlsx', buildTemplateXlsx(survey, qs));
  writeFileSync('out/03_模板JSON_政务服务满意度调查.json', JSON.stringify(buildTemplateJson(survey, qs), null, 2));
  writeFileSync('out/04_原始数据_政务服务满意度调查.csv', buildCsv(survey, qs, all));
  console.log('① 政务服务满意度调查：答卷', all.length, '份 → 4 个产物');
}

/* ② 委托方演示卷（含分节），验证分节在明细/统计/模板三处的表现 */
{
  const { survey } = dump['25'];
  const qs = JSON.parse(survey.questions || '[]');
  const all = synth(survey, qs, 14, 9100);
  writeFileSync('out/05_答卷报表_企业客户满意度回访.xlsx', buildAnswerReportXlsx(survey, qs, all, base));
  writeFileSync('out/06_问卷模板_企业客户满意度回访.xlsx', buildTemplateXlsx(survey, qs));
  console.log('② 企业客户满意度回访：答卷', all.length, '份（含分节）');
}

/* ③ 全题型覆盖卷（本地合成结构），确保 matrix/dropdown/date 等分支版式都跑到 */
{
  const survey = {
    id: 999, code: 'alltypes', title: '鸣儿独家版式全覆盖测试卷', type: '综合评估',
    target: 200, status: 'draft', thank_msg: '', deadline: '',
  };
  const qs = [
    { id: 'q1', type: 'section', title: '第一部分 · 基本信息', desc: '以下信息仅用于统计分析' },
    { id: 'q2', type: 'single', title: '您所在单位性质', options: ['国有企业', '民营企业', '事业单位', '外资企业'], required: true },
    { id: 'q3', type: 'dropdown', title: '您所在的行业', options: ['房屋建筑', '市政工程', '交通工程', '水利工程'] },
    { id: 'q4', type: 'date', title: '项目启动日期', required: false },
    { id: 'q5', type: 'section', title: '第二部分 · 服务评价', desc: '' },
    { id: 'q6', type: 'rating', title: '整体服务满意度', max: 5, required: true },
    { id: 'q7', type: 'matrix', title: '请对以下各项打分', rows: ['响应速度', '专业水平', '交付质量', '价格合理'], options: ['很满意', '满意', '一般', '不满意'] },
    { id: 'q8', type: 'multiple', title: '您使用过哪些服务', options: ['项目信息查询', '供应商资质核查', '政策红利匹配', '投标保函', '定制调查报告'], required: true },
    { id: 'q9', type: 'nps', title: '您向同行推荐的可能性（0-10）', max: 10 },
    { id: 'q10', type: 'text', title: '其他意见或建议' },
  ];
  const all = synth(survey, qs, 16, 9200);
  writeFileSync('out/07_答卷报表_全题型覆盖.xlsx', buildAnswerReportXlsx(survey, qs, all, base));
  writeFileSync('out/08_问卷模板_全题型覆盖.xlsx', buildTemplateXlsx(survey, qs));
  console.log('③ 全题型覆盖卷：答卷', all.length, '份（含矩阵/下拉/日期/分节）');
}

/* ④ 零答卷场景（模板导出最常见：客户拿到模板时还没有数据） */
{
  const { survey } = dump['25'];
  const qs = JSON.parse(survey.questions || '[]');
  writeFileSync('out/09_答卷报表_零答卷.xlsx', buildAnswerReportXlsx(survey, qs, [], base));
  console.log('④ 零答卷场景已生成');
}

console.log('\n样本目录：out/');
