// Backlog 3 #4 (06/10): a brand-new account's first milk-tea tap was refused "Chọn một nghề trước nhé" (14 sessions).
// The screen is drawn from state.focus (no `current` yet), but milk_tea.js / mother_baby.js sent api.command(op,payload)
// and api.js filled the career from state.current (null). Run by tests/test_command_career.py.
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {GameAPI} from '../public/js/api.js';

const sent=[];
globalThis.fetch=async(url,init={})=>{
  const body=init.body?JSON.parse(init.body):null;sent.push(body);
  return new Response(JSON.stringify({state:{current:body?.career??null,focus:'milk_tea',settings:{lang:'vi'}},revision:2,result:{message:'ok'}}),{status:200,headers:{'Content-Type':'application/json'}});
};
const a=new GameAPI();a.state={current:null,focus:'milk_tea',settings:{lang:'vi'}};a.revision=1;a.csrf='c';
await a.command('tea_prepare',{task:'t1'});
assert.equal(sent[0].career,'milk_tea','no career given and no `current`: the workplace on screen (focus)');
await a.command('tea_prepare',{task:'t1'},'mother_baby');
assert.equal(sent[1].career,'mother_baby','a career given wins');
a.state={...a.state,current:'grocery'};
await a.command('gr_scan',{});
assert.equal(sent[2].career,'grocery','`current` first');

// Every career module names its career when it calls api.command itself (the shared x.send / data-command path
// goes through app.js cmd(), which already uses current||focus).
const dir=new URL('../public/js/careers/',import.meta.url),bad=[];
for(const f of readdirSync(dir).filter(f=>f.endsWith('.js'))){
  const src=readFileSync(new URL(f,dir),'utf8');
  for(const m of src.matchAll(/\bapi\.command\(/g)){
    // count the top-level arguments up to the matching ')'
    let i=m.index+m[0].length,depth=1,args=1,q=null;
    for(;i<src.length&&depth;i++){
      const c=src[i];
      if(q){if(c==='\\')i++;else if(c===q)q=null;continue;}
      if(c==='"'||c==="'"||c==='`')q=c;
      else if('([{'.includes(c))depth++;
      else if(')]}'.includes(c))depth--;
      else if(c===','&&depth===1)args++;
    }
    if(args<3)bad.push(`${f}:${src.slice(0,m.index).split('\n').length}`);
  }
}
assert.deepEqual(bad,[],'career modules call api.command without a career: '+bad.join(', '));
console.log('command_career ok');
