import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {escapeHTML as esc} from '../public/js/icons.js';

const src=readFileSync(new URL('../public/js/v4/fair.js',import.meta.url),'utf8');
const block=src.slice(src.indexOf('async function loadBoard('),src.indexOf('/* ---- 🎁 Tiền vốn'));
const loss=()=>({board:'fair-loss',rows:[{rank:1,name:'Lan <b>',guest:true,xu:250,score:250,days:0,me:true}],me:{net:-250,xu:250,rank:1,visible:true},fair:{loss:true,weekly:true,next:1791738000,week:'2026-10-05',started:1791583200,tiers:[{label:'Top 1',emoji:'🥀',name:'Vua đen đủi'},{label:'Top 2–10',emoji:'☔',name:'Hội đen đủi'}],winners:[{rank:1,name:'Minh <img>',score:700,title:'Vua đen đủi',emoji:'🥀'}],crowned:'2026-10-05'}});
function harness(data=loss(),mode='loss'){
 const f={board:'fair-2026',forever:true,money:{total:9999}};
 const S={board:{mode,data,at:0,loading:false,error:'',request:0},tab:'board',dlg:{open:true},env:{api:{json:async()=>data}}};
 const fmt=n=>Number(n||0).toLocaleString('vi-VN');let renders=0;
 const c=vm.createContext({S,F:()=>f,won:()=>f.money.total,fmt,xu:n=>`${fmt(n)} xu`,esc,dateOf:t=>new Date(t*1000).toLocaleDateString('vi-VN',{day:'2-digit',month:'2-digit',timeZone:'Asia/Ho_Chi_Minh'}),endless:()=>true,serverNow:()=>1791610000000,Date,encodeURIComponent,render:()=>renders++,animating:()=>false});
 vm.runInContext(block,c);
 return {S,f,html:()=>c.boardView(),load:force=>c.loadBoard(force),renders:()=>renders};
}
test('weekly loss renderer distinguishes losses, weekly net, previous winners and escaped names',()=>{
 const h=harness(),html=h.html();
 assert.match(html,/Top lời/);assert.match(html,/Top lỗ/);assert.match(html,/aria-pressed="true"[^>]*>[^<]*Top lỗ/);
 assert.match(html,/-250 xu/);assert.match(html,/-700 xu/);assert.doesNotMatch(html,/\+250 xu|\+700 xu|9\.999 xu|0 ngày chơi/);
 assert.match(html,/Lan &lt;b&gt;/);assert.match(html,/Minh &lt;img&gt;/);assert.match(html,/Vua đen đủi/);assert.match(html,/Hội đen đủi/);
 assert.match(html,/Tuần từ 05\/10\/2026/);assert.match(html,/tuần trước/);assert.match(html,/Không thưởng xu/);assert.match(html,/Việt Nam/);
 assert.match(html,/tiền thua trừ tiền thắng và xu kiếm được/);assert.match(html,/không tính hồi tố/);
});
test('zero, positive net and hidden players never display a loss rank',()=>{
 for(const net of [0,120]){
  const data=loss();data.rows=[];data.me={net,xu:0,rank:null,visible:true};data.fair.winners=[];
  const html=harness(data).html();
  assert.match(html,net===0?/hòa vốn.*0 xu/:/đang lời.*\+120 xu/);
  assert.doesNotMatch(html,/-0 xu|hạng <b>|9\.999 xu/);assert.match(html,/Chưa ai có lỗ ròng tuần này/);
 }
 const data=loss();data.rows=[];data.me.visible=false;data.me.rank=4;
 const html=harness(data).html();assert.match(html,/Tên bạn đang ẩn/);assert.doesNotMatch(html,/hạng <b>/);
});
test('profit board keeps cumulative scoring and profit titles',()=>{
 const data={board:'fair-2026',rows:[{rank:1,name:'Lan',xu:350,days:4}],me:{rank:2,visible:true},fair:{weekly:true}};
 const html=harness(data,'win').html();assert.match(html,/\+350 xu/);assert.match(html,/9\.999 xu/);assert.match(html,/4 ngày chơi/);assert.match(html,/Vua trò chơi/);assert.doesNotMatch(html,/Vua đen đủi|lỗ ròng tuần này/);
});
test('loading and errors have distinct accessible states and retry control',()=>{
 const h=harness(null);h.S.board.loading=true;
 assert.match(h.html(),/Đang mở Top lỗ/);assert.match(h.html(),/aria-busy="true"/);
 h.S.board.loading=false;h.S.board.error='<b>offline</b>';
 const html=h.html();assert.match(html,/&lt;b&gt;offline&lt;\/b&gt;/);assert.match(html,/data-fh="boardrefresh"/);assert.doesNotMatch(html,/Đang mở|Chưa ai có lỗ/);
});
test('switching boards never accepts an old response, even after switching back',async()=>{
 const h=harness(null,'win'),pending=[];
 h.S.env.api.json=url=>new Promise((resolve,reject)=>pending.push({url,resolve,reject}));
 const first=h.load();h.S.board.mode='loss';const second=h.load();
 assert.equal(pending.length,2);assert.match(pending[0].url,/board=fair-2026/);assert.match(pending[1].url,/board=fair-loss/);
 pending[0].resolve({board:'fair-2026',rows:[{name:'STALE'}]});await first;
 assert.equal(h.S.board.data,null);assert.equal(h.S.board.loading,true);
 pending[1].resolve(loss());await second;assert.equal(h.S.board.data.board,'fair-loss');
 h.S.board.mode='win';const third=h.load();h.S.board.mode='loss';const fourth=h.load();
 pending[2].reject(new Error('old failure'));await third;assert.equal(h.S.board.error,'');assert.equal(h.S.board.loading,true);
 pending[3].resolve(loss());await fourth;assert.equal(h.S.board.loading,false);assert.equal(h.S.board.error,'');
});
