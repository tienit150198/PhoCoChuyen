import {escapeHTML as esc} from '../icons.js';
import {confirmPurchase} from './payment.js';

const button=(label,action,data={},disabled=false)=>`<button type="button" class="btn cream small" data-mr="fam:${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${disabled?' disabled':''}>${label}</button>`;
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const labels={food:'No bụng',clean:'Sạch sẽ',joy:'Vui vẻ'};

/** Canonical shared family, separate from journey.household's personal child and pet. */
export function familyView(f,c,form={}){
  if(!f)return '<section class="mr-card"><h3>Nhà &amp; Gia đình</h3><p>Chưa tải được gia đình của bạn.</p><button type="button" class="btn cream" data-mr="retry">Thử tải lại</button></section>';
  const married=c?.status==='married', pending=f.requests||[], copies=f.copies||[];
  const nav=(label,action,data={})=>`<button type="button" class="btn cream" data-mr="${action}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}>${label}</button>`;
  const requests=[...pending].sort((a,b)=>Number(a.mine)-Number(b.mine)).map(r=>`<section id="mr-family-invite-${r.kind==='home'?'home':'children'}" class="mr-card mr-family-invite${r.mine?'':' mr-accent'}"><span class="tag">${r.mine?'Đã gửi · Chờ người ấy':'Lời mời cần bạn trả lời'}</span><h3>${r.kind==='home'?'🏡 Mời về ở chung':'👶 Mời đón con chung'}</h3><p>${r.kind==='home'?esc(r.home):`${esc(r.name)} · ${r.origin==='birth'?'Đón bé mới sinh':'Nhận nuôi'}`}</p><p>${r.mine?'Người ấy mở Nhà &amp; Gia đình để đồng ý hoặc từ chối.':'Chỉ khi bạn đồng ý, hai bạn mới '+(r.kind==='home'?'ở chung nhà.':'cùng đón bé.')}</p><div class="mr-actions">${r.mine?button('Hủy lời mời','cancel',{id:r.id}):button(r.kind==='home'?'Đồng ý ở chung':'Đồng ý đón bé','answer',{id:r.id,answer:'accept'})+button('Từ chối','answer',{id:r.id,answer:'decline'})}</div></section>`).join('');
  const eligibility=f.eligibility, minDay=eligibility?.min_day||10;
  const waitingFor=eligibility?[...(!eligibility.self_story||eligibility.self_day<minDay?[`Bạn đang ở ngày sống ${eligibility.self_day||0}`]:[]),...(!eligibility.partner_story||eligibility.partner_day<minDay?[`Người ấy đang ở ngày sống ${eligibility.partner_day||0}`]:[])].join('. '):'';
  const homeRequest=pending.find(r=>r.kind==='home');
  const home=married?`<section class="mr-card" id="mr-family-home"><span class="tag">${f.together?'Đang ở chung':'Chưa ở chung'}</span><h3>🏡 Nhà của hai bạn</h3><p>${f.together?'Cùng trở về nhà và dùng nội thất của hai bạn.':homeRequest?(homeRequest.mine?'Lời mời đã gửi. Chờ người ấy đồng ý để dọn về cùng nhau.':'Bạn có lời mời ở chung ở phía trên.'):f.can_invite?`Bạn đang ở ${esc(f.home_name)}. Mời người ấy về ở cùng nhé.`:f.partner_can_invite?`Người ấy đang ở ${esc(f.partner_home_name)}. Nhờ người ấy mở Nhà &amp; Gia đình và gửi lời mời về ở chung.`:'Chủ nhà cần đang ở căn nhà mình sở hữu để gửi lời mời. Mở Nhà của bạn để mua nhà hoặc dọn về căn đã có; nếu nhà của người ấy, nhờ người ấy gửi lời mời.'}</p><div class="mr-actions">${nav('🚪 Vào nhà','nav:inside')}${f.can_invite&&!f.together&&!homeRequest?button('Mời người ấy về ở chung','home'):''}${nav(!f.can_invite&&!f.together&&!homeRequest?'🏠 Chọn nhà để ở chung':'Nhà của bạn','nav:house')}</div><details class="mr-more" data-family-details="home"><summary>Nhà ở &amp; quỹ chung</summary><p class="mr-hint">Nhà và đồ vẫn thuộc từng người. Góp tiền mua nhà qua Quỹ chung rồi chọn “Lấy từ quỹ chung” khi mua.</p>${nav('Mở quỹ chung','tab',{tab:'fund'})}${f.can_leave?`<p>${button('Rời nhà chung','leave')}</p>`:''}</details></section>`:`<section class="mr-card" id="mr-family-home"><h3>🏡 Một mái nhà của bạn</h3><p>${c?.status==='engaged'?'Bạn có thể mời bạn bè ở chung ngay. Hoàn tất lễ cưới để mở phần con chung.':'Mời bạn bè vào chơi hoặc ở chung lâu dài, không cần kết hôn. Người nhận cần đồng ý lời mời.'}</p><div class="mr-actions">${nav('🚪 Vào nhà','nav:inside')}${nav(c?.status==='engaged'?'Xem kế hoạch cưới':'Kết bạn với người ấy','tab',{tab:c?.status==='engaged'?'home':'friends'})}</div></section>`;
  const children=[...(f.child?[f.child]:[]),...copies].map(m=>`<section class="mr-card mr-family-child"${m.personal?'':' id="mr-family-children"'}><span class="tag">${m.personal?'Bé bạn tiếp tục chăm':'Con chung'}</span><h3>👶 ${esc(m.name)}</h3><p>${esc(m.stage)} · ${m.care_days} ngày được chăm · Gắn bó ${m.bond}/100</p>${m.waiting?`<p role="status">Cả hai đã đồng ý. Chờ đón bé mới sinh vào ${esc(m.born)} theo ngày lịch Việt Nam.</p>`:`<div class="mr-family-needs">${Object.entries(m.needs).map(([k,n])=>`<label>${labels[k]} ${n}/100 <meter min="0" max="100" value="${n}">${n}</meter></label>`).join('')}</div><p class="mr-family-today">${m.acts.every(a=>a.done)?'✓ Hôm nay đã chăm đủ các mục.':'Hôm nay, cùng chăm bé nhé'}</p><div class="mr-actions">${m.acts.map(a=>button(`${a.emoji} ${esc(a.name)}${a.cost?` · ${a.cost} xu`:''}${a.done?' ✓':''}`,'care',{child:m.id,act:a.id},a.done)).join('')}</div>`}<p class="mr-hint">${esc(f.clock)} · ${esc(f.day)}. ${m.personal?'Bạn tiếp tục chăm bé theo tiến trình riêng.':'Cả hai dùng chung tiến trình chăm bé.'} Chỉ số không tự giảm khi bạn vắng mặt.</p><details class="mr-more" data-family-details="${esc(m.id)}"><summary>Tên gọi &amp; đồ của bé</summary><label class="field">Tên gọi<input class="input" maxlength="24" required data-mr-field="family:name:${esc(m.id)}" value="${esc(form['name:'+m.id]??m.name)}"></label>${button('Đổi tên','rename',{child:m.id},m.waiting)}<h4>Đồ của bé</h4><div class="mr-actions">${(f.outfits||[]).map(o=>button(`${esc(o.name)}${m.outfit===o.id?' ✓':m.owned.includes(o.id)?'':` · ${o.cost} xu`}`,'style',{child:m.id,item:o.id},m.waiting||m.outfit===o.id)).join('')}</div></details></section>`).join('');
  const invitation=married&&!f.child&&!pending.some(r=>r.kind==='child')?`<section class="mr-card" id="mr-family-children"><h3>👶 Cùng đón con chung</h3><p>Mỗi cặp cùng chăm một bé sau khi cả hai đồng ý.</p>${f.ready?`<p class="mr-hint">Cả hai cần đạt ngày sống 10. Cả hai cách đều miễn phí và cùng chăm một bé như nhau. Nhận nuôi: bé về ngay sau khi người ấy đồng ý. Đón bé mới sinh: bé về vào ngày lịch Việt Nam kế tiếp, không phải sau khi khép một ca làm.</p><div class="mr-family-form"><label class="field">Tên gọi<input class="input" maxlength="24" data-mr-field="family:name" value="${esc(form.name||'')}" placeholder="Tên bé" required></label><label class="field">Cách đón bé<select class="input" data-mr-field="family:origin"><option value="adopt"${form.origin==='birth'?'':' selected'}>Nhận nuôi miễn phí</option><option value="birth"${form.origin==='birth'?' selected':''}>Đón bé mới sinh</option></select></label></div>${button('Gửi lời mời đón con','request')}`:`<p>${esc(waitingFor)}${waitingFor?'. ':''}Cả hai cần đến ngày sống ${minDay} trong hành trình. Tiếp tục làm việc và khép ca để mở đón con chung.</p>${nav('Tiếp tục hành trình','nav:home')}`}</section>`:'';
  const childPending=!f.child&&pending.some(r=>r.kind==='child')?'<p class="mr-hint" id="mr-family-children">Lời mời đón con đang chờ trả lời ở phía trên.</p>':'';
  const custody=(married||copies.length)?'<details class="mr-more" data-family-details="custody"><summary>Tiến trình của bé khi hai bạn chia tay</summary><p class="mr-hint">Mỗi người giữ một bản tiến trình để tiếp tục chăm riêng. Xóa tài khoản chỉ xóa bản của người xóa.</p></details>':'';
  return `<div class="mr-family">${requests}<section class="mr-card"><h3>👥 Bạn bè &amp; người ở cùng</h3><p>Mời vào chơi hoặc ở chung lâu dài. Người ở chung có thể vào nhà khi chủ offline.</p>${nav('Mời bạn bè · Xem lời mời','nav:guests')}</section>${home}${children}${invitation}${childPending}<section class="mr-card"><h3>🐾 Góc chăm riêng</h3><p>Chăm con riêng và thú cưng theo ngày sống của nhân vật.</p>${nav('Con riêng & thú cưng','nav:personal')}</section>${custody}<div class="mr-actions">${nav('Làm mới gia đình','retry')}</div></div>`;
}

