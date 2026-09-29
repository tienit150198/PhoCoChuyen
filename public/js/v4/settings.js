/** Settings sheet (v0.4): play, look & layout, sound & music, language,
 * notifications, AI, save data, privacy. */
import {icon,escapeHTML as esc} from '../icons.js';
import {layoutPref,setLayoutPref} from './shell.js';
import {pushState,enablePush,disablePush,isIOS,isStandalone} from './push.js';
import {accountPane,accountAction,accountNudge} from './account.js';
import {tutorialSettings} from '../tutorial/index.js';

const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
const button=(label,action,data={},style='')=>`<button type="button" class="btn ${style}" data-action="${action}"${attrs(data)}>${label}</button>`;
const pill=(label,kind='')=>`<span class="tag ${kind}">${label}</span>`;
const head=(title,sub,eyebrow)=>`<header class="sheet-head"><div class="grow"><span class="eyebrow">${eyebrow}</span><h2>${title}</h2>${sub?`<p>${sub}</p>`:''}</div><button class="icon-btn" type="button" data-action="close" aria-label="Đóng">${icon('x',21)}</button></header>`;

export const THEMES=[
  ['kem','Kem sữa','Ấm, sáng, dịu mắt',['#faf3e8','#c44b30','#3f8f7a']],
  ['tra_xanh','Trà xanh','Thanh mát, nhiều cây',['#eef5e9','#40772f','#c9793a']],
  ['bien','Biển chiều','Xanh biển, mát mắt',['#ecf3f9','#226ca0','#e8913a']],
  ['keo','Kẹo ngọt','Hồng pastel, vui tươi',['#fff1f6','#bf3f6d','#7a6ad8']],
  ['dem','Phố đêm','Tối, dịu, đỡ chói',['#15141b','#ff8a6b','#7fd1b9']],
];
const LAYOUTS=[['auto','Tự động','Theo kích thước màn hình'],['phone','Điện thoại','Thanh dưới, bảng trượt lên'],['tablet','Máy tính bảng','Thanh bên gọn, 2 cột'],['desktop','Máy tính','Thanh bên + bảng phải']];
const TRACKS=[['auto','Theo nghề'],['calm','Êm dịu'],['bright','Tươi vui'],['off','Tắt nhạc']];

const toggle=(key,label,on,note='')=>`<label class="switch-row"><span class="grow"><b>${label}</b>${note?`<small class="muted block">${note}</small>`:''}</span><input type="checkbox" role="switch" data-setting="${key}" ${on?'checked':''}><i aria-hidden="true"></i></label>`;
const segment=(key,items,value,kind='choice')=>`<div class="segmented" role="radiogroup">${items.map(([id,label])=>`<button type="button" role="radio" aria-checked="${id===value}" class="${id===value?'active':''}" data-action="v4Setting" data-key="${key}" data-value="${esc(id)}" data-kind="${kind}">${label}</button>`).join('')}</div>`;

