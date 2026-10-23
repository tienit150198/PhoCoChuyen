// 🏫 Trường học (public/js/v4/school.js): the page renders the server's view and sends the answers as the server grades
// them. `node tests/school.mjs` uses the small fixture below; tests/test_school.py ClientRenders pipes the real
// catalogue and real views (JSON {K, views: [view]}) on stdin, and every one must render without a gap.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
globalThis.document={querySelector:()=>null};
const {schoolView,schoolAction}=await import('../public/js/v4/school.js');

const stdin=(()=>{try{const t=readFileSync(0,'utf8');return t.trim()?JSON.parse(t):null;}catch{return null;}})();

function envOf(K,data){
  const sent=[];
  const env={ui:{},sent,api:{state:{name:'Mai',journey:{story:true,life_day:5}},content:{journey:{school:K},catalogue:[{id:'grocery',short:'Tạp hóa'},{id:'teller',short:'Ngân hàng'}]}},
    renderSheet(){},openSheet(id){env.opened=id;},toast(t){env.toasted=t;},confirmAction:async()=>true,
    reply:null,async cmd(op,payload){sent.push([op,payload]);const r=env.reply?env.reply(op,payload):{message:'ok',school:data};return r;}};
  return env;
}
const clean=html=>{assert.doesNotMatch(html,/undefined|NaN|\[object Object\]/,html.slice(0,400));return html;};

if(stdin){
  for(const v of stdin.views){
    const env=envOf(stdin.K,v);
    env.ui.school={tab:v.cur?.kind==='abroad'?'abroad':'uni',data:v,quiz:null,qi:0,ans:[],order:[],result:null,major:null,apply:null,docs:[],fly:null,note:null};
    clean(schoolView(env));
    for(const tab of ['uni','abroad','deg']){env.ui.school.tab=tab;clean(schoolView(env));}
    if(v.quiz){env.ui.school.quiz=v.quiz;clean(schoolView(env));}
  }
  env0: {
    const env=envOf(stdin.K,stdin.views[0]);env.ui.school={tab:'uni',data:stdin.views[0],quiz:null,qi:0,ans:[],order:[],result:null,major:stdin.K.majors[0].id,apply:null,docs:[],fly:null,note:null};
    clean(schoolView(env));env.ui.school.major=null;env.ui.school.tab='abroad';env.ui.school.apply=stdin.K.terms.at(-1).id;clean(schoolView(env));
  }
  process.stdout.write('ok');
  process.exit(0);
}

const K={uni:{name:'Đại học Phố Mây',short:'ĐH Phố Mây',emoji:'🏫'},
  majors:[{id:'kinh_te',name:'Kinh tế',emoji:'📈',blurb:'Làm ăn nhỏ mà chắc.',fee:165,careers:['grocery','teller'],sems:[[{id:'a',name:'Vi mô',emoji:'📈'},{id:'b',name:'Marketing',emoji:'📣'},{id:'c',name:'Bán hàng',emoji:'🤝'}],[{id:'d',name:'Tài chính',emoji:'🏦'},{id:'e',name:'Khởi nghiệp',emoji:'🚀'},{id:'f',name:'TMĐT',emoji:'🛒'}]]}],
  terms:[{id:'dh_trung_quoc',name:'Du học Trung Quốc',flag:'🇨🇳',country:'Trung Quốc',city:'Thượng Hải',school:'Học viện Trà Xanh',fee:420,visa:40,careers:['grocery'],sems:[[{id:'x',name:'Tiếng Trung',emoji:'🇨🇳'},{id:'y',name:'Văn hóa',emoji:'🏮'},{id:'z',name:'Thương mại',emoji:'📦'}]]}],
  docs:[{id:'passport',label:'🛂 Hộ chiếu'},{id:'cat',label:'🐱 Ảnh mèo'}],
  rules:{classes:3,per_day:2,exam_q:5,exam_pass:3,hw_q:3,credits:3,scholar:20,job_pay:[20,30],classes_pct:{xuat_sac:15,gioi:12,kha:10,tb:8},class_names:{},weekdays:[]}};
const sub=(id,o={})=>({id,name:id.toUpperCase(),emoji:'📘',a:0,cs:0,hw:-1,ex:-1,tries:0,passed:false,mark:null,letter:null,now:0,lesson:'Bài',can_class:false,can_hw:false,can_exam:false,hw_done_today:false,exam_today:false,...o});
const week=Array.from({length:7},(_,i)=>({wd:i,label:['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ nhật'][i],subjects:i<6?['a','b']:[]}));
const none={day:5,cur:null,deg:[],kept:{},quiz:null};

