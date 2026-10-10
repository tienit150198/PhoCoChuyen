/** A separate public workplace visit. Local career state and minigame drafts stay with their owner. */
import {escapeHTML as esc,icon} from '../icons.js';
import {stylesheet} from '../lazy.js';
import {T,isShop} from './terms.js';
import {avInner} from './face.js';
import {createQuayPoller,focusSnapshot,restoreInputFocus} from './quay-business-ui.js';
import {applyVisitEvent,ORDER_STATUS,REVIEW_TAGS,preserveVisitDraft,visitControlId,createVisitSettlementSync,visitSubtitle} from './workplace-visit-ui.js';
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
/** The visited place's career words (v4/terms.js): a quầy is a stall, so it keeps the shop words. */
const careerOf=x=>x?.kind==='quay'?'':(x?.target||x?.career||'');
const vt=(x,key)=>T(careerOf(x),key),shop=x=>isShop(careerOf(x));
const S={dlg:null,env:null,owner:'',scope:'friends',places:[],place:null,orders:[],reviews:[],inbox:null,tab:'places',busy:false,loading:false,error:'',drafts:{},offer:'',people:[],messages:[],activity:null,livePlace:null,me:null,off:[],seq:0};
const button=(label,act,attrs='',style='')=>`<button type="button" id="${visitControlId(act,attrs)}" class="btn ${style}" data-wv="${act}" ${attrs}${S.busy?' disabled':''}>${label}</button>`;
const apiGet=(name,query={})=>S.env.api.json('/api/work-visits/'+name+'?'+new URLSearchParams(Object.entries(query).filter(([,v])=>v!==''&&v!=null)));
const draft=id=>S.drafts[id]??={note:'',stars:5,tags:[],comment:'',chat:''};
const ownerFace=p=>avInner({fc:p?.fc,av:p?.av||p?.avatar||'🙂'});
function leaveRoom(send=true){if(send&&S.livePlace)S.env?.live?.()?.send({t:'visit_out'});S.livePlace=null;S.people=[];S.messages=[];S.activity=null;S.me=null;}
function joinRoom(){const live=S.env.live?.();if(!S.place||!live||(live.state!=='open'||!live.flags?.visits))return;if(S.livePlace!==S.place.id){leaveRoom();S.livePlace=S.place.id;live.send({t:'visit_in',place:S.place.id});}}
function cleanup(){S.seq++;S.poller?.stop();leaveRoom();S.off.splice(0).forEach(fn=>fn());document.removeEventListener('visibilitychange',visible);S.env?.api?.removeEventListener('state',ownState);O.joined=false;O.nextOrders=0;ownerJoin();renderOwner();O.refresh?.().catch(()=>{});}
function visible(){if(!document.hidden){if(S.livePlace){S.env.live?.()?.send({t:'visit_in',place:S.livePlace});}refresh();}}
function ownState(){/* Own state changes never overwrite the public visit projection or its drafts. */}
function bindLive(){const live=S.env.live?.();if(!live)return;for(const type of ['visit_state','visit_people','visit_mv','visit_emote','visit_chat','visit_activity'])S.off.push(live.on(type,event=>{const room={place:S.livePlace,people:S.people,messages:S.messages,activity:S.activity,me:S.me};if(applyVisitEvent(room,{...event,t:type})){Object.assign(S,{people:room.people,messages:room.messages,activity:room.activity,me:room.me});render();}}));S.off.push(live.on('welcome',()=>{S.livePlace=null;joinRoom();}));S.off.push(live.on('visit_left',event=>{if(event.place!==S.livePlace)return;leaveRoom(false);S.error='Bạn đã rời phòng trực tiếp. Quyền ghé thăm có thể vừa thay đổi.';render();}));}
export async function openWorkplaceVisit(env,data={}){
 await stylesheet('/css/workplace-visit.css');
 if(S.dlg?.open){await new Promise(resolve=>{S.dlg.addEventListener('close',resolve,{once:true});S.dlg.close();});}
 const account=env.api.account?.username||'';if(S.account!==account){S.drafts={};S.account=account;}
 S.env=env;if(O.joined)env.live?.()?.send({t:'visit_out'});O.joined=false;S.owner=data.code||data.pid||'';S.scope=data.scope||'friends';S.career=data.career||'';S.tab=data.inbox?'orders':'places';S.place=null;S.places=[];S.inbox=null;S.error='';S.busy=false;S.loading=true;S.offer='';S.seq++;
 if(!S.dlg){const d=document.createElement('dialog');d.className='wv-dialog';d.setAttribute('aria-labelledby','wv-title');document.body.append(d);S.dlg=d;d.addEventListener('close',cleanup);d.addEventListener('click',e=>{const b=e.target.closest('[data-wv]');if(b)action(b.dataset.wv,b.dataset);});d.addEventListener('input',input);d.addEventListener('change',input);d.addEventListener('submit',e=>{if(e.target.matches('[data-wv-chat]')){e.preventDefault();action('chat',{});}});d.addEventListener('keydown',e=>{if(e.target.matches('.wv-floor')&&['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const me=S.people.find(p=>p.pid===S.me)||{x:.5,y:.72};move(me.x+(e.key==='ArrowRight'?.08:e.key==='ArrowLeft'?-.08:0),me.y+(e.key==='ArrowDown'?.08:e.key==='ArrowUp'?-.08:0));}});}
 bindLive();document.addEventListener('visibilitychange',visible);render();S.dlg.showModal();S.dlg.scrollTop=0;renderOwner();
 S.poller??=createQuayPoller({active:()=>Boolean(S.dlg?.open&&!document.hidden&&!S.busy&&!S.loading),refresh:()=>refresh(),failed:failed=>{if(failed){S.error='Chưa kết nối được. Các đơn và bản nháp vẫn được giữ.';render();}}});S.poller.start();
 if(data.place)await openPlace(data.place);else await refresh();
}
export async function workplaceVisitAction(action,data,el,env){if(action!=='workVisit')return false;await openWorkplaceVisit(env,data);return true;}
async function refresh(){const seq=S.seq;S.loading=true;try{if(S.tab==='orders'){const d=await apiGet('orders');if(seq!==S.seq)return;S.inbox=d;await ownerOrders(d,S.env);}else if(S.place){const d=await apiGet('place',{place:S.place.id});if(seq!==S.seq)return;S.place=d.place;S.orders=d.orders||[];S.reviews=d.reviews||[];joinRoom();}else{const d=await apiGet('places',{scope:S.scope,owner:S.owner,career:S.career});if(seq!==S.seq)return;S.places=d.places||[];S.next=d.next||null;}S.error='';}catch(e){if(seq===S.seq)S.error=e.message||'Chưa tải được chỗ làm. Thử lại nhé.';}finally{if(seq===S.seq){S.loading=false;render();}}}
async function openPlace(id){S.seq++;leaveRoom();S.place={id};S.orders=[];S.reviews=[];S.tab='places';S.offer='';render();await refresh();}
async function post(route,body){if(S.busy)return null;const seq=S.seq,api=S.env.api;S.busy=true;render();try{const r=await api.post('/api/work-visits/'+route,body);await api.refresh().catch(()=>{});if(seq===S.seq){S.error='';await refresh();}return r;}catch(e){if(seq===S.seq)S.error=e.message||'Chưa gửi được. Bạn có thể thử lại.';return null;}finally{if(seq===S.seq){S.busy=false;render();}}}
function input(e){const el=e.target;if(!el.dataset.wvField)return;const d=draft(el.dataset.key||S.place?.id||'room');if(el.dataset.wvField==='tag'){d.tags=el.checked?[...new Set([...d.tags,el.value])]:d.tags.filter(t=>t!==el.value);}else if(el.dataset.wvField==='stars')d.stars=Number(el.value);else d[el.dataset.wvField]=el.value;}
function move(x,y){const me=S.people.find(p=>p.pid===S.me)||{x:.5,y:.72};S.env.live?.()?.send({t:'visit_mv',p:[[me.x,me.y],[Math.min(.94,Math.max(.06,x)),Math.min(.94,Math.max(.06,y))]],ms:450});}
async function action(act,data){if(act==='close'){S.dlg.close();return;}if(S.busy)return;
 if(act==='place'){await openPlace(data.id);return;}
 if(act==='floor'){/* Keyboard and the three floor targets offer the same movement. */move(Number(data.x||.5),Number(data.y||.72));return;}
 if(act==='emote'){S.env.live?.()?.send({t:'visit_emote',kind:data.kind});return;}
 if(act==='chat'){const d=draft(S.place.id);if(d.chat?.trim()&&S.env.live?.()?.send({t:'visit_chat',text:d.chat.trim()})){d.chat='';render();}return;}
 if(act==='back'||act==='scope'||act==='orders'){S.seq++;leaveRoom();S.place=null;S.tab=act==='orders'?'orders':'places';if(act==='scope'){S.scope=data.scope;S.owner='';}await refresh();return;}
 if(act==='more'){if(!S.next)return;const seq=S.seq;S.busy=true;render();try{const d=await apiGet('places',{scope:S.scope,owner:S.owner,offset:S.next});if(seq===S.seq){S.places=[...S.places,...(d.places||[]).filter(p=>!S.places.some(x=>x.id===p.id))];S.next=d.next||null;}}catch(e){if(seq===S.seq)S.error=e.message;}finally{if(seq===S.seq){S.busy=false;render();}}return;}
 if(act==='retry'){await refresh();return;}
 if(act==='offer'){S.offer=data.id;render();return;}
 if(act==='order'){const offer=S.place.offers?.find(o=>o.offer_id===S.offer);if(!offer)return;const d=draft(S.place.id);if(await S.env.confirmAction('Làm khách tại '+S.place.name+'?',`${offer.label} · ${fmt(offer.price)} xu. Xu được giữ cho đơn dịch vụ này.`, 'Đặt dịch vụ')){const fingerprint=JSON.stringify([offer.offer_id,offer.price,d.note]);if(d.fingerprint!==fingerprint){d.rid=crypto.randomUUID();d.fingerprint=fingerprint;}const r=await post('order',{place:S.place.id,offer_id:offer.offer_id,qty:1,note:d.note,rid:d.rid,expected_price:offer.price});if(r){d.rid=null;d.fingerprint=null;S.offer='';render();}}return;}
 if(act==='visibility'){await post('visibility',{place:S.place.id,visibility:data.value});return;}
 if(['accept','decline','cancel'].includes(act)){await post(act,{order:data.id});return;}
 if(act==='receive'){await post('receive',{order:data.id});return;}
 if(act==='reply'){await post('reply',{order:data.id,text:draft(data.id).reply||''});return;}
 if(act==='review'){const d=preserveVisitDraft(draft(data.id));await post('review',{order:data.id,stars:d.stars,tags:d.tags,comment:d.comment});return;}
 if(act==='serve'){S.dlg.close();await S.env.act('workVisitServe',{career:data.career,task:data.task,kind:data.kind,place:data.place,order:data.id});return;}
}
function render(){if(!S.dlg)return;const top=S.dlg.scrollTop,focus=focusSnapshot(document.activeElement);S.dlg.innerHTML=`<header class="wv-head">${S.place?button(icon('back',20),'back','aria-label="Quay lại"','ghost icon-btn'):''}<div><span class="eyebrow">GHÉ NHAU MỘT CHÚT</span><h2 id="wv-title">${esc(S.place?.name||'Chỗ làm quanh phố')}</h2><p>${visitSubtitle(S.place)}</p></div>${button(icon('x',20),'close','aria-label="Đóng"','ghost icon-btn')}</header><main class="wv-body">${S.error?`<p class="wv-error" role="status">${esc(S.error)} ${button('Thử lại','retry','','small ghost')}</p>`:''}${S.place?placeView():`<nav class="wv-nav">${[['friends','Bạn bè'],['public','Mọi người'],['mine','Chỗ của tôi']].map(([id,label])=>button(label,'scope',`data-scope="${id}" aria-pressed="${S.tab==='places'&&S.scope===id}"`,S.scope===id&&S.tab==='places'?'primary':'ghost')).join('')}${button('Đơn của tôi','orders',`aria-pressed="${S.tab==='orders'}"`,S.tab==='orders'?'primary':'ghost')}</nav>${S.tab==='orders'?inboxView():placesView()}`}</main>`;S.dlg.scrollTop=top;if(focus?.id&&S.dlg.querySelector(`[id="${focus.id}"]`))restoreInputFocus(S.dlg,focus);}
function placesView(){return `<div class="wv-intro"><span>🏘️</span><h3>${S.owner?'Chọn chỗ làm muốn ghé':S.scope==='public'?'Mọi người đang làm gì?':S.scope==='mine'?'Đón khách theo cách của bạn':'Hôm nay ghé ai nhỉ?'}</h3><p>${S.scope==='mine'?'Chọn nơi làm để đặt quyền ghé thăm và xem khách.':'Chọn một chỗ làm để xem bạn ấy đang làm gì.'}</p></div>${S.loading&&!S.places.length?'<p role="status">Đang tìm những cánh cửa đang mở…</p>':S.places.length?`<div class="wv-places">${S.places.map(p=>`<article class="wv-place"><div class="wv-person">${ownerFace(p.owner)}<div><h3>${esc(p.name)}</h3><p>${esc(p.owner?.name||'')} · ${p.kind==='quay'?'Quầy riêng':'Nghề hiện tại'}</p></div></div><p class="wv-place-status">${esc(p.reason||p.activity?.label||'Ghé xem dịch vụ và tình hình tiệm')}</p>${button(p.mine?'Xem chỗ của tôi':'Ghé chỗ làm','place',`data-id="${esc(p.id)}"`,'primary full')}</article>`).join('')}</div>${S.next?button('Xem thêm chỗ làm','more','','ghost full'):''}`:'<p class="wv-empty">Chưa có chỗ làm có thể ghé ở đây. Bạn có thể xem Mọi người quanh phố.</p>'}`;}
function scene(){const p=S.place,people=S.people,online=S.env.live?.()?.state==='open'&&S.env.live?.()?.flags?.visits,a=S.activity?.activity||S.activity||p.activity||{};return `<section class="wv-scene" aria-label="Không gian ghé chỗ làm"><div class="wv-window"></div><div class="wv-shelf">🪴<br>📚</div><div class="wv-sign">${esc(p.name)}</div><div class="wv-host"><span class="wv-avatar">${ownerFace(p.owner)}</span><strong>${esc(p.owner?.name||vt(p,'host'))}</strong><small>${esc(a.label||a.step||p.reason||'Chỗ làm của người chơi')}</small></div><div class="wv-counter"><span>${esc(p.kind==='quay'?'🧋':S.env.api.content?.catalogue?.find(c=>c.id===p.target)?.emoji||'🛠️')}</span><b>${esc(p.kind==='quay'?'QUẦY ĐÓN KHÁCH':S.env.api.content?.catalogue?.find(c=>c.id===p.target)?.short||'GÓC LÀM VIỆC')}</b><span>📋</span></div><div class="wv-floor" tabindex="0" role="group" aria-label="Chỗ đứng của bạn. Dùng phím mũi tên để di chuyển.">${people.map(w=>`<div class="wv-visitor${w.pid===S.me?' me':''}" style="left:${w.x*100}%;top:${w.y*100}%"><i>${esc(w.emote||'')}</i><span class="wv-avatar">${ownerFace(w)}</span><small>${esc(w.name)}${w.pid===S.me?' · Bạn':''}</small></div>`).join('')}${!people.length?'<span class="wv-quiet">Mời bạn ghé vào</span>':''}</div></section><div class="wv-room-tools">${button('👋 Chào','emote','data-kind="wave"','ghost')}${button('💗 Thả tim','emote','data-kind="heart"','ghost')}${button('👏 Cổ vũ','emote','data-kind="cheer"','ghost')}<details><summary>Đổi chỗ đứng</summary><div>${[['Bên trái',.22],['Ở giữa',.5],['Bên phải',.78]].map(([label,x])=>button(label,'floor',`data-x="${x}" data-y=".7"`,'small ghost')).join('')}</div></details></div>${online?`<div class="wv-chatter" role="log" aria-live="polite">${S.messages.map(m=>`<p><b>${esc(m.name)}:</b> ${esc(m.text)}</p>`).join('')}</div><form data-wv-chat class="wv-chat"><input id="wv-chat" data-wv-field="chat" data-key="${esc(p.id)}" value="${esc(draft(p.id).chat||'')}" maxlength="160" placeholder="Nói một câu tại đây…" aria-label="Lời nói trong chỗ làm"><button type="submit" class="btn ghost">Gửi</button></form>`:'<p class="wv-muted">Chưa kết nối phòng trực tiếp. Đơn dịch vụ vẫn cập nhật.</p>'}`;}
function placeView(){const p=S.place;if(!p.name)return '<p role="status">Đang mở cửa chỗ làm…</p>';const offers=p.available===false?[]:p.offers||[],selected=offers.find(o=>o.offer_id===S.offer),d=draft(p.id);return `${scene()}${p.activity?.progress?`<p class="wv-muted">${esc(p.activity.tasktitle||'Công việc hiện tại')} · ${Number(p.activity.progress.done)||0}/${Number(p.activity.progress.total)||0} đơn trong ca đã hoàn tất</p>`:''}${p.mine?`<section class="wv-card"><h3>Ai có thể ghé?</h3><div class="wv-privacy">${[['public','Mọi người'],['friends','Bạn bè'],['closed','Tạm đóng']].map(([v,label])=>button(label,'visibility',`data-value="${v}" aria-pressed="${p.visibility===v}"`,p.visibility===v?'primary':'ghost')).join('')}</div></section>`:`<section class="wv-card"><span class="eyebrow">LÀM KHÁCH</span><h3>Hôm nay bạn cần gì?</h3>${offers.length?`<div class="wv-offers">${offers.map(o=>button(`<span>${esc(o.label)}</span><b>${fmt(o.price)} xu</b>`,'offer',`data-id="${esc(o.offer_id)}" aria-pressed="${S.offer===o.offer_id}"`,S.offer===o.offer_id?'selected':'ghost')).join('')}</div>${selected?`<label class="wv-field">${shop(p)?'Lời nhắn cho người phục vụ':'Lời nhắn cho người làm'}<input id="wv-note" data-wv-field="note" data-key="${esc(p.id)}" value="${esc(d.note)}" maxlength="160" placeholder="Không bắt buộc"></label>${button(`Làm khách · ${fmt(selected.price)} xu`,'order','','primary full')}<p class="wv-muted">${esc(selected.label)} · ${selected.staffed||p.staffed?(shop(p)?'Nhân viên có thể phục vụ khi chủ tiệm vắng.':`Người phụ việc có thể làm thay khi ${vt(p,'owner')} vắng.`):(shop(p)?'Chủ tiệm nhận đơn và tự thực hiện trước khi bạn nhận.':`${vt(p,'host')} nhận đơn và tự làm trước khi bạn nhận.`)}</p>`:`<p class="wv-muted">${shop(p)?'Chọn dịch vụ để xem giá và gửi lời nhắn.':'Chọn một việc để xem giá và gửi lời nhắn.'}</p>`}`:`<p class="wv-empty">${shop(p)?'Nơi này chưa có dịch vụ nhận khách lúc này.':'Nơi này chưa nhận khách lúc này.'}</p>`}</section>`}${S.orders.length?`<section class="wv-card"><h3>${p.mine?'Khách đang ghé':'Đơn của bạn tại đây'}</h3>${S.orders.map(o=>orderView(o,p.mine)).join('')}</section>`:''}<section class="wv-card"><h3>${shop(p)?'Khách đã nhận dịch vụ':esc(vt(p,'people').replace(/^./,ch=>ch.toUpperCase()))+' đã ghé'}</h3>${S.reviews.length?S.reviews.slice(0,8).map(r=>`<article class="wv-review"><b>${esc(r.buyer?.name||'Khách')} · ${'★'.repeat(Math.max(0,Math.min(5,r.stars||0)))}</b><small>${esc(r.served_by==='staff'?vt(p,'by_staff'):vt(p,'by_owner'))}</small><p>${esc(r.comment||'')}</p>${r.reply?`<p>${esc(vt(p,'host'))}: ${esc(r.reply)}</p>`:p.mine?`<label class="wv-field">Trả lời khách<input id="wv-reply-${esc(r.order)}" data-wv-field="reply" data-key="${esc(r.order)}" value="${esc(draft(r.order).reply||'')}" maxlength="280"></label>${button('Gửi lời trả lời','reply',`data-id="${esc(r.order)}"`,'ghost')}`:''}</article>`).join(''):`<p class="wv-muted">${shop(p)?'Chưa có đánh giá dịch vụ.':`Chưa có ${esc(vt(p,'review'))} nào.`}</p>`}</section>`;}
function orderView(o,incoming=false){const d=draft(o.id);return `<article class="wv-order"><div><b>${esc(o.label)}</b><span>${fmt(o.price)} xu</span></div><p class="wv-status">${esc(o.staffed&&o.status==='accepted'?(shop(o)?'Nhân viên đang phục vụ':'Người phụ việc đang làm'):ORDER_STATUS[o.status]||o.status)}</p>${['ready','completed'].includes(o.status)?`<small>${esc(o.staffed?vt(o,'by_staff'):vt(o,'by_owner'))}</small>`:''}<p>${esc(incoming?o.customer?.name:o.provider?.name)}${o.place_name?` · ${esc(o.place_name)}`:''}</p>${o.note?`<blockquote>${esc(o.note)}</blockquote>`:''}${o.progress?.label?`<p>${esc(o.progress.label)}</p>`:''}<div class="wv-actions">${incoming&&o.status==='requested'?button('Nhận khách','accept',`data-id="${esc(o.id)}"`,'primary')+button('Chưa thể nhận','decline',`data-id="${esc(o.id)}"`,'ghost'):''}${incoming&&o.status==='accepted'&&!o.staffed&&(o.task_id||o.kind==='quay')?button('Phục vụ khách','serve',`data-id="${esc(o.id)}" data-task="${esc(o.task_id||'')}" data-career="${esc(o.career||'')}" data-kind="${esc(o.kind)}" data-place="${esc(o.place)}"`,'primary'):''}${!incoming&&o.status==='requested'?button('Hủy đơn','cancel',`data-id="${esc(o.id)}"`,'ghost'):''}${!incoming&&o.status==='ready'?button('Nhận dịch vụ','receive',`data-id="${esc(o.id)}"`,'primary'):''}</div>${!incoming&&o.can_review?`<fieldset class="wv-rating"><legend>Bạn thấy dịch vụ thế nào?</legend><div>${[1,2,3,4,5].map(n=>`<label><input id="wv-star-${esc(o.id)}-${n}" type="radio" name="wv-stars-${esc(o.id)}" data-wv-field="stars" data-key="${esc(o.id)}" value="${n}"${d.stars===n?' checked':''}><span>${n}★</span></label>`).join('')}</div></fieldset><div class="wv-tags">${REVIEW_TAGS.map(([id,label])=>`<label><input id="wv-tag-${esc(o.id)}-${id}" type="checkbox" data-wv-field="tag" data-key="${esc(o.id)}" value="${id}"${d.tags.includes(id)?' checked':''}>${label}</label>`).join('')}</div><textarea id="wv-comment-${esc(o.id)}" data-wv-field="comment" data-key="${esc(o.id)}" maxlength="280" placeholder="Một lời góp ý (không bắt buộc)" aria-label="Nhận xét dịch vụ">${esc(d.comment)}</textarea>${button('Gửi đánh giá','review',`data-id="${esc(o.id)}"`,'primary full')}`:''}</article>`;}
function inboxView(){if(!S.inbox)return '<p role="status">Đang mở sổ khách…</p>';return `<section class="wv-card"><h3>Khách cần bạn phục vụ</h3>${S.inbox.incoming?.length?S.inbox.incoming.map(o=>orderView(o,true)).join(''):'<p class="wv-empty">Chưa có đơn khách đang chờ.</p>'}</section><section class="wv-card"><h3>Dịch vụ bạn đã đặt</h3>${S.inbox.outgoing?.length?S.inbox.outgoing.map(o=>orderView(o)).join(''):'<p class="wv-empty">Ghé một chỗ làm để nhận dịch vụ đầu tiên.</p>'}</section>`;}

// The owner remains in their room while using the real career workbench. This small presence panel
// never opens a sheet or changes the active task; a visit to somebody else takes room precedence.
const O={env:null,box:null,place:null,people:[],messages:[],activity:null,me:null,incoming:[],joined:false,expanded:false,chat:'',lastPlaces:0,nextOrders:0,current:null,account:null,off:[],live:null};
function ownerMount(){
 if(!O.box)return;
 const sheet=document.getElementById('sheet'),compact=['phone','tablet'].includes(document.documentElement.dataset.layout);
 const hud=document.getElementById('taskHUD');
 // Keep the task HUD's children untouched: app.js owns and morphs those cards.
 // A shared compact container gives presence its own row below the task scroller.
 if(compact&&hud){
  if(!O.hudStack){O.hudStack=document.createElement('div');O.hudStack.className='wv-work-hud';}
  if(hud.parentElement!==O.hudStack){hud.before(O.hudStack);O.hudStack.append(hud);}
 }else if(O.hudStack?.parentElement){
  if(hud?.parentElement===O.hudStack)O.hudStack.before(hud);
  O.hudStack.remove();
 }
 const work=O.host?.open?O.host:sheet?.open?sheet:null;
 const host=work||(compact&&hud?O.hudStack:document.getElementById('side'))||document.body;
 if(O.box.parentElement!==host)host.append(O.box);
 O.box.classList.toggle('in-work',Boolean(work));
}
// Empty inboxes still discover new orders within 30 seconds. Pending buyer services need
// the fast cadence too, because polling can complete staff service and release escrow.
async function ownerOrders(orders,env){
 O.incoming=(orders.incoming||[]).filter(o=>['requested','accepted'].includes(o.status));
 const pending=[...(orders.incoming||[]),...(orders.outgoing||[])].some(o=>['requested','accepted','ready','refund_pending'].includes(o.status));
 O.nextOrders=Date.now()+(pending?5000:30000);
 env.api.workVisits=orders;
 await O.settlementSync?.(orders,env.api.account?.username||'');
}
export function workVisitsOwnerFocus(env,focus=null){if(!O.env)workVisitsBoot(env);O.preferred=focus;O.host=focus?.host||null;O.hostObserver?.disconnect();if(O.host){O.hostObserver=new MutationObserver(ownerMount);O.hostObserver.observe(O.host,{childList:true,attributes:true,attributeFilter:['open']});}O.lastPlaces=0;ownerMount();O.refresh?.().catch(()=>{});}
function ownerJoin(){const live=O.env?.live?.();if(S.dlg?.open||document.hidden||!O.place||(live?.state!=='open'||!live.flags?.visits)||O.joined)return;O.joined=live.send({t:'visit_in',place:O.place.id});}
function ownerBind(){const live=O.env?.live?.();if(!live||live===O.live)return;O.off.splice(0).forEach(fn=>fn());O.live=live;for(const type of ['visit_state','visit_people','visit_mv','visit_emote','visit_chat','visit_activity'])O.off.push(live.on(type,event=>{if(S.dlg?.open||!O.place)return;const data={place:O.place.id,people:O.people,messages:O.messages,activity:O.activity,me:O.me};if(applyVisitEvent(data,{...event,t:type})){Object.assign(O,{people:data.people,messages:data.messages,activity:data.activity,me:data.me});renderOwner();}}));O.off.push(live.on('welcome',()=>{O.joined=false;ownerJoin();}));O.off.push(live.on('visit_left',event=>{if(S.dlg?.open||event.place!==O.place?.id)return;O.joined=false;O.people=[];renderOwner();}));}
export function workVisitsBoot(env){if(O.env)return;O.env=env;O.settlementSync=createVisitSettlementSync(()=>env.api.refresh());const box=document.createElement('aside');box.className='wv-owner';box.setAttribute('aria-label','Khách ghé chỗ làm');document.body.append(box);O.box=box;stylesheet('/css/workplace-visit.css');box.addEventListener('input',e=>{if(e.target.id==='wv-owner-chat')O.chat=e.target.value;});box.addEventListener('submit',e=>{e.preventDefault();if(O.chat.trim()&&O.env.live?.()?.send({t:'visit_chat',text:O.chat.trim()})){O.chat='';renderOwner();}});box.addEventListener('click',e=>{const b=e.target.closest('[data-owner-visit]');if(!b)return;const a=b.dataset.ownerVisit;if(a==='toggle'){O.expanded=!O.expanded;renderOwner();}if(a==='orders')openWorkplaceVisit(env,{inbox:true});if(a==='wave')env.live?.()?.send({t:'visit_emote',kind:'wave'});if(a==='place')openWorkplaceVisit(env,O.place?{place:O.place.id}:{scope:'mine'});});
 const refresh=async()=>{
  if(O.refreshing||document.hidden||S.dlg?.open)return;
  O.refreshing=true;
  try{
   const account=env.api.account?.username||'';
   if(account!==O.account){O.account=account;O.lastPlaces=0;O.nextOrders=0;O.incoming=[];O.place=null;O.people=[];O.messages=[];O.joined=false;}
   if(!account){renderOwner();return;}
   ownerBind();const current=env.api.state?.current,now=Date.now();
   if(current!==O.current||!O.lastPlaces||now-O.lastPlaces>=120000){
    const d=await env.api.json('/api/work-visits/places?scope=mine');
    const wanted=O.preferred||{kind:'career',target:current},p=d.places?.find(p=>p.kind===wanted.kind&&p.target===wanted.target);
    if(p?.id!==O.place?.id){if(O.joined&&!S.dlg?.open)env.live?.()?.send({t:'visit_out'});O.joined=false;O.people=[];O.messages=[];}
    O.place=p||null;O.current=current;O.lastPlaces=now;
   }
   // A visitor dialog may have opened while workplace discovery was in flight.
   if(document.hidden||S.dlg?.open)return;
   if(now>=O.nextOrders){
    O.nextOrders=now+30000; // Bound retries when the connection is failing.
    const orders=await env.api.json('/api/work-visits/orders');
    await ownerOrders(orders,env);
   }
   ownerJoin();renderOwner();
  }finally{O.refreshing=false;}
 };
 O.refresh=refresh;O.mountObserver=new MutationObserver(ownerMount);
 const sheet=document.getElementById('sheet'),hud=document.getElementById('taskHUD');
 if(sheet)O.mountObserver.observe(sheet,{attributes:true,attributeFilter:['open']});
 if(hud)O.mountObserver.observe(hud,{childList:true});
 O.mountObserver.observe(document.documentElement,{attributes:true,attributeFilter:['data-layout']});
 ownerMount();
 O.poller=createQuayPoller({active:()=>!document.hidden&&!S.dlg?.open,refresh,failed:()=>{}});O.poller.start();refresh().catch(()=>{});
 document.addEventListener('visibilitychange',()=>{if(document.hidden){if(O.joined&&!S.dlg?.open)env.live?.()?.send({t:'visit_out'});O.joined=false;}else{O.nextOrders=0;refresh().catch(()=>{});}});
 env.api.addEventListener('state',()=>{if(O.current!==env.api.state?.current)O.lastPlaces=0;});
}
function renderOwner(){
 if(!O.box)return;ownerMount();const hidden=Boolean(S.dlg?.open||!O.env?.api?.account?.username);
 if(O.box.hidden!==hidden)O.box.hidden=hidden;if(hidden)return;
 const visitors=O.people.filter(p=>p.pid!==O.me),count=O.incoming.length;
 const html=`<button type="button" id="wv-owner-toggle" class="wv-owner-toggle" data-owner-visit="toggle" aria-expanded="${O.expanded}">🏡 Khách ghé${visitors.length||count?` <b>${visitors.length} tại chỗ · ${count} đơn</b>`:''}</button>${O.expanded?`<section class="wv-owner-panel"><div class="wv-person"><b>${esc(O.place?.name||'Chỗ làm của tôi')}</b><button class="btn ghost small" data-owner-visit="place">Xem chỗ làm</button></div><div class="wv-owner-people">${visitors.length?visitors.map(p=>`<span>${ownerFace(p)}<small>${esc(p.name)}</small>${p.emote?`<i>${esc(p.emote)}</i>`:''}</span>`).join(''):'<p class="wv-muted">Chưa có ai đang đứng tại đây.</p>'}</div>${count?`<button class="btn primary full" data-owner-visit="orders">${count} đơn khách · Mở sổ</button>`:'<button class="btn ghost full" data-owner-visit="orders">Sổ đơn dịch vụ</button>'}<div class="wv-chatter" role="log" aria-live="polite">${O.messages.slice(-4).map(m=>`<p><b>${esc(m.name)}:</b> ${esc(m.text)}</p>`).join('')}</div>${O.joined?`<form class="wv-chat"><input id="wv-owner-chat" value="${esc(O.chat)}" maxlength="160" placeholder="Nói với khách…" aria-label="Lời nói với khách ghé"><button class="btn ghost" type="submit">Gửi</button></form><button class="btn ghost small" data-owner-visit="wave">👋 Chào khách</button>`:'<p class="wv-muted">Phòng trực tiếp sẽ kết nối khi chỗ làm sẵn sàng.</p>'}</section>`:''}`;
 // Owner presence lists do not display coordinates. Keep the same nodes on movement and unchanged polls.
 if(O.box._html===html){
  // Typing changes the input property, not the cached markup; sending may return to that same markup.
  const input=O.box.querySelector('#wv-owner-chat');if(input&&input.value!==O.chat)input.value=O.chat;
  return;
 }
 const focus=focusSnapshot(document.activeElement);O.box.innerHTML=html;O.box._html=html;
 if(focus?.id&&O.box.querySelector(`[id="${focus.id}"]`))restoreInputFocus(O.box,focus);
}
