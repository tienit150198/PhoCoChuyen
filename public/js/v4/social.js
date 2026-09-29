/** "Phố nghề" — play with other people: visit shops, review each other, send
 * gifts, trade materials, share tips, and push a weekly goal together. */
import {icon,escapeHTML as esc} from '../icons.js';

const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const button=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const stars=n=>n?'★'.repeat(Math.round(n))+'☆'.repeat(5-Math.round(n)):'☆☆☆☆☆';
const head=(title,sub,extra='')=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">CHƠI CÙNG MỌI NGƯỜI</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div>${extra}<button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;
const ago=t=>{const s=Math.max(0,Date.now()/1000-t);if(s<60)return'vừa xong';if(s<3600)return`${Math.floor(s/60)} phút trước`;if(s<86400)return`${Math.floor(s/3600)} giờ trước`;return`${Math.floor(s/86400)} ngày trước`;};
const AVATARS=['🌸','☕','🍜','🎉','💪','🌈','🍀','⭐','🧁','🎁','🧑‍🍳','👩‍🏫','🧑‍💼','🧑‍🌾','🐱','🐶'];
const TABS=[['street','Phố','map'],['board','Bảng tin','chat'],['market','Chợ','cart'],['inbox','Hộp thư','inbox'],['me','Hồ sơ','user']];

function careerName(api,id){return api.content.careers?.[id]?.meta?.short||api.content.catalogue?.find(c=>c.id===id)?.short||id;}

/* Data cache with one in-flight load per key; views re-render when data lands. */
function load(env,key,route,query={}){
  const {api,ui}=env;ui.soc??={};ui.socBusy??={};
  if(ui.soc[key]||ui.socBusy[key])return ui.soc[key];
  ui.socBusy[key]=true;
  api.socialGet(route,query).then(d=>{ui.soc[key]=d;}).catch(e=>{ui.soc[key]={error:e.message};}).finally(()=>{ui.socBusy[key]=false;if(ui.view==='social')env.renderSheet();});
  return null;
}
export function invalidate(ui,...keys){ui.soc??={};for(const k of Object.keys(ui.soc))if(!keys.length||keys.some(x=>k.startsWith(x)))delete ui.soc[k];}
const loading=`<div class="empty">${icon('sparkle',26)}<p class="muted">Đang tải Phố nghề…</p></div>`;
const failed=d=>`<div class="notice danger">${icon('alert',17)}<div>${esc(d.error)}</div></div>`;

function profileForm(env,me){
  const s=env.api.state.settings;
  return `<form class="settings-block soc-profile" data-soc-form="profile">
    <h3>${icon('user',18)} ${me?'Hồ sơ của bạn':'Tạo hồ sơ để vào Phố nghề'}</h3>    <label class="field">Tên hiển thị<input class="input" name="name" data-preserve maxlength="24" minlength="2" required value="${esc(me?.name||env.api.state.name||'')}" autocomplete="nickname"></label>
    <label class="field">Giới thiệu ngắn<input class="input" name="bio" data-preserve maxlength="140" value="${esc(me?.bio||'')}" placeholder="Quán mì cay nhất phố, chủ quán hiền"></label>
    <div class="field">Biểu tượng<div class="avatar-pick">${AVATARS.map(a=>`<label><input type="radio" name="avatar" value="${a}" ${(me?.avatar||'🌸')===a?'checked':''}><span>${a}</span></label>`).join('')}</div></div>
    <label class="switch-row"><span class="grow"><b>Hiện quán của tôi cho mọi người</b></span><input type="checkbox" name="visible" role="switch" ${me?(me.visible?'checked':''):(s.publicProfile||!me?'checked':'')}><i aria-hidden="true"></i></label>
    <p class="small muted">Phố nghề dành cho người từ 13 tuổi. Hãy tử tế, đừng đăng số điện thoại, địa chỉ hay đường link. <a href="/terms" target="_blank" rel="noopener">Quy tắc cộng đồng</a></p>
    <button class="btn primary full" type="submit">${me?'Lưu hồ sơ':'Vào Phố nghề'}</button>
  </form>`;
}

