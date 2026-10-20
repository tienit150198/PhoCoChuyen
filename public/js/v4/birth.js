import {escapeHTML as esc} from '../icons.js';

/** 🏥 Phòng sinh & nhận nuôi (game/birth.py): the child section of Nhà & Gia đình when the server sends
 * family.birth. Choose sinh con / nhận nuôi → the place and its price → who pays → the partner agrees → (birth) check in,
 * a countdown, the birth moment → the baby card. Also the homestay owner's room and the nurse's calls. */
const rid=()=>globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
const n=v=>String(Math.max(0,Math.round(Number(v)||0))).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
const xu=v=>`${n(v)} xu`;
const btn=(label,op,data={},{primary=false,disabled=false,hidden=false,extra=''}={})=>`<button type="button" class="btn ${primary?'primary':'cream'} small" data-mr="fam:${op}"${Object.entries(data).map(([k,v])=>` data-${k}="${esc(v)}"`).join('')}${disabled?' disabled':''}${hidden?' hidden':''}${extra}>${label}</button>`;
const stars=(s,k)=>s==null?'Chưa có đánh giá':`⭐ ${String(s).replace('.',',')} (${k})`;
const SEEN=new Set();
const seenKey=b=>`mnl.born.${b.at}`;
function seen(b){if(SEEN.has(seenKey(b)))return true;try{return globalThis.localStorage?.getItem(seenKey(b))==='1';}catch{return false;}}
function markSeen(b){SEEN.add(seenKey(b));try{globalThis.localStorage?.setItem(seenKey(b),'1');}catch{/* this tab remembers it */}}

export function leftText(sec){
  sec=Math.max(0,Math.ceil(sec));const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60),s=sec%60;
  return h?`${h} giờ ${String(m).padStart(2,'0')} phút`:m?`${m} phút ${String(s).padStart(2,'0')} giây`:`${s} giây`;
}

/** The baby card's line about where it was born (nothing for a child of the old flow). */
export function childBirthLine(m){
  const b=m?.birth;if(!b)return '';
  return `<p class="mr-hint mr-birth-line">${m.origin==='adopt'?'📄 Nhận nuôi qua':'🏥 Chào đời ở'} ${esc(b.where)}${b.nurse?` · 🩺 Điều dưỡng ${esc(b.nurse)} hỗ trợ`:''}</p>`;
}

/** The birth moment, once per baby in this browser (a fresh birth or adoption of the last 3 days). */
export function bornOverlay(f){
  const m=f?.child,b=m?.birth;
  if(!b||typeof b.at!=='number'||Date.now()/1000-b.at>3*86400||seen(b))return '';
  const born=m.origin!=='adopt';
  return `<div class="mr-born" role="dialog" aria-modal="true" aria-labelledby="mr-born-t"><div class="mr-born-card"><div class="mr-born-art" aria-hidden="true"><span class="mr-born-door">${born?'🏥':'📄'}</span><span class="mr-born-baby">👶</span><i>💗</i><i>✨</i><i>💛</i><i>✨</i><i>💗</i></div><h3 id="mr-born-t">${born?'Chào mừng':'Về nhà rồi,'} bé ${esc(m.name)}!</h3><p>${born?'Mẹ tròn con vuông ở':'Giấy tờ xong ở'} ${esc(b.where)}.${b.nurse?` 🩺 Điều dưỡng ${esc(b.nurse)} hỗ trợ: bé khỏe mạnh, vui vẻ.`:''}</p>${btn('🤱 Bế bé','born-seen',{},{primary:true})}</div></div>`;
}

