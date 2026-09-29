/** AI characters in "Trò chuyện": chat bubbles, typing indicator, quick replies and
 * the one-time AI notice. The server stores every line (scripted first, then the AI
 * wording when it passes the guards); this module only renders and sends.
 * Contract: docs/superpowers/specs/2026-09-29-ai-characters-design.md */
import {icon,escapeHTML as esc} from '../icons.js';

export const CHAT_MAX=200;
const pending={}; // npc id -> {text}
const en=api=>api.state?.settings?.lang==='en';
const attrs=obj=>Object.entries(obj).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');

/** AI voices characters only when the server has a provider and the player allows it. */
export const aiOn=api=>!!(api.ai?.configured&&api.state?.settings?.aiConsent);
export const chatBusy=npc=>!!pending[npc];

function bubble(m,name){
  if(m.role==='user')return `<div class="bubble user" data-no-translate><div>${esc(m.text)}</div></div>`;
  const ai=m.mode==='ai';
  const badge=ai?`<span class="ai-badge" title="${esc('Lời gốc: '+(m.canonical||''))}" aria-label="Câu trả lời do AI viết">AI</span>`:'';
  return `<div class="bubble npc${ai?' ai':''}"${ai?' data-no-translate':''}>${badge}<div>${esc(m.text)}</div></div>`;
}

/** Message list: stored lines, the pending player line and a typing indicator. */
export function chatMessages(env,{npc,name,messages,opening}){
  const rows=messages.length?messages.map(m=>bubble(m,name)).join(''):`<div class="bubble npc"><div>${esc(opening||'Chào bạn! Hôm nay mình trò chuyện một chút nhé?')}</div></div>`;
  const wait=pending[npc];
  const typing=wait?`<div class="bubble user pending" data-no-translate><div>${esc(wait.text)}</div></div><div class="bubble npc typing" role="status" aria-label="${esc(name)} đang trả lời…"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span></div>`:'';
  const note=noticeWanted(env.api)?`<div class="ai-notice inline" role="region" aria-label="AI">${noticeHTML(env.api)}</div>`:'';
  return `${note}<div id="messages" class="chat-messages" role="log" aria-live="polite">${rows}${typing}</div>`;
}

/** Quick replies (scripted options + server suggestions), input with a 200-char limit. */
export function chatFooter(env,{npc,name,quick=[],suggestions=[]}){
  const {api}=env,busy=!!pending[npc],on=aiOn(api);
  const chips=quick.map(([label,text])=>`<button type="button" class="btn ghost small" data-action="quickChat"${attrs({text})}${busy?' disabled':''}>${esc(label)}</button>`);
  for(const s of suggestions||[]){
    if(s.action==='ask'&&s.task)chips.unshift(`<button type="button" class="btn ghost small" data-command="ask" data-payload="${esc(JSON.stringify({task:s.task}))}">${esc(s.label)}</button>`);
    else if(s.action==='open_task'&&s.task)chips.unshift(`<button type="button" class="btn ghost small" data-action="job"${attrs({task:s.task})}>${esc(s.label)}</button>`);
  }
  const mode=on?`<small class="chat-mode">${icon('sparkle',13)} ${en(api)?'AI replies · no real personal info':'AI trả lời · đừng gõ thông tin thật'}</small>`:'';
  return `<footer class="sheet-foot chat-foot"><div class="quick-replies">${chips.join('')}</div>`+
    `<form id="chatForm" class="chat-form"><textarea id="chat-input" data-preserve rows="1" placeholder="Nói gì đó với ${esc(name)}…" maxlength="${CHAT_MAX}" required aria-label="Tin nhắn tới ${esc(name)}" aria-describedby="chat-count"></textarea>`+
    `<button type="submit" class="btn primary" aria-label="Gửi"${busy?' disabled':''}>${icon('send',17)}<span>Gửi</span></button></form>`+
    `<div class="chat-meta">${mode}<output id="chat-count" class="chat-count" aria-live="off">0/${CHAT_MAX}</output></div></footer>`;
}

function queued(api,fn){const job=api.queue.then(fn,fn);api.queue=job.catch(()=>{});return job;}
function rid(){return globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;}

/** Send one line. AI on: POST /api/ai/chat (stores the turn); otherwise the plain `talk`
 * command. Returns the command result ({reply,suggestions}) or null. */
