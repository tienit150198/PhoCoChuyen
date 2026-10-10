/** Shared home presence and server-confirmed invitations. No pose changes saved coordinates. */
import {lookOf,figureOf} from './look.js';
import {affectionFigure,POSE_MS} from './home-affection.js';
import {escapeHTML as esc} from '../icons.js';
const unit=n=>Math.round(Math.max(0,Math.min(1,Number(n)||0))*1000)/1000;
const point=p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite);
const EMOTES={hug:['🤗','Ôm','ôm'],kiss:['😘','Hôn','hôn'],heart:['💗','Thả tim','thả tim cho']};
export function crowd({live,state,redraw,still,svg,xy,approach,isWalking=()=>false}){
  const C={want:false,r:'',scope:'',host:'',room:null,me:null,joining:false,blocked:false,people:new Map(),at:[.5,.8],raf:0,effect:null,effectTimer:0,waitTimer:0,invite:null,pending:null,token:0,note:''};
  const ok=()=>live?.state==='open'&&live.flags?.home;
  const subs=[];
  const on=(t,fn)=>{if(live?.on)subs.push(live.on(t,fn));};
  const busy=()=>Boolean(C.pending||C.invite||C.effect);
  const involved=pid=>[C.invite,C.effect].some(e=>e&&(e.pid===pid||e.to===pid));
  function resetAction(){C.token++;C.pending=null;C.invite=null;C.effect=null;clearTimeout(C.effectTimer);clearTimeout(C.waitTimer);C.effectTimer=0;C.waitTimer=0;}
  function clear(){resetAction();C.room=null;C.me=null;C.joining=false;C.people.clear();if(C.raf)cancelAnimationFrame(C.raf);C.raf=0;}
  function join(r,at,scope=C.scope,host=C.host){
    host=typeof host==='string'?host:'';
    if(C.r!==r||C.scope!==scope||C.host!==host){if(C.room||C.joining)live?.send({t:'home_out'});clear();C.r=r;if(C.scope!==scope||C.host!==host){C.scope=scope;C.host=host;C.blocked=false;C.note='';}}
    C.want=true;if(point(at)&&!C.room&&!C.joining)C.at=at.map(unit);
    if(C.blocked||C.room||C.joining||!ok()||!r)return;
    const st=state()||{};C.joining=live.send({t:'home_in',r,...(C.host?{host:C.host}:{}),look:lookOf(st),g:st.journey?.gender??null,x:C.at[0],y:C.at[1]});
  }
  function leave(){if(C.room||C.joining)live?.send({t:'home_out'});C.want=false;C.r='';C.scope='';C.host='';C.blocked=false;C.note='';clear();}
  function reopen(){C.blocked=false;C.note='';}
  function walk(p,ms,approaching=false){
    if(!Array.isArray(p)||p.length<2||!p.every(point))return;
    if(!approaching&&busy()){resetAction();C.note='';redraw();}
    C.at=p.at(-1).map(unit);
    if(C.room&&ok())live.send({t:'home_mv',p:p.map(q=>q.map(unit)),ms:Math.min(3000,Math.max(0,Math.round(ms)))});
  }
  function add(e){if(e.pid===C.me||!e.pid||!Number.isFinite(e.x)||!Number.isFinite(e.y))return;if(!C.people.has(e.pid)&&C.people.size>=11)return;C.people.set(e.pid,{...e,x:unit(e.x),y:unit(e.y),path:null});}
  function at(q){if(!q.path)return [q.x,q.y];const t=Math.min(1,(performance.now()-q.t0)/q.ms),p=q.path;if(t>=1||still()){q.path=null;return [q.x,q.y];}return [p[0]+(q.x-p[0])*t,p[1]+(q.y-p[1])*t];}
  function order(el,y){el.dataset.y=String(y);const next=[...el.parentNode.querySelectorAll(':scope>g.dc-it[data-y],:scope>g.dc-mate[data-y],:scope>g.hw-me[data-y],:scope>g.hc-person[data-y]')].find(g=>g!==el&&+g.dataset.y>y+2);const before=next||el.parentNode.querySelector(':scope>.dc-cats');if(before&&el.nextSibling!==before)el.parentNode.insertBefore(el,before);}
  function paint(){const root=svg();if(!root)return;for(const el of root.querySelectorAll('.hc-person')){const q=C.people.get(el.dataset.pid);if(!q)continue;const [x,y]=xy(at(q));el.style.transform=`translate(${x.toFixed(1)}px,${y.toFixed(1)}px)`;el.querySelector('.hw-fig')?.classList.toggle('walk',Boolean(q.path)&&!still());order(el,y);}}
  function animate(){if(C.raf||!globalThis.requestAnimationFrame)return;C.raf=requestAnimationFrame(()=>{C.raf=0;paint();if([...C.people.values()].some(q=>q.path))animate();});}
  const pos=pid=>pid===C.me?C.at:C.people.has(pid)?at(C.people.get(pid)):null;
  function pose(pid){
    const e=C.effect;if(!e||(!e.paired&&pid!==e.pid)||(pid!==e.pid&&pid!==e.to))return null;
    const mine=e.positions[pid],other=e.positions[pid===e.pid?e.to:e.pid];
    const dir=other[0]===mine[0]?(pid< (pid===e.pid?e.to:e.pid)?1:-1):other[0]>mine[0]?1:-1;
    const kind=pid===e.pid&&e.paired?(e.kind==='shy'?'heart':e.kind==='sulk'?'shy':e.kind):e.kind;
    return {kind,role:pid===e.pid?'send':'receive',dir,elapsed:performance.now()-e.start};
  }
  function figure(F,pid=C.me){return affectionFigure(F,pose(pid));}
  function markup(r=C.r,scope=C.scope){
    if(r!==C.r||scope!==C.scope)return '';let out='';
    for(const q of C.people.values()){let fig='';try{fig=figure(figureOf(q.lk,q.g),q.pid);}catch{}const [x,y]=xy(at(q));out+=`<g class="hc-person" data-pid="${esc(q.pid)}" data-y="${y}" aria-hidden="true" style="transform:translate(${x.toFixed(1)}px,${y.toFixed(1)}px)"><g class="hw-fig${q.path?' walk':''}"><g transform="scale(.42)">${fig}</g></g><text class="hc-name" text-anchor="middle" y="-69">${esc(q.name||'Người thương')}</text></g>`;}
    const e=C.effect;
    if(e){const a=xy(e.positions[e.pid]),b=xy(e.positions[e.to]),elapsed=performance.now()-e.start;out+=`<g class="hc-effect hc-effect-${e.kind}" aria-hidden="true" transform="translate(${a[0]},${a[1]-37})" style="--hc-flight-x:${b[0]-a[0]}px;--hc-flight-y:${b[1]-a[1]-5}px;--hc-delay:-${Math.min(POSE_MS,elapsed)}ms"><text class="hc-heart" text-anchor="middle">${e.kind==='heart'?'♥':e.kind==='hug'?'♡':e.kind==='kiss'?'♥':e.kind==='shy'?'〃':'…'}</text></g>`;}
    return out;
  }
  function panel(r=C.r,scope=C.scope){
    if(r!==C.r||scope!==C.scope)return '';
    const peers=[...C.people.values()],i=C.invite;
    const shared=state()?.marriage?.spouse;if(!peers.length&&!C.note&&!shared&&!C.host)return '';
    const status=C.note||(!ok()?'Đang mất kết nối. Mọi người sẽ gặp lại khi kết nối trở lại.':C.joining?'Đang vào nhà…':!peers.length?'Chưa có ai khác ở phòng này.':'Chọn một cử chỉ để lại gần người trong phòng.');
    const replyButton=(answer,label)=>`<button type="button" class="btn ${answer==='accept'?'primary':'ghost'} small" data-dc="hwReply" data-answer="${answer}" data-id="${esc(i.id)}"${C.pending?' disabled':''}>${label}</button>`;
    return `<section class="hc-panel" aria-label="Cùng ở nhà">${peers.map(q=>`<p>🏡 <b>${esc(q.name||'Bạn')}</b> đang ở cùng phòng</p><div class="bk-actions">${Object.entries(EMOTES).map(([kind,[emoji,label]])=>`<button type="button" class="btn ghost small" data-dc="hwEmote" data-kind="${kind}" data-to="${esc(q.pid)}" aria-label="${label} ${esc(q.name||'bạn')}"${busy()?' disabled':''}>${emoji} ${label}</button>`).join('')}</div>`).join('')}<p class="hc-status" role="status" aria-live="polite">${esc(status)}</p>${i&&(i.to===C.me||i.pid===C.me)?`<div class="hc-response bk-actions" aria-label="Trả lời cử chỉ">${i.to===C.me?replyButton('accept','Đáp lại')+replyButton('shy','☺ Ngại ngùng')+replyButton('sulk','😤 Giận dỗi')+replyButton('decline','Để sau'):replyButton('cancel','Thôi, để sau')}</div>`:''}</section>`;
  }
  function emote(kind,to){
    const q=C.people.get(to);if(!q||!EMOTES[kind]||!C.room||!ok()||busy())return;
    const room=C.room,token=++C.token;C.pending='approach';C.note=`Đang lại gần ${q.name||'người thương'} để ${EMOTES[kind][2]}…`;redraw();
    // A bounded wait also covers an interrupted walking callback or missing socket acknowledgement.
    C.waitTimer=setTimeout(()=>{if(C.token===token){resetAction();C.note='Chưa gặp được người thương. Thử lại nhé.';redraw();}},7000);
    approach(at(q),()=>{if(C.token!==token||C.room!==room||!C.people.has(to)||!ok())return;C.pending='sending';C.note='Đang chờ người thương nhận cử chỉ…';live.send({t:'home_emote',kind,to});redraw();});
  }
  function reply(answer,id){
    const i=C.invite;if(!i||i.id!==id||C.pending||!ok())return;
    if(i.to===C.me?!['accept','shy','sulk','decline'].includes(answer):answer!=='cancel')return;
    if(['accept','shy','sulk'].includes(answer)&&isWalking()){C.note='Đợi nhân vật dừng lại rồi đáp nhé.';redraw();return;}
    C.pending='reply';C.note='Đang gửi lời đáp…';live.send({t:'home_reply',id,answer});redraw();
  }
  function effect(e,paired=false){
    // A confirmed gesture follows the sender's arrival. Use the reported destination on
    // both screens instead of a network-delayed interpolation frame for its orientation.
    for(const pid of [e.pid,e.to]){const q=C.people.get(pid);if(q)q.path=null;}
    const a=pos(e.pid),b=pos(e.to);if(!a||!b)return;
    C.effect={...e,paired,start:performance.now(),positions:{[e.pid]:[...a],[e.to]:[...b]}};
    clearTimeout(C.effectTimer);C.effectTimer=setTimeout(()=>{C.effect=null;redraw();},POSE_MS);
  }
  on('home_room',f=>{if(!C.want||C.blocked||f.r!==C.r||(f.host||'')!==C.host)return;resetAction();C.room=f.room;C.me=f.me;C.joining=false;C.people.clear();C.note='';for(const p of f.people||[])add(p);redraw();});
  on('renamed',f=>{const q=C.people.get(f.pid);if(q){q.name=f.name;redraw();}});
  on('home_left',f=>{if(f.why==='out')return;clear();C.blocked=true;C.note=f.why==='other'?'Bạn đang ở nhà trong cửa sổ khác. Đóng rồi mở lại nhà để quay về đây.':'Nhà chung đã thay đổi. Đóng rồi mở lại nhà nhé.';redraw();});
  on('home',f=>{
    if(!C.room||(f.room&&f.room!==C.room))return;let changed=false;
    for(const e of f.ev||[]){
      if(e.k==='in'){add(e);changed=true;}
      else if(e.k==='out'){C.people.delete(e.pid);if(involved(e.pid)||C.pending==='approach'){resetAction();C.note='Người ấy đã rời phòng.';}changed=true;}
      else if(e.k==='mv'){
        const q=C.people.get(e.pid);if(!q||!Array.isArray(e.p)||!e.p.length||!e.p.every(point))continue;
        if(involved(e.pid)){resetAction();C.note='';changed=true;}
        const start=at(q),end=e.p.at(-1);q.x=unit(end[0]);q.y=unit(end[1]);q.path=still()||!(e.ms>0)?null:start;q.t0=performance.now();q.ms=Math.min(3000,Math.max(1,e.ms));paint();animate();
      }else if(e.k==='emote'&&EMOTES[e.kind]&&e.pid!==e.to&&(e.pid===C.me||C.people.has(e.pid))&&(e.to===C.me||C.people.has(e.to))){
        if(C.invite?.id&&C.invite.id===e.id)continue;
        resetAction();const q=C.people.get(e.pid)||C.people.get(e.to);
        C.invite=e.id?{...e}:null;effect(e);
        C.note=`${e.pid===C.me?'Bạn':q?.name||'Người thương'} ${EMOTES[e.kind][2]} ${e.to===C.me?'bạn':q?.name||'người thương'} ${EMOTES[e.kind][0]}${e.id?(e.to===C.me?' · Bạn muốn đáp lại thế nào?':' · Chờ người thương đáp lại…'):''}`;
        if(e.id)C.waitTimer=setTimeout(()=>{resetAction();C.note='Cử chỉ đã khép lại. Hai bạn có thể thử lại lúc khác.';redraw();},Math.min(20,Math.max(1,Number(e.ttl)||15))*1000);changed=true;
      }else if(e.k==='reaction'&&C.invite?.id===e.id&&e.pid===C.invite.to&&e.to===C.invite.pid&&['accept','shy','sulk'].includes(e.answer)){
        const i=C.invite;resetAction();
        effect({...i,kind:e.answer==='accept'?i.kind:e.answer},true);
        C.note=e.answer==='accept'?'Hai bạn cùng đáp lại cử chỉ 💞':e.answer==='shy'?'Ngại quá… nhưng vẫn thấy vui ☺':'Giận dỗi một chút thôi nhé 😤';changed=true;
      }else if(e.k==='ended'&&C.invite?.id===e.id){resetAction();C.note=e.why==='declined'?'Để lúc khác nhé.':e.why==='expired'?'Người thương chưa đáp lại. Để lúc khác nhé.':'Cử chỉ đã khép lại.';changed=true;}
    }
    if(changed)redraw();
  });
  on('down',f=>{clear();if(f.code===4002)C.blocked=true;C.note='Đang mất kết nối với nhà chung…';redraw();});
  on('welcome',()=>{if(C.want&&!C.blocked)join(C.r,C.at);});
  on('error',f=>{
    if(f.ref==='home_in'){C.joining=false;C.blocked=true;return;}
    if(f.ref!=='home_emote'&&f.ref!=='home_reply')return;
    // A broadcast offer supersedes our outgoing request. Its delayed rejection must
    // not erase that offer (or a reaction already confirmed by the server).
    if(C.invite||C.effect?.id){
      if(f.ref!=='home_reply'||C.pending!=='reply')return;
      C.pending=null; // Keep the authoritative offer and its original expiry for retry.
    }else resetAction();
    C.note=f.msg||f.message||'Chưa thể làm lúc này. Thử lại sau nhé.';redraw();
  });
  // Read-only render projection for the 3D view. It uses this same authorized room and capped peer map.
  function presentation(){return [...C.people.values()].map(q=>{
    if(!q.art){try{q.art=figure(figureOf(q.lk,q.g),q.pid);}catch{q.art='';}}
    return {id:q.pid,name:q.name||'Bạn',at:at(q),art:q.art,height:1.65};
  });}
  return {join,leave,reopen,walk,markup,panel,emote,reply,figure,presentation,resume:()=>{paint();animate();},dispose:()=>{leave();for(const off of subs)off();},state:()=>({room:C.room,r:C.r,me:C.me,people:[...C.people.values()].map(q=>({pid:q.pid,name:q.name,at:at(q)}))})};
}