function community(c){
  if(!c)return'';
  const pct=Math.min(100,Math.round(c.progress/c.goal*100));
  return `<article class="card community ${c.done?'done':''}"><div class="row spread"><span class="eyebrow">MỤC TIÊU CẢ PHỐ TUẦN NÀY</span>${c.done?pill('Hoàn thành 🎉','green'):pill(`${c.players} người góp sức`)}</div><h3>${esc(c.label)}</h3><div class="bar big"><i style="width:${pct}%"></i></div><p class="small muted">${c.progress.toLocaleString('vi-VN')} / ${c.goal.toLocaleString('vi-VN')} khách được phục vụ tuần này.</p></article>`;
}

function playerCard(env,p){
  const shop=p.shop||{},cur=shop.careers?.[0];
  return `<article class="player-card"><span class="avatar big">${esc(p.avatar)}</span><div class="grow"><h4>${esc(p.name)} ${p.me?pill('Bạn','blue'):''}</h4>${shop.title?`<p class="small clip">${esc(shop.title.emoji)} ${esc(shop.title.name)}</p>`:''}<p class="small muted clip">${esc(p.bio||'Chưa có lời giới thiệu')}</p>
    <div class="row wrap small">${(shop.careers||[]).slice(0,3).map(c=>`<span class="chip">${esc(c.short)} · Lv${c.level}${c.rating?` · ${c.rating}★`:''}</span>`).join('')}</div></div>
    ${button(p.me?'Xem quán':'Ghé quán '+icon('chevron',13),'socShop',{pid:p.pid},'small '+(p.me?'ghost':'primary'))}</article>`;
}

function street(env){
  const {ui,api}=env,f=ui.socFilter||{},key=`dir:${f.career||''}:${f.q||''}:${f.follow||''}`;
  const d=load(env,key,'directory',{career:f.career,q:f.q,filter:f.follow?'following':''});
  const careers=Object.keys(api.state.careers);
  return `${community(d?.community||api.social?.community)}
    <form class="soc-filter row wrap" data-soc-form="filter"><input class="input grow" name="q" data-preserve placeholder="Tìm tên quán…" value="${esc(f.q||'')}" maxlength="30"><select name="career"><option value="">Mọi nghề</option>${careers.map(id=>`<option value="${id}" ${f.career===id?'selected':''}>${esc(careerName(api,id))}</option>`).join('')}</select><label class="check-label"><input type="checkbox" name="follow" ${f.follow?'checked':''}>Đang theo dõi</label><button class="btn small" type="submit">${icon('search',15)} Lọc</button></form>
    ${!d?loading:d.error?failed(d):d.players.length?`<div class="player-list">${d.players.map(p=>playerCard(env,p)).join('')}</div>`:`<div class="empty">${icon('map',28)}<p>Chưa có quán nào ở đây.</p></div>`}`;
}

