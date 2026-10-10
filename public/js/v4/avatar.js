/** 🙂 Ảnh đại diện: the face other players see beside the player's chat messages. Loaded the first time it opens
 * (journey.js: jrView 'avatar', actions jrAv*; also from Cài đặt and the chat's Bạn bè tab). Trying parts is local
 * (ui.av.draft); "Lưu" sends jr_avatar (game/avatar.py checks every id), and live.js then shows the new face in chat.
 * The clothes come from the Tủ đồ (shirt 'tu'), or a plain tee in one colour. Art: ./face.js; ids: ./face-code.js. */
import {icon,escapeHTML as esc} from '../icons.js';
import {faceSVG,NAMES,COLORS,PLAIN_HEAD} from './face.js';
import {PARTS,EMOJIS,DEFAULT_FACE,faceOf,encode} from './face-code.js';
import {portrait,lookOf} from './look.js';
import {nameOf as colorName} from './palette.js';

const TABS=[['mat','Gương mặt','🙂',['skin','shape','age','expr']],['toc','Mái tóc','💇',['hair','hc']],
  ['pk','Phụ kiện','🕶️',['glasses','head','hwc','beard','extra','freckles']],['ao','Áo & nền','👕',['shirt','bg']]];
const LABEL={skin:'Màu da',shape:'Dáng mặt',age:'Độ tuổi',expr:'Nét mặt',hair:'Kiểu tóc',hc:'Màu tóc',glasses:'Kính',head:'Mũ · khăn',
  hwc:'Màu mũ · khăn',beard:'Râu',extra:'Điểm nhấn',freckles:'Tàn nhang',shirt:'Áo',bg:'Màu nền'};
const SWATCH=new Set(['skin','hc','hwc','bg']);
const SAMPLE='Chào cả phố! 👋';
const presets=api=>api.content?.journey?.wardrobe?.avatar_presets||[];

const saved=api=>{const a=api.state.avatar;return {kind:a?.kind==='emoji'?'emoji':'face',emoji:EMOJIS.includes(a?.emoji)?a.emoji:EMOJIS[0],face:faceOf(api.state).f};};
const S=(ui,api)=>ui.av??={tab:'mat',...saved(api)};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const changed=(api,st)=>{const s=saved(api);return !api.state.avatar||st.kind!==s.kind||(st.kind==='emoji'?st.emoji!==s.emoji:!same(st.face,s.face));};
const code=(api,f)=>encode('f1',f,api.state);
const opt=(part,v,on,inner,label)=>`<button type="button" class="av-opt${SWATCH.has(part)?' sw':''}${on?' on':''}" data-action="jrAvPick" data-part="${part}" data-value="${esc(v)}" aria-pressed="${on}" title="${esc(label)}" aria-label="${esc(label)}">${inner}</button>`;

function options(api,st,part){
  const f=st.face;
  if(part==='freckles')return `<div class="av-opts">${opt('freckles','0',!f.freckles,faceSVG(code(api,{...f,freckles:false}),48),'Không tàn nhang')}${opt('freckles','1',f.freckles,faceSVG(code(api,{...f,freckles:true}),48),'Có tàn nhang')}</div>`;
  if(part==='hwc'&&PLAIN_HEAD.has(f.head))return '';
  const ids=PARTS[part];
  if(part==='shirt'){
    const L=lookOf(api.state),g=api.state.journey?.gender;
    return `<div class="av-opts">`+opt('shirt','tu',f.shirt==='tu',`<span class="av-tu">${portrait(L,g,44,'')}</span>`,'Đồ trong Tủ đồ')+
      ids.filter(x=>x!=='tu').map(x=>opt('shirt',x,f.shirt===x,faceSVG(code(api,{...f,shirt:x}),48),`Áo trơn · ${colorName(api,x)}`)).join('')+'</div>';
  }
  if(SWATCH.has(part))return `<div class="av-opts">${ids.map(x=>opt(part,x,f[part]===x,`<i style="background:${COLORS[part][x]}"></i>`,NAMES[part]?.[x]||colorName(api,x))).join('')}</div>`;
  return `<div class="av-opts">${ids.map(x=>opt(part,x,f[part]===x,faceSVG(code(api,{...f,[part]:x}),48)+`<small>${esc(NAMES[part][x])}</small>`,NAMES[part][x])).join('')}</div>`;
}

