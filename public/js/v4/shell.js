/** Shell-level behaviour: layout mode (phone/tablet/desktop), colour theme,
 * language, background music. Other modules stay unaware of the device. */
import {setLanguage,language} from './i18n.js';

/** Keep the phone "Thêm" button's aria-expanded in step with the menu. */
const syncMenu=()=>{const open=document.documentElement.classList.contains('menu-open');document.querySelectorAll('[data-action="v4Menu"]').forEach(b=>b.setAttribute('aria-expanded',String(open)));};
const KEY='mnl.layout',THEME_KEY='mnl.theme';
const read=()=>{try{return localStorage.getItem(KEY)||'auto';}catch{return 'auto';}};
const write=v=>{try{localStorage.setItem(KEY,v);}catch{}};
// Paint the last used theme before the first state arrives (no light flash in "Phố đêm").
try{const t=localStorage.getItem(THEME_KEY);if(t&&/^[a-z_]+$/.test(t))document.documentElement.dataset.theme=t;}catch{/* storage blocked */}

export function detectLayout(){
  const w=window.innerWidth,h=window.innerHeight,coarse=matchMedia('(pointer:coarse)').matches;
  if(w<700||(coarse&&Math.min(w,h)<500))return 'phone';
  if(w<1100)return 'tablet';
  return 'desktop';
}
export function applyLayout(){
  const root=document.documentElement,pref=read(),w=window.innerWidth;
  let mode=pref==='auto'?detectLayout():pref;
  // A forced layout still has to fit: desktop needs ~760px, tablet ~560px.
  if(mode==='desktop'&&w<760)mode='tablet';
  if(mode==='tablet'&&w<560)mode='phone';
  if(mode!=='phone')root.classList.remove('menu-open');
  root.dataset.layoutPref=pref;
  root.dataset.orientation=window.innerWidth>window.innerHeight?'landscape':'portrait';
  if(root.dataset.layout!==mode){root.dataset.layout=mode;window.dispatchEvent(new Event('layoutchange'));}
  return mode;
}
export const layoutPref=read;
export function setLayoutPref(v){write(['auto','phone','tablet','desktop'].includes(v)?v:'auto');applyLayout();}

function applyTheme(settings){
  const root=document.documentElement;
  root.dataset.theme=settings.uiTheme||'kem';
  root.classList.toggle('reduce-motion',!!settings.reduceMotion);
  root.classList.toggle('large-text',!!settings.largeText);
  try{localStorage.setItem(THEME_KEY,root.dataset.theme);}catch{/* storage blocked */}
  const meta=document.querySelector('meta[name="theme-color"]');
  if(meta)meta.content=getComputedStyle(root).getPropertyValue('--bg').trim()||'#fff6ee';
}

let music=null;
async function syncMusic(env){
  const st=env.api.state?.settings;if(!st)return;
  if(!music){const mod=await import('./music.js');music=new mod.Music();}
  music.configure({on:st.music,volume:st.musicVolume,track:st.musicTrack,career:env.api.state.current,open:env.api.state.careers?.[env.api.state.current]?.open});
}

export const shell={
  boot(env){
    applyLayout();applyTheme(env.api.state.settings);
    let t;window.addEventListener('resize',()=>{clearTimeout(t);t=setTimeout(applyLayout,120);});
    window.addEventListener('orientationchange',()=>setTimeout(applyLayout,200));
    const unlock=()=>{syncMusic(env).then(()=>music?.unlock());};
    window.addEventListener('pointerdown',unlock,{once:true});
    window.addEventListener('keydown',unlock,{once:true});
    document.addEventListener('visibilitychange',()=>{if(music)music.setHidden(document.hidden);});
    // Phone "Thêm" menu (the rail as a bottom sheet): any tap closes it; taps
    // outside the menu are swallowed so they don't also hit the scene.
    const root=document.documentElement;
    document.addEventListener('click',e=>{
      if(!root.classList.contains('menu-open'))return;
      root.classList.remove('menu-open');syncMenu();
      if(!e.target.closest('#rail')){e.preventDefault();e.stopPropagation();}
    },true);
    window.addEventListener('keydown',e=>{if(e.key==='Escape'&&root.classList.contains('menu-open')){root.classList.remove('menu-open');syncMenu();e.stopPropagation();}},true);
  },
  update(env){
    applyTheme(env.api.state.settings);
    if(env.api.state.settings.lang!==language())setLanguage(env.api.state.settings.lang).then(()=>{if(env.api.state.settings.lang==='vi')location.reload();});
    if(music||env.api.state.settings.music)syncMusic(env);
  },
  async action(action,data,el,env){
    switch(action){
      case'v4Layout':setLayoutPref(data.value);env.renderSheet();return true;
      case'v4Menu':document.documentElement.classList.toggle('menu-open');syncMenu();return true;
      case'homeCat':env.ui.homeCat=data.cat;env.renderSheet();return true;
      case'v4Setting':{
        let value=data.value;
        if(data.kind==='bool')value=data.value==='true';
        if(data.kind==='int')value=Number(data.value);
        await env.cmd('settings',{[data.key]:value},{quiet:true});return true;
      }
    }
    return false;
  },
  async submit(){return false;},
};