function shopView(env,pid){
  const {ui,api}=env,d=load(env,'shop:'+pid,'shop',{pid});
  const back=button(icon('chevron',13)+' Quay lại phố','socBack',{},'ghost small back-btn');
  if(!d)return back+loading;if(d.error)return back+failed(d);
  const p=d.profile,me=p.me;
  const gift=ui.socGift||{sticker:'🌸',coins:0};
  const reviewForm=d.can_review?`<form class="card soc-review-form" data-soc-form="review" data-pid="${esc(pid)}"><h4>Chấm quán ${esc(p.name)}</h4><div class="star-pick">${[1,2,3,4,5].map(n=>`<label><input type="radio" name="stars" value="${n}" ${n===5?'checked':''}><span>★</span></label>`).join('')}</div><textarea name="text" data-preserve maxlength="280" minlength="4" required placeholder="Quán bạn này có gì hay? Góp ý thật lòng nhé."></textarea><button class="btn primary small" type="submit">Gửi đánh giá</button></form>`:'';
  const giftForm=d.can_gift?`<details class="card soc-gift"><summary>${icon('gift',16)} Tặng quà</summary><form data-soc-form="gift" data-pid="${esc(pid)}"><div class="sticker-pick">${(api.social?.stickers||['🌸']).map(s=>`<label><input type="radio" name="sticker" value="${s}" ${gift.sticker===s?'checked':''}><span>${s}</span></label>`).join('')}</div><div class="segmented">${[0,10,20].map(c=>`<label><input type="radio" name="coins" value="${c}" ${c===0?'checked':''}><span>${c?c+' xu':'Chỉ sticker'}</span></label>`).join('')}</div><input class="input" name="note" data-preserve maxlength="80" placeholder="Lời nhắn (không bắt buộc)"><button class="btn primary small" type="submit">Gửi quà</button><p class="small muted">Xu lấy từ ví nghề bạn đang chơi. Mỗi ngày tặng mỗi người 1 lần.</p></form></details>`:'';
  const reviews=d.reviews.map(r=>`<article class="p-review"><div class="row"><span class="avatar">${esc(r.avatar||'🙂')}</span><div class="grow"><b>${esc(r.author)}</b> <span class="stars">${stars(r.stars)}</span><small class="muted block">${esc(careerName(api,r.career))} · ${ago(r.at)}</small></div>${r.mine||r.owner?'':button(icon('flag',13),'socReport',{kind:'review',id:r.id},'icon-btn small ghost')}</div><p>${esc(r.text)}</p>${r.reply?`<p class="owner-reply">${icon('chat',13)} <b>Chủ quán:</b> ${esc(r.reply)}</p>`:r.owner?`<form class="row" data-soc-form="reply" data-id="${r.id}"><input class="input grow" name="text" data-preserve maxlength="280" placeholder="Trả lời một lần, thật lòng nhé" required><button class="btn small" type="submit">Trả lời</button></form>`:''}</article>`).join('')||`<p class="muted small">Chưa có hàng xóm nào chấm sao.</p>`;
  const listings=d.listings.length?`<h4 class="section-title">Hàng đang bán</h4><div class="listing-grid">${d.listings.map(m=>listingCard(m)).join('')}</div>`:'';
  return `${back}<section class="shop-hero card"><span class="avatar huge">${esc(p.avatar)}</span><div class="grow"><h3>${esc(p.name)}</h3>${p.shop?.title?`<p class="small">${esc(p.shop.title.emoji)} ${esc(p.shop.title.name)}</p>`:''}<p class="muted">${esc(p.bio||'')}</p><div class="row wrap small">${pill(`${d.visits} lượt ghé`)} ${d.rating?pill(`${d.rating}★ từ hàng xóm`,'amber'):''} ${pill(`${(p.served||0).toLocaleString('vi-VN')} khách đã phục vụ`,'green')}</div></div>
    ${me?'':`<div class="row wrap">${button(p.following?'Đang theo dõi':'Theo dõi',p.following?'socUnfollow':'socFollow',{pid},'small '+(p.following?'ghost':''))}${button(icon('flag',13)+' Báo cáo','socReport',{kind:'profile',id:pid},'small ghost')}${button('Chặn','socBlock',{pid},'small ghost danger')}</div>`}</section>
    <div class="shop-careers">${(p.shop?.careers||[]).map(c=>`<div class="kv-card"><b>${esc(c.place)}</b><small>Lv${c.level} · ngày ${c.day} · ${c.rating?c.rating+'★':'chưa có sao'} · ${c.served} khách</small></div>`).join('')||'<p class="muted small">Chưa mở quán nào.</p>'}</div>
    ${giftForm}${reviewForm}${listings}<h4 class="section-title">Hàng xóm chấm sao</h4><div class="stack">${reviews}</div>`;
}

