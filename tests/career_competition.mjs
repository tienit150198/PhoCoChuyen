import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
const moduleURL=new URL('../public/js/v4/career-competition.js',import.meta.url);
assert.ok(existsSync(moduleURL),'Competition renderer must exist');
const {competitionCard}=await import(moduleURL.href);
const {promoView}=await import('../public/js/v4/promo.js');

const state={league:0,title:'Đồng nghiệp mới',recognizer:'Tổ trưởng',focus:'Giữ đúng quy trình',
  period:{number:1,worked_days:3,total_days:10,score:240,eligible_income:700},
  standings:[{id:'peer_a',name:'Ngọc',strength:'Kiểm tra kỹ',score:240,rank:1,is_player:false},
    {id:'player',name:'Bạn',strength:'Tự làm',score:240,rank:1,is_player:true},
    {id:'peer_b',name:'Bình',strength:'Phối hợp',score:225,rank:3,is_player:false},
    {id:'peer_c',name:'Lan',strength:'Bền bỉ',score:200,rank:4,is_player:false}],
  today:{completed:2,score:84,components:[{id:'quality',label:'Chất lượng',score:84,weight:50}],case_completed:false},
  next:{league:1,title:'Đồng đội vững tay',requirements:[{id:'good',label:'Kỳ đạt chuẩn',got:1,need:2,met:false},{id:'rank',label:'Bậc chức vụ',got:2,need:2,met:true}]},
  reward:{cap:300,rate:0.1,cash:true,spirit_cap:3},
  case:{unlocked:false,ready:false,reason:'Từ bậc chức vụ 3 hoặc hạng thi đua 2.',active:null,result:null},last_result:null};
assert.equal(competitionCard(null),'');
let html=competitionCard(state);
assert.match(html,/Thi đua cùng đồng nghiệp/);
assert.match(html,/3\/10 ca/);assert.match(html,/Hạng 1\/5/);
assert.equal((html.match(/class="cc-league(?: is-current| is-past)?"/g)||[]).length,5);
assert.match(html,/aria-label="Tiến độ kỳ thi đua"/);
assert.equal((html.match(/class="cc-standing(?: is-player)?"/g)||[]).length,4);
assert.equal((html.match(/<small>Đồng hạng 1<\/small>/g)||[]).length,2,'equal ranks must be described as ties');
for(const name of ['Ngọc','Bình','Lan','Kiểm tra kỹ'])assert.ok(html.includes(name));
assert.match(html,/84\/100/);assert.match(html,/2 việc/);assert.match(html,/trọng số 50/);
assert.match(html,/300 xu/);assert.match(html,/10%/);assert.match(html,/1\/2/);assert.match(html,/2\/2/);
assert.match(html.slice(0,html.indexOf('<details')),/300 xu/,'reward cap is visible without opening rules');
assert.match(html,/Từ bậc chức vụ 3/);assert.doesNotMatch(html,/data-command=/);
const empty={...state,period:{...state.period,worked_days:0,score:0},today:{completed:0,score:0,components:[]}};
assert.match(competitionCard(empty),/Chưa có việc tự làm được ghi nhận hôm nay/);
assert.doesNotMatch(competitionCard(empty),/0\/100/,'lack of evidence must not appear as a graded zero');
html=competitionCard({...state,case:{...state.case,unlocked:true,ready:true,reason:''}});
assert.match(html,/data-command="competition_start" data-payload="\{\}"/);
const active={id:'inspect',title:'Kiểm tra ca',text:'Một việc cần kiểm lại.',options:[{id:'a',label:'Xem chứng cứ',score:987654,feedback:'HIDDEN_FEEDBACK'},{id:'b',label:'Chờ'}]};
html=competitionCard({...state,case:{unlocked:true,ready:false,reason:'',active,result:null}});
assert.equal((html.match(/data-command="competition_answer"/g)||[]).length,2);
assert.match(html,/&quot;option&quot;:&quot;a&quot;/);
assert.doesNotMatch(html,/987654|HIDDEN_FEEDBACK|competition_start/);
html=competitionCard({...state,case:{...state.case,unlocked:true,ready:true,result:{id:'inspect',title:'Kiểm tra ca',option:'a',score:987654,feedback:'Đã kiểm tra kỹ.'}},last_result:{period:1,league:0,score:82,rank:2,good:true,bonus:70,spirit:0,message:'Tổ trưởng ghi nhận tiến bộ.'}});
assert.match(html,/Đã kiểm tra kỹ/);assert.match(html,/Tổ trưởng ghi nhận tiến bộ/);assert.match(html,/70 xu/);
assert.doesNotMatch(html,/987654|data-command="competition_(start|answer)"/,'answered case is immutable');
html=competitionCard({...state,league:4,next:null,reward:{cap:0,rate:0.1,cash:false,spirit_cap:3},last_result:{period:2,league:4,score:90,rank:1,good:true,bonus:0,spirit:2,message:'Ghi nhận công quả.'}});
assert.match(html,/Hạng 5\/5/);assert.match(html,/hạng thi đua cao nhất/);assert.match(html,/2 tinh thần/);assert.match(html,/Không thưởng xu/);assert.match(html,/3 tinh thần/);
const hostile='<img src=x onerror="bad()">';
html=competitionCard({...state,title:hostile,recognizer:hostile,focus:hostile,standings:[{...state.standings[0],name:hostile,strength:hostile}],case:{...state.case,active:{...active,title:hostile,text:hostile,options:[{id:hostile,label:hostile}]}}});
assert.doesNotMatch(html,/<img|data-payload="[^"]*<|onerror="bad/);assert.match(html,/&lt;img/);assert.match(html,/&amp;quot;|&quot;/);
html=competitionCard(state,{compact:true});assert.match(html,/data-action="promo"/);assert.doesNotMatch(html,/data-command=|upgrade-card/);
const room={competition:state,mastery:{tier:0,title:'Đang rèn nghề',today:{},next:null},promo:null};
const env={api:{state:{current:'laundry',careers:{laundry:room}},content:{catalogue:[]}},ui:{}};
for(const promo of [null,{title:'Chủ tiệm',rank:4,top:7,track:'own',pct:12,next:null,ladder:[],log:[]},
  {due:{of:2,n:0,title:'Chủ tiệm',q:{text:'Câu hỏi thăng tiến',options:[]}}},
  {org:{due:{k:'course',of:2,n:0,title:'Nghiệp vụ',q:{text:'Câu hỏi cấp bậc',options:[]}}}}]){
  room.promo=promo;html=promoView(env);assert.match(html,/Thi đua cùng đồng nghiệp/);assert.match(html,/Tay nghề lâu năm/);
}
const css=readFileSync(new URL('../public/css/promo.css',import.meta.url),'utf8');
assert.match(css,/\.cc-card\s*\{[^}]*min-width:\s*0/);
assert.match(css,/\.cc-options\s+\.btn\s*\{[^}]*white-space:\s*normal/);
assert.match(css,/\.cc-options\s+\.btn\s*\{[^}]*min-height:\s*48px/);
assert.match(css,/\.cc-standing\s*\{[^}]*minmax\(0,\s*1fr\)/);
assert.doesNotMatch(competitionCard(state),/upgrade-card/,'avoid app phone grid forcing multiple paragraphs onto one row');
const en=JSON.parse(readFileSync(new URL('../output/career-competition/ui-en.json',import.meta.url),'utf8'));
assert.equal(en.strings['Thi đua cùng đồng nghiệp'],'Career competition');assert.ok(en.patterns);
console.log('Competition UI: period, standings/ties, evidence, caps, gates, cases, escaping, promo paths and mobile contracts pass');
