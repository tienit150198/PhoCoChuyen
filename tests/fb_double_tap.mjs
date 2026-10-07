// 1.9.3 regression (07/10): an AI write (the reviewer's answer, the reworded review, the teacher's voice) holds the
// command queue for up to AI_WAIT, and a tap waiting behind it showed nothing: 'busy' fired only when a command
// started, so the click hold, the submit guard and the pending mark let a second tap through. The copies queued up,
// the first landed and the rest were refused ("Khách đang đọc phản hồi trước của bạn.", "Còn một chuyện trong lớp cần
// xử lý trước."). Now an identical command queued or on the wire is not queued again, 'busy' comes when a command is
// QUEUED, and the review reply form is off while its reply is on its way. Run by tests/test_fb_queue.py.
import assert from 'node:assert/strict';
import {GameAPI} from '../public/js/api.js';
import {v4Submit} from '../public/js/v4/views.js';
import {termsSource,offersOf,SHOP} from '../public/js/v4/terms.js';

const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ok=data=>new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});
const srv={revision:1,commands:[],ai:[]};
const state=()=>({current:'milk_tea',focus:'milk_tea',settings:{lang:'vi',aiConsent:true}});
globalThis.fetch=async(url,init={})=>{
  const body=init.body?JSON.parse(init.body):null;
  if(url==='/api/command'){
    srv.commands.push(body);
    if(body.expected_revision!==srv.revision)return new Response(JSON.stringify({error:'conflict',code:'revision_conflict',state:state(),revision:srv.revision}),{status:409,headers:{'Content-Type':'application/json'}});
    // The second fb_reply on the same review: the server's refusal (game/feedback.py).
    if(body.action==='fb_reply'&&srv.commands.filter(c=>c.action==='fb_reply'&&c.payload.post===body.payload.post).length>1)
      return new Response(JSON.stringify({error:'Khách đang đọc phản hồi trước của bạn.'}),{status:400,headers:{'Content-Type':'application/json'}});
    srv.revision++;return ok({state:state(),revision:srv.revision,result:{message:'Đã gửi'}});
  }
  if(url==='/api/state')return ok({state:state(),revision:srv.revision});
  if(url==='/api/ai/feedback'||url==='/api/ai/review'){
    let land;const answered=new Promise(r=>{land=r;});srv.ai.push({url,body,land});await answered;
    srv.revision++;return ok({state:state(),revision:srv.revision,result:{message:'Cảm ơn quán nha'},mode:'ai'});
  }
  throw new Error('unexpected '+url);
};
const a=new GameAPI();a.state=state();a.revision=1;a.csrf='c';
const events=[];
a.addEventListener('busy',e=>events.push(['busy',e.detail]));
a.addEventListener('queued',e=>events.push(['queued',e.detail.action]));
a.addEventListener('net',e=>events.push(['net',e.detail]));

// 1. The review is being reworded (the model writes for seconds): it holds the queue.
const rv=a.aiReview('p1');await sleep(0);
assert.equal(srv.ai.length,1);
// The reply tap waits behind it: busy at once (the click hold, the submit guard and the pending mark work), before
// any request of its own.
const reply={post:'p1',text:'Xin lỗi bạn',offer:'none',tone:'sorry'};
const first=a.command('fb_reply',reply);
assert.deepEqual(events.filter(e=>e[0]!=='net'),[['busy',true],['queued','fb_reply']],'busy as soon as the command is queued');
assert.equal(a.waiting,1);assert.equal(srv.commands.length,0,'nothing sent yet');
// 2. The double tap: the same command again (a re-render, another path) is the same promise, never a second command.
const second=a.command('fb_reply',{...reply});
assert.equal(second,first,'an identical command already queued: the same promise');
assert.equal(a.waiting,1);
assert.ok(a.sending('fb_reply',reply),'sending() names it');
// A different command still queues (and the queue order holds).
const other=a.command('tea_prepare',{task:'t1'});
assert.equal(a.waiting,2);
await sleep(150);assert.equal(srv.commands.length,0,'still behind the AI write');
srv.ai[0].land();await rv;
const [r1,r2]=await Promise.all([first,second]);await other;
assert.equal(r1,r2);assert.equal(r1.message,'Đã gửi');
assert.deepEqual(srv.commands.map(c=>c.action),['fb_reply','tea_prepare'],'exactly one fb_reply went out');
await sleep(0);
assert.equal(a.waiting,0);assert.equal(a.sending('fb_reply',reply),null);
assert.deepEqual(events.filter(e=>e[0]==='busy'),[['busy',true],['busy',false]],'busy stays on until the last queued command is answered');
// Once it landed the same words may be sent again (a new round): only queued / on-the-wire copies are folded.
await a.command('fb_reply',reply).catch(e=>assert.equal(e.message,'Khách đang đọc phản hồi trước của bạn.'));
assert.equal(srv.commands.filter(c=>c.action==='fb_reply').length,2);