export function settingsView(env){
  const {api,ui}=env,s=api.state.settings,tab=ui.setTab||'play';
  const tabs=[['account','Tài khoản','user'],['play','Cách chơi','leaf'],['look','Giao diện','palette'],['sound','Âm thanh','music'],['lang','Ngôn ngữ','globe'],['notify','Thông báo','bell'],['data','Dữ liệu','shield']];
  const nav=`<nav class="settings-tabs" role="tablist">${tabs.map(([id,label,ic])=>`<button role="tab" aria-selected="${id===tab}" class="${id===tab?'active':''}" data-action="v4SetTab" data-tab="${id}">${icon(ic,17)}<span>${label}</span></button>`).join('')}</nav>`;
  let body='';
  const feedbackBlock=`<section class="settings-block settings-feedback"><h3>${icon('chat',18)} Góp ý</h3><p class="small muted">Gặp lỗi, có ý tưởng hay thấy chỗ nào khó dùng? Nhà làm game đọc từng góp ý và có thể trả lời bạn.</p>${button('💬 Góp ý cho nhà làm game','gopy',{},'small')}</section>`;
  if(tab==='account')body=accountPane(env);
  if(tab==='play')body=`${accountNudge(env)}<form id="settingsForm" class="settings-block">
      <h3>${icon('user',18)} Hồ sơ</h3>
      <label class="field">Tên của bạn<input class="input" id="player-name" data-preserve maxlength="24" required value="${esc(api.state.name)}"></label>
      <button class="btn primary full" type="submit">Lưu</button>
    </form>
    ${tutorialSettings()}
    ${feedbackBlock}
    <section class="settings-block">${toggle('reduceMotion','Giảm chuyển động',s.reduceMotion)}${toggle('largeText','Chữ lớn',s.largeText)}</section>
    ${api.ai?.configured?`<section class="settings-block"><h3>${icon('chat',18)} Trò chuyện bằng AI</h3>
      ${toggle('aiConsent','Nhân vật trò chuyện bằng AI',s.aiConsent,'Khi bật, tin nhắn bạn gõ trong Trò chuyện, lời trả lời review và vài dữ kiện của lượt chơi được gửi tới nhà cung cấp AI của máy chủ. Đừng gõ thông tin cá nhân thật. Xem <a href="/privacy" target="_blank" rel="noopener">Quyền riêng tư</a>.')}
    </section>`:''}`;
  if(tab==='look'){
    const pref=layoutPref(),mode=document.documentElement.dataset.layout;
    body=`<section class="settings-block"><h3>${icon('palette',18)} Phong cách</h3><div class="theme-grid">${THEMES.map(([id,name,desc,sw])=>`<button type="button" class="theme-card ${s.uiTheme===id?'active':''}" data-action="v4Setting" data-key="uiTheme" data-value="${id}" aria-pressed="${s.uiTheme===id}"><span class="swatches">${sw.map(c=>`<i style="background:${c}"></i>`).join('')}</span><b>${name}</b><small>${desc}</small></button>`).join('')}</div></section>
    <section class="settings-block"><h3>${icon('layout',18)} Bố cục màn hình</h3><p class="small muted">Đang dùng: <b>${{phone:'Điện thoại',tablet:'Máy tính bảng',desktop:'Máy tính'}[mode]||mode}</b></p>
      <div class="layout-grid">${LAYOUTS.map(([id,name,desc])=>`<button type="button" class="layout-card ${pref===id?'active':''}" data-action="v4Layout" data-value="${id}" aria-pressed="${pref===id}"><span class="layout-thumb ${id}"><i></i><i></i><i></i></span><b>${name}</b><small>${desc}</small></button>`).join('')}</div></section>`;
  }
  if(tab==='sound')body=`<section class="settings-block">${toggle('sound','Âm thanh thao tác',s.sound)}
      <label class="field">Âm lượng hiệu ứng <output>${s.sfxVolume}</output><input type="range" min="0" max="100" step="5" value="${s.sfxVolume}" data-setting-range="sfxVolume"></label></section>
    <section class="settings-block"><h3>${icon('music',18)} Nhạc nền</h3>
      ${toggle('music','Bật nhạc nền',s.music)}
      <div class="field">Kiểu nhạc${segment('musicTrack',TRACKS,s.musicTrack)}</div>
      <label class="field">Âm lượng nhạc <output>${s.musicVolume}</output><input type="range" min="0" max="100" step="5" value="${s.musicVolume}" data-setting-range="musicVolume"></label></section>`;
  if(tab==='lang')body=`<section class="settings-block"><h3>${icon('globe',18)} Ngôn ngữ / Language</h3>
      <div class="lang-grid">${[['vi','🇻🇳','Tiếng Việt','Ngôn ngữ gốc'],['en','🇬🇧','English','Interface & story text translated']].map(([id,flag,name,desc])=>`<button type="button" class="lang-card ${s.lang===id?'active':''}" data-action="v4Setting" data-key="lang" data-value="${id}" data-no-translate><span class="flag">${flag}</span><b>${name}</b><small>${desc}</small></button>`).join('')}</div></section>`;
  if(tab==='notify'){
    const st=ui.pushState;
    let status='';
    if(!st)status=`<p class="muted small">Đang kiểm tra trình duyệt…</p>`;
    else if(!st.available)status=`<div class="notice">${icon('bell',17)}<div>${{server:'Máy chủ này chưa bật thông báo đẩy.',browser:'Trình duyệt này chưa hỗ trợ thông báo đẩy.',denied:'Bạn đã chặn thông báo cho trang này. Mở cài đặt trang của trình duyệt để cho phép lại.',ios_install:'Trên iPhone/iPad: bấm <b>Chia sẻ → Thêm vào MH chính</b>, mở game từ biểu tượng mới rồi bật thông báo ở đây.'}[st.reason]}</div></div>`;
    else status=`${pill(st.subscribed?'Đang bật trên thiết bị này':'Đang tắt',st.subscribed?'green':'')}<div class="row wrap space-top">${st.subscribed?button('Tắt thông báo','v4PushOff',{},'ghost'):button(icon('bell',16)+' Bật thông báo','v4PushOn',{},'primary')}${st.subscribed?button('Nhắc mở quán lúc 19:00 mỗi ngày','v4PushDaily',{},'ghost small'):''}</div>`;
    body=`<section class="settings-block"><h3>${icon('bell',18)} Thông báo đẩy</h3>${status}</section>
      ${isIOS()&&!isStandalone()?`<section class="settings-block"><h3>${icon('download',18)} Cài như ứng dụng</h3><p class="small muted">Safari → Chia sẻ → Thêm vào MH chính.</p></section>`:''}`;
    if(!st)pushState(api).then(x=>{ui.pushState=x;env.renderSheet();}).catch(()=>{ui.pushState={available:false,reason:'browser'};env.renderSheet();});
  }
  if(tab==='data')body=`${feedbackBlock}<section class="settings-block"><h3>${icon('download',18)} Bản lưu</h3>
      <div class="row wrap">${button('Xuất bản lưu','export',{},'small')}${button('Nhập bản lưu','import',{},'small ghost')}</div><input type="file" id="import-file" accept=".json,application/json" hidden>
      <div class="divider"></div>${button('Bắt đầu lại riêng nghề này','resetCareer',{},'danger small')}</section>
    <section class="settings-block"><h3>${icon('shield',18)} Quyền riêng tư</h3>
      ${toggle('publicProfile','Hiện quán của tôi ở Phố nghề',s.publicProfile)}
      <p class="small"><a href="/privacy" target="_blank" rel="noopener">Chính sách quyền riêng tư</a> · <a href="/terms" target="_blank" rel="noopener">Điều khoản sử dụng</a> · <a href="mailto:trachanhtv.works@gmail.com">trachanhtv.works@gmail.com</a></p>
      <div class="danger-zone"><b>Xóa dữ liệu của tôi</b><p class="small muted">Xóa vĩnh viễn bản lưu, tài khoản, hồ sơ, bài viết, quà, hàng ở chợ và đăng ký thông báo trên máy chủ. Không thể hoàn tác.</p>${button('Xóa toàn bộ dữ liệu','v4DeleteData',{},'danger small')}</div></section>`;
  return head('Cài đặt','','THIẾT LẬP')+`<div class="sheet-body settings-v4">${nav}<div class="settings-pane">${body}</div></div>`;
}

