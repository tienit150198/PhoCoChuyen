/** Scene layer for "chuyện bất ngờ trong ca": a thief walks in and grabs
 * something, a drunk guest breaks glasses, kids knock a shelf over, a
 * football smashes the window, a stray dog runs through, a scooter is
 * ridden off, a car gets scratched, or the shop was broken into last night
 * (before/after view). Render-only: the server already decided what happens
 * and what it costs; this file only animates what the public view says.
 * With reduceMotion the actor stands still at the spot with a caption.
 *
 * Coordinates are scene pixels of BobaWorld's plan (landscape or portrait). */
import {t as tr} from './i18n.js';

const R=(c,x,y,w,h,fill,r=10,stroke=null,lw=2)=>{c.beginPath();c.roundRect(x,y,w,h,r);c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=lw;c.stroke();}};
const E=(c,x,y,rx,ry,fill)=>{c.beginPath();c.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),0,0,Math.PI*2);c.fillStyle=fill;c.fill();};
const L=(c,x,y,x2,y2,color,width=2)=>{c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.beginPath();c.moveTo(x,y);c.lineTo(x2,y2);c.stroke();};
const T=(c,s,x,y,size=14,color='#fff',weight=800)=>{c.font=`${weight} ${size}px "Trebuchet MS", "Segoe UI", sans-serif`;c.fillStyle=color;c.textAlign='center';c.textBaseline='middle';c.fillText(s,x,y);};
const lerp=(a,b,t)=>a+(b-a)*Math.max(0,Math.min(1,t));
const ease=t=>{t=Math.max(0,Math.min(1,t));return t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;};

/** Short caption over the actor: who it is, in the story's words. */
export const ACTOR_TAG={thief:'Kẻ gian',pickpocket:'Kẻ móc túi',biker:'Kẻ gian',drunk:'Khách say',teens:'Nhóm quậy phá',kids:'Mấy đứa nhỏ',
  kid_ball:'Cậu nhóc',dog:'Chó hoang',cat:'Mèo nhà bên',customer:'Khách',guest:'Khách trọ',student:'Học sinh',self:'Sự cố'};

function anchors(w){
  const pl=w.plan(),port=w.isPortrait(),door=pl.spots.door[0],cus=pl.customers;
  return port?{door:[door[0]-10,door[1]-10],out:[720,850],shelf:[160,694],till:[455,694],table:cus[1],window:[338,470],glass:[338,340],car:[610,742],street:[-40,760]}
             :{door:[door[0]-20,door[1]-6],out:[1190,690],shelf:[300,616],till:[760,616],table:cus[1],window:[573,452],glass:[573,330],car:[1085,606],street:[1190,560]};
}

