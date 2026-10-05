export const SPAWN={x:510,y:1090};
export const SHOPS=[
 {id:'grocery',name:'Cô Ba',place:'Tạp hóa Cô Ba',at:{x:442,y:922},hit:{x:290,y:700,r:190}},
 {id:'cafe',name:'Chú Hùng',place:'Cà phê bên biển',at:{x:657,y:996},hit:{x:852,y:810,r:145}}
];
const BORDER=[[235,1500],[449,1500],[513,1350],[614,1235],[614,1174],[720,1038],[755,1005],[683,936],[637,846],[611,775],[643,685],[608,650],[556,728],[531,797],[439,854],[360,909],[358,994],[388,1053],[327,1120],[377,1178],[333,1240],[310,1320]];
export function walkable(p){
 if(!Number.isFinite(p.x)||!Number.isFinite(p.y))return false;
 let inside=false;for(let i=0,j=BORDER.length-1;i<BORDER.length;j=i++){
  const [ax,ay]=BORDER[i],[bx,by]=BORDER[j];if((ay>p.y)!==(by>p.y)&&p.x<(bx-ax)*(p.y-ay)/(by-ay)+ax)inside=!inside;
 }return inside;
}
export function clear(a,b){const length=Math.hypot(b.x-a.x,b.y-a.y),steps=Math.max(1,Math.ceil(length/3));for(let i=0;i<=steps;i++)if(!walkable({x:a.x+(b.x-a.x)*i/steps,y:a.y+(b.y-a.y)*i/steps}))return false;return true;}
export function move(p,input,dt){
 if(!Number.isFinite(input.x)||!Number.isFinite(input.y))return {...p};
 const n=Math.max(1,Math.hypot(input.x,input.y)),stride=180*Math.min(.05,Math.max(0,Number(dt)||0)),next={x:p.x+input.x/n*stride,y:p.y+input.y/n*stride};
 if(clear(p,next))return next;
 const slides=[{x:next.x,y:p.y},{x:p.x,y:next.y}].sort((a,b)=>Math.hypot(b.x-p.x,b.y-p.y)-Math.hypot(a.x-p.x,a.y-p.y));
 return slides.find(q=>clear(p,q))||{...p};
}
export function advance(from,path,stride){
 let p={...from},i=0,left=Math.max(0,stride);while(i<path.length){const q=path[i],d=Math.hypot(q.x-p.x,q.y-p.y);if(d>left)return {point:{x:p.x+(q.x-p.x)*left/d,y:p.y+(q.y-p.y)*left/d},path:path.slice(i)};p={...q};left-=d;i++;}return {point:p,path:[]};
}
const STEP=24,grid=new Map();
for(let y=648;y<1510;y+=STEP)for(let x=216;x<780;x+=STEP)if(walkable({x,y}))grid.set(`${x},${y}`,{x,y});
export function route(start,end){
 if(!walkable(start)||!walkable(end))return [];
 if(clear(start,end))return [{...end}];
 const cost=new Map(),parent=new Map(),open=[],closed=new Set();
 const near=p=>[...grid].filter(([,q])=>Math.hypot(q.x-p.x,q.y-p.y)<=STEP*2&&clear(p,q));
 const finish=new Set(near(end).map(([k])=>k));
 for(const [key,p] of near(start)){cost.set(key,Math.hypot(p.x-start.x,p.y-start.y));parent.set(key,null);open.push(key);}
 let goal=null;while(open.length){open.sort((a,b)=>cost.get(a)+Math.hypot(grid.get(a).x-end.x,grid.get(a).y-end.y)-cost.get(b)-Math.hypot(grid.get(b).x-end.x,grid.get(b).y-end.y));const key=open.shift();if(closed.has(key))continue;if(finish.has(key)){goal=key;break;}closed.add(key);const p=grid.get(key);
  for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[1,-1],[-1,1]]){const next=`${p.x+dx*STEP},${p.y+dy*STEP}`,q=grid.get(next);if(!q||closed.has(next)||!clear(p,q))continue;const value=cost.get(key)+Math.hypot(dx,dy)*STEP;if(value>=(cost.get(next)??Infinity))continue;cost.set(next,value);parent.set(next,key);open.push(next);}
 }
 if(!goal)return [];
 const raw=[end];for(let k=goal;k;k=parent.get(k))raw.push(grid.get(k));raw.reverse();
 const result=[];let from=start,i=0;while(i<raw.length){let j=raw.length-1;while(j>i&&!clear(from,raw[j]))j--;result.push({...raw[j]});from=raw[j];i=j+1;}return result;
}
