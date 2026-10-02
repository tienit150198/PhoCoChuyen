import assert from 'node:assert/strict';
import fs from 'node:fs';
import {questionView,readAccountingAnswer,accountingSchoolView,accountingSchoolOpen,accountingSchoolAction} from '../public/js/v4/accounting-school.js';

const fixture=JSON.parse(fs.readFileSync(0,'utf8'));
const ui=()=>({drafts:{},messages:{}});
const dangerous='<img src=x onerror=alert(1)>';
for(const q of fixture.questions){
  const copy=structuredClone(q);copy.prompt=dangerous;
  const html=questionView(copy,{mode:'practice',context:'x',lesson:'x',ui:ui()});
  assert.ok(html.includes('&lt;img'));
  assert.ok(!html.includes(dangerous));
  assert.ok(!html.includes('_key'));
  assert.ok(html.includes('data-as-form="practice"'));
  assert.ok(html.includes('type="submit"'));
  if(q.kind==='entry')assert.ok(html.includes('Tài khoản Nợ')&&html.includes('Tài khoản Có'));
}
const env={api:{state:fixture.school_state},ui:{accounting:{tab:'company',drafts:{},messages:{},hints:{},data:fixture.school_state.accounting_school}}};
let html=accountingSchoolView(env);
assert.ok(html.includes('Nhận việc thực hành')&&html.includes('disabled'));
env.ui.accounting.tab='exam';html=accountingSchoolView(env);
assert.ok(html.includes('Bắt đầu thi')&&html.includes('disabled'));
env.ui.accounting.tab='learn';html=accountingSchoolView(env);
assert.ok(html.includes('Kế toán cơ bản')&&html.includes('Kế toán doanh nghiệp'));
const companyQuestion=questionView(fixture.book.task,{mode:'company',context:1,ui:ui()});
assert.ok(!companyQuestion.includes('undefined'),'company account names must be readable');
assert.ok(companyQuestion.includes('Tiền mặt')&&companyQuestion.includes('Tiền gửi không kỳ hạn'),'account options require the supplied company names');
env.ui.accounting.data.company=fixture.book;
env.ui.accounting.tab='company';env.ui.accounting.companyTab='documents';
html=accountingSchoolView(env);
assert.ok(html.includes('Mở chứng từ gốc'));
assert.ok(!html.includes('data-as-form="company"'),'closed document must not allow journal submission');
env.ui.accounting.companyTab='ledger';html=accountingSchoolView(env);
assert.ok(html.includes('Đầu kỳ Nợ')&&html.includes('Phát sinh Có')&&html.includes('Cuối kỳ Có'));
env.ui.accounting.companyTab='reports';env.ui.accounting.reportTab='B09';html=accountingSchoolView(env);
assert.ok(html.includes('BẢN THUYẾT MINH')&&html.includes('IX.7'));

// Hints: one more per tap, escaped, never in the graded exam; the TT99 lookup filters and escapes.
{
  const q=structuredClone(fixture.questions.find(x=>x.help?.length));q.help=[dangerous,'Hai'];
  const u=ui();u.hints={};
  let h=questionView(q,{mode:'practice',context:'x',lesson:'x',ui:u});
  assert.ok(h.includes('Cần gợi ý?')&&!h.includes('Gợi ý 1'));
  u.hints['practice|x|'+q.id]=1;h=questionView(q,{mode:'practice',context:'x',lesson:'x',ui:u});
  assert.ok(h.includes('Gợi ý 1')&&h.includes('&lt;img')&&!h.includes(dangerous)&&h.includes('Gợi ý tiếp'));
  h=questionView(q,{mode:'exam',context:'x',ui:u});
  assert.ok(!h.includes('Gợi ý'),'no hints in the graded exam');
  const g={...env.ui.accounting,tab:'learn',glossary:[{code:'131',name:'Phải thu của khách hàng',group:'Loại 1',nature:dangerous},{code:'331',name:'Phải trả cho người bán',group:'Loại 3',nature:'x'}],glossQuery:'phai thu'};
  const book=structuredClone(fixture.book);book.task.docs=book.task.docs.map(d=>({...d,closed:undefined,lines:['x']}));book.task.help=['a','b'];
  g.data={...g.data,company:book};g.tab='company';g.companyTab='documents';
  h=accountingSchoolView({api:env.api,ui:{accounting:g}});
  assert.ok(h.includes('Tra cứu TT99')&&h.includes('131')&&!h.includes('>331<')&&!h.includes(dangerous));
  const locked=structuredClone(fixture.book);locked.statements.B01={title:'B01',rows:[],locked:true};
  h=accountingSchoolView({api:env.api,ui:{accounting:{...g,data:{...g.data,company:locked},companyTab:'reports',reportTab:'B01'}}});
  assert.ok(h.includes('bản đầy đủ hiện ra sau khi chấm đúng'));
}