function listingCard(m){
  return `<article class="listing ${m.mine?'mine':''}"><span class="tile-emoji">${esc(m.emoji)}</span><div class="grow"><b>${m.qty} × ${esc(m.name)}</b><small class="muted block">${esc(m.seller)} · còn hạn ${m.life_left>=999?'lâu':m.life_left+' ngày'} · ${ago(m.at)}</small></div><div class="price"><b>${m.total.toLocaleString('vi-VN')} xu</b><small>${m.price} xu/đv</small></div>${m.mine?(m.status==='active'?button('Gỡ','socUnlist',{id:m.id},'small ghost'):pill('Đã bán','green')):button('Mua','socBuy',{id:m.id,total:m.total,name:m.name,qty:m.qty},'small primary')}</article>`;
}

function board(env){
  const {ui,api}=env,career=ui.socBoardCareer||'all',kind=ui.socBoardKind||'',key=`board:${career}:${kind}`;
  const d=load(env,key,'board',{career,kind});
  const kinds=api.social?.board_kinds||{tip:'Mẹo nghề',story:'Chuyện nghề',ask:'Hỏi nhanh',trade:'Cần mua/bán'};
  const reactions=api.social?.reactions||['❤️','😂','👏','💡'];
  const cur=api.state.current;
  const compose=`<form class="card soc-compose" data-soc-form="board"><div class="row wrap"><select name="kind">${Object.entries(kinds).map(([k,v])=>`<option value="${k}">${esc(v)}</option>`).join('')}</select><select name="career"><option value="all">Mọi nghề</option>${cur?`<option value="${cur}" ${career===cur?'selected':''}>${esc(careerName(api,cur))}</option>`:''}</select></div><textarea name="text" data-preserve maxlength="400" minlength="4" required placeholder="Chia sẻ một mẹo, một chuyện nghề, hay hỏi mọi người…"></textarea><button class="btn primary small" type="submit">Đăng</button></form>`;
  const filters=`<nav class="pill-tabs">${[['all','Mọi nghề'],...(cur?[[cur,careerName(api,cur)]]:[])].map(([id,l])=>`<button class="${id===career?'active':''}" data-action="socBoardCareer" data-value="${esc(id)}">${esc(l)}</button>`).join('')}<span class="sep"></span>${[['','Tất cả'],...Object.entries(kinds)].map(([id,l])=>`<button class="${id===kind?'active':''}" data-action="socBoardKind" data-value="${id}">${esc(l)}</button>`).join('')}</nav>`;
  const posts=!d?loading:d.error?failed(d):d.posts.length?d.posts.map(p=>`<article class="board-post"><div class="row"><span class="avatar">${esc(p.avatar||'🙂')}</span><div class="grow"><b>${esc(p.author)}</b> ${pill(esc(kinds[p.kind]||p.kind))}<small class="muted block">${p.career==='all'?'Mọi nghề':esc(careerName(api,p.career))} · ${ago(p.at)}</small></div>${p.mine?button(icon('trash',14),'socDeletePost',{post:p.id},'icon-btn small ghost'):button(icon('flag',13),'socReport',{kind:'board',id:p.id},'icon-btn small ghost')}</div><p class="post-text">${esc(p.text)}</p><div class="row wrap reactions">${reactions.map(e=>{const r=p.reactions[e];return `<button class="react ${r?.mine?'active':''}" data-action="socReact" data-post="${p.id}" data-emoji="${e}">${e}${r?` ${r.n}`:''}</button>`;}).join('')}</div><details class="comments"><summary>${p.comments.length} bình luận</summary>${p.comments.map(c=>`<p class="comment"><span>${esc(c.avatar||'🙂')}</span><b>${esc(c.author)}</b> ${esc(c.text)} <small class="muted">${ago(c.at)}</small></p>`).join('')}<form class="row" data-soc-form="comment" data-post="${p.id}"><input class="input grow" name="text" data-preserve maxlength="200" required placeholder="Viết bình luận…"><button class="btn small" type="submit">Gửi</button></form></details></article>`).join(''):`<div class="empty">${icon('chat',28)}<p>Chưa có bài nào.</p></div>`;
  return filters+compose+`<div class="stack">${posts}</div>`;
}

