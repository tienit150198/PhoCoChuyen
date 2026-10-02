import assert from 'node:assert/strict';
import fs from 'node:fs';
import {questionView,readAccountingAnswer,accountingSchoolView} from '../public/js/v4/accounting-school.js';

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
const env={api:{state:fixture.school_state},ui:{accounting:{tab:'company',drafts:{},messages:{}}}};
let html=accountingSchoolView(env);
assert.ok(html.includes('Nhận việc thực hành')&&html.includes('disabled'));
env.ui.accounting.tab='exam';html=accountingSchoolView(env);
assert.ok(html.includes('Bắt đầu thi')&&html.includes('disabled'));
env.ui.accounting.tab='learn';html=accountingSchoolView(env);
assert.ok(html.includes('Kế toán cơ bản')&&html.includes('Kế toán doanh nghiệp'));
const companyQuestion=questionView(fixture.book.task,{mode:'company',context:1,ui:ui()});
assert.ok(!companyQuestion.includes('undefined'),'company account names must be readable');
assert.ok(companyQuestion.includes('Tiền mặt')&&companyQuestion.includes('Tiền gửi không kỳ hạn'),'account options require the supplied company names');
env.api.state.accounting_school.company=fixture.book;
env.ui.accounting.tab='company';env.ui.accounting.companyTab='documents';
html=accountingSchoolView(env);
assert.ok(html.includes('Mở chứng từ gốc'));
assert.ok(!html.includes('data-as-form="company"'),'closed document must not allow journal submission');
env.ui.accounting.companyTab='ledger';html=accountingSchoolView(env);
assert.ok(html.includes('Đầu kỳ Nợ')&&html.includes('Phát sinh Có')&&html.includes('Cuối kỳ Có'));
env.ui.accounting.companyTab='reports';env.ui.accounting.reportTab='B09';html=accountingSchoolView(env);
assert.ok(html.includes('BẢN THUYẾT MINH')&&html.includes('IX.7'));

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
console.log('PASS accounting UI: seven question kinds, escaping, locked gates and valid answer shapes');