// Exercise answer reading independently of browser defaults: zero and negative
// values are legitimate, while blank and partial orders must not submit.
globalThis.FormData=class{
  constructor(form){this.rows=form.values;}
  get(k){return this.rows.find(x=>x[0]===k)?.[1]??null;}
  getAll(k){return this.rows.filter(x=>x[0]===k).map(x=>x[1]);}
  [Symbol.iterator](){return this.rows[Symbol.iterator]();}
};
function read(q,values,extra={}){
  const u=ui();u.drafts.k={values:{},order:[],entries:[],...extra};
  const form={dataset:{key:'k',kind:q.kind,questionData:JSON.stringify(q)},values};
  return readAccountingAnswer(form,u);
}
assert.equal(read({kind:'number'},[['ans','0']]),0);
assert.equal(read({kind:'number'},[['ans','-100']]),-100);
assert.equal(read({kind:'number'},[['ans','']]),null);
assert.equal(read({kind:'number'},[['ans','1.5']]),null);
assert.deepEqual(read({kind:'fields',fields:[{id:'assets'}]},[['f:assets','1240000000']]),{assets:1240000000});
assert.equal(read({kind:'multi'},[]),null);
assert.deepEqual(read({kind:'multi'},[['ans','a'],['ans','b']]),['a','b']);
assert.equal(read({kind:'order',items:[{id:'a'},{id:'b'}]},[],{order:['a']}),null);
assert.deepEqual(read({kind:'order',items:[{id:'a'},{id:'b'}]},[],{order:['b','a']}),['b','a']);
assert.equal(read({kind:'entry'},[['d:0','111'],['c:0','111'],['a:0','100']],{entries:[{}]}),null);
assert.deepEqual(read({kind:'entry'},[['d:0','111'],['c:0','112'],['a:0','100']],{entries:[{}]}),[{debit:'111',credit:'112',amount:100}]);
// The view rides on as_* answers: opening asks once (with the glossary), a tab whose part is missing asks again,
// a replayed answer (no view) asks again; every command carries the tab on screen.
{
  const calls=[],base=fixture.school_state.accounting_school;
  const reply=(cmd,p)=>{calls.push([cmd,p]);if(cmd==='as_company_finish')return {message:'ok'};return {message:'ok',accounting_view:{...base,tab:p.view.tab,company:p.view.tab==='company'?(({journal,...rest})=>rest)(fixture.book):null,...(p.view.glossary?{glossary:[{code:'111',name:'Tiền mặt',group:'Loại 1',nature:'x'}]}:{})}};};
  const e={api:{state:{}},ui:{},cmd:async(c,p)=>reply(c,p),renderSheet(){},toast(){}};
  assert.ok(await accountingSchoolOpen(e));
  assert.equal(calls[0][0],'as_view');assert.equal(calls[0][1].view.glossary,true);assert.ok(e.ui.accounting.glossary.length);
  await accountingSchoolAction('asTab',{tab:'company'},null,e);
  assert.equal(calls.length,2);assert.equal(calls[1][1].view.tab,'company');assert.ok(!('glossary' in calls[1][1].view));
  await accountingSchoolAction('asCompanyTab',{tab:'journal'},null,e);
  assert.equal(calls.length,3);assert.equal(calls[2][1].view.sub,'journal');
  await accountingSchoolAction('asCompanyFinish',{},null,e);
  assert.equal(calls.at(-1)[0],'as_view','a result without a view is followed by as_view');
  await accountingSchoolAction('asHint',{key:'k'},null,e);
  assert.equal(e.ui.accounting.hints.k,1);
}
console.log('PASS accounting UI: seven question kinds, escaping, locked gates and valid answer shapes');