export async function aiTalk(env,npc,text){
  const {api,ui,cmd,toast,renderSheet}=env;
  text=String(text||'').trim().slice(0,CHAT_MAX);
  if(!text||!npc||pending[npc])return null;
  if(!aiOn(api)||!api.ai?.chat)return cmd('talk',{npc,text},{quiet:true});
  const career=api.state.current,redraw=()=>{if(ui.view==='chat'&&ui.npc===npc)renderSheet();};
  pending[npc]={text};redraw();
  const send=()=>queued(api,()=>api.post('/api/ai/chat',{career,npc,text,request_id:rid(),expected_revision:api.revision},20000));
  try{
    let data;
    try{data=await send();}
    catch(error){
      if(error.status===409&&error.data?.state){api.accept(error.data);data=await send();}
      else throw error;
    }
    delete pending[npc];api.accept(data);
    return data.result;
  }catch(error){
    delete pending[npc];
    if(!error.status)return cmd('talk',{npc,text},{quiet:true}); // lost connection to the AI route: scripted line
    toast(error.message||'Chưa gửi được tin nhắn.',true);return null;
  }finally{delete pending[npc];redraw();}
}

/* ---- one-time notice ----------------------------------------------------- */
let dismissed=false,noticeEnv=null;
function noticeWanted(api){const s=api.state?.settings;return !dismissed&&!!api.ai?.configured&&!!s?.aiConsent&&s.aiNoticeSeen===false;}
function noticeHTML(api){
  const E=en(api);
  return `<span class="ai-notice-icon" aria-hidden="true">${icon('sparkle',18)}</span><p>${E?'Characters chat using AI. Do not type real personal information.':'Nhân vật trò chuyện bằng AI. Đừng gõ thông tin cá nhân thật.'} <a href="/privacy" target="_blank" rel="noopener">${E?'Privacy':'Quyền riêng tư'}</a></p>`+
    `<div class="ai-notice-actions"><button type="button" class="btn ghost small" data-ai-notice="off">${E?'Turn AI off':'Tắt AI'}</button><button type="button" class="btn primary small" data-ai-notice="ok">${E?'Got it':'Đã hiểu'}</button></div>`;
}
/** Floating card: over the scene, or over a sheet without a footer (home). Sheets with
 * actions at the bottom keep it hidden (the chat sheet shows it inline instead). */
function place(el){
  const top=[document.getElementById('confirmDialog'),document.getElementById('sheet')].find(d=>d?.open)||document.body;
  if(el.parentNode!==top)top.append(el);
  el.hidden=top!==document.body&&!!top.querySelector('.sheet-foot');
}
function sync(){
  const api=noticeEnv?.api;if(!api)return;
  let el=document.getElementById('aiNotice');
  if(!noticeWanted(api)){el?.remove();document.querySelectorAll('.ai-notice.inline').forEach(x=>x.remove());return;}
  if(!el){el=document.createElement('div');el.id='aiNotice';el.className='ai-notice';el.setAttribute('role','region');el.setAttribute('aria-label','AI');el.innerHTML=noticeHTML(api);}
  place(el);
}
/** Shows a small, non-blocking card the first time AI is on; persists through `settings`. */
export function aiNoticeBoot(env){
  noticeEnv=env;
  env.api.addEventListener('state',sync);
  const watch=new MutationObserver(sync);
  for(const id of ['sheet','confirmDialog']){const d=document.getElementById(id);if(d)watch.observe(d,{attributes:true,attributeFilter:['open']});}
  const content=document.getElementById('sheetContent');if(content)watch.observe(content,{childList:true});
  sync();
}
document.addEventListener('click',async e=>{
  const b=e.target.closest?.('[data-ai-notice]');if(!b||!noticeEnv)return;
  e.preventDefault();e.stopPropagation();
  const env=noticeEnv,off=b.dataset.aiNotice==='off';
  dismissed=true;sync();
  const r=await env.cmd('settings',off?{aiConsent:false,aiNoticeSeen:true}:{aiNoticeSeen:true},{quiet:true});
  if(r&&off)env.toast(en(env.api)?'AI is off. Characters use scripted lines.':'Đã tắt AI. Nhân vật dùng lời thoại có sẵn. Bật lại trong Cài đặt → Cách chơi.');
  if(!r){dismissed=false;sync();}
},true);

// Live character counter and Enter-to-send (Shift+Enter = new line; never while an IME is composing).
document.addEventListener('input',e=>{if(e.target.id==='chat-input'){const out=document.getElementById('chat-count');if(out)out.textContent=`${e.target.value.length}/${CHAT_MAX}`;}});
document.addEventListener('keydown',e=>{if(e.target.id==='chat-input'&&e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){e.preventDefault();e.target.form?.requestSubmit();}});