function stayCard(b,s){
  const title=s.kind==='birth'?'🏥 Phòng sinh':'📄 Nhận nuôi';
  const head=`<h3>${title} · bé ${esc(s.name)}</h3><p><b>${s.emoji||'🏥'} ${esc(s.where)}</b> · ${xu(s.price)}</p>`;
  const nurse=s.kind!=='birth'?'':s.nurse?`<p>🩺 Điều dưỡng ${esc(s.nurse)} sẽ hỗ trợ: bé chào đời khỏe hơn.</p>`:s.nurse_ok?'<p class="mr-hint">🩺 Đang chờ một điều dưỡng (người chơi) nhận hỗ trợ. Không bắt buộc, không tốn thêm xu.</p>':'';
  if(s.status==='proposed'&&s.mine)return `<section class="mr-card mr-birth" id="mr-family-children"><span class="tag">Đã gửi · Chờ người ấy</span>${head}<p>${s.payer==='me'?'Bạn trả khi người ấy đồng ý.':'Người ấy trả khi đồng ý.'} Chưa có khoản nào bị trừ.</p><div class="mr-actions">${btn('Hủy lời mời','birth-cancel',{id:s.id})}</div></section>`;
  if(s.status==='proposed')return `<section class="mr-card mr-birth mr-accent" id="mr-family-invite-children"><span class="tag">Lời mời cần bạn trả lời</span>${head}<p>${s.kind==='birth'?`Người ấy muốn đặt phòng sinh ${s.hours} giờ cho bé.`:'Người ấy muốn làm giấy tờ nhận nuôi bé.'} ${s.payer==='me'?'Bạn trả ngay khi đồng ý.':'Người ấy trả khi bạn đồng ý.'}</p><div class="mr-actions">${btn(s.payer==='me'?`Đồng ý · trả ${xu(s.price)}`:'Đồng ý','birth-answer',{id:s.id,answer:'accept'},{primary:true})}${btn('Từ chối','birth-answer',{id:s.id,answer:'decline'})}</div></section>`;
  if(s.status==='booked')return `<section class="mr-card mr-birth" id="mr-family-children"><span class="tag">Đã đặt phòng</span>${head}<p>${s.paid?`Đã trả ${esc(s.paid)}. `:''}Khi hai bạn sẵn sàng, bấm Nhận phòng: bé chào đời sau ${s.hours} giờ thật.</p>${nurse}<div class="mr-actions">${btn('🏨 Nhận phòng','birth-checkin',{id:s.id},{primary:true})}${btn(`Hủy · hoàn ${xu(s.price)}`,'birth-cancel',{id:s.id})}</div></section>`;
  b._at??=Date.now();
  const total=s.hours*3600,left=Math.max(0,s.left||0),end=b._at+left*1000,pct=Math.round(100*(total-left)/total);
  return `<section class="mr-card mr-birth" id="mr-family-children"><span class="tag">Đang ở phòng sinh</span>${head}<div class="mr-birth-clock" data-birth-end="${end}" data-birth-total="${total}" data-id="${s.id}"><span class="mr-birth-bar" role="progressbar" aria-label="Thời gian ở phòng sinh" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></span><p role="timer" aria-live="off">👶 Bé chào đời sau <b data-birth-left>${leftText(left)}</b></p></div>${nurse}<p class="mr-hint">Đã nhận phòng nên không hủy được. Có thể đóng trang, bé vẫn chào đời đúng giờ.</p><div class="mr-actions">${btn('👶 Đón bé','birth-done',{id:s.id},{primary:true,hidden:!s.due,extra:' data-birth-ready'})}</div></section>`;
}