// 3. The reply form (v4Submit): the box and the send button are off while the reply is on its way; a second submit
//    meanwhile sends nothing; an offer the career does not give goes as 'none'.
function fakeForm({offer='none'}={}){
  const el=()=>({disabled:false,attrs:{},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},
    classList:{set:new Set(),toggle(c,on){if(on)this.set.add(c);else this.set.delete(c);},contains(c){return this.set.has(c);}}});
  const ta=Object.assign(el(),{value:'  Xin lỗi bạn nhé  '}),go=el(),radio={value:offer},tone={value:'sorry'};
  const form={dataset:{v4Fb:'p9'},isConnected:true,querySelector(sel){
    if(sel==='textarea')return ta;if(sel==='input[name=offer]:checked')return radio;if(sel==='input[name=tone]')return tone;
    if(sel==='button[type=submit],button:not([type])')return go;return null;}};
  return {form,ta,go};
}
termsSource(()=>[{id:'tour_guide',terms:{...SHOP,commerce:false,offers:{drink:'Nước suối · 6 xu',gift:'Ảnh tặng · 10 xu',refund:null}}}]);
{
  const sent=[];let land;
  const env={api:{state:{current:'tour_guide'},aiFeedback:async()=>({})},ui:{},toast(){},cmd:(action,payload)=>{sent.push([action,payload]);return new Promise(r=>{land=r;});}};
  const {form,ta,go}=fakeForm({offer:'refund'});
  const p=v4Submit(form,env);
  assert.equal(sent.length,1);
  assert.deepEqual(sent[0],['fb_reply',{post:'p9',text:'Xin lỗi bạn nhé',offer:'none',tone:'sorry'}],'refund is not this career\'s: sent as none');
  assert.equal(ta.disabled,true,'the box is off while the reply is on its way');
  assert.equal(go.disabled,true,'the send button too');
  assert.equal(go.attrs['aria-busy'],'true');assert.ok(go.classList.contains('is-pending'),'and shows pending');
  assert.equal(await v4Submit(form,env),true);assert.equal(sent.length,1,'a second submit meanwhile sends nothing');
  land(null);await p;   // refused: the form comes back for another try
  assert.equal(ta.disabled,false);assert.equal(go.disabled,false);assert.ok(!go.classList.contains('is-pending'));
  assert.equal(ta.value,'  Xin lỗi bạn nhé  ','a refused reply keeps the words');
}
{
  const sent=[];
  const env={api:{state:{current:'tour_guide'},aiFeedback:async()=>({})},ui:{},toast(){},cmd:async(action,payload)=>{sent.push(payload);return null;}};
  await v4Submit(fakeForm({offer:'gift'}).form,env);
  assert.equal(sent[0].offer,'gift','an offer this career gives goes as it is');
}
// 4. offersOf without the career's own row (catalogue not in, or older than `terms`): nothing, never the shop's three.
assert.deepEqual(offersOf('police'),[]);
assert.deepEqual(offersOf('tour_guide').map(([id])=>id),['drink','gift']);
termsSource(()=>null);
assert.deepEqual(offersOf('milk_tea'),[],'no catalogue: no offer (Không bù is always safe)');
termsSource(()=>[{id:'milk_tea'}]);
assert.deepEqual(offersOf('milk_tea'),[],'a catalogue from before terms: no offer');
console.log('fb double tap ok');