export async function settingsAction(action,data,el,env){
  const {api,ui,cmd,renderSheet,toast,confirmAction}=env;
  if(await accountAction(action,data,el,env))return true;
  switch(action){
    case'v4SetTab':ui.setTab=data.tab;renderSheet(false);return true;
    case'v4PushOn':try{const r=await enablePush(api);toast(r.message);ui.pushState=null;}catch(e){toast(e.message,true);}renderSheet();return true;
    case'v4PushOff':try{const r=await disablePush(api);toast(r.message);ui.pushState=null;}catch(e){toast(e.message,true);}renderSheet();return true;
    case'v4PushDaily':try{await enablePush(api,{daily:true,hour:19});toast('Sẽ nhắc bạn mở quán lúc 19:00 mỗi ngày.');}catch(e){toast(e.message,true);}return true;
    case'v4DeleteData':{
      if(!await confirmAction('Xóa toàn bộ dữ liệu?','Bản lưu mọi nghề, hồ sơ Phố nghề và thông báo sẽ bị xóa vĩnh viễn khỏi máy chủ.','Xóa vĩnh viễn'))return true;
      try{await disablePush(api).catch(()=>{});const r=await api.deleteAccount();toast(r.message);setTimeout(()=>location.replace('/'),900);}catch(e){toast(e.message,true);}
      return true;
    }
  }
  return false;
}

/** Checkbox switches and range sliders save immediately. */
export async function settingsChange(el,env){
  if(el.dataset.setting){await env.cmd('settings',{[el.dataset.setting]:el.checked},{quiet:true});return true;}
  if(el.dataset.settingRange){await env.cmd('settings',{[el.dataset.settingRange]:Number(el.value)},{quiet:true});return true;}
  return false;
}
export function settingsInput(el){
  if(el.dataset.settingRange){const out=el.closest('label')?.querySelector('output');if(out)out.textContent=el.value;return true;}
  return false;
}
