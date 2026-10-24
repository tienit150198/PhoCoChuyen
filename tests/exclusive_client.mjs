// 🌧️ Danh hiệu độc nhất (game/exclusive.py, public/js/v4/exclusive.js): the title's chip and popover, the frame
// "Mưa rơi" (avatar, chat bubble, chooser), the canvas name tags and the town's tag, for its id only.
//   node tests/exclusive_client.mjs
import assert from 'node:assert/strict';
import {EX,isEx,exOf,firstEx,rainFrame,exChip,exPill,exRain,exInk,exTownTag} from '../public/js/v4/exclusive.js';
import {ofId,pick,choices,chooser,avatar,bubble,chipClass} from '../public/js/v4/honour-frames.js';
import {title,titles,chips,list,icons} from '../public/js/v4/honours.js';

const X='ex_cuong_vu';
assert.deepEqual(Object.keys(EX),[X]);
assert.ok(isEx(X)&&!isEx('ex_nope')&&!isEx('toString')&&!isEx('__proto__'));
assert.equal(exOf(X).frame,'Mưa rơi');assert.equal(firstEx(['lb_all_1',X]).id,X);assert.equal(firstEx(['lb_all_1']),null);

// 1. the title: first-class chip with its own class, marked one of a kind
const t=title(null,X);
assert.equal(t.full,'Cuồng Vũ Tán Tiên');assert.ok(t.ex);assert.match(t.src,/Độc nhất/);assert.match(t.src,/Mưa rơi/);
assert.equal(title(null,'ex_nope'),null);
assert.deepEqual(titles(null,[X,'lb_all_1','ex_bad']).map(x=>x.id),[X,'lb_all_1']);
assert.match(chips(null,[X],2),/class="hn-chip hn-ex"/);
assert.match(list(null,[X],'Mưa'),/class="ex-ti">Cuồng Vũ Tán Tiên<\/span><i class="ex-tag">Độc nhất/);
assert.equal(chipClass(X),' hn-ex');assert.equal(chipClass('ex_nope'),'');
assert.equal(icons(null,[X,'lb_all_1'],'🌧️ Cuồng Vũ Tán Tiên'),'👑');
assert.match(exChip({id:X,emoji:'x',name:'y'}),/🌧️<\/i><span>Cuồng Vũ Tán Tiên/);   // the table wins over a row's text
assert.equal(exChip(null),'');assert.doesNotMatch(exChip({emoji:'<b>',name:'<script>'}),/<script>|<b>/);

// 2. the frame: its own (no art, no medal), first when held, put away with 'off', never for an unknown id
assert.deepEqual(ofId(X),{n:null,tier:7,ex:X});assert.equal(ofId('ex_nope'),null);assert.equal(ofId('ex_'),null);
assert.equal(pick([X,'lb_all_1'],{}).ex,X);
assert.equal(pick(['hf_off',X],{}),null);
assert.equal(pick(['lb_all_1',X],{}).board,'all');   // she chose a top frame: that one
assert.equal(pick(['ex_nope'],{}),null);
const av=avatar([X],{},'<i class="pic"></i>');
assert.match(av,/^<span class="hf-av hf-ex" style="--hf-img:url\('data:image\/svg\+xml,/);
assert.doesNotMatch(av,/data-hf-rank|data-hf-icon/);
assert.deepEqual(bubble([X],{}),{cls:' hf-ex',attrs:''});
assert.notEqual(bubble(['dh_den_long'],{}).cls,' hf-ex');
// the svg: rain, ripples, sparkles, cloud and umbrella; animated, and a still one (reduced motion) without SMIL
const dec=u=>decodeURIComponent(u.slice('data:image/svg+xml,'.length));
const A=dec(rainFrame(true)),S=dec(rainFrame(false));
assert.match(A,/<animateTransform/);assert.match(A,/attributeName="rx"/);assert.match(A,/clip-path="url\(#b\)"/);
assert.doesNotMatch(S,/<animate/);assert.ok(S.length>1500&&A.length<20000,`${S.length} ${A.length}`);
assert.equal((A.match(/<g class="dr">/g)||[]).length,20,'20 drops');
// the chooser: hers first, labelled one of a kind; picked, it is "on"
const api=(pick_)=>({state:{journey:{hf_pick:pick_}},content:{journey:{}},lbTitles:[{board:'all',rank:1,emoji:'👑',name:'Trùm cuối của phố',label:'Top 1'}],exTitles:[{id:X,emoji:'🌧️',name:'Cuồng Vũ Tán Tiên',frame:'Mưa rơi'}]});
assert.deepEqual(choices(api()).map(x=>[x.id,x.name,x.label]),[[X,'Mưa rơi','Độc nhất · Cuồng Vũ Tán Tiên'],['lb_all_1','Trùm cuối của phố','Top 1']]);
assert.match(chooser(api(X)),new RegExp(`class="hf-opt on" data-action="jrFrame" data-id="${X}" aria-pressed="true"`));
assert.doesNotMatch(chooser(api(X)),/Danh hiệu đã chọn không còn giữ/);
assert.match(chooser({...api(X),exTitles:[]}),/Danh hiệu đã chọn không còn giữ/,'not hers: the choice is gone');
assert.deepEqual(choices({...api(),exTitles:[{id:'ex_nope'}]}).map(x=>x.id),['lb_all_1']);

// 3. canvas name tags: a pill, rain inside it (moves with time, stands still at t=0), its ink
function ctx(){const calls=[];const g={addColorStop(){}};return {calls,save(){},restore(){},beginPath(){},roundRect(){calls.push('rr');},rect(){},fill(){calls.push('fill');},stroke(){calls.push('stroke');},clip(){},
  moveTo(x,y){calls.push(['m',+x.toFixed(2),+y.toFixed(2)]);},lineTo(){},ellipse(){calls.push('e');},closePath(){},createLinearGradient(){return g;},set fillStyle(v){},set strokeStyle(v){},set lineWidth(v){},set lineCap(v){},set shadowColor(v){},set shadowBlur(v){},set globalAlpha(v){}};}
const c1=ctx();exPill(c1,0,0,80,28,false);assert.deepEqual(c1.calls,['rr','fill','stroke']);
const r0=ctx(),r1=ctx();exRain(r0,0,0,80,28,0,true);exRain(r1,0,0,80,28,.5,true);
assert.ok(r0.calls.filter(x=>x[0]==='m').length>=6);assert.notDeepEqual(r0.calls,r1.calls,'the rain falls');
assert.ok(r0.calls.includes('e'),'ripples');
const ink=exInk(ctx(),0,10,false);assert.ok(ink.name&&ink.title);

// 4. the town's name tag: her title's line in its own ink and background, then the bang
assert.deepEqual(exTownTag([X]),{line:'🌧️ Cuồng Vũ Tán Tiên',ink:'#3f37b5',tb:'#e8ecff'});assert.equal(exTownTag(['lb_all_1']),null);
globalThis.location??={search:'',hash:'',pathname:'/',href:'http://x/'};
const {tagOf}=await import('../public/js/isometric-town.js');
const bg={n:'Rồng Đỏ',e:'🐉',c:'do',r:'tv'};
assert.deepEqual(tagOf(null,[X]),{tag:'🌧️ Cuồng Vũ Tán Tiên',ink:'#3f37b5',tb:'#e8ecff'});
assert.equal(tagOf(bg,[X]).tag,'🌧️ Cuồng Vũ Tán Tiên\n🐉 Rồng Đỏ');
assert.equal(tagOf(bg,['lb_all_1']).tb,undefined);assert.deepEqual(tagOf(null,null),{});
console.log('exclusive client ok');