function market(env){
  const {ui,api}=env,cur=api.state.current,room=api.state.careers[cur];
  const view=ui.socMarketCareer||(room?.inventory?cur:'');
  const d=load(env,'market:'+view,'market',{career:view});
  const invCareers=Object.entries(api.state.careers).filter(([,c])=>c.inventory).map(([id])=>id);
  const items=(api.content.inventory?.items?.[cur]||[]);
  const sell=room?.inventory?`<details class="card"><summary>${icon('box',16)} Đăng bán nguyên liệu của ${esc(careerName(api,cur))}</summary><form data-soc-form="list" data-career="${esc(cur)}" class="stack"><select name="item" required>${items.filter(i=>(room.inventory.stock[i.id]||0)>0).map(i=>`<option value="${esc(i.id)}" data-cost="${i.cost}">${esc(i.emoji||'')} ${esc(i.name)} · còn ${room.inventory.stock[i.id]} · giá nhập ${i.cost} xu</option>`).join('')||'<option value="">Kho đang trống</option>'}</select><div class="row"><label class="field grow">Số lượng<input class="input" type="number" name="qty" min="1" max="50" value="1" required></label><label class="field grow">Giá / đơn vị (xu)<input class="input" type="number" name="price" min="1" max="100000" required placeholder="0.5×–3× giá nhập"></label></div><button class="btn primary small" type="submit">Đưa lên chợ</button><p class="small muted">Hàng rời kho ngay (giữ hộ). Không bán được sau ${d?.rules?.days||3} ngày thì tự về kho, trừ phần đã hết hạn.</p></form></details>`:`<div class="notice">${icon('box',17)}<div>Nghề hiện tại không có kho. Chuyển sang nghề buôn bán (quán mì, tiệm hoa…) để đăng bán.</div></div>`;
  const filter=`<nav class="pill-tabs">${[['','Mọi nghề'],...invCareers.map(id=>[id,careerName(api,id)])].map(([id,l])=>`<button class="${id===view?'active':''}" data-action="socMarketCareer" data-value="${esc(id)}">${esc(l)}</button>`).join('')}</nav>`;
  const body=!d?loading:d.error?failed(d):`${d.notes?.length?`<div class="notice success">${icon('check',17)}<div>${d.notes.map(esc).join('<br>')}</div></div>`:''}${d.mine.length?`<h4 class="section-title">Hàng của bạn</h4><div class="listing-grid">${d.mine.map(listingCard).join('')}</div>`:''}<h4 class="section-title">Đang bán ở chợ</h4>${d.listings.filter(m=>!m.mine).length?`<div class="listing-grid">${d.listings.filter(m=>!m.mine).map(listingCard).join('')}</div>`:`<div class="empty">${icon('cart',28)}<p>Chợ đang vắng.</p></div>`}`;
  return sell+filter+body+`<p class="small muted space-top">Mua ở chợ: hàng về kho của nghề tương ứng, xu trừ ở ví nghề đó. Người bán nhận xu lần tới họ vào game.</p>`;
}

function inbox(env){
  const {ui}=env,d=load(env,'inbox','inbox');
  if(!d)return loading;if(d.error)return failed(d);
  if(d.unread&&!ui.socInboxRead){ui.socInboxRead=true;env.api.socialPost('inbox_read').then(()=>{if(env.api.social)env.api.social.unread=0;}).catch(()=>{});}
  const kindIcon={visit:'👀',review:'⭐',reply:'💬',gift:'🎁',sale:'🧺',comment:'💬'};
  return `${d.notes?.length?`<div class="notice success">${icon('check',17)}<div>${d.notes.map(esc).join('<br>')}</div></div>`:''}
    ${d.gifts.length?`<h4 class="section-title">Quà đã nhận</h4><div class="gift-row">${d.gifts.map(g=>`<div class="gift"><span>${esc(g.sticker)}</span><small><b>${esc(g.author)}</b>${g.coins?` · ${g.coins} xu`:''}${g.note?`<br>“${esc(g.note)}”`:''}</small></div>`).join('')}</div>`:''}
    <h4 class="section-title">Thông báo</h4>${d.items.length?`<ul class="inbox">${d.items.map(x=>`<li class="${x.read?'':'unread'}"><span>${kindIcon[x.kind]||'🔔'}</span><p class="grow">${esc(x.text)}<small class="muted block">${ago(x.at)}</small></p>${x.ref&&/^[0-9a-f]{16}$/.test(x.ref)?button('Xem','socShop',{pid:x.ref},'small ghost'):''}</li>`).join('')}</ul>`:`<div class="empty">${icon('inbox',28)}<p>Chưa có gì mới.</p></div>`}`;
}

