// 💼 Việc làm kế toán markup (run by tests/test_accounting_jobs.py): referral, entry check, journey card helpers.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {accountingSchoolView} from '../public/js/v4/accounting-school.js';
import {acctPlace,acctTag,acctTags} from '../public/js/v4/acct-jobs.js';

const fx=JSON.parse(fs.readFileSync(0,'utf8'));
const dangerous='<img src=x onerror=alert(1)>';
const ui=extra=>({accounting:{tab:'exam',course:'basic',companyTab:'documents',drafts:{},messages:{},hints:{},data:fx.view,...extra}});

// Giới thiệu việc làm: under the certificates, server text escaped, a way to the place that hires
let html=accountingSchoolView({api:{state:{name:'Lan'}},ui:ui()});
assert.ok(html.includes('Giới thiệu việc làm'));
assert.ok(html.includes('Nhận bạn')&&html.includes('Chưa đủ chứng nhận'));
assert.ok(html.includes('data-action="choose" data-career="corp_accounting"'));
assert.ok(!html.includes('data-action="choose" data-career="group_accounting"'));
assert.ok(html.includes('&lt;img')&&!html.includes(dangerous));
assert.ok(html.includes('225–300 xu/ngày'));

// the holiday line
html=accountingSchoolView({api:{state:{}},ui:ui({data:{...fx.view,jobs:{places:{},holiday:'Quốc khánh 2/9'}}})});
assert.ok(html.includes('🎉 Hôm nay lễ (Quốc khánh 2/9): lương kế toán x5'));

// the entry check: one question at a time, no key, then the result with lessons to reread
const check={career:'corp_accounting',attempt:0,answers:{},at:0,data:fx.check,result:null};
html=accountingSchoolView({api:{state:{}},ui:ui({check})});
assert.ok(html.includes('Kiểm tra kiến thức')&&html.includes('data-as-form="check"')&&html.includes('Câu 1/3'));
assert.ok(!html.includes('_key')&&!html.includes('Giới thiệu việc làm'));
html=accountingSchoolView({api:{state:{}},ui:ui({check:{...check,result:{passed:false,right:1,total:3,need:2,review:[{lesson:'basic_entity',title:dangerous}]}}})});
assert.ok(html.includes('Đúng 1/3 câu')&&html.includes('data-action="asCheckLesson"')&&html.includes('data-action="asCheckRetry"'));
assert.ok(html.includes('&lt;img')&&!html.includes(dangerous));

// journey cards: shut with the reason, or today's rate; nothing from an older server
const api=jobs=>({state:{accounting_school:{jobs}}});
const shut=acctPlace(api({places:{corp_accounting:[0,1,0]}}),'corp_accounting');
assert.equal(shut.ok,false);assert.ok(shut.why.includes('Kế toán cơ bản'));
assert.equal(acctPlace(api({places:{}}),'corp_accounting'),null);
assert.equal(acctPlace({state:{accounting_school:{salary_multiplier:1}}},'corp_accounting'),null);
assert.equal(acctTag(acctPlace(api({places:{corp_accounting:[1,3,1]}}),'corp_accounting')),'💼 Lương kế toán x3');
assert.equal(acctTag(acctPlace(api({places:{corp_accounting:[1,5,1]},holiday:'Tết Nguyên đán'}),'corp_accounting')),'🎉 Lễ: lương kế toán x5');
assert.equal(acctTag(shut),'');
// a shut card keeps only its lock: no 'Mới mở', no other badge
const t=(s,c)=>`<span class="${c}">${s}</span>`,built=[t('Mới mở','green'),t('🔥 Lời x3 hôm nay','amber')];
assert.deepEqual(acctTags(shut,built,t),[t('🔒 Cần thi chứng nhận','amber')]);
assert.equal(acctTags(null,built,t),built);
assert.equal(acctTags(acctPlace(api({places:{corp_accounting:[1,3,1]}}),'corp_accounting'),built,t),built);
console.log('ok');