export async function familyAction(action,data,{env,family:f,form={},post}){
  if(!action.startsWith('fam:'))return false;
  const op=action.slice(4), child=[f?.child,...(f?.copies||[])].find(m=>m?.id===data.child);
  let name,payload;
  if(op==='request'){
    name=(form.name||'').trim();if(!name)return true;
    const origin=form.origin||'adopt';
    if(!await env.confirmAction('Gửi lời mời đón con chung?',`${name}. ${origin==='birth'?'Đón bé mới sinh sau một ngày lịch Việt Nam.':'Nhận nuôi miễn phí.'} Người ấy cần đồng ý; con riêng được giữ nguyên.`,'Gửi lời mời'))return true;
    payload={name,origin};action='family_child_request';
  }else if(op==='home'){
    if(!await env.confirmAction('Mời người ấy về ở chung?',`${f.home_name}. Người ấy cần đồng ý. Quyền sở hữu nhà và đồ vẫn riêng.`,'Gửi lời mời'))return true;
    payload={};action='family_home_request';
  }else if(op==='answer'){
    const request=f.requests.find(r=>r.id===Number(data.id));if(!request)return true;
    if(data.answer==='accept'&&!await env.confirmAction(request.kind==='home'?'Đồng ý ở chung?':'Cùng đón bé?',request.kind==='home'?'Bạn chuyển về căn nhà được mời, miễn phí. Nhà cá nhân để trống, vẫn thuộc bạn; phòng trọ trả lại tiền cọc. Nội thất vẫn thuộc từng người.':`${request.name}. ${request.origin==='birth'?'Chờ một ngày lịch Việt Nam để đón bé.':'Nhận nuôi miễn phí.'} Con riêng và thú cưng của bạn được giữ nguyên.`,'Đồng ý'))return true;
    payload={id:request.id,answer:data.answer};action='family_answer';
  }else if(op==='cancel'){payload={id:Number(data.id)};action='family_cancel';
  }else if(op==='leave'){
    if(!await env.confirmAction('Rời nhà chung?','Bạn thôi ở nhà chung. Nhà và đồ cá nhân vẫn thuộc mỗi người; nếu chưa có chỗ ở riêng, bạn về gác Bà Tám. Con chung vẫn được cả hai chăm.','Dọn ra'))return true;
    payload={};action='family_home_leave';
  }else if(['care','style','rename'].includes(op)){
    if(!child||child.waiting)return true;
    payload={child:child.id};action=`family_child_${op}`;
    if(op==='rename'){name=(form['name:'+child.id]??child.name).trim();if(!name)return true;payload.name=name;
    }else{
      const item=op==='care'?child.acts.find(a=>a.id===data.act):f.outfits.find(o=>o.id===data.item);
      if(!item||(op==='care'&&item.done))return true;
      const cost=op==='style'&&child.owned.includes(item.id)?0:item.cost;
      const pay=cost?await confirmPurchase(env,{title:item.name,message:`Cho ${child.name}: ${cost} xu.`,label:'Xác nhận',cost,noJoint:true}):'cash';
      if(!pay)return true;
      Object.assign(payload,op==='care'?{act:item.id,pay}:{item:item.id,pay});
    }
  }else return true;
  await post(action,{...payload,rid:rid()});
  return true;
}

/** Poll only a visible, idle family sheet. A mutation/close invalidates older reads. */
export function familyRefresh({active,read,apply,delay=15000,setTimer=setTimeout,clearTimer=clearTimeout}){
  let timer=0,running=false,version=0;
  const schedule=()=>{if(running&&!timer)timer=setTimer(tick,delay);};
  const tick=async()=>{
    timer=0;const seq=version;
    try{if(running&&active()){const data=await read();if(running&&seq===version&&active())apply(data);}}
    catch{/* manual refresh remains available after network errors */}
    finally{schedule();}
  };
  return {
    start(){running=true;version++;if(timer)clearTimer(timer);timer=0;schedule();},
    stop(){running=false;version++;if(timer)clearTimer(timer);timer=0;},
    invalidate(){version++;},
  };
}