export function socialView(env){
  const {ui,api}=env,tab=ui.socTab||'street';
  const me=api.social?.me;
  const unread=api.social?.unread||0;
  const nav=`<nav class="soc-tabs" role="tablist">${TABS.map(([id,label,ic])=>`<button role="tab" aria-selected="${id===tab}" class="${id===tab?'active':''}" data-action="socTab" data-tab="${id}">${icon(ic,17)}<span>${label}</span>${id==='inbox'&&unread?`<em class="badge">${unread}</em>`:''}</button>`).join('')}</nav>`;
  let body;
  if(!me&&tab!=='street')body=profileForm(env,null);
  else if(ui.socShop)body=shopView(env,ui.socShop);
  else body={street:()=>street(env),board:()=>board(env),market:()=>market(env),inbox:()=>inbox(env),me:()=>profileForm(env,me)}[tab]();
  const intro=!me&&tab==='street'?`<div class="notice soc-guest">${icon('user',17)}<div class="grow"><b>Bạn đang xem với tư cách khách.</b></div>${button('Tạo hồ sơ','socTab',{tab:'me'},'small primary')}</div>`:'';
  return head('Phố nghề','')+`<div class="sheet-body social-v4">${nav}${intro}${body}</div>`;
}

export async function socialAction(action,data,el,env){
  const {api,ui,toast,renderSheet,confirmAction}=env;
  const run=async(route,body,msg=true,keys=[])=>{try{const r=await api.socialPost(route,body);if(msg&&r.message)toast(r.message);invalidate(ui,...keys);renderSheet();return r;}catch(e){toast(e.message,true);return null;}};
  switch(action){
    case'social':ui.view!=='social'&&invalidate(ui);env.openSheet('social');return true;
    case'socTab':ui.socTab=data.tab;ui.socShop=null;if(data.tab==='inbox'){ui.socInboxRead=false;invalidate(ui,'inbox');}renderSheet();return true;
    case'socShop':ui.socShop=data.pid;invalidate(ui,'shop:');renderSheet();return true;
    case'socBack':ui.socShop=null;renderSheet();return true;
    case'socFollow':await run('follow',{pid:data.pid},true,['shop:','dir:']);return true;
    case'socUnfollow':await run('unfollow',{pid:data.pid},true,['shop:','dir:']);return true;
    case'socBlock':if(await confirmAction('Chặn quán này?','Hai bạn sẽ không thấy quán, bài viết và quà của nhau.','Chặn')){await run('block',{pid:data.pid},true);ui.socShop=null;renderSheet();}return true;
    case'socReport':{
      const reasons={spam:'Spam / quảng cáo',rude:'Thô lỗ, quấy rối',private:'Lộ thông tin cá nhân',scam:'Lừa đảo',other:'Khác'};
      const choice=await pickReason(env,reasons);if(!choice)return true;
      await run('report',{kind:data.kind,id:String(data.id),reason:choice},true,['shop:','board:','market:']);return true;
    }
    case'socUnlist':await run('unlist',{id:Number(data.id)},true,['market:','shop:']);return true;
    case'socBuy':if(await confirmAction('Mua hàng ở chợ?',`${data.qty} × ${data.name} với giá ${Number(data.total).toLocaleString('vi-VN')} xu.`,'Mua'))await run('buy',{id:Number(data.id)},true,['market:','shop:']);return true;
    case'socReact':await run('react',{post:Number(data.post),emoji:data.emoji},false,['board:']);return true;
    case'socDeletePost':if(await confirmAction('Xóa bài viết?','Bình luận và biểu cảm cũng bị xóa.','Xóa'))await run('delete_post',{post:Number(data.post)},true,['board:']);return true;
    case'socBoardCareer':ui.socBoardCareer=data.value;renderSheet();return true;
    case'socBoardKind':ui.socBoardKind=data.value;renderSheet();return true;
    case'socMarketCareer':ui.socMarketCareer=data.value;renderSheet();return true;
  }
  return false;
}

