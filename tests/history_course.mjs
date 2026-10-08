// 📜 Học lịch sử Việt Nam page (public/js/v4/history-course.js): every state renders, text is escaped, no exam key.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {historyCourseView,historyCourseAction} from '../public/js/v4/history-course.js';

const fx=JSON.parse(fs.readFileSync(0,'utf8'));
const dangerous='<img src=x onerror=alert(1)>';
const env=(data,ui={})=>({api:{state:{name:fx.name}},ui:{history:{tab:'learn',lesson:null,hint:{},msg:{},data,...ui}}});
const clean=html=>{assert.ok(!html.includes('undefined'),'no undefined');assert.ok(!html.includes('[object Object]'));return html;};

// The index: twelve lessons, a start button, the exam locked with its reason.
let html=clean(historyCourseView(env(fx.index)));
assert.equal((html.match(/data-action="vsLesson"/g)||[]).length,fx.index.total+1);
assert.ok(html.includes('Bắt đầu học'));
html=clean(historyCourseView(env(fx.index,{tab:'exam'})));
assert.ok(/data-action="vsExamStart"[^>]*disabled/.test(html),'exam locked before every lesson');
assert.ok(html.includes('Học xong cả'));

// A lesson: body, one solved question with its why, one open with three buttons; the hint line is marked.
const lesson=structuredClone(fx.lesson);
lesson.lesson.body[0]=dangerous;
html=clean(historyCourseView(env(lesson,{lesson:lesson.lesson.id,hint:{[lesson.lesson.id]:1},msg:{[lesson.lesson.questions[1].id]:'Chưa đúng.'}})));
assert.ok(html.includes('&lt;img')&&!html.includes(dangerous));
assert.equal((html.match(/class="hc-hint"/g)||[]).length,1);
assert.equal((html.match(/data-action="vsPick"/g)||[]).length,3);
assert.ok(html.includes(lesson.lesson.questions[0].why));
assert.ok(html.includes('Chưa đúng.'));

// The exam in progress: the current question, its three options, no key anywhere.
const ex=fx.exam;
html=clean(historyCourseView(env(ex,{tab:'exam'})));
assert.equal((html.match(/data-action="vsExamPick"/g)||[]).length,3);
assert.ok(!('answer' in ex.active.question)&&!('why' in ex.active.question));
html=clean(historyCourseView(env({...ex,active:null},{tab:'exam'})));
assert.ok(html.includes('Mã PCC-HIS-'),'the certificate shows');
assert.ok(html.includes('Bài thi gần nhất'),'the last paper is reviewed');
assert.equal((html.match(/<li class="ok">/g)||[]).length,ex.review.questions.length);

// Actions: a tab switch re-renders; unknown actions fall through.
let renders=0;
const e=env(fx.index);e.renderSheet=()=>{renders++;};
assert.equal(await historyCourseAction('vsTab',{tab:'exam'},null,e),true);
assert.equal(e.ui.history.tab,'exam');
assert.equal(renders,1);
assert.equal(await historyCourseAction('asTab',{},null,e),false);
console.log('history course page OK');
