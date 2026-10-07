/** 🏅 Danh hiệu bên tên (owner 07/10: "bảng xếp hạng, hội chợ event mà có là hiển thị ra hết"): the live service sends
 * `tt`, the ids of every honour title a player holds now, best first (live/honours.py), beside the name on chat
 * messages, quotes, walkers and cards. This draws them as small chips: emoji + a short name ("💰 Top 3 Tài phú",
 * "🌪️ Bão bầu cua"), at most `max` inline plus "+N"; `list` gives every one with its full name for a popover.
 * The names mirror game/lb_titles.py, game/fair.py TITLE_ROWS and game/wedding_live.py (tests/test_live_honours.py
 * compares them). An unknown id shows nothing; an older service sends no `tt`. */
import {escapeHTML as esc} from '../icons.js';

// game/lb_titles.py BOARD_TITLES, TIERS: the main boards' tiers (top 1 / top 2–3 / top 4–10)
const BOARDS={
  all:['Trải nghiệm',[['👑','Trùm cuối của phố'],['🔥','Chiến thần cày cuốc'],['⚡','Dân cày top 10']]],
  titles:['Danh hiệu',[['🏅','Vua săn danh hiệu'],['✨','Nhà sưu tầm xịn sò'],['🎖️','Hội săn danh hiệu']]],
  certs:['Chứng chỉ',[['🎓','Thủ khoa của phố'],['📜','Học bá chính hiệu'],['🤓','Mọt sách có số má']]],
  wealth:['Tài phú',[['💎','Đại gia của phố'],['💰','Đại gia mới nổi'],['🤑','Hội nhà giàu']]],
};
const tierOf=r=>r===1?0:r<=3?1:2;
// game/lb_titles.py CAREER_NOUN (a workplace board's top 1 is "🏆 Trùm <noun>"), CAREER_TITLE (no "Trùm" there)
const NOUN={milk_tea:'trà sữa',grocery:'tạp hóa',delivery:'giao hàng',cafe_bakery:'bánh & cà phê',florist:'tiệm hoa',
  mother_baby:'mẹ & bé',restaurant:'mì cay',pet_care:'chăm thú cưng',salon:'salon tóc',repair:'sửa đồ',farm:'nông trại',
  homestay:'homestay',clothing:'shop quần áo',pet_shop:'shop thú cưng',tra_da:'trà đá',fruit:'trái cây',garbage:'thu gom rác',
  drain:'thông cống',homemaker:'nội trợ',ice_cream:'tiệm kem',pho:'quán phở',com:'quán cơm',nail:'tiệm nail',pagoda:'việc chùa',
  photobooth:'tiệm ảnh',library:'thư viện',giupviec:'giúp việc',naucom:'bếp nhà khách',babysitter:'trông trẻ',
  customer_care:'chăm sóc khách',pharmacy:'nhà thuốc',tour_guide:'dẫn tour',teacher:'bục giảng',accounting:'sổ sách',
  pilot:'buồng lái',flight_attendant:'khoang khách',oil:'giàn khoan',corp_accounting:'kế toán doanh nghiệp',
  tax_payroll:'thuế & lương',group_accounting:'kế toán tập đoàn',hr_admin:'nhân sự',secretary:'thư ký',it_helpdesk:'IT văn phòng',
  railway:'gác chắn',nurse:'khoa Nội',lighthouse:'hải đăng',rescue:'tổng đài cứu hộ',lifeguard:'hồ bơi',police:'công an phường',zpop:'tiệm album'};
const CAREER_TITLE={pagoda:['🪷','Siêng việc chùa nhất tuần','Siêng việc chùa']};
// game/fair.py TITLE_ROWS (full names) with a short one for the chip; game/wedding_live.py TITLE_NAMES (the race)
const EVENT={
  f_king:['👑','Vua trò chơi','Vua trò chơi','Hội chợ dân gian'],
  f_master:['🎪','Cao thủ hội chợ','Cao thủ hội chợ','Hội chợ dân gian'],
  f_oaq:['🪨','Cao tay ô ăn quan','Ô ăn quan','Hội chợ dân gian'],
  f_ring:['💍','Tay ném vòng thần sầu','Ném vòng','Hội chợ dân gian'],
  f_loto:['🎱','Thần lô tô hội chợ','Thần lô tô','Hội chợ dân gian'],
  f_kinh2:['🎎','Kinh đôi rộn ràng','Kinh đôi','Hội chợ dân gian'],
  f_nguoc:['🙃','Đọc ngược như xuôi','Đọc ngược','Hội chợ dân gian'],
  f_hu:['🏺','Ôm hũ đêm hội','Hũ đêm hội','Hội chợ dân gian'],
  f_bao:['🌪️','Trúng bão bầu cua','Bão bầu cua','Hội chợ dân gian'],
  f_dart:['🎯','Mắt thần phi tiêu','Mắt thần','Hội chợ dân gian'],
  f_raid:['🚨','Bị công an hỏi thăm','Bị hỏi thăm','Hội chợ dân gian'],
  w_vip:['🥇','Khách quý của phố','Khách quý','Khách mời của tuần'],
  w_pro:['🎊','Ăn cưới chuyên nghiệp','Ăn cưới pro','Khách mời của tuần'],
};
const LB=/^lb_([a-z][a-z0-9_]{0,39})_([1-9]|10)$/;
function noun(api,b){const n=NOUN[b];if(n)return n;const s=api?.content?.careers?.[b]?.meta?.short;return s?s.charAt(0).toLowerCase()+s.slice(1):null;}

