/** Nearby social UI. The server owns audience, permissions and acknowledgements. */
import {live} from './v4/live.js';
import {stylesheet} from './lazy.js';

const EMOTES=['👋','❤️','😂','😮','🙏','👏','👍'],REACTIONS=['❤️','😂','😮','😢','👍','🔥'];
const REASONS=[['minor','An toàn / trẻ vị thành niên'],['spam','Spam'],['rude','Thô tục'],['scam','Lừa đảo'],['private','Lộ thông tin'],['other','Khác']];
const WAIT=12000;

export function createTownSocial(envGetter,options={}){
  const socket=options.transport||live,doc=options.document||globalThis.document,
    events=options.events||globalThis.window,now=options.now||(()=>Date.now());
  const env=()=>typeof envGetter==='function'?envGetter():envGetter;
  const bubbles=new Map(),blocked=new Set(),pending=new Map(),off=[];
  let snapshot={},lastWorld=null,lastIdentity=null,stopped=false,seq=0,raf=0,expanded=false,selected=null,card=null,latestCardCid=null,nearKey='',draft='',draftEpoch=0,friendBusy=false;
  let dock,panel,input,sendButton,status,people,cardNode,toggle,layer;
  const available=()=>!stopped&&snapshot.enabled&&snapshot.active&&Boolean(snapshot.room)&&socket.state==='open'&&doc?.visibilityState!=='hidden';
  const nearby=()=>{
    const at=env()?.world?.getPresence?.();if(!at)return [];
    return (snapshot.peers||[]).filter(p=>!p.activity&&!blocked.has(p.pid)&&Math.hypot(p.x-at.x,p.y-at.y)<=8);
  };
  const eligible=pid=>pid===snapshot.me||nearby().some(p=>p.pid===pid);
  const el=(tag,key,text)=>{const n=doc.createElement(tag);if(key)n.dataset.social=key;if(text!=null)n.textContent=text;return n;};
  const button=(key,text,fn)=>{const b=el('button',key,text);b.type='button';b.addEventListener('click',fn);return b;};
  function notice(text){if(status)status.textContent=text;}
  function syncSend(){if(sendButton)sendButton.disabled=[...pending.values()].some(p=>p.kind==='town_say');}
  function transmit(kind,data={}){
    if(!available()){notice('Chưa kết nối được. Bản nháp vẫn được giữ.');return null;}
    const cid=`social-${now().toString(36)}-${++seq}`;
    pending.set(cid,{kind,...data,at:now(),epoch:draftEpoch});
    if(!socket.send({t:kind,...data,cid})){pending.delete(cid);notice('Chưa gửi được. Thử lại nhé.');return null;}
    syncSend();return cid;
  }
  function expand(value){expanded=value;panel.hidden=!value;toggle.setAttribute('aria-expanded',value);}
  function build(){
    if(dock||!doc?.createElement)return;
    stylesheet('/css/isometric-social.css');
    layer=el('div','bubbles');layer.className='town-social-bubbles';
    dock=el('section','dock');dock.className='town-social';dock.setAttribute('aria-label','Trò chuyện gần đây');
    toggle=button('toggle','💬 Nói gần đây',()=>expand(!expanded));toggle.className='town-social-toggle';toggle.setAttribute('aria-expanded','false');
    panel=el('div','panel');panel.className='town-social-panel';panel.hidden=true;
    const heading=el('div',null);heading.className='town-social-heading';heading.append(el('strong',null,'Nói gần đây'),button('close','Đóng',()=>expand(false)));
    const hint=el('p',null,'Chỉ người ở gần nghe được lời bạn.');
    const composer=el('form','composer');input=el('textarea','draft');input.rows=2;input.maxLength=240;input.placeholder='Nói gì đó… (tối đa 120 ký tự)';input.setAttribute('aria-label','Lời nói gần đây');
    input.addEventListener('input',()=>{draft=input.value;draftEpoch++;});
    sendButton=el('button','send','Gửi');sendButton.type='submit';
    composer.addEventListener('submit',e=>{e.preventDefault();if(sendButton.disabled)return;const text=draft.trim();if(!text)return;if([...text].length>120){notice('Lời nói tối đa 120 ký tự nhé.');return;}if(transmit('town_say',{text}))notice('Đang gửi…');});
    composer.append(input,sendButton);
    const emotes=el('div','emotes');emotes.className='town-social-emotes';emotes.setAttribute('aria-label','Cảm xúc cho người gần đây');
    for(const e of EMOTES){const b=button('emote-'+e,e,()=>transmit('town_emote',{e}));b.setAttribute('aria-label','Gửi '+e+' cho người gần đây');emotes.append(b);}
    status=el('p','status');status.className='town-social-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
    people=el('div','people');people.className='town-social-people';people.setAttribute('aria-label','Người ở gần');
    cardNode=el('div','card');cardNode.className='town-social-card';cardNode.hidden=true;
    panel.append(heading,hint,composer,emotes,status,el('strong',null,'Người ở gần'),people,cardNode);dock.append(toggle,panel);
    // Stop game keyboard/joystick handlers from seeing composer and menu input.
    for(const name of ['keydown','keyup','pointerdown','pointerup','click'])dock.addEventListener(name,e=>{e.stopPropagation();if(name==='keydown'&&e.key==='Escape'){expand(false);toggle.focus();}});
    doc.body.append(layer,dock);
    // 2.4.67 (owner 21/10 screenshot "cái này nó che nè"): step aside while a menu or a sheet is open — the
    // 2.5D Tiện ích / Khu phố panel (a <details open> in #isoHUD) or any open dialog — so the chip never covers a tile.
    const covered=()=>typeof doc.querySelector==='function'&&Boolean(doc.querySelector('#isoHUD details[open], dialog[open], .sheet[open]'));
    const sync=()=>{if(!dock?.classList)return;const c=covered();dock.classList.toggle('is-covered',c);if(c&&expanded)expand(false);};
    doc.addEventListener?.('toggle',sync,true);   // <details> open/close (does not bubble: capture)
    try{if(typeof MutationObserver==='function'&&doc.body)new MutationObserver(sync).observe(doc.body,{subtree:true,attributes:true,attributeFilter:['open']});}catch{/* old browsers or a test double: toggle only */}
    sync();
  }
  function drop(pid){bubbles.get(pid)?.node.remove();bubbles.delete(pid);if(!bubbles.size&&raf){events?.cancelAnimationFrame?.(raf);raf=0;}}
  function clear(){for(const pid of [...bubbles.keys()])drop(pid);pending.clear();selected=null;card=null;latestCardCid=null;friendBusy=false;nearKey='';if(cardNode){cardNode.hidden=true;cardNode.replaceChildren();}syncSend();}
  function frame(){
    raf=0;if(!available()){clear();return;}
    const w=env()?.world,rect=w?.canvas?.getBoundingClientRect?.();
    for(const [pid,b] of bubbles){
      if(now()>=b.until||!eligible(pid)){drop(pid);continue;}
      const point=w?.getSocialAnchor?.(pid===snapshot.me?null:pid);
      const visible=point&&Number.isFinite(point.x)&&Number.isFinite(point.y)&&(!rect||(point.x>=rect.left&&point.x<=rect.right&&point.y>=rect.top&&point.y<=rect.bottom));
      b.node.hidden=!visible;if(visible){b.node.style.left=`${point.x}px`;b.node.style.top=`${point.y}px`;}
    }
    if(bubbles.size)raf=events?.requestAnimationFrame?.(frame)||0;
  }
  function drawBubble(f,isEmote=false){
    if(!available()||f.room!==snapshot.room||typeof f.pid!=='string'||!eligible(f.pid)||blocked.has(f.pid))return;
    if(isEmote?!EMOTES.includes(f.e):typeof f.text!=='string'||!f.id||typeof f.ch!=='string'||!f.ch.startsWith('iso-talk:'))return;
    drop(f.pid);const node=el('div','bubble-'+f.pid);node.className='town-social-bubble'+(isEmote?' town-social-bubble-emote':'');
    const author=f.pid===snapshot.me?'Bạn':String(f.name||snapshot.peers?.find(p=>p.pid===f.pid)?.name||'Người chơi').slice(0,24);
    const recipient=f.target===snapshot.me?'Bạn':String(snapshot.peers?.find(p=>p.pid===f.target)?.name||'Người ở gần').slice(0,24);
    node.append(el('strong',null,isEmote&&f.target?`${author} → ${recipient}`:author),el('span',null,isEmote?f.e:f.text));
    const bubble={...f,node,until:now()+(isEmote?3000:6000),isEmote};
    if(!isEmote){
      const actions=el('div','reactions-'+f.pid);actions.className='town-social-bubble-actions';
      for(const e of REACTIONS){const b=button(null,e,()=>transmit('react',{id:f.id,e}));b.setAttribute('aria-label','Thả '+e+' cho lời nói');actions.append(b);}
      const counts=el('span','counts-'+f.pid);counts.className='town-social-counts';node.append(actions,counts);bubble.counts=counts;
    }
    bubbles.set(f.pid,bubble);layer?.append(node);if(!raf)frame();if(selected===f.pid&&card)renderCard();
  }
  function refreshPeople(){
    if(!people)return;const list=nearby(),key=JSON.stringify(list.map(p=>[p.pid,p.name]));
    if(selected&&!list.some(p=>p.pid===selected)){selected=null;card=null;latestCardCid=null;cardNode.hidden=true;}
    if(key===nearKey)return;nearKey=key;people.replaceChildren();
    for(const p of list)people.append(button('peer-'+p.pid,p.name||'Người chơi',()=>choose(p.pid)));
    if(!list.length)people.append(el('span',null,'Chưa có ai ở gần. Đi lại gần để chào nhé.'));
  }
  function choose(pid){
    if(!available()||!nearby().some(p=>p.pid===pid))return;
    selected=pid;card=null;friendBusy=false;expand(true);cardNode.hidden=false;cardNode.replaceChildren(el('p',null,'Đang xem người bạn này…'));
    latestCardCid=transmit('town_card',{pid});if(!latestCardCid)cardNode.hidden=true;
  }
  function renderCard(){
    if(!card||card.pid!==selected)return;cardNode.replaceChildren();cardNode.hidden=false;
    cardNode.append(el('strong',null,card.name||'Người chơi'));
    if(card.friend&&typeof card.rel?.name==='string')cardNode.append(el('small','rel',`${typeof card.rel.emoji==='string'?card.rel.emoji:'💞'} ${card.rel.name}`.slice(0,40)));   // 💞 the relationship the two set (game/friend_charms.py)
    cardNode.append(button('greet','👋 Chào',()=>transmit('town_emote',{e:'👋',target:selected})));
    const emotes=el('div',null);emotes.className='town-social-emotes';
    for(const e of EMOTES.slice(1)){const b=button(null,e,()=>transmit('town_emote',{e,target:selected}));b.setAttribute('aria-label','Gửi '+e+' cho '+card.name);emotes.append(b);}cardNode.append(emotes);
    if(card.friend)cardNode.append(button('dm','Nhắn riêng',async()=>{const pid=selected;try{const chat=await import('./v4/chat.js');if(!available()||selected!==pid||!card?.friend)return;expand(false);await chat.openChat(env(),{ch:`dm:${[snapshot.me,pid].sort().join(':')}`});}catch{notice('Chưa mở được tin nhắn. Thử lại nhé.');}}));
    else if(card.code&&card.account)cardNode.append(button('friend',friendBusy?'Đang gửi…':'Kết bạn',async()=>{
      if(friendBusy||!available())return;const pid=selected,api=env()?.api,identity=lastIdentity,cid=latestCardCid;
      const current=()=>available()&&lastIdentity===identity&&selected===pid&&latestCardCid===cid;
      friendBusy=true;renderCard();
      try{const result=await api.json('/api/marriage/friend_request',{method:'POST',headers:{'Content-Type':'application/json','X-Game-CSRF':api.csrf},body:JSON.stringify({code:card.code})});if(current())notice(result.message||'Đã gửi lời mời kết bạn.');if(available()&&lastIdentity===identity)socket.send({t:'sync'});}catch(e){if(current())notice(e.message||'Chưa gửi được lời mời.');}finally{if(current()){friendBusy=false;renderCard();}}
    }));
    if(socket.flags?.blocks)cardNode.append(button('block','Chặn người này',()=>{transmit('block',{pid:selected});}));
    const speech=bubbles.get(selected);
    if(speech&&!speech.isEmote)cardNode.append(button('report','Báo cáo lời nói',()=>{
      const reasons=el('div',null);reasons.className='town-social-report';for(const [reason,label] of REASONS)reasons.append(button(null,label,()=>{if(bubbles.get(selected)?.id===speech.id&&transmit('report',{id:speech.id,reason}))notice('Đang gửi báo cáo…');}));cardNode.append(reasons);
    }));
  }
  function update(value){
    if(stopped)return;const changed=snapshot.room!==value.room||snapshot.me!==value.me||lastWorld!==env()?.world;
    if(value.me&&value.me!==lastIdentity){
      if(lastIdentity!==null){blocked.clear();draft='';draftEpoch++;if(input)input.value='';notice('');}
      lastIdentity=value.me;
    }
    if(changed)clear();snapshot=value;lastWorld=env()?.world;
    if(!available()){clear();if(dock){dock.hidden=true;expand(false);}return;}
    build();dock.hidden=false;syncSend();refreshPeople();
    for(const [cid,p] of pending)if(now()-p.at>=WAIT){pending.delete(cid);if(p.kind==='town_card'&&cid!==latestCardCid)continue;notice(p.kind==='town_say'?'Chưa nhận xác nhận. Bản nháp vẫn còn; hãy kiểm tra trước khi gửi lại.':'Chưa nhận xác nhận. Thử lại khi kết nối ổn định.');if(p.kind==='town_card'){latestCardCid=null;card=null;cardNode.hidden=true;}}
    syncSend();for(const [pid,b] of bubbles)if(!eligible(pid)||now()>=b.until)drop(pid);
  }
  function acknowledge(f,kind){const p=pending.get(f.cid);if(!p||p.kind!==kind)return null;pending.delete(f.cid);syncSend();return p;}
  off.push(socket.on('town_said',f=>{if(f.room!==snapshot.room)return;const p=acknowledge(f,'town_say');if(p&&f.pid===snapshot.me){if(draftEpoch===p.epoch){draft='';input.value='';}notice('Đã nói với người ở gần.');}drawBubble(f);}),
    socket.on('town_emoted',f=>{if(f.room!==snapshot.room)return;acknowledge(f,'town_emote');drawBubble(f,true);}),
    socket.on('town_card',f=>{const p=acknowledge(f,'town_card');if(!p||f.cid!==latestCardCid||f.pid!==p.pid||f.pid!==selected||f.room!==snapshot.room||!eligible(f.pid)||!available())return;card=f;renderCard();}),
    socket.on('reacts',f=>{for(const b of bubbles.values())if(!b.isEmote&&b.id===f.id&&b.ch===f.ch){const r=f.r&&typeof f.r==='object'?f.r:{};b.counts.textContent=Object.entries(r).filter(([e,n])=>REACTIONS.includes(e)&&Number.isFinite(n)&&n>0).map(([e,n])=>`${e} ${n}`).join(' · ');}for(const [cid,p] of pending)if(p.kind==='react'&&p.id===f.id)pending.delete(cid);}),
    socket.on('error',f=>{const p=pending.get(f.ref);if(!p)return;pending.delete(f.ref);syncSend();if(p.kind==='town_card'&&f.ref!==latestCardCid)return;notice(f.msg||f.message||'Chưa thực hiện được. Thử lại nhé.');if(p.kind==='town_card'){latestCardCid=null;card=null;cardNode.hidden=true;}}),
    socket.on('blocked',f=>{if(f.on){blocked.add(f.pid);drop(f.pid);if(selected===f.pid){selected=null;card=null;if(cardNode)cardNode.hidden=true;}}else blocked.delete(f.pid);for(const [cid,p] of pending)if(p.kind==='block'&&p.pid===f.pid)pending.delete(cid);refreshPeople();}),
    socket.on('reply_hidden',f=>{blocked.add(f.pid);drop(f.pid);refreshPeople();if(selected===f.pid){card=null;selected=null;if(cardNode)cardNode.hidden=true;}}),
    socket.on('reported',f=>{let matched=false;for(const [cid,p] of pending)if(p.kind==='report'&&(!f.id||f.id===p.id)){pending.delete(cid);matched=true;}if(matched)notice('Đã gửi báo cáo đến ban quản lý.');}),
    ...['deleted','hid'].map(t=>socket.on(t,f=>{for(const [pid,b] of bubbles)if(b.id===f.id&&(!f.ch||f.ch===b.ch))drop(pid);if(card)renderCard();})),
    ...['down','welcome'].map(t=>socket.on(t,()=>{clear();snapshot={};if(dock){dock.hidden=true;expand(false);}notice('Kết nối đã thay đổi. Bản nháp vẫn được giữ.');})));
  const onPeer=e=>choose(e.detail?.pid),onVisibility=()=>{if(doc.visibilityState==='hidden'){clear();if(dock){dock.hidden=true;expand(false);}}};
  events?.addEventListener?.('mnl:town-peer',onPeer);doc?.addEventListener?.('visibilitychange',onVisibility);
  return {update,stop(){if(stopped)return;stopped=true;clear();for(const fn of off)fn?.();events?.removeEventListener?.('mnl:town-peer',onPeer);doc?.removeEventListener?.('visibilitychange',onVisibility);dock?.remove();layer?.remove();}};
}