export function avatarView(env){
  const {api,ui}=env,st=S(ui,api),name=api.state.name||'Bạn';
  const top=`<header class="sheet-head jr-head"><button type="button" class="btn ghost small jr-back" data-action="jrView" data-view="home" aria-label="Quay lại hành trình">${icon('back',18)}</button><div class="grow"><span class="eyebrow">NHÂN VẬT</span><h2>Ảnh đại diện</h2></div></header>`;
  const big=st.kind==='emoji'?`<span class="av-emoji big" aria-hidden="true">${st.emoji}</span>`:faceSVG(code(api,st.face),112,'Ảnh đại diện đang chọn');
  const mini=st.kind==='emoji'?`<span class="av-emoji" aria-hidden="true">${st.emoji}</span>`:faceSVG(code(api,st.face),34);
  const dirty=changed(api,st);
  const kind=`<div class="segmented av-kind" role="group" aria-label="Kiểu ảnh">${[['face','Khuôn mặt'],['emoji','Biểu tượng']].map(([k,l])=>`<button type="button" class="${st.kind===k?'active':''}" data-action="jrAvKind" data-kind="${k}" aria-pressed="${st.kind===k}">${l}</button>`).join('')}</div>`;
  let body;
  if(st.kind==='emoji')body=`<div class="av-opts av-emojis">${EMOJIS.map(e=>`<button type="button" class="av-opt em${st.emoji===e?' on':''}" data-action="jrAvEmoji" data-emoji="${e}" aria-pressed="${st.emoji===e}">${e}</button>`).join('')}</div>`;
  else{
    const tab=TABS.find(t=>t[0]===st.tab)||TABS[0];
    const choices=presets(api),quick=choices.length?`<section class="av-part"><h4>Mẫu gương mặt</h4><div class="av-opts">${choices.map(p=>{const on=same(st.face,p.face);return `<button type="button" class="av-opt${on?' on':''}" data-action="jrAvPreset" data-preset="${esc(p.id)}" aria-pressed="${on}" aria-label="${esc(p.name)}">${faceSVG(code(api,p.face),48)}<small>${esc(p.name)}</small></button>`;}).join('')}</div></section>`:'';
    body=quick+`<nav class="av-tabs" role="tablist" aria-label="Phần của gương mặt">${TABS.map(([id,l,e])=>`<button type="button" role="tab" class="av-tab${tab[0]===id?' active':''}" aria-selected="${tab[0]===id}" data-action="jrAvTab" data-tab="${id}"><span aria-hidden="true">${e}</span>${l}</button>`).join('')}</nav>`+
      tab[3].map(p=>{const o=options(api,st,p);return o?`<section class="av-part"><h4>${LABEL[p]}</h4>${o}</section>`:'';}).join('')+
      (tab[0]==='ao'?`<p class="small muted av-note">Mặc đồ trong Tủ đồ thì đổi áo, đổi phụ kiện là ảnh đổi theo. <button type="button" class="btn ghost small" data-action="jrWardrobe">👗 Tủ đồ</button></p>`:'');
  }
  const follow=api.state.avatar?`<button type="button" class="btn ghost small" data-action="jrAvFollow">Theo nhân vật</button>`:'';
  return top+`<div class="sheet-body jr-body av">
    <section class="jr-card av-stage">
      <div class="av-big">${big}</div>
      <div class="av-side">
        <div class="av-chat" aria-hidden="true"><span class="av-mini">${mini}</span><span class="av-bub"><b data-no-translate>${esc(name)}</b>${SAMPLE}</span></div>
        <div class="av-actions"><button type="button" class="btn primary small" data-action="jrAvSave"${dirty?'':' disabled'}>${dirty?'Lưu':'Đang dùng'}</button>
          ${st.kind==='face'?`<button type="button" class="btn ghost small" data-action="jrAvRandom">🎲 Ngẫu nhiên</button>`:''}${follow}</div>
      </div>
    </section>
    ${kind}${body}</div>`;
}

const pick=ids=>ids[Math.floor(Math.random()*ids.length)];

export async function avatarAction(action,data,el,env){
  const {api,ui,cmd,renderSheet}=env,st=S(ui,api);
  switch(action){
    case'jrAvPreset':{const preset=presets(api).find(p=>p.id===data.preset);if(preset){st.kind='face';st.face={...preset.face};}renderSheet(false);return true;}
    case'jrAvTab':st.tab=TABS.some(t=>t[0]===data.tab)?data.tab:'mat';renderSheet(false);return true;
    case'jrAvKind':st.kind=data.kind==='emoji'?'emoji':'face';renderSheet(false);return true;
    case'jrAvEmoji':if(EMOJIS.includes(data.emoji))st.emoji=data.emoji;renderSheet(false);return true;
    case'jrAvPick':{const p=data.part,v=data.value;
      if(p==='freckles')st.face={...st.face,freckles:v==='1'};
      else if(PARTS[p]?.includes(v))st.face={...st.face,[p]:v};
      renderSheet(false);return true;}
    case'jrAvRandom':{const f={...DEFAULT_FACE};for(const k of Object.keys(PARTS))f[k]=pick(PARTS[k]);
      // mostly plain: no headwear / glasses / beard / extra half of the time, the wardrobe's clothes kept
      for(const k of ['glasses','head','beard','extra'])if(Math.random()<.5)f[k]='0';
      f.freckles=Math.random()<.25;f.shirt=st.face.shirt;st.face=f;renderSheet(false);return true;}
    case'jrAvFollow':if(await cmd('jr_avatar',{reset:true}))ui.av={tab:st.tab,...saved(api)};renderSheet(false);return true;
    case'jrAvSave':if(await cmd('jr_avatar',{kind:st.kind,face:st.face,emoji:st.emoji}))ui.av={tab:st.tab,...saved(api)};renderSheet(false);return true;
  }
  return false;
}
