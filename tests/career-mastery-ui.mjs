import assert from 'node:assert/strict';
import {masteryCard} from '../public/js/v4/career-mastery.js';
import {promoView} from '../public/js/v4/promo.js';
import {experienceView} from '../public/js/experience-ui.js';

const state={tier:0,title:'Đang rèn nghề',badge:'🌱',bonus:0,clean:20,qualified_days:8,
  today:{completed:3,clean:2,qualified:false},ready:false,retry_good_days:0,exam:null,last_result:null,
  next:{tier:1,title:'Chuyên gia chăm vải',requirements:[
    {id:'clean',label:'Việc làm sạch lỗi',got:20,need:40,met:false},
    {id:'days',label:'Ngày làm đạt chuẩn',got:8,need:15,met:false},
    {id:'level',label:'Cấp kinh nghiệm',got:20,need:20,met:true}]}};
assert.equal(masteryCard(null),'');
let html=masteryCard(state);
assert.match(html,/20\/40/);assert.match(html,/8\/15/);assert.match(html,/Chuyên gia chăm vải/);
assert.doesNotMatch(html,/data-command="mastery_start"/);
assert.match(html,/aria-label="Việc làm sạch lỗi"/);
assert.match(masteryCard(state,{compact:true}),/data-action="promo"/);
assert.doesNotMatch(masteryCard(state,{compact:true}),/data-command=/);
html=masteryCard({...state,ready:true});assert.match(html,/data-command="mastery_start"/);
html=masteryCard({...state,retry_good_days:2,last_result:{passed:false,score:6,total:8}});
assert.match(html,/6\/8/);assert.match(html,/2 ngày/);assert.doesNotMatch(html,/data-command="mastery_start"/);
html=masteryCard({...state,exam:{index:1,total:4,complete:false,question:{id:'q2',text:'<script>bad</script>',options:[{id:'b',label:'Kiểm & sửa'}]}}});
assert.match(html,/Câu 2\/4/);assert.match(html,/&lt;script&gt;/);assert.match(html,/mastery_answer/);
assert.match(html,/&quot;option&quot;:&quot;b&quot;/);assert.doesNotMatch(html,/mastery_start|mastery_finish/);
html=masteryCard({...state,exam:{index:4,total:4,complete:true,question:null}});
assert.match(html,/mastery_finish/);assert.doesNotMatch(html,/mastery_answer/);
html=masteryCard({...state,tier:3,title:'Người truyền nghề',bonus:20,next:null,ready:false});
assert.match(html,/20 xu/);assert.doesNotMatch(html,/mastery_start/);
const room={mastery:state,life:{shop_name:'Tiệm',badges_view:[],stickers:[],chapters:{},goals:[]},metrics:{served:0}};
const env={api:{state:{current:'laundry',careers:{laundry:room}},content:{catalogue:[]}},ui:{}};
assert.match(promoView(env),/Tay nghề lâu năm/,'mastery remains available without an employment contract');
room.promo={title:'Chủ tiệm',rank:4,top:7,track:'own',pct:12,next:null,ladder:[],log:[]};
assert.match(promoView(env),/Tay nghề lâu năm/);
room.promo={org:{due:{k:'course',of:2,n:0,title:'Nghiệp vụ',q:{text:'Câu hỏi cấp bậc',options:[]}}}};
assert.match(promoView(env),/Tay nghề lâu năm/,'organization promotion branch retains separate mastery');
const passport=experienceView('passport','laundry',room,{experiences:{stories:[]}},{place:'Tiệm'}, {},env.api.state);
assert.match(passport,/data-action="promo"/,'shared passport provides an always available entry');
console.log('Mastery UI: gates, accessible counters, retry, reloadable review, escaping, compact and final tier pass');