/** The section where a couple without a shared child chooses how to welcome one (or follows its booking). */
export function birthCard(f,form,{waitingFor,minDay,nav}){
  const b=f.birth,s=b.stay;
  if(s)return stayCard(b,s);
  if(!f.ready)return `<section class="mr-card" id="mr-family-children"><h3>👶 Cùng đón con chung</h3><p>${esc(waitingFor)}${waitingFor?'. ':''}Cả hai cần đến ngày sống ${minDay} trong hành trình. Tiếp tục làm việc và khép ca để mở đón con chung.</p>${nav('Tiếp tục hành trình','nav:home')}</section>`;
  const mode=form.mode==='adopt'?'adopt':'birth';
  const seg=(id,label)=>btn(label,'birth-mode',{mode:id},{primary:mode===id,extra:` aria-pressed="${mode===id}"`});
  const rooms=b.rooms||[],where=rooms.some(r=>String(r.id)===String(form.where))?String(form.where):'npc';
  const opt=(value,title,sub,price,checked)=>`<label class="mr-opt"><input type="radio" name="mr-bwhere" value="${esc(value)}" data-mr-field="family:where"${checked?' checked':''}><span class="grow"><b>${title}</b><small>${sub}</small></span><strong>${xu(price)}</strong></label>`;
  const places=mode==='birth'
    ?`<fieldset class="mr-birth-opts"><legend>Chọn phòng sinh</legend>${opt('npc',`${b.npc.emoji} ${esc(b.npc.name)}`,`Giá cố định · luôn còn chỗ · ${b.hours} giờ`,b.npc.price,where==='npc')}${rooms.map(r=>opt(r.id,`🏡 ${esc(r.name)}`,`Chủ phòng: ${esc(r.owner)} · ${stars(r.stars,r.rated)}${r.born?` · đã đón ${r.born} bé`:''}${r.full?' · đang kín chỗ, chờ nhận phòng':''}`,r.price,where===String(r.id))).join('')}${rooms.length?'':`<p class="mr-hint">Chưa có homestay nào của người chơi mở phòng sinh. Chủ homestay mở phòng ở thẻ “Phòng sinh của bạn”, giá từ ${xu(b.floor)}.</p>`}</fieldset><label class="mr-check"><input type="checkbox" data-mr-field="family:nurse"${form.nurse===false?'':' checked'}> 🩺 Mời điều dưỡng (người chơi) hỗ trợ nếu có: bé khỏe hơn, không tốn thêm xu</label>`
    :`<div class="mr-birth-opts"><div class="mr-opt is-static"><span class="grow"><b>${b.agency.emoji} ${esc(b.agency.name)}</b><small>Phí giấy tờ · bé về nhà ngay khi người ấy đồng ý</small></span><strong>${xu(b.agency.fee)}</strong></div></div>`;
  return `<section class="mr-card mr-birth" id="mr-family-children"><h3>👶 Đón con chung</h3><p>Sinh con ở phòng sinh hoặc làm giấy tờ nhận nuôi. Người ấy cần đồng ý; tiền chỉ trừ lúc đó.</p><div class="mr-seg" role="group" aria-label="Cách đón bé">${seg('birth','🏥 Sinh con')}${seg('adopt','📄 Nhận nuôi')}</div><div class="mr-family-form"><label class="field">Tên gọi<input class="input" maxlength="24" data-mr-field="family:name" value="${esc(form.name||'')}" placeholder="Tên bé" required${form.err==='name'?' aria-invalid="true"':''}></label><label class="field">Ai trả tiền<select class="input" data-mr-field="family:payer"><option value="me"${form.payer==='partner'?'':' selected'}>Tôi trả</option><option value="partner"${form.payer==='partner'?' selected':''}>Nhờ người ấy trả</option></select></label></div>${places}<p class="mr-hint">Trả bằng tiền mặt trước rồi tới tài khoản; không quẹt thẻ tín dụng, không mắc nợ. Hủy trước khi nhận phòng được hoàn đủ.</p>${form.err==='name'?'<p class="mr-hint mr-bad" role="alert">Đặt tên gọi cho bé trước khi gửi lời mời nhé.</p>':''}<div class="mr-actions">${btn('Gửi lời mời cho người ấy','birth-book',{},{primary:true})}</div></section>`;
}

