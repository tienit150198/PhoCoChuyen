import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import {escapeHTML} from '../public/js/icons.js';

const source=readFileSync(new URL('../public/js/v4/chat.js',import.meta.url),'utf8').replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'');
// the stripped imports: 🎨 style-tag.js and 🏅 honours.js (a name with no `st` / `tt` draws as before)
const STUBS={nameAttrs:()=>'',frameAttrs:()=>({cls:'',attrs:''}),titleChip:()=>'',hnChips:()=>'',hnList:()=>'',hnTitles:()=>[],inlineMax:()=>2};
const CH='dm:aaaaaaaaaaaaaaaa:bbbbbbbbbbbbbbbb',OTHER='group:other';
const message=(id,extra={})=>({t:'msg',ch:CH,id,pid:'bbbbbbbbbbbbbbbb',name:'Bạn <An>',text:'Gốc <img onerror=x>',at:1700000000+id,...extra});
function harness(ch=CH){
  const listeners=new Map(),sent=[],nodes=new Map();let focused=0;
  const ta={value:'',style:{},scrollHeight:40,maxLength:1000,focus:()=>focused++};
  nodes.set('textarea',ta);nodes.set('.ch-reply-compose',{innerHTML:'',hidden:true});
  const dlg={open:true,querySelector:s=>nodes.get(s)||null};
  const live={state:'open',me:{pid:'aaaaaaaaaaaaaaaa',account:true,name:'Mình',adm:true},flags:{chatdel:true},chans:[{id:CH,kind:'dm'},{id:OTHER,kind:'group'}],friends:[],limits:{},
    on:(type,fn)=>listeners.set(type,fn),send(frame){sent.push(frame);return this.state==='open';},chan(ch){return this.chans.find(c=>c.id===ch);},friend:()=>null,unread:()=>0,quiet:()=>false};
  const ctx=vm.createContext({live,document:{visibilityState:'visible'},icon:()=>'',esc:escapeHTML,avInner:()=>'',stylesheet:async()=>{},faceCode:()=>'',setTimeout:()=>1,clearTimeout:()=>{},console,...STUBS});
  vm.runInContext(source+'\nrender=()=>{if(typeof renderReply===\"function\")renderReply();};counter=()=>{};countdown=()=>{};globalThis.chat={S,bind,thread,openThread,onAct,submit,onClose,actBar,messages:(list,more,kind)=>msgList(list,kind,more),renderPin};',ctx);
  const h=ctx.chat;h.S.dlg=dlg;h.bind();if(ch!=='town')h.openThread(ch,false);
  const list=ch==='town'?h.S.town:h.thread(ch);list.msgs=[message(12,{ch})];list.loaded=true;
  return {...h,live,sent,ta,nodes,ctx,focused:()=>focused,emit:(type,f={})=>listeners.get(type)?.(f),list};
}

test('live rename updates cached messages, quote selection and group members without losing drafts',()=>{
  const h=harness(),pid='bbbbbbbbbbbbbbbb';h.onAct('reply',{id:'12'});h.ta.value='Bản nháp đang gõ';
  h.list.msgs.push(message(13,{pid:'other',reply:{id:12,pid,name:'Tên cũ',text:'Gốc'}}));
  h.S.members={members:[{pid,name:'Tên cũ'}]};h.S.town.pin=message(14);
  h.emit('renamed',{pid,name:'Tên mới'});
  assert.equal(h.list.msgs[0].name,'Tên mới');assert.equal(h.list.msgs[1].reply.name,'Tên mới');assert.equal(h.S.reply.name,'Tên mới');
  assert.equal(h.S.members.members[0].name,'Tên mới');assert.equal(h.S.town.pin.name,'Tên mới');assert.equal(h.ta.value,'Bản nháp đang gõ');
  h.submit();const f=h.sent.find(f=>f.t==='send');h.emit('renamed',{pid,name:'Tên lần nữa'});h.emit('error',{ref:f.cid,msg:'Thử lại'});
  assert.equal(h.S.reply.name,'Tên lần nữa');assert.equal(h.ta.value,'Bản nháp đang gõ');
});