async function pickReason(env,reasons){
  // Reuse the confirm dialog with a simple choice list.
  const dialog=document.getElementById('confirmDialog'),box=document.getElementById('confirmContent');
  return new Promise(resolve=>{
    box.innerHTML=`<h3>Báo cáo nội dung</h3><div class="stack">${Object.entries(reasons).map(([k,v])=>`<button type="button" class="btn ghost full" data-reason="${k}">${esc(v)}</button>`).join('')}<button type="button" class="btn full" data-reason="">Hủy</button></div>`;
    const done=e=>{const b=e.target.closest('[data-reason]');if(!b)return;box.removeEventListener('click',done);dialog.close();resolve(b.dataset.reason||null);};
    box.addEventListener('click',done);dialog.showModal();
  });
}

export async function socialSubmit(form,env){
  const kind=form.dataset.socForm;if(!kind)return false;
  const {api,ui,toast,renderSheet}=env,f=new FormData(form);
  const send=async(route,body,keys=[])=>{try{const r=await api.socialPost(route,body);if(r.message)toast(r.message);invalidate(ui,...keys);renderSheet();return r;}catch(e){toast(e.message,true);return null;}};
  switch(kind){
    case'filter':ui.socFilter={q:(f.get('q')||'').trim(),career:f.get('career')||'',follow:f.get('follow')==='on'};renderSheet();break;
    case'profile':{
      const r=await send('profile',{name:(f.get('name')||'').trim(),bio:(f.get('bio')||'').trim(),avatar:f.get('avatar')||'🌸',visible:f.get('visible')==='on'},['dir:']);
      if(r){api.social={...(api.social||{}),me:r.me};if(api.state.settings.publicProfile!==r.me.visible)await env.cmd('settings',{publicProfile:r.me.visible},{quiet:true});ui.socTab='street';renderSheet();}
      break;
    }
    case'review':await send('review',{pid:form.dataset.pid,stars:Number(f.get('stars')),text:(f.get('text')||'').trim()},['shop:']);break;
    case'reply':await send('reply',{id:Number(form.dataset.id),text:(f.get('text')||'').trim()},['shop:']);break;
    case'gift':await send('gift',{pid:form.dataset.pid,sticker:f.get('sticker'),coins:Number(f.get('coins')||0),note:(f.get('note')||'').trim()},['shop:']);break;
    case'board':await send('board',{kind:f.get('kind'),career:f.get('career'),text:(f.get('text')||'').trim()},['board:']);break;
    case'comment':await send('comment',{post:Number(form.dataset.post),text:(f.get('text')||'').trim()},['board:']);break;
    case'list':{
      if(!f.get('item')){toast('Kho đang trống.',true);break;}
      await send('list',{career:form.dataset.career,item:f.get('item'),qty:Number(f.get('qty')),price:Number(f.get('price'))},['market:']);break;
    }
  }
  return true;
}

/** Keeps the Phố nghề badge fresh while the tab is visible (cheap GET, once a minute). */
export function startSocialPoll(env){
  const tick=async()=>{
    if(document.hidden)return;
    try{
      const d=await env.api.socialGet('me');
      env.api.social={...(env.api.social||{}),unread:d.unread,community:d.community,me:d.me};
      const btn=document.querySelector('.top-social');
      if(btn){let b=btn.querySelector('.badge');if(d.unread){if(!b){b=document.createElement('em');b.className='badge';btn.append(b);}b.textContent=d.unread;}else b?.remove();}
    }catch{/* offline: try again later */}
  };
  setInterval(tick,60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)tick();});
}
