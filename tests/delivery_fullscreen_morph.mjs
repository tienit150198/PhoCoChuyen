import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
const body=source.slice(source.indexOf('function morphKids('),source.indexOf('function morphNode('));
const morphKids=new Function(`${body};return morphKids;`)();
for(const [current,incoming,kept] of [[true,true,true],[false,false,false],[true,false,false]]){
  let removed=false;
  const stage={nextSibling:null,remove(){removed=true;}};
  const from={nodeType:1,firstChild:stage,hasAttribute:()=>current};
  const to={nodeType:1,firstChild:null,hasAttribute:()=>incoming};
  morphKids(from,to);
  assert.equal(!removed,kept,'only matching runtime-owned slots preserve their mounted stage');
}
console.log('courier fullscreen: state refresh preserves the mounted stage; ordinary slots still update');