export class SceneFx{
  constructor(){this.ev=null;this.onTap=null;this.box=null;}
  /** A live happening from the public view. */
  start(w,live){
    if(this.ev&&this.ev.id===live.id)return;
    this.ev={id:live.id,live,t0:w.time,end:null,won:null,shards:[]};
  }
  /** The server's result: won → the actor leaves empty-handed. */
  finish(w,last){const ev=this.ev;if(!ev||ev.end)return;ev.end=w.time;ev.won=last?!!last.won:false;ev.good=last?.good;}
  clear(){this.ev=null;this.box=null;}
  get busy(){return !!this.ev;}
  tap(pos){const b=this.box;if(!b||!this.ev||this.ev.end)return false;
    if(pos.x>=b.x0&&pos.x<=b.x1&&pos.y>=b.y0&&pos.y<=b.y1){this.onTap?.(this.ev.live);return true;}return false;}
  /** Where the actor is and what it does at time t (seconds since start). */
  path(w,t){
    const a=anchors(w),ev=this.ev,lv=ev.live,to=a[lv.target]||a.shelf,reduced=w.reduced;
    const stay=lv.anim==='night';
    if(reduced)return {p:to,moving:false,phase:'act',carry:!ev.end||!ev.won,face:1};
    const enter=lv.anim==='knock'?1.2:1.7,act=enter+.9;
    if(ev.end!=null){
      const k=(w.time-ev.end);
      const from=ev.last||to,dest=ev.won&&['drunk','customer','guest','teens'].includes(lv.actor)?a.door:a.out;
      if(k>2.4)return null;
      return {p:[lerp(from[0],dest[0],ease(k/2.2)),lerp(from[1],dest[1],ease(k/2.2))],moving:true,phase:'leave',carry:!ev.won,face:dest[0]>=from[0]?1:-1,fade:Math.max(0,1-(k-1.6)/.8)};
    }
    if(stay)return {p:to,moving:false,phase:'act',carry:false,face:1};
    const start=lv.anim==='ride'||lv.anim==='scratch'?a.street:a.out;
    let p,phase,moving;
    if(t<enter){const k=ease(t/enter);p=[lerp(start[0],to[0],k),lerp(start[1],to[1],k)];phase='enter';moving=true;}
    else if(t<act){p=to;phase='act';moving=false;}
    else if(['snatch','pick','ride'].includes(lv.anim)){
      // Slipping away towards the door while you decide.
      const k=ease((t-act)/3.2),door=a.door;p=[lerp(to[0],door[0],k*.8),lerp(to[1],door[1],k*.8)];phase='sneak';moving=k<1;
    }else{p=[to[0]+Math.sin(t*3)*6,to[1]];phase='linger';moving=lv.actor==='dog'||lv.actor==='cat'||lv.actor==='kids';}
    ev.last=p;
    return {p,moving,phase,carry:phase!=='enter',face:phase==='sneak'?1:(p[0]<=to[0]?1:-1)};
  }
  draw(w){
    const ev=this.ev;if(!ev)return;const c=w.ctx,lv=ev.live,t=w.time-ev.t0,a=anchors(w),reduced=w.reduced;
    c.save();
    if(lv.anim==='night'&&!ev.end)this.nightView(w,c,a,lv);
    // Debris that stays on the floor until the moment has passed.
    if(['smash','knock','drop','spill','ball'].includes(lv.anim)&&(t>1.6||reduced)&&(!ev.end||w.time-ev.end<2.4))this.debris(c,a[lv.target]||a.shelf,lv,t,w.isPortrait());
    if(lv.anim==='ball'&&!ev.end)this.ball(c,a,t,reduced);
    if(lv.anim==='scratch'||lv.target==='car')this.car(c,a.car,t>2&&lv.anim==='scratch');
    if(lv.anim==='ride'&&(!ev.end||!ev.won))this.scooter(c,a.door,ev,w);
    const at=lv.anim==='night'||lv.anim==='ball'?null:this.path(w,t);
    if(at){
      c.globalAlpha=at.fade??1;
      const [x,y]=at.p,s=w.isPortrait()?.92:1;
      this.actor(c,x,y,lv.actor,w.time,at.moving,at.face,s,reduced);
      if(at.carry&&['snatch','pick','ride'].includes(lv.anim)&&(at.phase!=='enter'))this.loot(c,x+18*at.face,y-70*s,lv,w.time);
      if(!ev.end)this.tag(w,c,x,y,s,lv,reduced);else this.box=null;
      c.globalAlpha=1;
    }else if(lv.anim==='ball'&&!ev.end){const k=a.door,s=w.isPortrait()?.92:1;this.actor(c,k[0],k[1],'kid_ball',w.time,false,-1,s,reduced);this.tag(w,c,k[0],k[1]+30,s*.8,lv,reduced);}
    else this.box=null;
    // Result pop: a big mark where it happened.
    if(ev.end&&w.time-ev.end<2.2){const k=w.time-ev.end,p=a[lv.target]||a.shelf,up=reduced?0:k*18;
      c.globalAlpha=Math.max(0,1-k/2.2);E(c,p[0],p[1]-120-up,26,26,ev.won||ev.good===true?'#3f9b63':'#c0392b');T(c,ev.won||ev.good===true?'✓':'−',p[0],p[1]-121-up,28,'#fff');c.globalAlpha=1;}
    if(ev.end&&w.time-ev.end>2.4)this.ev=null;
    c.restore();
  }
  /** Red caption over the actor; the whole figure is a tap target. */
  tag(w,c,x,y,s,lv,reduced){
    const tag=tr(ACTOR_TAG[lv.actor]||'Kẻ gian'),size=w.isPortrait()?15:12,tw=Math.max(64,tag.length*size*.62+26),ty=y-150*s;
    const pulse=reduced?0:Math.sin(w.time*6)*2;
    R(c,x-tw/2,ty-14-pulse,tw,28,lv.kind==='den'?'#c2803f':'#c0392b',14,'#fff5ee',2);T(c,tag,x,ty-pulse,size,'#fff');
    E(c,x+tw/2-4,ty-16-pulse,9,9,'#ffd35c');T(c,'!',x+tw/2-4,ty-16-pulse,12,'#7a3b00');
    this.box={x0:x-50*s,x1:x+50*s,y0:ty-20,y1:y+12};
  }
  loot(c,x,y,lv,time){const icon=lv.target==='till'?'💵':lv.anim==='ride'?'🔑':'📦';E(c,x,y,15,13,'#fff7e6');T(c,icon,x,y+1,18,'#000',400);}
  debris(c,p,lv,t,port){
    const [x,y]=p,s=port?.9:1;
    if(lv.anim==='spill'){E(c,x+10,y+14,48*s,12*s,'#b98a5a88');E(c,x+30,y+18,20*s,6*s,'#b98a5aaa');R(c,x-18,y+2,16,22,'#f0e6d6',4,'#b9a58c',1.5);}
    else if(lv.actor==='dog'||lv.actor==='cat'||lv.anim==='knock'){for(let i=0;i<5;i++){const dx=(i*37%70)-35,dy=(i*23%20)+6;R(c,x+dx,y+dy,16,12,['#d9a86c','#b7c6aa','#e3b5a4','#a8c3d4','#e8d38a'][i],3,'#8c7358',1);}}
    // glass shards
    for(let i=0;i<9;i++){const ang=i*.7,r=(18+(i*13)%34)*s;c.beginPath();c.moveTo(x+Math.cos(ang)*r,y+12+Math.sin(ang)*r*.35);c.lineTo(x+Math.cos(ang)*r+7,y+9+Math.sin(ang)*r*.35);c.lineTo(x+Math.cos(ang)*r+2,y+17+Math.sin(ang)*r*.35);c.closePath();c.fillStyle='#d8eef4';c.fill();c.strokeStyle='#8fb3c0';c.lineWidth=1;c.stroke();}
  }
  ball(c,a,t,reduced){
    const g=a.glass,k=reduced?1:Math.min(1,t/.9);
    if(k<1){const x=lerp(a.door[0],g[0],k),y=lerp(a.door[1]-40,g[1],k)-Math.sin(k*Math.PI)*120;this.football(c,x,y);return;}
    // cracked window
    c.strokeStyle='#5b7f8c';c.lineWidth=2.4;for(let i=0;i<8;i++){const ang=i*Math.PI/4+.3;c.beginPath();c.moveTo(g[0],g[1]);c.lineTo(g[0]+Math.cos(ang)*(40+(i%3)*18),g[1]+Math.sin(ang)*(34+(i%2)*16));c.stroke();}
    E(c,g[0],g[1],10,10,'#eaf6f8');this.football(c,g[0]+30,a.window[1]+10);
  }
  football(c,x,y){E(c,x,y,13,13,'#fbfbf7');c.strokeStyle='#333';c.lineWidth=1.4;c.beginPath();c.arc(x,y,13,0,Math.PI*2);c.stroke();E(c,x,y,4.5,4.5,'#333');for(let i=0;i<5;i++){const a=i*Math.PI*2/5;E(c,x+Math.cos(a)*10,y+Math.sin(a)*10,2.6,2.6,'#333');}}
  car(c,p,scratched){const [x,y]=p;E(c,x,y+8,78,12,'#0000001c');R(c,x-78,y-44,156,46,'#6f8fb3',16,'#4d6a8a',2);R(c,x-48,y-72,96,34,'#86a6c7',14,'#4d6a8a',2);R(c,x-40,y-66,36,22,'#d7eef7',6);R(c,x+4,y-66,36,22,'#d7eef7',6);E(c,x-46,y+2,16,16,'#3c3c3c');E(c,x+46,y+2,16,16,'#3c3c3c');E(c,x-46,y+2,6,6,'#aaa');E(c,x+46,y+2,6,6,'#aaa');
    if(scratched){c.strokeStyle='#f5f5f5';c.lineWidth=2.2;c.beginPath();c.moveTo(x-60,y-24);c.bezierCurveTo(x-20,y-30,x+10,y-16,x+62,y-26);c.stroke();}}
  scooter(c,door,ev,w){const moving=ev.end&&!ev.won,k=moving?Math.min(1,(w.time-ev.end)/1.6):0,x=door[0]+40+k*220,y=door[1]+10;c.globalAlpha=1-k*.8;
    E(c,x,y+10,44,8,'#0000001f');E(c,x-28,y,13,13,'#333');E(c,x+30,y,13,13,'#333');R(c,x-30,y-26,58,22,'#d65f5f',10,'#9c3b3b',2);R(c,x+18,y-52,8,30,'#777',3);R(c,x+10,y-56,24,7,'#555',3);R(c,x-22,y-34,34,10,'#3c3c3c',5);c.globalAlpha=1;}
  nightView(w,c,a,lv){
    // Dim, bluish morning light and the broken lock at the door.
    c.fillStyle='rgba(40,52,90,.18)';c.fillRect(-200,-200,1700,1300);
    const d=a.door;E(c,d[0],d[1]-60,24,24,'#fff4e0');R(c,d[0]-11,d[1]-66,22,18,'#c9a24a',4,'#7d5d16',2);c.strokeStyle='#7d5d16';c.lineWidth=3.5;c.beginPath();c.arc(d[0]-4,d[1]-68,8,Math.PI,Math.PI*1.9);c.stroke();L(c,d[0]+7,d[1]-80,d[0]+14,d[1]-70,'#c0392b',3);
    const sh=a[lv.target]||a.shelf,rows=lv.before||[];
    rows.slice(0,4).forEach((row,i)=>{const x=sh[0]-60+i*52,y=sh[1]-200;c.setLineDash([5,4]);R(c,x-20,y-20,40,40,'rgba(255,255,255,.35)',8,'#c0392b',2);c.setLineDash([]);
      T(c,row.emoji||'📦',x,y,18,'#000',400);R(c,x+6,y+8,26,18,'#c0392b',9);T(c,`−${row.before-row.after}`,x+19,y+17,11,'#fff');});
    if(!rows.length){R(c,sh[0]-40,sh[1]-220,80,50,'rgba(255,255,255,.35)',8,'#c0392b',2);T(c,'?',sh[0],sh[1]-195,22,'#c0392b');}
    // papers scattered on the floor
    for(let i=0;i<6;i++){const x=sh[0]-50+i*40,y=sh[1]+20+(i%2)*18;c.save();c.translate(x,y);c.rotate((i%3-1)*.4);R(c,-12,-8,24,16,'#fbf6ea',2,'#cdbf9f',1);c.restore();}
  }
  actor(c,x,y,kind,time,moving,face,s,reduced){
    const bob=reduced?0:Math.sin(time*(moving?9:2))*(moving?2.5:1),step=moving&&!reduced?Math.sin(time*10)*4:0;
    c.save();c.translate(x,y+bob);c.scale(face*s,s);
    if(kind==='dog'){E(c,0,4,34,8,'#0000001f');R(c,-30,-38,54,26,'#b98a5a',13);E(c,28,-44,16,14,'#c99a68');E(c,40,-40,8,6,'#8a6440');E(c,32,-48,2.4,2.8,'#222');E(c,22,-56,6,10,'#8a6440');for(const lx of [-22,-8,6,18])R(c,lx,-16+(lx%2?step:-step)*.5,8,18,'#a47850',3);L(c,-30,-30,-44,-46+step,'#b98a5a',6);c.restore();return;}
    if(kind==='cat'){E(c,0,4,24,6,'#0000001f');E(c,0,-18,22,14,'#d9a05b');E(c,18,-30,12,11,'#e0ad6c');c.beginPath();c.moveTo(10,-38);c.lineTo(13,-50);c.lineTo(18,-39);c.moveTo(20,-39);c.lineTo(26,-49);c.lineTo(28,-37);c.fillStyle='#e0ad6c';c.fill();E(c,22,-31,1.8,2.3,'#222');L(c,-20,-18,-34,-36+step,'#d9a05b',5);c.restore();return;}
    const kid=kind==='kids'||kind==='kid_ball'||kind==='student',k=kid?.72:1;
    c.scale(k,k);
    const hood={thief:'#3d4050',pickpocket:'#5a4e6e',biker:'#44505e',teens:'#7a5c9e',drunk:'#8f6b52',customer:'#9fb7c8',guest:'#c8a07c',kids:'#e6a04a',kid_ball:'#4f8fd1',student:'#ffffff',self:'#b58ab0'}[kind]||'#3d4050';
    E(c,0,2,24,7,'#0000002a');
    R(c,-17,-22,14,22,'#2f3140',5);R(c,3,-22,14,22,'#2f3140',5);R(c,-19,-7+step,17,9,'#222',4);R(c,2,-7-step,17,9,'#222',4);
    R(c,-24,-58,48,40,hood,15);E(c,-26,-40,8,14,hood);E(c,26,-40,8,14,hood);
    if(kind==='student'){R(c,-6,-56,12,20,'#2c5aa0',3);}
    const skin=kind==='drunk'?'#f2b7a0':'#f5d2b4';
    E(c,0,-86,30,31,kind==='thief'||kind==='pickpocket'||kind==='biker'?hood:'#4b3a30');E(c,0,-80,26,25,skin);
    if(kind==='drunk'){E(c,-15,-72,7,5,'#e57f75');E(c,15,-72,7,5,'#e57f75');R(c,24,-60,9,22,'#5f8f4e',3);R(c,26,-66,5,8,'#5f8f4e',2);L(c,-10,-82,-4,-80,'#553',2);L(c,4,-80,10,-82,'#553',2);}
    else{E(c,-10,-82,3.6,4.4,'#3b2a20');E(c,10,-82,3.6,4.4,'#3b2a20');}
    if(kind==='thief'||kind==='pickpocket'){R(c,-22,-76,44,18,'#2a2b33',8);if(kind==='thief'){R(c,-30,-112,60,16,'#23242c',8);R(c,-2,-104,40,8,'#23242c',4);}}
    if(kind==='biker'){c.beginPath();c.arc(0,-90,31,Math.PI*1.02,Math.PI*1.98);c.fillStyle='#e0c040';c.fill();R(c,-24,-94,48,8,'#394b5a',4);R(c,-22,-76,44,16,'#2a2b33',8);}
    if(kind==='teens'){R(c,-30,-112,60,12,'#c0392b',6);}
    if(kind==='kid_ball')this.football(c,30,-12);
    if(kind==='guest'){R(c,-54,-44,26,40,'#6b8cae',6,'#3f5d7c',2);L(c,-41,-44,-41,-52,'#3f5d7c',3);}
    if(kind==='self'){L(c,-8,-68,8,-68,'#8a5a4a',2);}
    else if(kind!=='drunk'&&kind!=='thief'&&kind!=='pickpocket'&&kind!=='biker'){c.beginPath();c.arc(0,-68,5,Math.PI*1.1,Math.PI*1.9,false);c.strokeStyle='#8a5a4a';c.lineWidth=2;c.stroke();}
    c.restore();
  }
}
