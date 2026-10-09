// 🐕 Đua chó (public/js/v4/fair-dog.js): the race played out ends in the server's order, a photo finish is close,
// the stall's page shows payouts but no chance, the 📣 cổ vũ sends nothing, a running race's payout is held back.
import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {script,at,setup} from '../public/js/v4/fair-dog.js';

test('the race ends in the order the server drew, whatever the seed',()=>{
  for(let seed=1;seed<400;seed++){
    const order=[0,1,2,3,4,5].sort((a,b)=>((a*7+seed)%11)-((b*7+seed)%11));
    const paths=script(order,seed,seed%3===0,6,15500);
    const fin=paths.map(p=>p.fin);
    for(let k=1;k<6;k++)assert.ok(fin[order[k]]>fin[order[k-1]],`seed ${seed}: place ${k}`);
    if(seed%3===0)assert.equal(fin[order[1]]-fin[order[0]],60);
    for(const [lane,p] of paths.entries()){
      let last=0;
      for(let ms=0;ms<=p.fin;ms+=97){const x=at(p,ms);assert.ok(x>=last-1e-9&&x<=1,`lane ${lane} goes forward`);last=x;}
      assert.equal(at(p,p.fin),1);assert.equal(at(p,0),0);
    }
    // at the winner's finish nobody else has finished
    for(const lane of order.slice(1))assert.ok(at(paths[lane],fin[order[0]])<1);
  }
});

test('the lead changes on the way in most races',()=>{
  let changes=0;
  for(let seed=1;seed<200;seed++){
    const order=[3,1,4,0,5,2],paths=script(order,seed,false,6,15500);
    const lead=ms=>paths.map((p,i)=>[at(p,ms),i]).sort((a,b)=>b[0]-a[0])[0][1];
    const seen=new Set();for(let ms=500;ms<15000;ms+=500)seen.add(lead(ms));
    if(seen.size>1)changes++;
  }
  assert.ok(changes>120,`lead changes in ${changes}/199 races`);
});

function stall(){
  const sent=[],noop=()=>{};
  const dog={min:10,max:1000000,slot:120,dogs:Array.from({length:14},(_,i)=>({name:'Chó '+i,breed:'Chó ta',shape:'mutt',b:'#000',m:'#111',l:'#222',e:'#333'})),
    races:[[100,[[0,29],[1,39],[2,52],[3,78],[4,105],[5,190]]]]};
  const S={dlg:null};
  const ui=setup({S,F:()=>({dog,wallet:5000}),btn:(l,op,d,c,x='')=>`<button data-fh="${op}"${x}>${l}</button>`,say:(w,t)=>`<p>${t}</p>`,xu:n=>`${n} xu`,esc:s=>String(s),
    send:async(a,p)=>{sent.push([a,p]);return {fair:{game:'dg',race:p.race,lane:p.lane,stake:p.stake,order:[p.lane,0,1,2,3,4].filter((v,i,a)=>a.indexOf(v)===i).slice(0,6),won:true,mult:29,back:290,net:190,photo:false,seed:9,loc:{bonus:810}}};},
    render:noop,sfx:noop,pick:a=>a[0],reduce:()=>true,serverNow:()=>100*120*1000+5000,amtBox:()=>'',amtClear:noop,payX:x=>String(x).replace('.',',')});
  return {S,ui,sent};
}

test('the page shows the payouts, no chance; cổ vũ sends nothing; the payout waits for the finish',async()=>{
  const f=stall();
  const html=f.ui.view();
  assert.match(html,/×2,9/);assert.match(html,/×19/);
  assert.doesNotMatch(html.replace(/style="[^"]*"/g,''),/\d\s*%/);   // (the dogs' places on the track are styles)
  assert.match(html,/data-fh="dggo" disabled/);   // no dog picked yet
  f.ui.click('dgpick',{v:'0'});
  f.ui.click('dgstake',{v:'100'});
  assert.doesNotMatch(f.ui.view(),/data-fh="dggo" disabled/);
  globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};globalThis.performance??={now:()=>0};
  f.ui.click('dggo',{});
  await new Promise(ok=>setTimeout(ok,0));
  assert.deepEqual(f.sent,[['fair_dg',{race:100,lane:0,stake:100}]]);
  assert.ok(f.ui.live());
  assert.equal(f.ui.hold('day'),290);assert.equal(f.ui.hold(),290+810);
  for(let i=0;i<20;i++)f.ui.click('dgcheer',{});
  assert.equal(f.sent.length,1,'cheering sends nothing');
  f.ui.stop();
  assert.ok(!f.ui.live());assert.equal(f.ui.hold(),0);
  assert.match(f.ui.view(),/về nhất/);
});

test('fair.js wires the stall in and holds its payout back while it runs',()=>{
  const src=readFileSync(new URL('../public/js/v4/fair.js',import.meta.url),'utf8');
  for(const bit of ["dg:['🐕','Đua chó']","dg:()=>F().dog?dg().view():homeView()","dgHold('day')","op.startsWith('dg')","DG?.stop()"])assert.ok(src.includes(bit),bit);
});
