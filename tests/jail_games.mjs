// 🚔 The công ích mini-games of public/js/v4/jail.js, played move by move through their pure step() the way a player
// taps them, on the server's own puzzles (tests/test_jail_games.py feeds game/jail.py puzzle() on stdin and checks the
// answers with game/jail.py _right). Every task: a wrong move is refused and changes nothing, the right moves finish
// the game, and the answer goes out. Prints one JSON line: [{task, done, ans, refused, problems}].
import {readFileSync} from 'node:fs';
import {games} from '../public/js/v4/jail.js';

const {fresh,finished,answer,precheck,step,TRASH,STEPS}=games;
const input=JSON.parse(readFileSync(0,'utf8'));
const clone=o=>JSON.parse(JSON.stringify(o));

/** The moves of someone who does it right. */
function solve(g){
  const pz=g.pz,moves=[];
  const m=(op,data={})=>moves.push([op,data]);
  switch(g.task){
    case'sweep':for(const c of pz.piles)for(let k=0;k<3;k++)m('sweep',{c});break;
    case'plant':case'dishes':{const st=STEPS[g.task];
      for(let i=0;i<pz[st.n];i++)for(const [t] of st.tools){m('tool',{t});m('hole',{i});}break;}
    case'rice':pz.want.forEach((w,i)=>{for(let k=0;k<w;k++)m('scoop',{i});});break;
    case'paint':for(const c of pz.dirty)m('paint',{c});break;
    case'books':[...pz.nums.keys()].sort((a,b)=>pz.nums[a]-pz.nums[b]).forEach(i=>m('book',{i}));break;
    case'laundry':pz.items.forEach((it,i)=>{m('cloth',{i});m('peg',{p:pz.pegs.indexOf(it.c)});});break;
    case'mop':pz.dirt.forEach((d,i)=>{for(let k=0;k<d;k++)m('mop',{i});});break;
    case'trash':pz.items.forEach((x,i)=>{m('junk',{i});m('bin',{b:TRASH[x][2]});});break;
    case'veg':for(const i of pz.yellow)m('leaf',{i});break;
    case'chicken':pz.want.forEach((w,i)=>{m('tool',{t:w});m('hen',{i});});break;
    case'fix':pz.nails.forEach((n,i)=>{for(let k=0;k<n;k++)m('nail',{i});});break;
    case'ledger':for(const k of pz.kinds){const n=pz.pile.filter(x=>x===k).length;for(let c=0;c<n;c++)m('cnt',{k,d:1});}break;
    case'fold':for(const card of pz.cards)for(const t of card)m('fold',{t});break;
  }
  return moves;
}

/** A move that must be refused (with words) and change nothing, before anything is done. */
function wrong(g){
  const pz=g.pz;
  switch(g.task){
    case'plant':case'dishes':{const st=STEPS[g.task];return [['tool',{t:st.tools[1][0]}],['hole',{i:0}]];}
    case'books':{const big=[...pz.nums.keys()].sort((a,b)=>pz.nums[b]-pz.nums[a])[0];return [['book',{i:big}]];}
    case'laundry':{const p=pz.pegs.findIndex(c=>c!==pz.items[0].c);return [['cloth',{i:0}],['peg',{p}]];}
    case'mop':{const i=pz.dirt.findIndex(d=>d>0);return Array.from({length:pz.dirt[i]+1},()=>['mop',{i}]);}
    case'trash':{const b=['giay','nhua','huu_co'].find(x=>x!==TRASH[pz.items[0]][2]);return [['junk',{i:0}],['bin',{b}]];}
    case'veg':{const i=[...Array(pz.leaves).keys()].find(k=>!pz.yellow.includes(k));return [['leaf',{i}]];}
    case'chicken':{const t=Object.keys(games.FEED).find(f=>f!==pz.want[0]);return [['tool',{t}],['hen',{i:0}]];}
    case'fix':return Array.from({length:pz.nails[0]+1},()=>['nail',{i:0}]);
    case'fold':{const t=Object.keys(games.FOLD).find(f=>f!==pz.cards[0][0]);return [['fold',{t}]];}
    default:return null;   // sweep, rice, paint, ledger: nothing to refuse (tap, add / take away, count)
  }
}

const out=[];
for(const {task,pz,ready=0} of input){
  const problems=[];
  // a wrong move: words, and the answer it would send is not the right one yet
  let refused=null;
  const bad=wrong(fresh(task,clone(pz),ready));
  if(bad){
    const g=fresh(task,clone(pz),ready);let said='';
    for(const [op,data] of bad){const r=step(g,op,data);if(r)said=r[0];}
    refused=said;
    if(!said)problems.push('a wrong move went through silently');
    if(finished(g))problems.push('finished after a wrong move');
  }
  // the right moves
  const g=fresh(task,clone(pz),ready);
  if(finished(g))problems.push('finished before anything was done');
  const moves=solve(g);
  if(!moves.length)problems.push('no moves');
  for(const [op,data] of moves){const r=step(g,op,data);if(r&&r[1])problems.push(`refused a right move ${op} ${JSON.stringify(data)}: ${r[0]}`);}
  if(!finished(g))problems.push('not finished after the right moves');
  if(precheck(g))problems.push('precheck: '+precheck(g));
  if(task==='ledger'){   // one count off: said before sending
    const h=fresh(task,clone(pz),ready);for(const [op,data] of solve(h))step(h,op,data);
    step(h,'cnt',{k:pz.kinds[0],d:1});
    if(!precheck(h))problems.push('a wrong count was not said');
  }
  out.push({task,done:finished(g),ans:answer(g),refused,moves:moves.length,problems});
}
process.stdout.write(JSON.stringify(out));
