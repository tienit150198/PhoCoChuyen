/** Shell-level behaviour: layout mode (phone/tablet/desktop), colour theme,
 * language, background music. Other modules stay unaware of the device. */
import {setLanguage,language} from './i18n.js';
import {emojiOf} from './journey.js';

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
  applyCareer();
}

/* ---- Career accent -------------------------------------------------------
 * Each career tints a few pieces of chrome (task card, dock, day ring, sheet
 * eyebrows, the job sheet) with its own colour: catalogue meta.color, the same
 * source the scenes paint with. The colour is fitted to the theme: in a light
 * theme it is darkened (same hue) until white text reads >= 4.5:1 on it; in
 * the dark theme it is lifted and gets a deep same-hue ink. Surfaces and text
 * stay the theme's. Tokens: --career --career-strong --career-soft
 * --career-ink --career-text (docs/DESIGN.md). */
const rgbOf=h=>{h=String(h||'').trim().replace('#','');if(h.length===3)h=[...h].map(c=>c+c).join('');if(!/^[0-9a-f]{6}$/i.test(h))return null;const n=parseInt(h,16);return [n>>16&255,n>>8&255,n&255];};
const hexOf=c=>'#'+c.map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0')).join('');
const lum=c=>{const f=v=>(v/=255)<=.03928?v/12.92:((v+.055)/1.055)**2.4;return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2]);};
export const contrast=(a,b)=>{const x=lum(rgbOf(a)),y=lum(rgbOf(b));return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
const hslOf=([r,g,b])=>{r/=255;g/=255;b/=255;const mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/2,d=mx-mn;if(!d)return [0,0,l*100];
  const s=d/(1-Math.abs(2*l-1)),h=mx===r?((g-b)/d+6)%6:mx===g?(b-r)/d+2:(r-g)/d+4;return [h*60,s*100,l*100];};
const hsl=(h,s,l)=>{s=Math.max(0,Math.min(100,s))/100;l=Math.max(0,Math.min(100,l))/100;const k=n=>(n+h/30)%12,a=s*Math.min(l,1-l);
  return hexOf([0,8,4].map(n=>255*(l-a*Math.max(-1,Math.min(k(n)-3,9-k(n),1)))));};
const mixHex=(a,b,t)=>{const x=rgbOf(a),y=rgbOf(b);return hexOf(x.map((v,i)=>v+(y[i]-v)*t));};
const readable=(c,grounds)=>Math.min(...grounds.map(g=>contrast(c,g)));
/** Theme-fitted accent set for one career colour. theme = {bg,surface,surface2} as hex. */
export function careerPalette(color,theme){
  const AA=4.6; // WCAG AA is 4.5:1; a little headroom for rounding
  const base=rgbOf(color)||rgbOf('#c44b30'),[h,s0,l0]=hslOf(base),dark=lum(rgbOf(theme.bg)||[255,255,255])<.2;
  let career,strong,ink,soft,text,l=l0;
  if(dark){
    const s=Math.min(s0,78);l=Math.max(l0,50);
    while(l<88&&lum(rgbOf(hsl(h,s,l)))<.32)l++;
    career=hsl(h,s,l);strong=hsl(h,s,l-10);
    let il=12;ink=hsl(h,Math.min(s,60),il);while(il>0&&contrast(ink,career)<AA)ink=hsl(h,Math.min(s,60),--il);
    soft=mixHex(theme.surface,career,.2);
    let tl=l;text=career;while(tl<96&&readable(text,[theme.bg,theme.surface,theme.surface2,soft])<AA)text=hsl(h,s,++tl);
  }else{
    while(l>0&&contrast('#ffffff',hsl(h,s0,l))<AA)l--;
    career=hsl(h,s0,l);strong=hsl(h,s0,l-8);ink='#ffffff';
    soft=mixHex(theme.surface,career,.13);
    let tl=l;text=career;while(tl>0&&readable(text,[theme.bg,theme.surface,theme.surface2,soft])<AA)text=hsl(h,s0,--tl);
  }
  return {career,strong,soft,ink,text};
}
let careerMeta=null,careerKey='',themeKey='';
/** Set html[data-career] and the --career-* tokens (again when the theme changes). */
function applyCareer(m){
  if(m)careerMeta=m;m=careerMeta;if(!m)return;
  const root=document.documentElement,cs=getComputedStyle(root),v=k=>cs.getPropertyValue(k).trim();
  const theme={bg:v('--bg'),surface:v('--surface'),surface2:v('--surface-2')};
  if(!rgbOf(theme.bg)||!rgbOf(theme.surface)||!rgbOf(theme.surface2))return;
  const key=[m.id,m.color,theme.bg,theme.surface,theme.surface2].join('|');if(key===careerKey)return;careerKey=key;
  const p=careerPalette(m.color,theme);root.dataset.career=m.id||'';
  for(const [k,val] of Object.entries({'--career':p.career,'--career-strong':p.strong,'--career-soft':p.soft,'--career-ink':p.ink,'--career-text':p.text}))root.style.setProperty(k,val);
}

let music=null;
async function syncMusic(env){
  const st=env.api.state?.settings;if(!st)return;
  if(!music){const mod=await import('./music.js');music=new mod.Music();}
  music.configure({on:st.music,volume:st.musicVolume,track:st.musicTrack,career:env.api.state.current,open:env.api.state.careers?.[env.api.state.current]?.open});
}

export const shell={
  /** Called by renderMain with the current career's catalogue meta. */
  career(m){applyCareer(m);},
  /** The career's identity mark for the scene title card (decorative). */
  mark(m){return `<span class="scene-mark" aria-hidden="true">${emojiOf(m||{})}</span>`;},
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
    // Every command lands here: re-theme only when a theme setting changed (applyTheme reads computed
    // style, which would force a full style recalc right after each re-render).
    const st=env.api.state.settings,key=[st.uiTheme,st.reduceMotion,st.largeText].join('|');
    if(key!==themeKey){themeKey=key;applyTheme(st);}
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