// the catalogue: majors, detail, terms, the application, the degrees
let env=envOf(K,none);env.ui.school={tab:'uni',data:none,quiz:null,qi:0,ans:[],order:[],result:null,major:null,apply:null,docs:[],fly:null,note:null};
let html=clean(schoolView(env));
assert.match(html,/📈/);assert.match(html,/165 xu\/học kỳ/);assert.match(html,/data-action="schMajor" data-id="kinh_te"/);
await schoolAction('schMajor',{id:'kinh_te'},null,env);
html=clean(schoolView(env));
assert.match(html,/Học kỳ 2/);assert.match(html,/Tạp hóa, Ngân hàng/);assert.match(html,/data-action="schEnrol"/);
await schoolAction('schEnrol',{program:'kinh_te',name:'Kinh tế',fee:165},null,env);
assert.deepEqual(env.sent.at(-1),['jr_sch_enrol',{program:'kinh_te'}]);
await schoolAction('schTab',{tab:'abroad'},null,env);
html=clean(schoolView(env));
assert.match(html,/🇨🇳 Trung Quốc · Thượng Hải/);assert.match(html,/Nộp hồ sơ · 460 xu/);assert.match(html,/data-action="abroad" data-tab="study"/);
await schoolAction('schApplyOpen',{program:'dh_trung_quoc'},null,env);
html=clean(schoolView(env));
assert.match(html,/data-action="schDoc" data-id="passport"/);assert.match(html,/data-action="schApply"[^>]*disabled/);
await schoolAction('schDoc',{id:'passport'},null,env);
html=clean(schoolView(env));assert.match(html,/data-id="passport" checked/);
await schoolAction('schApply',{program:'dh_trung_quoc'},null,env);
assert.deepEqual(env.sent.at(-1),['jr_sch_apply',{program:'dh_trung_quoc',docs:['passport']}]);

// a program running: today, the subjects, the timetable, homework and exam buttons, Thôi học
const study={...none,cur:{p:'kinh_te',kind:'uni',sem:0,sems:2,ph:'study',fee:165,paid:165,wd:0,wd_label:'Thứ 2',week,avail:['a','b'],left:2,
  subjects:[sub('a'),sub('b',{a:2,hw:-1,can_hw:true}),sub('c',{a:3,hw:2,can_exam:true,tries:1,ex:2})],marks:{},gpa:0,gpa_text:'0,00',
  events:[{id:'hoi_thao',emoji:'🏸',title:'Hội thao',scene:'Thiếu người',options:['Ra sân','Cổ vũ'],done:false}],can_event:true,next_fee:0}};
env=envOf(K,study);env.ui.school={tab:'uni',data:study,quiz:null,qi:0,ans:[],order:[],result:null,major:null,apply:null,docs:[],fly:null,note:null};
html=clean(schoolView(env));
assert.match(html,/Hôm nay: Thứ 2/);assert.match(html,/Vào lớp A/);assert.match(html,/Buổi 1\/3/);
assert.match(html,/data-action="schOpen" data-kind="hw" data-subject="b"/);assert.match(html,/Thi lại/);
assert.match(html,/Thời khóa biểu tuần/);assert.match(html,/data-action="schEvent"/);assert.match(html,/data-action="schDrop"/);
study.cur.wd=6;study.cur.wd_label='Chủ nhật';study.cur.avail=[];
assert.match(clean(schoolView(env)),/Chủ nhật trường nghỉ/);
study.cur.ph='break';study.cur.next_fee=165;
assert.match(clean(schoolView(env)),/Đóng học phí học kỳ 2 · 165 xu/);

// a class: the lecture, then one question at a time; the answers go in one command in the order the server drew them
const quiz={kind:'class',subject:'a',n:1,title:'Cung và cầu',points:['Giá tăng thì cầu giảm.','Cung là lượng muốn bán.'],qs:[
  {k:'c',text:'Câu 1?',options:[{i:2,label:'Hai'},{i:0,label:'Không'},{i:1,label:'Một'}]},
  {k:'t',text:'Câu 2.'},
  {k:'o',text:'Câu 3:',items:[{i:1,label:'Giữa'},{i:2,label:'Cuối'},{i:0,label:'Đầu'}]}]};
