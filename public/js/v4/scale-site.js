import {lookOf} from './look.js';
import {createSitePresence,createSiteBubbles} from './site-presence.js';

/** Owned sites reuse the game's collision-tested isometric walking room. */
const PROP={laundry:'machine',homestay:'bed',salon:'chair',nail:'table',photobooth:'screen',art_studio:'easel',
  library:'shelf',grocery:'counter',clothing:'shelf',pet_care:'play',farm:'flowerbed',pagoda:'bench'};
const OFFICE=new Set(['accounting','lawyer','tax_payroll','corp_accounting','group_accounting','hr_admin','secretary','it_helpdesk','police','rescue','post_office','customs']);

export function scaleRoom(scale,site){
  const resources=(scale.resources||[]).filter(r=>r.site===site.id),props=[],stations=[],actors=[];
  const room={id:`scale:${scale.cid}:${site.id}`,title:site.name,width:460,height:360,entry:{x:230,y:325},
    outdoor:scale.cid==='farm',floor:'#e9d2ad',wall:'#f3e6cc',accent:'#986a47',props,stations,actors};
  const kind=PROP[scale.cid]||(OFFICE.has(scale.cid)?'table':'counter');
  const cells=Array.from({length:6},(_,i)=>({x:70+i%3*145,y:95+Math.floor(i/3)*110}));
  // A zone may represent several preserved legacy resources, with all IDs shown
  // at its station; activating scale never deletes a larger existing workplace.
  for(let i=0;i<Math.min(6,resources.length);i++){
    const group=resources.filter((_,n)=>n%6===i),r=group[0],at=cells[i];
    props.push({kind,x:at.x-25,y:at.y-(kind==='bed'?77:48),w:50,h:kind==='bed'?65:32,colour:r.busy?'#bc8c77':'#a7b598'});
    const label=group.length===1?(r.label||`${scale.resource_name} ${i+1}`):`${group.length} ${scale.resource_name}`;
    stations.push({id:r.id,site:site.id,resources:group.map(x=>x.id),label,...at,
      detail:group.map(x=>`${x.label||x.id}${x.crew_name?` · ${x.crew_name}`:''}${x.busy?' · Đang vận hành':''}`).join('; ')});
    for(const [j,unit] of group.entries())if(unit.crew_name)actors.push({id:unit.id,name:unit.crew_name,x:at.x+35+(j%2)*13,y:at.y-24,colour:'#8e9cab'});
  }
  props.push({kind:'shelf',x:20,y:265,w:65,h:25,colour:'#a17d59'},{kind:'table',x:350,y:260,w:65,h:25,colour:'#bd9c7a'});
  stations.push({id:'stock',site:site.id,label:OFFICE.has(scale.cid)?'Tài liệu và vật tư':'Kho cơ sở',x:105,y:290,detail:'Kiểm vật tư và phiếu điều chuyển của cơ sở này.'},
    {id:'management',site:site.id,label:'Bàn điều phối',x:330,y:300,detail:'Xem hợp đồng, lịch tài nguyên và biên nhận.'});
  return room;
}

