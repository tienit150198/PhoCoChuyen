import assert from 'node:assert/strict';
import {bindXfer,xferOpen,xferPage,xferClick,xferInput} from '../public/js/v4/bank-xfer.js';

const sent=[];
const view={friends:[{code:'TEST01',name:'Bạn',ok:true}],lock:null,recent:[],today:{left:null},
  rules:{unlimited:true,min:10,chips:[1000,5000],note_max:60,account_days:1,friend_minutes:60}};
const env={api:{json:async(url,opts)=>{if(opts){sent.push(JSON.parse(opts.body));return{receipt:{amount:5000,to:'Bạn',code:'CK1',at:1,src:'acc'}};}return view;}}};
bindXfer({env:()=>env,render:()=>{},B:()=>({balance:9000}),J:()=>({wallet:50}),dlg:()=>null});
xferOpen();await new Promise(resolve=>setImmediate(resolve));
assert.match(xferPage(),/Không giới hạn số lần/);
assert.doesNotMatch(xferPage(),/tối đa 0 xu/);
await xferClick('x-to',{code:'TEST01'});
xferInput({id:'bx-amt',value:'5000'});
await xferClick('x-next',{});
assert.match(xferPage(),/Kiểm tra lại nhé/);
await xferClick('x-send',{});
assert.equal(sent.length,1);assert.equal(sent[0].amount,5000);
await xferClick('x-again',{});await xferClick('x-to',{code:'TEST01'});
xferInput({id:'bx-amt',value:'9001'});await xferClick('x-next',{});
assert.match(xferPage(),/Tài khoản chỉ còn 9.000 xu/);
assert.equal(sent.length,1);
console.log('Unlimited transfers: confirmation, payment and insufficient balance pass.');