/** Cards that do not need a couple: rate the last room, the homestay owner's birth room, the nurse's calls. */
export function birthExtras(f,form){
  const b=f?.birth;if(!b)return '';
  let out='';
  if(b.rate)out+=`<section class="mr-card mr-birth"><h3>⭐ Chấm phòng sinh</h3><p>Bé ${esc(b.rate.name)} chào đời ở ${esc(b.rate.where)}. Hai bạn thấy phòng thế nào?</p><div class="mr-actions mr-stars">${[1,2,3,4,5].map(k=>btn('⭐'.repeat(k),'birth-rate',{id:b.rate.id,stars:k},{extra:` aria-label="${k} sao"`})).join('')}</div></section>`;
  const mine=b.my_room;
  if(mine){
    const r=mine.room;
    const name=form['room:name']??r?.name??'',price=form['room:price']??r?.price??b.floor,open=form['room:open']??r?.open??true;
    out+=`<section class="mr-card mr-birth" id="mr-family-room"><span class="tag">Chủ homestay</span><h3>🏡 Phòng sinh của bạn</h3><p>Cho các cặp vợ chồng đặt phòng sinh ${b.hours} giờ. Giá do bạn đặt, tối thiểu ${xu(b.floor)}, tối đa ${xu(b.max)}. Bạn nhận ${100-b.burn_pct}% khi bé chào đời (${b.burn_pct}% phí).</p>${r?`<p>${r.open?'🟢 Đang nhận khách':'⚪ Đang tạm đóng'} · ${xu(r.price)} · ${stars(r.stars,r.rated)} · ${r.born} bé đã chào đời · ${mine.staying} ca đang ở · ${mine.booked} ca đã đặt</p>`:''}${mine.can?`<div class="mr-family-form"><label class="field">Tên phòng<input class="input" maxlength="30" data-mr-field="family:room:name" value="${esc(name)}" placeholder="Ví dụ: Phòng Đồi Thông" required${form['room:err']?' aria-invalid="true"':''}></label><label class="field">Giá một ca (xu)<input class="input" type="number" inputmode="numeric" min="${b.floor}" max="${b.max}" step="10000" data-mr-field="family:room:price" value="${esc(price)}"></label></div><label class="mr-check"><input type="checkbox" data-mr-field="family:room:open"${open?' checked':''}> Đang nhận khách</label>${form['room:err']?'<p class="mr-hint mr-bad" role="alert">Đặt tên phòng trước khi lưu nhé (ví dụ: Phòng Đồi Thông).</p>':''}<div class="mr-actions">${btn('Lưu phòng sinh','room-save',{},{primary:true})}</div>`:'<p class="mr-hint">Cần sở hữu homestay (quy mô nghề Homestay từ cấp 1) để sửa hoặc mở lại phòng.</p>'}</section>`;
  }
  const nu=b.nurse;
  if(nu){
    const row=(c,act)=>`<li><span class="grow">👶 ${esc(c.name)} · ${esc(c.where)}${c.status==='staying'?` · còn ${leftText(c.left||0)}`:' · chưa nhận phòng'}</span>${act}</li>`;
    out+=`<section class="mr-card mr-birth" id="mr-family-nurse"><span class="tag">Điều dưỡng</span><h3>🩺 Ca sinh cần điều dưỡng</h3><p>Hỗ trợ ca sinh của người chơi: bé chào đời khỏe hơn. Không tính xu, gia đình nhận lời cảm ơn của bạn. Đã hỗ trợ ${nu.done} ca.</p>${nu.helping.length?`<h4>Bạn đang hỗ trợ</h4><ul class="mr-birth-list">${nu.helping.map(c=>row(c,'')).join('')}</ul>`:''}${nu.calls.length?`<ul class="mr-birth-list">${nu.calls.map(c=>row(c,btn('🩺 Nhận hỗ trợ','birth-nurse',{id:c.id},{disabled:nu.full}))).join('')}</ul>`:'<p class="mr-hint">Chưa có ca nào cần điều dưỡng lúc này.</p>'}</section>`;
  }
  return out;
}

