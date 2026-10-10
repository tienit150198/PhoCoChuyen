import assert from 'node:assert/strict';
import {feedbackPageView,feedbackInput,feedbackAction,feedbackSubmit} from '../public/js/v4/feedback.js';

globalThis.document={documentElement:{dataset:{layout:'phone'}},getElementById(){return null;}};
globalThis.innerWidth=390;globalThis.innerHeight=844;
globalThis.FileReader=class{
  readAsDataURL(file){queueMicrotask(()=>{if(file.fail){this.onerror();return;}this.result=file.data;this.onload();});}
};
const photo='data:image/png;base64,iVBORw0KGgo=';
const env={ui:{view:'gopy'},api:{state:{},content:{},json:async()=>({items:[]}),post:async()=>({id:1,message:'Đã gửi'})},
  renderSheet(){},openSheet(){},toast(message){env.messages.push(message);},messages:[]};
feedbackPageView(env);
await new Promise(resolve=>setImmediate(resolve));
const fb=env.ui.fb;
assert.match(feedbackPageView(env),/id="fb-images"[^>]*multiple/,'same feedback form offers multiple image selection');
assert.match(feedbackPageView(env),/tối đa 3 ảnh/i);
const select=async files=>{
  assert.equal(feedbackInput({id:'fb-images',files,value:'selected'},env),true);
  await new Promise(resolve=>setImmediate(resolve));
};
await select([{name:'a.png',type:'image/png',size:100,data:photo},{name:'b.png',type:'image/png',size:100,data:photo}]);
assert.equal(fb.images.length,2);
assert.match(feedbackPageView(env),/data-action="fbRemoveImage"/);
await select([{name:'c.png',type:'image/png',size:100,data:photo},{name:'d.png',type:'image/png',size:100,data:photo}]);
assert.equal(fb.images.length,2,'reject the whole selection if combined count exceeds three');
await select([{name:'large.png',type:'image/png',size:2*1024*1024+1,data:photo}]);
await select([{name:'unsafe.svg',type:'image/svg+xml',size:50,data:'data:image/svg+xml;base64,eA=='}]);
await select([{name:'broken.png',type:'image/png',size:50,fail:true}]);
assert.equal(fb.images.length,2,'failed reads, size and type errors preserve selected images');
await feedbackAction('fbRemoveImage',{index:'0'},null,env);
assert.equal(fb.images.length,1);
fb.draft='Màn hình bị lỗi';
const form={id:'fbForm',dataset:{},querySelector:()=>({value:fb.draft})};
let posted;
env.api.post=async(path,body)=>{posted={path,body};throw new Error('offline');};
await feedbackSubmit(form,env);
assert.equal(fb.images.length,1,'failed submission preserves the attachment draft');
assert.equal(fb.draft,'Màn hình bị lỗi');
assert.deepEqual(posted.body.images,[photo]);
env.api.post=async()=>({id:1,message:'Đã gửi'});
await feedbackSubmit(form,env);
assert.equal(fb.images.length,0,'only successful submission clears draft images');
assert.equal(fb.draft,'');
const item={id:1,kind:'bug',status:'done',text:'Báo lỗi',created_at:1,reply:'Đã xử lý',images:[{
  id:'a'.repeat(32),url:'/api/feedback/images/'+'a'.repeat(32),mime:'image/png',width:16,height:12,size:70}]};
fb.mine={items:[item]};fb.sent=null;
assert.match(feedbackPageView(env),/href="\/api\/feedback\/images\/a{32}"/,'player can open submitted image');
env.api.admin=true;fb.tab='inbox';fb.inbox={items:[item],counts:{done:1},next:null};
assert.match(feedbackPageView(env),/src="\/api\/feedback\/images\/a{32}"/,'operator sees submitted image after done');
console.log('Feedback image draft, validation, submission and gallery checks passed.');
