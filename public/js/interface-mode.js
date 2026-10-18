/** Renderer preference belongs to the authenticated save; never to a browser-wide cache. */
import {stylesheet} from './lazy.js';
import {setIconRenderer} from './icons.js';
import {kindOf} from './scenes/vocabulary.js';

export const newInterface=state=>state?.settings?.newInterface!==false;
/** A new neighbour (story, first life day: v4/onboard.js firstDay) never saw the old interface: no question over the
 * intro (the server marks it seen at naming, game/journey.py _welcome_settings). */
const newcomer=state=>Boolean(state?.journey?.story&&(Number(state.journey.life_day)||1)<=1);
export const interfacePromptDue=state=>newInterface(state)&&state?.settings?.interfacePromptSeen!==true&&!newcomer(state);

/** A full page restart releases the old canvas, listeners and styles after the server confirms the choice. */
const saving=new WeakMap();
export function saveInterface(env,enabled){
  if(saving.has(env.api))return saving.get(env.api);
  const changed=newInterface(env.api.state)!==enabled;
  const request=(async()=>{
    const result=await env.cmd('settings',{newInterface:enabled,interfacePromptSeen:true},{quiet:true});
    if(!result)return false;
    if(changed)location.reload();
    return true;
  })();
  saving.set(env.api,request);
  return request.finally(()=>saving.delete(env.api));
}

/** Decide only after bootstrap, so a different account on this device gets its own saved choice. */
export async function loadInterface(state){
  if(globalThis.document?.documentElement)document.documentElement.dataset.game=newInterface(state)?'isometric':'classic';
  if(newInterface(state)){
    const [iso]=await Promise.all([import('./iso-boot.js'),stylesheet('/css/isometric.css'),stylesheet('/css/cozy-reference.css')]);
    return {iso,World:null};
  }
  const [{BobaWorld},{classicIcon}]=await Promise.all([import('./boba-world.js'),import('./classic-icons.js')]);
  setIconRenderer(classicIcon);
  return {iso:null,World:BobaWorld};
}

export function loadCareerScene(state,id){
  return newInterface(state)?Promise.resolve():import(`./scenes/${kindOf(id)}.js`).catch(()=>{});
}

let offering=null;
/** One decision per account, before the tutorial and automatic announcement cards. Escape keeps the new look. */
export function promptInterface(env){
  if(!interfacePromptDue(env.api.state))return Promise.resolve(true);
  return askInterface(env);
}
/** The same question asked on purpose (2.5D ☰ Thêm → "Giao diện cũ", isometric-shell.js): `title`, `text` replace the
 * first-visit wording. Resolves true when the player keeps the 2.5D town. */
export function askInterface(env,{title='Bạn có muốn quay về giao diện cũ?',text='Đổi lúc nào cũng được trong Cài đặt → Giao diện, tiến trình giữ nguyên.'}={}){
  if(offering)return offering;
  const back=document.activeElement,dialog=document.createElement('dialog');
  dialog.id='interfacePrompt';dialog.className='confirm-dialog';
  dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-labelledby','interfacePromptTitle');
  dialog.setAttribute('aria-describedby','interfacePromptDescription');
  const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
  dialog.innerHTML=`<h2 id="interfacePromptTitle">${esc(title)}</h2>`+
    `<p id="interfacePromptDescription">${esc(text)}</p>`+
    '<div class="row wrap space-top"><button type="button" class="btn big" data-interface="legacy">Về giao diện cũ</button><button type="button" class="btn primary big" data-interface="new">Giữ giao diện mới</button></div><p role="status" aria-live="polite"></p>';
  let resolve,busy=false;
  offering=new Promise(done=>{resolve=done;});
  const buttons=()=>[...dialog.querySelectorAll('button')].filter(b=>!b.disabled);
  const choose=async enabled=>{
    if(busy)return;busy=true;
    // Keeping the interface in use needs no reload: close at once and save in the background, so a failed save (a
    // deploy's 503, a weak network) never traps the player behind this prompt; it simply shows again next visit (#344).
    if(enabled===newInterface(env.api.state)){
      dialog.close();dialog.remove();offering=null;back?.isConnected&&back.focus({preventScroll:true});resolve(enabled);
      saveInterface(env,enabled).catch(error=>console.warn('interface preference:',error));return;
    }
    for(const button of dialog.querySelectorAll('button'))button.disabled=true;
    const status=dialog.querySelector('[role="status"]');status.textContent='Đang lưu lựa chọn…';
    try{
      if(await saveInterface(env,enabled)){
        dialog.close();dialog.remove();offering=null;back?.isConnected&&back.focus({preventScroll:true});resolve(enabled);return;
      }
    }catch(error){console.warn('interface preference:',error);}
    busy=false;for(const button of dialog.querySelectorAll('button'))button.disabled=false;
    status.textContent='Chưa lưu được lựa chọn. Kiểm tra kết nối rồi thử lại nhé.';
    dialog.querySelector(enabled?'[data-interface="new"]':'[data-interface="legacy"]').focus();
  };
  dialog.addEventListener('click',event=>{
    const button=event.target.closest('button[data-interface]');
    if(button&&dialog.contains(button))return choose(button.dataset.interface==='new');
  });
  dialog.addEventListener('cancel',event=>{event.preventDefault();return choose(true);});
  dialog.addEventListener('keydown',event=>{
    if(event.key!=='Tab')return;
    const list=buttons(),first=list[0],last=list.at(-1),active=document.activeElement;
    if(!first){event.preventDefault();return;}
    if(event.shiftKey&&(active===first||!dialog.contains(active))){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&(active===last||!dialog.contains(active))){event.preventDefault();first.focus();}
  });
  document.body.append(dialog);dialog.showModal();dialog.querySelector('[data-interface="new"]').focus();
  return offering;
}