export async function birthAction(op,data,{env,family:f,form={},post,render}){
  const b=f?.birth;
  if(op==='birth-mode'){form.mode=data.mode==='adopt'?'adopt':'birth';render?.();return true;}
  if(op==='born-seen'){if(f?.child?.birth)markSeen(f.child.birth);render?.();return true;}
  if(!b)return true;
  const s=b.stay,id=Number(data.id);
  if(op==='birth-book'){
    const name=(form.name||'').trim();
    if(!name){form.err='name';render?.();env?.toast?.('Đặt tên gọi cho bé trước khi gửi lời mời nhé.','error');return true;}
    form.err='';
    const mode=form.mode==='adopt'?'adopt':'birth',payer=form.payer==='partner'?'partner':'me';
    let where='agency',price=b.agency.fee,label=b.agency.name;
    if(mode==='birth'){const r=(b.rooms||[]).find(x=>String(x.id)===String(form.where));where=r?r.id:'npc';price=r?r.price:b.npc.price;label=r?`${r.name} (${r.owner})`:b.npc.name;}
    const msg=`${label}: ${xu(price)}. ${payer==='me'?'Bạn trả khi người ấy đồng ý':'Người ấy trả khi đồng ý'}${mode==='birth'?`; sau khi nhận phòng, bé chào đời sau ${b.hours} giờ`:'; bé về nhà ngay'}.`;
    if(!await env.confirmAction(mode==='birth'?`Mời người ấy đặt phòng sinh cho bé ${name}?`:`Mời người ấy nhận nuôi bé ${name}?`,msg,'Gửi lời mời'))return true;
    await post('family_birth_book',{kind:mode,name,where,price,payer,nurse:mode==='birth'&&form.nurse!==false,rid:rid()});return true;
  }
  if(op==='birth-answer'){
    if(!s||s.id!==id)return true;
    if(data.answer==='accept'&&!await env.confirmAction(s.kind==='birth'?'Đồng ý đặt phòng sinh?':'Đồng ý nhận nuôi?',`${s.where} · ${xu(s.price)}. ${s.payer==='me'?'Bạn trả ngay bây giờ: tiền mặt trước, rồi tài khoản.':'Người ấy trả ngay bây giờ.'}${s.kind==='birth'?' Hủy trước khi nhận phòng được hoàn đủ.':' Bé về nhà ngay.'}`,'Đồng ý',s.payer==='me'?{cost:s.price,pocket:['wallet','account']}:null))return true;
    await post('family_birth_answer',{id,answer:data.answer==='accept'?'accept':'decline',rid:rid()});return true;
  }
  if(op==='birth-cancel'){
    if(!s||s.id!==id)return true;
    if(s.status==='booked'&&!await env.confirmAction('Hủy đặt phòng sinh?',`Hoàn đủ ${xu(s.price)} cho ${s.payer==='me'?'bạn':'người ấy'}, về đúng nơi đã trả.`,'Hủy đặt phòng'))return true;
    await post('family_birth_cancel',{id,rid:rid()});return true;
  }
  if(op==='birth-checkin'){
    if(!s||s.id!==id)return true;
    if(!await env.confirmAction('Nhận phòng sinh?',`Bé ${s.name} chào đời sau ${s.hours} giờ thật. Đã nhận phòng thì không hủy được.`,'Nhận phòng'))return true;
    await post('family_birth_checkin',{id,rid:rid()});return true;
  }
  if(op==='birth-done'){await post('family_birth_done',{id,rid:rid()});return true;}
  if(op==='birth-rate'){await post('family_birth_rate',{id,stars:Math.max(1,Math.min(5,Number(data.stars)||5)),rid:rid()});return true;}
  if(op==='birth-nurse'){
    if(!await env.confirmAction('Nhận hỗ trợ ca sinh?','Bạn là điều dưỡng của ca này: bé chào đời khỏe hơn. Không tính xu.','Nhận hỗ trợ'))return true;
    await post('family_birth_nurse',{id,rid:rid()});return true;
  }
  if(op==='room-save'){
    const r=b.my_room?.room,name=String(form['room:name']??r?.name??'').trim(),price=Math.round(Number(form['room:price']??r?.price??b.floor));
    if(!name){form['room:err']=true;render?.();env?.toast?.('Đặt tên phòng trước khi lưu nhé (ví dụ: Phòng Đồi Thông).','error');return true;}
    form['room:err']=false;
    await post('family_room_set',{name,price,open:(form['room:open']??r?.open??true)!==false,rid:rid()});return true;
  }
  return false;
}

/** One ticking clock for every visible birth countdown; at 0 it shows "Đón bé" and taps it once. */
let clock=0;const tapped=new Set();
export function birthClock(doc=globalThis.document){
  if(!doc?.querySelectorAll)return;
  const tick=()=>{
    const boxes=[...doc.querySelectorAll('[data-birth-end]')];
    if(!boxes.length){clearInterval(clock);clock=0;return;}
    for(const box of boxes){
      const left=Math.max(0,(Number(box.dataset.birthEnd)-Date.now())/1000),total=Number(box.dataset.birthTotal)||1;
      const t=box.querySelector('[data-birth-left]');if(t)t.textContent=leftText(left);
      const bar=box.querySelector('.mr-birth-bar i');if(bar)bar.style.width=`${Math.round(100*(total-left)/total)}%`;
      if(left<=0){
        const go=box.closest('section')?.querySelector('[data-birth-ready]');
        if(go){go.hidden=false;if(!tapped.has(box.dataset.id)&&!go.disabled){tapped.add(box.dataset.id);go.click();}}
      }
    }
  };
  tick();
  if(!clock&&doc.querySelector('[data-birth-end]'))clock=setInterval(tick,1000);
}