let currentVisit=null,visitSequence=0;
export function parseScaleSiteCode(code){
  const match=/^([0-9a-f]{16}):([a-z_]{1,40}):(base|branch-[1-9][0-9]?)$/.exec(String(code||'').trim());
  if(!match)throw new Error('Mã cơ sở không hợp lệ. Dán đầy đủ mã chủ cơ sở đã chia sẻ.');
  return {owner:match[1],career:match[2],site:match[3]};
}
export async function openScaleSiteGuest(env,code){
  try{return await visitScaleSite(env,parseScaleSiteCode(code));}
  catch(error){env.toast(error.message,true);return null;}
}
export async function openScaleSite(env,siteId){
  const {live}=await import('./live.js');
  const cid=env.api.state.current;
  if(!env.api.state.careers?.[cid]?.scale?.sites?.some(s=>s.id===siteId)){env.toast('Cơ sở đã thay đổi. Mở lại bảng mở rộng nhé.',true);return null;}
  if(!live.me?.pid){env.toast('Đang kết nối cơ sở trực tuyến. Hãy thử lại sau.',true);return null;}
  return openScaleSiteGuest(env,`${live.me.pid}:${cid}:${siteId}`);
}
async function visitScaleSite(env,key){
  const {live}=await import('./live.js');
  if(env.api.state?.jail){await env.act('jail');return null;}
  const request=++visitSequence;currentVisit?.close();currentVisit=null;
  let view=null,people=[],socialStatus='Đang vào cơ sở…',room=null,log=null,nearList=null,statusNode=null;
  const owned=key.owner===live.me?.pid;
  const bubbles=createSiteBubbles({wake:()=>view?.wake()});
  const refreshNearby=()=>{
    if(!nearList||!view)return;
    const selected=nearList.value,near=people.filter(p=>Math.hypot(p.x-view.scene.state.x,p.y-view.scene.state.y)<=160);
    const signature=near.map(p=>p.pid+':'+p.name).join('|');if(nearList.dataset.people===signature)return;
    nearList.dataset.people=signature;nearList.replaceChildren(new Option('Mọi người ở gần',''));
    for(const p of near)nearList.add(new Option(p.name,p.pid));if(near.some(p=>p.pid===selected))nearList.value=selected;
  };
  const append=text=>{if(!log)return;const line=document.createElement('div');line.textContent=text;log.append(line);while(log.children.length>20)log.firstChild.remove();log.scrollTop=log.scrollHeight;};
  const session=createSitePresence(key,{transport:live,appearance:()=>({look:lookOf(env.api.state),g:env.api.state.journey?.gender}),
    onJoin:f=>{if(room){const next=scaleRoom({...f.layout,resource_name:'Vị trí'},f.site);Object.assign(room,next);view?.refreshLayout();if(view)view.element.querySelector('.venue-free').textContent=f.site.public?'Đang đón khách':'Riêng tư';}},
    onReset:()=>bubbles.clear(),
    onPeers:p=>{people=p;bubbles.retain(new Set([live.me?.pid,...p.map(peer=>peer.pid)]));view?.wake();refreshNearby();},
    onCorrect:p=>{if(view){view.scene.reset();Object.assign(view.scene.state,p);view.wake();}},
    onStatus:text=>{socialStatus=text;if(statusNode)statusNode.textContent=text;},
    onMessage:f=>{if(f.t==='town_said'||f.t==='town_emoted')bubbles.show(f.pid,f.t==='town_said'?f.text:f.e);const name=f.pid===live.me?.pid?'Bạn':people.find(p=>p.pid===f.pid)?.name||f.name||'Người chơi';
      if(f.t==='town_said')append(`${name}: ${f.text}`);
      else if(f.t==='town_emoted')append(`${name} ${f.e}${f.target?' → '+(people.find(p=>p.pid===f.target)?.name||'Bạn'):''}`);
      else append(`${f.name}${f.friend?' · Bạn bè':f.code?' · Mã kết bạn: '+f.code:''}`);},
    onClose:why=>{view?.close();if(why==='private'||why==='other')env.toast(why==='private'?'Cơ sở đã đóng cửa đón khách.':'Cơ sở đang mở ở tab khác.',true);}});
  currentVisit=session;
  const frame=await session.start();if(request!==visitSequence){session.close();return null;}
  const {openVenue}=await import('./venue-visit.js');
  if(session.destroyed)return null;
  room=scaleRoom({...frame.layout,resource_name:'Vị trí'},frame.site);
  view=await openVenue({...env,getPeers:()=>people,getBubbles:()=>bubbles.get().flatMap(b=>{const p=b.pid===live.me?.pid?view?.scene.state:people.find(p=>p.pid===b.pid);return p?[{...b,x:p.x,y:p.y}]:[];}),onMove:point=>{session.move(point);refreshNearby();},
    onClose:()=>{session.close();if(currentVisit===session)currentVisit=null;env.onClose?.();},
    onInteract:async station=>{
      if(!owned){append(station.detail);return;}
      const current=env.api.state.careers?.[key.career]?.scale;
      if(env.api.state.current!==key.career||!current?.sites?.some(s=>s.id===station.site))throw new Error('Bạn đã đổi cơ sở.');
      env.ui.scaleSite=station.site;
      await new Promise(resolve=>{env.openSheet('promo');const dialog=document.getElementById('sheet');if(!dialog){resolve();return;}dialog.addEventListener('close',resolve,{once:true});});
    }},{id:'scale',title:frame.site.name,layout:room,eyebrow:owned?'CƠ SỞ CỦA BẠN':'GHÉ THĂM CƠ SỞ',badge:frame.site.public?'Đang đón khách':'Riêng tư'});
  if(!view){session.close();return null;}
  if(session.destroyed){view.close();return null;}
  const panel=document.createElement('section');panel.className='scale-site-social';panel.style.cssText='padding:12px 20px;display:grid;gap:8px;flex-shrink:0';
  panel.setAttribute('aria-label','Trò chuyện tại cơ sở');
  panel.innerHTML='<style>.scale-site-social button,.scale-site-social input,.scale-site-social select{font:inherit;font-size:13px;border:1px solid #cdbfa9;border-radius:8px;background:#fff9ef;color:#494f43;min-height:44px;padding:7px 10px}.scale-site-social button{cursor:pointer}.scale-site-social label{font-size:12px}.scale-site-social [role=log]{padding:5px;background:#ffffff55;border-radius:8px}.scale-site-social .site-reactions{flex-wrap:wrap}</style><p role="status" style="margin:0;font-size:12px"></p><label>Mã cơ sở <input class="site-code" readonly aria-label="Mã cơ sở để chia sẻ" style="width:100%"></label><div style="display:flex;gap:6px"><button type="button" class="site-copy">Sao chép mã</button><select aria-label="Người ở gần" style="min-width:0;flex:1"></select><button type="button" class="site-card">Xem bạn</button></div><div role="log" aria-live="polite" style="max-height:72px;overflow:auto;font-size:13px"></div><form style="display:flex;gap:6px"><input maxlength="120" aria-label="Lời nhắn trong cơ sở" placeholder="Nói với người ở gần…" style="min-width:0;flex:1"><button>Gửi</button></form><div class="site-reactions" style="display:flex;gap:8px"></div>';
  statusNode=panel.querySelector('[role=status]');statusNode.textContent=socialStatus;
  const codeInput=panel.querySelector('.site-code');codeInput.value=`${key.owner}:${key.career}:${key.site}`;
  codeInput.onclick=()=>codeInput.select();panel.querySelector('.site-copy').onclick=async()=>{codeInput.select();try{await navigator.clipboard.writeText(codeInput.value);statusNode.textContent='Đã sao chép mã cơ sở.';}catch{statusNode.textContent='Mã đã được chọn. Giữ để sao chép.';}};
  log=panel.querySelector('[role=log]');nearList=panel.querySelector('select');nearList.add(new Option('Mọi người ở gần',''));refreshNearby();
  panel.querySelector('.site-card').onclick=()=>{if(nearList.value)session.card(nearList.value);else statusNode.textContent='Chọn một người đang ở gần.';};
  panel.querySelector('form').onsubmit=e=>{e.preventDefault();const input=e.currentTarget.querySelector('input');if(input.value.trim()){session.say(input.value.trim());input.value='';}};
  for(const emoji of ['👋','❤️','😂','😮','🙏','👏','👍']){const button=document.createElement('button');button.type='button';button.textContent=emoji;button.setAttribute('aria-label',`Thả biểu cảm ${emoji}`);button.style.cssText='min-width:44px;min-height:44px';button.onclick=()=>session.emote(emoji,nearList.value);panel.querySelector('.site-reactions').append(button);}
  view.element.append(panel);view.wake();return view;
}