/** {emoji, short, full, src} of one id, or null. */
export function title(api,id){
  if(typeof id!=='string')return null;
  const e=EVENT[id];if(e)return {emoji:e[0],short:e[2],full:e[1],src:e[3]};
  // 👑 a one-of-a-kind title won at the auction house (game/auction_content.py, content.journey.auction)
  if(id.startsWith('dh_')){const u=(api?.content?.journey?.auction?.items||[]).find(x=>x.id===id&&x.kind==='title');return u?{emoji:u.emoji,short:u.short||u.name,full:u.name,src:'Danh hiệu độc bản · Nhà đấu giá'}:null;}
  const m=LB.exec(id);if(!m)return null;
  const b=m[1],r=Number(m[2]),B=BOARDS[b];
  if(B){const [label,tiers]=B,[emoji,name]=tiers[tierOf(r)];return {emoji,short:`Top ${r} ${label}`,full:name,src:`Top ${r} ${label} · tuần này`};}
  if(r!==1)return null;
  const c=CAREER_TITLE[b];if(c)return {emoji:c[0],short:c[2],full:c[1],src:'Top 1 tuần này'};
  const n=noun(api,b);return n?{emoji:'🏆',short:`Trùm ${n}`,full:`Trùm ${n}`,src:'Top 1 tuần này'}:null;
}
/** The known titles of a `tt` (deduplicated, at most 16). */
export function titles(api,tt){
  if(!Array.isArray(tt))return [];
  const out=[],seen=new Set();
  for(const id of tt.slice(0,16)){if(seen.has(id))continue;seen.add(id);const t=title(api,id);if(t)out.push(t);}
  return out;
}

let ready=false;
function ensureCss(){
  if(ready||typeof document==='undefined')return;ready=true;
  const s=document.createElement('style');s.dataset.hnCss='';
  s.textContent=`.hn-chips{display:inline-flex;flex-wrap:wrap;align-items:center;gap:3px;min-width:0;max-width:100%;vertical-align:middle}
.hn-chip{display:inline-flex;align-items:center;gap:2px;max-width:12.5em;padding:0 6px;border-radius:999px;font-style:normal;font-size:.72rem;line-height:1.5;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:var(--hn-bg,#fff3d6);color:var(--hn-ink,#6b4a12);box-shadow:inset 0 0 0 1px var(--hn-line,rgba(176,124,34,.28))}
.hn-chip>span{overflow:hidden;text-overflow:ellipsis}
.hn-more{background:var(--surface-2,#f1e8dc);color:var(--ink-2,#5a4436);box-shadow:none}
html[data-theme="dem"] .hn-chip{--hn-bg:#3d3220;--hn-ink:#f4dca4;--hn-line:rgba(244,220,164,.25)}
html[data-theme="dem"] .hn-more{background:rgba(255,255,255,.1);color:inherit}
.hn-pop{margin:4px 0 6px;padding:8px 10px;border-radius:12px;background:var(--surface,#fff);color:var(--ink,#3a2a20);box-shadow:0 4px 16px rgba(0,0,0,.14),0 0 0 1px var(--line,rgba(0,0,0,.08));max-width:min(100%,320px);font-size:.82rem;font-weight:400;text-align:left}
.hn-pop>b{display:block;font-size:.75rem;color:var(--muted,#8a7768);margin-bottom:4px}
.hn-pop ul{list-style:none;margin:0;padding:0;display:grid;gap:4px}
.hn-pop li{display:flex;gap:6px;align-items:baseline;line-height:1.3}
.hn-pop li>i{font-style:normal}
.hn-pop small{display:block;color:var(--muted,#8a7768);font-size:.72rem}`;
  document.head.append(s);
}
/** Chips for a name: the first `max` titles and "+N" for the rest (all of them when max is 0; no "+N" when `more` is
 * false), or ''. */
export function chips(api,tt,max=2,more=true){
  const L=titles(api,tt);if(!L.length)return '';ensureCss();
  const n=max>0?Math.min(max,L.length):L.length,rest=more?L.length-n:0;
  const chip=t=>`<em class="hn-chip" title="${esc(t.full)}"><i aria-hidden="true">${esc(t.emoji)}</i><span>${esc(t.short)}</span></em>`;
  return `<span class="hn-chips" aria-label="Danh hiệu: ${esc(L.map(t=>t.full).join(', '))}">${L.slice(0,n).map(chip).join('')}${rest?`<em class="hn-chip hn-more">+${rest}</em>`:''}</span>`;
}
/** How many chips fit inline: 2 on a phone, 3 on a wide screen (the chat column is at most 360 px). */
export function inlineMax(){try{return matchMedia('(min-width: 700px)').matches?3:2;}catch{return 2;}}
/** The popover's content: every title with its full name and where it comes from. */
export function list(api,tt,who=''){
  const L=titles(api,tt);if(!L.length)return '';ensureCss();
  return `<div class="hn-pop" role="note">${who?`<b data-no-translate>Danh hiệu của ${esc(who)}</b>`:'<b>Danh hiệu</b>'}<ul>${L.map(t=>`<li><i aria-hidden="true">${esc(t.emoji)}</i><span>${esc(t.full)}<small>${esc(t.src)}</small></span></li>`).join('')}</ul></div>`;
}
/** The emojis of the titles a name tag does not already show (a canvas tag: at most `max`). */
export function icons(api,tt,shown='',max=3){
  return [...new Set(titles(api,tt).map(t=>t.emoji))].filter(e=>!String(shown).includes(e)).slice(0,max).join('');
}
