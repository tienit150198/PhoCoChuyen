// F#503 "cảm ơn người góp ý tưởng" (public/js/v4/feedback.js): an idea offers "ghi tên nhân vật" (unticked = ẩn danh),
// sends it as `credit`, lets the player change it while editing; the inbox shows the operator's badge and the one
// ✅ Ghi nhận thank-you gift (owner 23/10), which the player's form never mentions. Run by tests/test_player_feedback.py.
import assert from 'node:assert/strict';
import {feedbackPageView,feedbackInput,feedbackAction,feedbackSubmit} from '../public/js/v4/feedback.js';

globalThis.document={documentElement:{dataset:{layout:'phone'}},getElementById(){return null;}};
globalThis.innerWidth=390;globalThis.innerHeight=844;
let posts=[];
const env={ui:{view:'gopy'},api:{state:{name:'Lụm'},content:{},json:async()=>({items:[]}),post:async(path,body)=>{posts.push({path,body});return {id:7,message:'Đã gửi',item:{id:7,kind:'idea',text:body.text,status:'new',created_at:1,credit:body.credit?'name':'anon',images:[]}};}},
  renderSheet(){},openSheet(){},toast(m){env.messages.push(m);},messages:[]};
feedbackPageView(env);
await new Promise(r=>setImmediate(r));
const fb=env.ui.fb;
const page=()=>feedbackPageView(env);
assert.doesNotMatch(page(),/id="fb-credit"/,'a bug report has no credit box');
assert.doesNotMatch(page(),/thưởng|30\.000|\bxu\b/i,'the reward stays a secret in the form');
await feedbackAction('fbKind',{kind:'idea'},null,env);
assert.match(page(),/<input type="checkbox" id="fb-credit">/,'an idea offers it, unticked by default');
assert.match(page(),/ghi tên nhân vật của tôi trong “Có gì mới”/);
assert.match(page(),/data-no-translate>\(Lụm\)</,'the character name is shown, never translated');
assert.doesNotMatch(page(),/thưởng|30\.000|\bxu\b/i);
const form={id:'fbForm',dataset:{},querySelector:()=>({value:'Thêm nghề làm bánh'})};
await feedbackSubmit(form,env);
assert.equal(posts.at(-1).body.credit,false,'unticked: anonymous');
fb.sent=null;
assert.equal(feedbackInput({id:'fb-credit',checked:true},env),true);
assert.match(page(),/id="fb-credit" checked/);
await feedbackSubmit(form,env);
assert.equal(posts.at(-1).body.credit,true);
fb.sent=null;
assert.equal(fb.credit,false,'the next note starts anonymous again');
await feedbackAction('fbKind',{kind:'bug'},null,env);fb.sent=null;
await feedbackSubmit(form,env);
assert.ok(!('credit' in posts.at(-1).body),'only ideas carry it');
// The player's own list: their choice, and the edit form keeps / changes it.
fb.mine={items:[{id:7,kind:'idea',text:'Thêm nghề làm bánh',status:'new',created_at:1,credit:'name',images:[]}]};
assert.match(page(),/🙋 Nếu ý tưởng được làm: ghi tên nhân vật của bạn/);
await feedbackAction('fbEdit',{id:'7'},null,env);
assert.match(page(),/id="fb-edit-credit" checked/);
feedbackInput({id:'fb-edit-credit',checked:false},env);
await feedbackSubmit({dataset:{fbEdit:'7'},querySelector:()=>({value:'Thêm nghề làm bánh mì'})},env);
assert.deepEqual(posts.at(-1),{path:'/api/feedback/edit',body:{id:7,text:'Thêm nghề làm bánh mì',credit:false}});
// The operator's inbox: the badge, ✅ Ghi nhận, then the read-only line.
const idea={id:9,kind:'idea',status:'new',text:'Thêm nghề làm bánh',created_at:1,images:[],context:{},credit:'name',name:'Lụm <b>',reward:null,reward_coins:30000};
env.api.admin=true;fb.tab='inbox';fb.inbox={items:[idea,{...idea,id:10,credit:'anon',name:null}],counts:{new:2},next:null};
let html=page();
assert.match(html,/🙋 Muốn ghi tên: <b data-no-translate>Lụm &lt;b&gt;<\/b>/,'escaped name');
assert.match(html,/🕶️ Ẩn danh/);
assert.match(html,/data-action="fbAck" data-id="9" data-coins="30000">✅ Ghi nhận \(thưởng 30\.000 xu\)/);
globalThis.confirm=()=>false;posts=[];
await feedbackAction('fbAck',{id:'9',coins:'30000'},null,env);
assert.equal(posts.length,0,'no payment without the confirm');
globalThis.confirm=()=>true;
env.api.post=async(path,body)=>{posts.push({path,body});return {item:{...idea,reward:{coins:30000,status:'pending'}}};};
await feedbackAction('fbAck',{id:'9',coins:'30000'},null,env);
assert.deepEqual(posts.at(-1),{path:'/api/admin/feedback',body:{id:9,acknowledge:true}});
html=page();
assert.match(html,/🎁 Đã ghi nhận · thưởng 30\.000 xu/);
assert.doesNotMatch(html,/data-action="fbAck" data-id="9"/);
console.log('feedback-credit.mjs: ok');