study.cur.ph='study';study.cur.wd=0;study.cur.wd_label='Thứ 2';study.cur.avail=['a','b'];
env.reply=(op,p)=>op==='jr_sch_view'?{message:'',school:{...study,quiz}}:{message:'Xong buổi 1/3.',school:study,quiz:{kind:'class',subject:'a',right:2,of:3,rows:[{text:'Câu 1?',ok:true,right:'Không',why:'Vì vậy.'},{text:'Câu 2.',ok:false,right:'Sai',why:'Vì thế.'},{text:'Câu 3:',ok:true,right:'Đầu → Giữa → Cuối',why:'Thứ tự.'}]}};
await schoolAction('schOpen',{kind:'class',subject:'a'},null,env);
assert.deepEqual(env.sent.at(-1),['jr_sch_view',{view:{open:'class',subject:'a'}}]);
html=clean(schoolView(env));
assert.match(html,/Buổi 1: Cung và cầu/);assert.match(html,/Câu 1\/3/);assert.match(html,/data-action="schPick" data-v="2"/);
assert.doesNotMatch(html,/role="tablist"/,'no tabs while answering');
await schoolAction('schPick',{v:'0'},null,env);
html=clean(schoolView(env));
assert.match(html,/Câu 2\/3/);assert.doesNotMatch(html,/Cung và cầu/,'the lecture shows before the first question only');assert.match(html,/✅ Đúng/);
await schoolAction('schPick',{v:'false'},null,env);
html=clean(schoolView(env));
assert.match(html,/Chạm lần lượt/);assert.match(html,/data-action="schOrderDone"[^>]*disabled/);
for(const i of [0,1,2])await schoolAction('schOrder',{i:String(i)},null,env);
html=clean(schoolView(env));
assert.match(html,/<b class="sch-n">3<\/b> Cuối/);
await schoolAction('schOrderDone',{},null,env);
assert.deepEqual(env.sent.at(-1),['jr_sch_class',{subject:'a',answers:[0,false,[0,1,2]]}]);
html=clean(schoolView(env));
assert.match(html,/Đúng 2\/3 câu/);assert.match(html,/Đáp án: Sai/);assert.match(html,/Vì thế\./);
await schoolAction('schDone',{},null,env);
assert.match(clean(schoolView(env)),/Hôm nay: Thứ 2/);

// a number question
env.ui.school.quiz={kind:'exam',subject:'c',attempt:2,qs:[{k:'n',text:'Bao nhiêu?'}]};env.ui.school.qi=0;env.ui.school.ans=[];
html=clean(schoolView(env));assert.match(html,/id="sch-num"/);assert.match(html,/Lần thi 2/);
globalThis.document={querySelector:s=>s==='#sch-num'?{value:'800',focus(){}}:null};
env.reply=(op)=>({message:'Đạt',school:study,quiz:{kind:'exam',subject:'c',right:1,of:1,rows:[],passed:true}});
await schoolAction('schNum',{},null,env);
assert.deepEqual(env.sent.at(-1),['jr_sch_exam',{subject:'c',answers:[800]}]);

// abroad: visa, the flight, a part-time job
const abroad={...none,cur:{...study.cur,p:'dh_trung_quoc',kind:'abroad',sems:1,ph:'visa',visa:{q:'Vì sao?',options:['Học','Chơi']},job:{can:true,n:0,max:12,pay:[20,30]}}};
env=envOf(K,abroad);env.ui.school={tab:'abroad',data:abroad,quiz:null,qi:0,ans:[],order:[],result:null,major:null,apply:null,docs:[],fly:null,note:null};
html=clean(schoolView(env));assert.match(html,/Phỏng vấn visa/);assert.match(html,/data-action="schVisa" data-option="0"/);
abroad.cur.ph='fly';abroad.cur.fly=['🧳 a','🛫 b','🛬 c','🏠 d'];
html=clean(schoolView(env));assert.match(html,/Lên máy bay/);assert.match(html,/🛬 c/);
abroad.cur.ph='study';
html=clean(schoolView(env));assert.match(html,/Làm thêm ở Thượng Hải/);assert.match(html,/data-action="schOpen" data-kind="job"/);

// the degrees
const deg={...none,deg:[{p:'kinh_te',name:'Bằng cử nhân Kinh tế',kind:'uni',g:'gioi',cls:'Giỏi',gpa:340,gpa_text:'3,40',date:'2026-10-23',serial:'PCC-KT-ABCDEF',d:9,ev:2,pct:12,careers:['grocery']}]};
env=envOf(K,deg);env.ui.school={tab:'deg',data:deg,quiz:null,qi:0,ans:[],order:[],result:null,major:null,apply:null,docs:[],fly:null,note:null};
html=clean(schoolView(env));assert.match(html,/TỐT NGHIỆP LOẠI GIỎI/);assert.match(html,/GPA 3,40\/4/);assert.match(html,/📜 Bằng \(1\)/);
// outside the story
env.api.state.journey.story=false;assert.match(schoolView(env),/có trong hành trình/);
console.log('school.mjs ok');