test('tap and long-press action rows offer reply for real messages including own and admin messages',()=>{
  const h=harness();
  for(const m of [message(12),message(13,{pid:h.live.me.pid}),message(14,{adm:true})])assert.match(h.actBar(m,m.pid===h.live.me.pid,'dm'),/data-ch-act="reply"/);
  assert.doesNotMatch(h.actBar(message(15,{del:1}),false,'dm'),/data-ch-act="reply"/);
});
test('choose and cancel reply without changing composer text; focus and escaped preview',()=>{
  const h=harness();h.ta.value='Bản nháp';h.onAct('reply',{id:'12'});
  assert.equal(h.S.reply?.id,12);assert.equal(h.S.reply.ch,CH);assert.equal(h.ta.value,'Bản nháp');assert.equal(h.focused(),1);
  assert.match(h.nodes.get('.ch-reply-compose').innerHTML,/Bạn &lt;An&gt;/);assert.match(h.nodes.get('.ch-reply-compose').innerHTML,/Gốc &lt;img onerror=x&gt;/);
  h.onAct('replyCancel',{});assert.equal(h.S.reply,null);assert.equal(h.ta.value,'Bản nháp');
});
test('reply sends only canonical original id in town, DM, and group',()=>{
  for(const ch of ['town',CH,OTHER]){
    const h=harness(ch);h.onAct('reply',{id:'12'});h.ta.value='Đồng ý';h.submit();
    const f=h.sent.find(f=>f.t==='send');assert.equal(f.reply_to,12);assert.equal(f.text,'Đồng ý');assert.ok(!('reply' in f));assert.equal(h.S.reply,null);assert.equal(h.ta.value,'');
  }
});
test('switching channels and closing cancel selection',()=>{
  const h=harness();h.onAct('reply',{id:'12'});h.openThread(OTHER,false);assert.equal(h.S.reply,null);
  h.openThread(CH,false);h.onAct('reply',{id:'12'});h.onClose();assert.equal(h.S.reply,null);
});
test('offline and rejected transport keep text and reply intact',()=>{
  const h=harness();h.onAct('reply',{id:'12'});h.ta.value='Giữ lại';h.live.state='down';h.submit();assert.equal(h.ta.value,'Giữ lại');assert.equal(h.S.reply.id,12);
  h.live.state='open';h.live.send=()=>false;h.submit();assert.equal(h.ta.value,'Giữ lại');assert.equal(h.S.reply.id,12);
});
test('server send error restores unchanged current text and reply',()=>{
  const h=harness();h.onAct('reply',{id:'12'});h.ta.value='Gửi lại';h.submit();const f=h.sent.find(f=>f.t==='send');h.emit('error',{ref:f.cid,msg:'Thử lại'});
  assert.equal(h.ta.value,'Gửi lại');assert.equal(h.S.reply?.id,12);
});
test('late error never overwrites newer typing or leaks draft to another channel',()=>{
  for(const mode of ['new text','another channel','left and returned']){
    const h=harness();h.onAct('reply',{id:'12'});h.ta.value='Tin lỗi';h.submit();const f=h.sent.find(f=>f.t==='send');
    if(mode==='new text')h.ta.value='Tin mới';else{h.openThread(OTHER,false);if(mode==='left and returned')h.openThread(CH,false);}
    h.emit('error',{ref:f.cid,msg:'Thử lại'});assert.equal(h.ta.value,mode==='new text'?'Tin mới':'');assert.equal(h.S.reply,null);
  }
});
test('quoted message markup is escaped and does not nest interactive elements',()=>{
  const h=harness(),q=message(13,{text:'Trả lời',reply:{id:12,pid:'peer',name:'<b>An</b>',text:'<script>x</script>'}});
  const html=h.messages([q],false,'dm');assert.match(html,/&lt;b&gt;An&lt;\/b&gt;/);assert.match(html,/&lt;script&gt;x&lt;\/script&gt;/);assert.doesNotMatch(html,/<script>|<button[^>]*>[\s\S]*<button/);
  q.reply={id:12,unavailable:true};assert.match(h.messages([q],false,'dm'),/Tin nhắn không còn khả dụng/);
});
for(const event of ['deleted','hid','cleared','blocked'])test(`${event} redacts loaded, inbox, pin and pending quotes and cancels selection`,()=>{
  const h=harness(),quote={id:12,pid:'bbbbbbbbbbbbbbbb',name:'Bí mật',text:'Nội dung kín'};
  h.list.msgs.push(message(13,{reply:{...quote},pid:'other'}));h.live.chans[0].last=message(13,{reply:{...quote},pid:'other'});h.S.town.pin=message(14,{ch:'town',reply:{...quote},pid:'other'});
  h.onAct('reply',{id:'12'});h.ta.value='Bản nháp';
  const f=event==='cleared'?{chs:{[CH]:12}}:event==='blocked'?{pid:quote.pid,on:true}:{ch:CH,id:12};
  h.emit(event,f);assert.equal(h.S.reply,null);assert.equal(h.ta.value,'Bản nháp');
  assert.deepEqual(JSON.parse(JSON.stringify(h.list.msgs.find(m=>m.id===13).reply)),{id:12,unavailable:true});
  assert.equal(h.live.chans[0].last.reply.unavailable,true);
  if(event==='blocked')assert.equal(h.S.town.pin.reply.unavailable,true);
});
test('deleting an original outside loaded history still scrubs its quote, and failure cannot restore it',()=>{
  const h=harness();h.onAct('reply',{id:'12'});h.ta.value='Nội dung trả lời';h.submit();const f=h.sent.find(f=>f.t==='send');
  h.list.msgs=[message(13,{reply:{id:12,pid:'peer',name:'An',text:'Gốc'}})];
  h.emit('deleted',{ch:CH,id:12});assert.equal(h.list.msgs[0].reply.unavailable,true);
  h.emit('error',{ref:f.cid,msg:'Không còn tin gốc'});assert.equal(h.ta.value,'Nội dung trả lời');assert.equal(h.S.reply,null);
});
test('reply_hidden scrubs quotes when the other participant blocks or deletes their account',()=>{
  const h=harness();h.onAct('reply',{id:'12'});h.list.msgs.push(message(13,{pid:'other',reply:{id:12,pid:'bbbbbbbbbbbbbbbb',name:'An',text:'Gốc'}}));
  h.emit('reply_hidden',{pid:'bbbbbbbbbbbbbbbb'});assert.equal(h.S.reply,null);assert.equal(h.list.msgs[1].reply.unavailable,true);
});
test('gone send error keeps draft text but cancels an unavailable reply even if deletion push was missed',()=>{
  const h=harness();h.onAct('reply',{id:'12'});h.ta.value='Giữ nội dung';h.submit();const f=h.sent.find(f=>f.t==='send');
  h.emit('error',{ref:f.cid,code:'gone',msg:'Tin nhắn gốc không còn'});
  assert.equal(h.ta.value,'Giữ nội dung');assert.equal(h.S.reply,null);
});
