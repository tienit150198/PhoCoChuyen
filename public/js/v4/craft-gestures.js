/** Small, deterministic workshop interactions; coordinates use the 560 × 440 work mat. */
export const RECIPES={teddy:['measure','cut','sew','stuff','decorate'],tote:['measure','cut','sew','straps','decorate'],pot:['shape','glaze','decorate'],bracelet:['thread','beads','decorate'],card:['fold','decorate']};
export const SIZES={teddy:[24,30],tote:[32,36],pot:[20,24],bracelet:[18,1],card:[15,20]};
export const PATHS={cut:[[152,110],[408,110],[408,398],[152,398],[152,110]],sew:[[168,126],[168,382],[392,382],[392,126]],shape:[[184,150],[192,198],[200,246],[208,294],[216,342],[344,342],[352,294],[360,246],[368,198],[376,150]],glaze:[[216,190],[344,190],[344,230],[216,230],[216,270],[344,270],[344,310],[216,310]],thread:[[160,250],[192,226],[224,210],[256,202],[288,202],[320,210],[352,226],[384,250]],fold:[[280,118],[280,358]]};
export const BEAR_OUTLINE=[[240,110],[256,118],[260,132],[280,128],[300,132],[304,118],[320,110],[336,118],[340,134],[332,150],[328,156],[334,176],[328,198],[320,210],[340,216],[366,232],[376,246],[368,258],[352,258],[332,246],[336,282],[334,306],[340,328],[336,344],[320,350],[304,344],[296,318],[264,318],[256,344],[240,350],[224,344],[220,328],[226,306],[224,282],[228,246],[208,258],[192,258],[184,246],[194,232],[220,216],[240,210],[232,198],[226,176],[232,156],[228,150],[220,134],[224,118],[240,110]];
export const pathFor=(d,id=RECIPES[d.kind][d.step])=>d.kind==='teddy'&&id==='cut'?BEAR_OUTLINE:d.kind==='teddy'&&id==='sew'?BEAR_OUTLINE.slice(3,-1).map(([x,y])=>[280+(x-280)*.94,230+(y-230)*.94]):PATHS[id];
const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));
export const distance=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
export function sampledPath(vertices,spacing=8){const points=[vertices[0]];for(let i=1;i<vertices.length;i++){const a=vertices[i-1],b=vertices[i],n=Math.ceil(distance(a,b)/spacing);for(let k=1;k<=n;k++)points.push([a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n]);}return points;}
export function traceStart(path){return {count:0,last:null,cursor:[...path[0]]};}
export function tracePoint(trace,path,p){
 if(!p.every(Number.isFinite)||trace.count>=path.length)return trace;
 const next=path[trace.count];
 // Never credit a jump to a distant endpoint: every intervening path sample must be visited.
 if(trace.last&&distance(trace.last,p)>40)return {...trace,last:null};
 if(distance(p,next)>17)return trace;
 let count=trace.count;
 while(count<path.length&&distance(p,path[count])<=10)count++;
 return {count,last:[...p],cursor:[...p]};
}
export function traceKeyboard(trace,path,key){const d={ArrowLeft:[-8,0],ArrowRight:[8,0],ArrowUp:[0,-8],ArrowDown:[0,8]}[key];if(!d)return trace;return tracePoint({...trace,cursor:[...trace.cursor]},path,[clamp(trace.cursor[0]+d[0],40,520),clamp(trace.cursor[1]+d[1],40,420)]);}
export function newDraft({kind='teddy',color='rose',pattern='flower'}={}){if(!RECIPES[kind])kind='teddy';return {v:1,kind,color,pattern,step:0,done:[],measure:[12,12],trace:{},placed:[],stuffed:[],face:[],marks:[]};}
export const draftKey=(account,kind)=>account?`mnl:craft:v1:${encodeURIComponent(account)}:${kind}`:null;
export function stepComplete(d){const id=RECIPES[d.kind][d.step];if(id==='measure')return d.measure.every((n,i)=>n===SIZES[d.kind][i]);if(pathFor(d,id))return (d.trace[id]?.count||0)>=sampledPath(pathFor(d,id)).length;if(id==='stuff')return [0,1,2,3].every(i=>d.stuffed?.includes(i));if(id==='straps')return d.placed.includes(0)&&d.placed.includes(1);if(id==='beads')return Array.from({length:8},(_,i)=>i).every(i=>d.placed.includes(i));return id==='decorate'&&d.marks.length>0&&(d.kind!=='teddy'||[0,1,2,3].every(i=>d.face?.includes(i)));}
export function nextStep(d){if(!stepComplete(d))return false;const id=RECIPES[d.kind][d.step];if(!d.done.includes(id))d.done.push(id);if(d.step<RECIPES[d.kind].length-1)d.step++;return true;}
export function craftWork(d){if(!stepComplete(d)||d.step!==RECIPES[d.kind].length-1)return null;if(!RECIPES[d.kind].slice(0,-1).every(x=>d.done.includes(x)))return null;return {v:1,steps:[...RECIPES[d.kind]],size:[...SIZES[d.kind]],marks:d.marks.map(p=>p.map(n=>Math.round(n*1000)/1000))};}
export function restoreDraft(raw,selection){try{const d=JSON.parse(raw);if(d.v!==1||d.kind!==selection.kind||!RECIPES[d.kind]||!Number.isInteger(d.step)||d.step<0||d.step>=RECIPES[d.kind].length||!Array.isArray(d.done)||!Array.isArray(d.measure)||d.measure.length!==2||!d.measure.every(n=>Number.isFinite(n)&&n>=0&&n<=45)||!Array.isArray(d.placed)||!d.placed.every(n=>Number.isInteger(n)&&n>=0&&n<8)||!Array.isArray(d.marks)||d.marks.length>12||!d.marks.every(p=>Array.isArray(p)&&p.length===2&&p.every(n=>Number.isFinite(n)&&n>=0&&n<=1))||!d.trace||typeof d.trace!=='object')return null;
 for(let i=0;i<d.step;i++)if(!d.done.includes(RECIPES[d.kind][i])||!stepComplete({...d,step:i}))return null;
 for(const field of ['stuffed','face']){d[field]??=[];if(!Array.isArray(d[field])||!d[field].every(n=>Number.isInteger(n)&&n>=0&&n<4))return null;}
 for(const [id,t] of Object.entries(d.trace)){if(!pathFor(d,id)||!Number.isInteger(t.count)||t.count<0||t.count>sampledPath(pathFor(d,id)).length||!Array.isArray(t.cursor)||t.cursor.length!==2||!t.cursor.every(Number.isFinite))return null;t.last=null;}
 return d;}catch{return null;}}
export function reconcileDraft(raw,selection={}){const selected=newDraft(selection),restored=restoreDraft(raw,selected);if(!restored)return selected;for(const field of ['color','pattern'])if(selection.materialChanges?.[field])restored[field]=selected[field];return restored;}
export function saveDraft(storage,key,d){if(!key)return false;try{storage.setItem(key,JSON.stringify(d));return true;}catch{return false;}}
export async function submitCraft(env,d,pay,{storage,key}={}){const work=craftWork(d);if(!work)return null;const result=await env.cmd('jr_out_craft',{kind:d.kind,color:d.color,pattern:d.pattern,pay,work});if(result&&key)try{storage.removeItem(key);}catch{}return result;}
