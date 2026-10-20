/** 💐 Thiệp 20/10 (/2010, game/event2010.py): write a card, share its link; anyone opens it without the game.
 * The server renders public/2010.html with the page's data (<script type="application/json" id="ev-data">: the home,
 * one card, or why a card does not open) and the link-preview tags. This module draws everything else:
 * - the writer (signed-in accounts): who to, the words, the signature, 13 themes with a live preview, stickers; the draft
 *   is kept on this device (localStorage) so signing in on the game page and coming back loses nothing;
 * - sharing: copy, the phone's own share sheet, Facebook, Messenger, Zalo (the share sheet, else the copied link);
 * - reading: an envelope that opens (each theme its own reveal and falling petals / rising balloons / stars), ❤ thả tim
 *   (taps gathered, sent in small batches), "Viết thiệp tặng lại", report / delete;
 * - prefers-reduced-motion: no falling things, the envelope opens at once.
 * Every word from people goes in through esc(). All art is drawn here (inline SVG), no picture is downloaded. */

const $=(s,el=document)=>el.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const still=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const DRAFT='mnl.ev2010.draft',BACK='mnl.ev2010.back';
const store={get(k){try{return JSON.parse(localStorage.getItem(k)||'null');}catch{return null;}},set(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch{/* blocked */}},del(k){try{localStorage.removeItem(k);}catch{/* blocked */}}};
const dm=t=>{const d=new Date(t*1000);return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}`;};
let DATA={},ME=null,toastTimer=0;
try{DATA=JSON.parse($('#ev-data')?.textContent||'{}')||{};}catch{DATA={};}

/* ------------------------------------------------------------ art: small SVG pieces, drawn here */
const heartD='M0 7C-11-1-9-12 0-6 9-12 11-1 0 7Z';
const starD=(r=10,i=4.2)=>{let d='';for(let k=0;k<10;k++){const a=Math.PI/5*k-Math.PI/2,R=k%2?i:r;d+=(k?'L':'M')+(Math.cos(a)*R).toFixed(1)+' '+(Math.sin(a)*R).toFixed(1);}return d+'Z';};
const g=(x,y,inner,s=1,r=0)=>`<g transform="translate(${x} ${y}) rotate(${r}) scale(${s})">${inner}</g>`;
const leaf=(x,y,r,s=1,c='#5a9a5a')=>g(x,y,`<path d="M0 0C6-5 16-5 22 0 16 5 6 5 0 0Z" fill="${c}"/><path d="M1 0H20" stroke="#ffffff55" stroke-width=".8"/>`,s,r);
const rose=(x,y,s=1,c='#d6264f',d='#9d0b33')=>g(x,y,`<circle r="13" fill="${c}"/><path d="M-9 3C-9-7 6-10 8-2 9 5 0 8-4 4-7 0-2-5 2-3" fill="none" stroke="${d}" stroke-width="2.2" stroke-linecap="round"/><path d="M-12 6C-6 13 6 13 12 5" fill="none" stroke="${d}" stroke-width="1.6" opacity=".7"/><circle cx="-4" cy="-6" r="2.2" fill="#fff" opacity=".35"/>`,s);
const tulip=(x,y,s=1,c='#ff8fab',d='#e5668b')=>g(x,y,`<path d="M0 0V34" stroke="#6aa86a" stroke-width="2.4"/><path d="M0 22C-9 14-14 18-12 26 -8 26-3 25 0 22Z" fill="#7cbf7c"/><path d="M-9-2C-11-14-6-20-6-20L0-12 6-20C6-20 11-14 9-2 6 5-6 5-9-2Z" fill="${c}"/><path d="M0-12C-3-6-3 0 0 4 3 0 3-6 0-12Z" fill="${d}"/>`,s);
const flower=(x,y,s,n,petal,pc,center,cc,r=0)=>{let p='';for(let k=0;k<n;k++)p+=`<path d="${petal}" fill="${pc}" transform="rotate(${360/n*k})"/>`;return g(x,y,p+`<circle r="${center}" fill="${cc}"/>`,s,r);};
const daisy=(x,y,s=1,r=0)=>g(x,y,'<circle r="15" fill="#e4ecd8" opacity=".55"/>',s)+flower(x,y,s,14,'M0-3C-2.2-6-2.2-13 0-15 2.2-13 2.2-6 0-3Z','#fff" stroke="#c9c2a6" stroke-width=".6',4.2,'#f6c343',r)+g(x,y,'<circle r="4.2" fill="none" stroke="#e0a82e" stroke-width=".8"/>',s);
const sunflower=(x,y,s=1)=>flower(x,y,s,18,'M0-8C-3.5-12-3-20 0-24 3-20 3.5-12 0-8Z','#ffc300',9,'#7a4a1f')+g(x,y,`<circle r="9" fill="#7a4a1f"/>${[...Array(9)].map((_,k)=>`<circle cx="${(Math.cos(k*.7)*k*.7).toFixed(1)}" cy="${(Math.sin(k*.7)*k*.7).toFixed(1)}" r=".9" fill="#c98b3d"/>`).join('')}`,s);
const sakura=(x,y,s=1,r=0,c='#ffb7c5')=>flower(x,y,s,5,'M0 0C-6-5-5-12-2-13L0-10.5 2-13C5-12 6-5 0 0Z',c,2.2,'#ff6f91',r);
const lotus=(x,y,s=1)=>g(x,y,`<ellipse cx="0" cy="4" rx="26" ry="5" fill="#2f8f6f"/><path d="M0 2C-14 0-22-8-24-14-14-14-6-8 0 2Z" fill="#f9b8cf"/><path d="M0 2C14 0 22-8 24-14 14-14 6-8 0 2Z" fill="#f9b8cf"/><path d="M0 2C-10-4-13-16-10-24-4-18 0-10 0 2Z" fill="#f48fb1"/><path d="M0 2C10-4 13-16 10-24 4-18 0-10 0 2Z" fill="#f48fb1"/><path d="M0 2C-6-8-6-20 0-30 6-20 6-8 0 2Z" fill="#ec6f9b"/>`,s);
const pad=(x,y,s=1)=>g(x,y,'<path d="M0 0A14 6 0 1 0 2-5Z" fill="#3fa37f"/><path d="M0 0L10-3" stroke="#2f8f6f" stroke-width="1"/>',s);
const nonla=(x,y,s=1)=>g(x,y,`<path d="M-26 0L0-18 26 0Q0 5-26 0Z" fill="#f2d48f"/>${[-16,-8,0,8,16].map(k=>`<path d="M0-18L${k*1.6} 1.5" stroke="#c9a24a" stroke-width=".7"/>`).join('')}<path d="M-26 0Q0 5 26 0" fill="none" stroke="#b8862f" stroke-width="1.2"/>`,s);
const aodai=(x,y,s=1,c='#c1121f')=>g(x,y,`<path d="M-5-26H5L8-14 15 34H3L0 2-3 34H-15L-8-14Z" fill="${c}"/><path d="M-5-26H5L4-21H-4Z" fill="#8a0c16"/><path d="M-8-14L-14 4-11 5-5-10M8-14L14 4 11 5 5-10" fill="${c}"/><path d="M-3-12L3-2M-3 0L3 10" stroke="#f2c14e" stroke-width="1.1" opacity=".9"/><circle cx="0" cy="-30" r="5" fill="#3a2a22"/>`,s);
const bear=(x,y,s=1)=>g(x,y,`<circle cx="-15" cy="-14" r="8" fill="#b9814f"/><circle cx="15" cy="-14" r="8" fill="#b9814f"/><circle cx="-15" cy="-14" r="4" fill="#f2c9a5"/><circle cx="15" cy="-14" r="4" fill="#f2c9a5"/><circle r="20" fill="#c8925f"/><ellipse cy="6" rx="9" ry="7" fill="#f2d6b8"/><ellipse cy="2.5" rx="3" ry="2.2" fill="#4a2c1a"/><circle cx="-7" cy="-4" r="2.2" fill="#3a2418"/><circle cx="7" cy="-4" r="2.2" fill="#3a2418"/><ellipse cx="-12" cy="5" rx="3.6" ry="2.2" fill="#ff9aa8" opacity=".7"/><ellipse cx="12" cy="5" rx="3.6" ry="2.2" fill="#ff9aa8" opacity=".7"/><path d="M-3 8Q0 11 3 8" stroke="#4a2c1a" stroke-width="1.2" fill="none"/>`,s);
const cat=(x,y,s=1)=>g(x,y,`<path d="M-18-6L-14-26-3-15ZM18-6L14-26 3-15Z" fill="#f5b971"/><path d="M-15-10L-13-21-7-15ZM15-10L13-21 7-15Z" fill="#ffd4dc"/><ellipse rx="20" ry="17" fill="#f5b971"/><path d="M-4-16Q0-10 4-16M-2-17L0-12 2-17" stroke="#e59a4a" stroke-width="1.4" fill="none"/><path d="M-10-3Q-7-6-4-3M4-3Q7-6 10-3" stroke="#3a2418" stroke-width="1.6" fill="none" stroke-linecap="round"/><path d="M0 2L-2 0H2Z" fill="#e5668b"/><path d="M-4 5Q-2 7 0 5 2 7 4 5" stroke="#3a2418" stroke-width="1.1" fill="none"/><path d="M-9 3H-22M-9 6L-21 9M9 3H22M9 6L21 9" stroke="#8a5a2a" stroke-width=".7"/><ellipse cx="-12" cy="4" rx="3.4" ry="2" fill="#ff9aa8" opacity=".7"/><ellipse cx="12" cy="4" rx="3.4" ry="2" fill="#ff9aa8" opacity=".7"/>`,s);
const cup=(x,y,s=1)=>g(x,y,`<path d="M-2-38L6-14" stroke="#ff8fab" stroke-width="4" stroke-linecap="round"/><path d="M-15-14Q0-26 15-14Z" fill="#fff" stroke="#e8d5c4"/><path d="M-14-13H14L10 20Q0 24-10 20Z" fill="#d9a77a"/><path d="M-12.5-2H12.5L10 20Q0 24-10 20Z" fill="#c48a5a"/>${[[-6,14],[0,17],[6,14],[-3,9],[4,8]].map(([a,b])=>`<circle cx="${a}" cy="${b}" r="2.6" fill="#3d2418"/>`).join('')}<path d="M-14-13H14" stroke="#fff" stroke-width="2"/><path d="M-7 0Q-4 4-1 0" stroke="#5a3a28" stroke-width="1.2" fill="none"/><circle cx="-9" cy="-4" r="1.3" fill="#5a3a28"/><circle cx="2" cy="-4" r="1.3" fill="#5a3a28"/>`,s);
const cake=(x,y,s=1)=>g(x,y,`<path d="M-16 12L16 12 16-2-16-8Z" fill="#fff4e6"/><path d="M-16-8L16-2 16 2-16-4Z" fill="#ffb5c2"/><path d="M-16 3L16 6" stroke="#ffb5c2" stroke-width="2"/><path d="M-16-8L4-14 16-2Z" fill="#ffd6dd"/><path d="M-2-14C-6-20 4-24 4-16Z" fill="#e63950"/><path d="M0-21L2-24" stroke="#4a9a4a" stroke-width="1.5"/>`,s);
const balloon=(x,y,s=1,c='#ff6b9a')=>g(x,y,`<path d="M0 10Q-5 22 2 34 6 44 0 54" stroke="#b9a" stroke-width="1" fill="none"/><path d="${heartD}" transform="scale(2.1)" fill="${c}"/><path d="M-12-14Q-14-6-9-2" stroke="#fff" stroke-width="2.4" fill="none" opacity=".55" stroke-linecap="round"/><path d="M-2 13L2 13 0 10Z" fill="${c}"/>`,s);
const moon=(x,y,s=1)=>g(x,y,'<circle r="22" fill="#fff3c4" opacity=".14"/><path d="M8-17A18 18 0 1 0 8 17 13 13 0 1 1 8-17Z" fill="#ffe8a3"/><circle cx="-6" cy="-3" r="2.4" fill="#f1d27e"/><circle cx="-2" cy="8" r="1.6" fill="#f1d27e"/>',s);
const star=(x,y,s=1,c='#ffe8a3')=>g(x,y,`<path d="${starD()}" fill="${c}"/>`,s);
const stamp=(x,y,s=1)=>g(x,y,`<rect x="-17" y="-21" width="34" height="42" fill="#fff8ea" stroke="#fff8ea" stroke-width="5" stroke-dasharray="1.5 2.6" stroke-linecap="round"/><rect x="-13" y="-17" width="26" height="34" fill="#f7d9c9"/><path d="${heartD}" transform="scale(1.1) translate(0 -1)" fill="#d1495b"/><text x="0" y="13" font-size="6" text-anchor="middle" fill="#7a4a3a" font-family="serif">20·10</text>`,s,6);
const postmark=(x,y,s=1)=>g(x,y,`<circle r="15" fill="none" stroke="#7a5c4a" stroke-width="1.2" opacity=".6"/><circle r="11" fill="none" stroke="#7a5c4a" stroke-width=".7" opacity=".6"/><text y="2" font-size="6" text-anchor="middle" fill="#7a5c4a" opacity=".7" font-family="serif">THƯƠNG</text>${[0,6,12].map(k=>`<path d="M18 ${k-6}Q24 ${k-9} 30 ${k-6}T42 ${k-6}T54 ${k-6}" stroke="#7a5c4a" stroke-width=".9" fill="none" opacity=".5"/>`).join('')}`,s,-8);
const sprig=(x,y,s=1,r=0)=>g(x,y,`<path d="M0 0V-34" stroke="#8a7a5a" stroke-width="1.2"/>${[...Array(7)].map((_,k)=>`<ellipse cx="${k%2?2.5:-2.5}" cy="${-8-k*4}" rx="2" ry="3.4" fill="#9b8ec4" transform="rotate(${k%2?25:-25} ${k%2?2.5:-2.5} ${-8-k*4})"/>`).join('')}`,s,r);
const cloud=(x,y,s=1,c='#fff')=>g(x,y,`<path d="M-16 6A8 8 0 0 1-10-6 10 10 0 0 1 8-8 8 8 0 0 1 18 4Z" fill="${c}"/>`,s);
const sparkleD='M0-9C1-2 2-1 9 0 2 1 1 2 0 9-1 2-2 1-9 0-2-1-1-2 0-9Z';
const sparkle=(x,y,s=1,c='#f2c14e')=>g(x,y,`<path d="${sparkleD}" fill="${c}"/>`,s);

/** The header art of each theme (viewBox 0 0 240 96). */
const ART={
  hoa_hong:()=>leaf(84,62,-150,1.2)+leaf(156,62,-30,1.2)+leaf(104,74,160,.9)+leaf(136,74,20,.9)+rose(98,52,1.05)+rose(142,52,1.05,'#e23d64')+rose(120,40,1.3,'#c9184a')+sparkle(40,30,.8)+sparkle(204,26,.7)+sparkle(186,64,.5),
  tulip:()=>tulip(66,48,1,'#ffafcc','#f48fb1')+tulip(94,40,1.1,'#cdb4db','#b197d6')+tulip(122,34,1.2,'#ff8fab','#e5668b')+tulip(150,40,1.1,'#ffd6a5','#f4b183')+tulip(178,48,1,'#a2d2ff','#7fb5e8')+`<path d="M30 88H210" stroke="#cfe8cf" stroke-width="3" stroke-linecap="round"/>`,
  cuc_hoa_mi:()=>[[48,60,.9,-10],[80,40,1.1,8],[112,58,.85,20],[132,34,1.25,-6],[166,56,1,14],[196,38,.95,-14]].map(([x,y,s,r])=>`<path d="M${x} ${y+12}Q${x+(r>0?6:-6)} ${y+30} ${x} 96" stroke="#7e9c6a" stroke-width="1.4" fill="none"/>`+daisy(x,y,s,r)).join('')+leaf(60,84,-40,.7,'#8fb07a')+leaf(180,84,-140,.7,'#8fb07a'),
  huong_duong:()=>leaf(70,78,-150,1.3,'#5d8f3a')+leaf(170,78,-30,1.3,'#5d8f3a')+`<path d="M92 60V96M150 56V96" stroke="#5d8f3a" stroke-width="3"/>`+sunflower(92,48,1.25)+sunflower(150,42,1.45)+sunflower(208,30,.7)+sunflower(36,32,.6),
  sen:()=>pad(52,80,1.4)+pad(196,78,1.2)+lotus(120,70,1.5)+lotus(66,74,.75)+lotus(178,74,.8)+sparkle(30,28,.6,'#f9d27e')+sparkle(214,30,.7,'#f9d27e'),
  ao_dai:()=>`<path d="M0 90Q60 70 120 84T240 78" stroke="#f2c14e" stroke-width="1.4" fill="none" opacity=".7"/>`+aodai(104,52,1.05)+aodai(140,54,1,'#f7f1e3')+nonla(104,22,.8)+nonla(140,24,.75)+sakura(46,40,1,0,'#ffd7a8')+sakura(200,36,1.1,20,'#ffd7a8')+sparkle(30,70,.6)+sparkle(214,70,.6),
  anh_dao:()=>`<path d="M-4 20Q60 30 110 22T246 34M70 26Q86 44 84 62M150 26Q168 40 190 44" stroke="#7a4b3a" stroke-width="3.2" fill="none" stroke-linecap="round"/>`+[[30,22,1,0],[58,30,.8,30],[86,60,1,12],[100,24,1.1,-10],[132,22,.9,40],[168,36,1.15,5],[192,44,.8,22],[216,30,1,-20],[150,30,.7,60]].map(([x,y,s,r])=>sakura(x,y,s,r)).join('')+sakura(40,70,.6,10,'#ffd1dc')+sakura(206,76,.6,40,'#ffd1dc'),
  gau_meo:()=>`<path d="M0 96V80Q120 66 240 80V96Z" fill="#ffe3d3"/>`+bear(84,54,1.15)+cat(156,56,1.15)+g(120,62,`<path d="${heartD}" transform="scale(1.5)" fill="#ff6b8a"/>`)+star(40,28,.7,'#ffd166')+star(204,24,.6,'#ffd166')+g(30,64,`<path d="${heartD}" fill="#ffb3c6"/>`)+g(212,64,`<path d="${heartD}" fill="#ffb3c6"/>`),
  tra_sua:()=>cup(96,58,1.3)+cake(156,64,1.25)+g(128,24,`<path d="${heartD}" transform="scale(1.1)" fill="#ff8fab"/>`)+[[40,40],[54,70],[200,34],[214,66],[186,80]].map(([x,y])=>`<circle cx="${x}" cy="${y}" r="3.4" fill="#5a3a28" opacity=".55"/>`).join(''),
  bong_bong:()=>balloon(70,30,.9,'#ff8fab')+balloon(104,20,1.1,'#ff4d8d')+balloon(140,26,1,'#ffb3c6')+balloon(172,34,.85,'#c77dff')+cloud(36,74,1.1)+cloud(210,70,1)+cloud(124,84,.8),
  dem_sao:()=>moon(180,40,1.15)+[[30,20,.6],[56,52,.4],[84,24,.75],[112,60,.45],[136,18,.5],[214,70,.5],[226,22,.45],[70,80,.35],[150,78,.4]].map(([x,y,s])=>star(x,y,s)).join('')+cloud(110,88,1.3,'#3d3570')+cloud(34,90,1,'#3d3570'),
  thu_tay:()=>stamp(206,46,1.05)+postmark(150,40,1)+sprig(28,92,1.1,-12)+sprig(42,94,.9,8)+g(36,58,`<path d="M0 0Q8-6 14 0" stroke="#c9a88a" stroke-width="1.2" fill="none"/>`),
  polaroid:()=>`<defs><linearGradient id="evsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bde0fe"/><stop offset="1" stop-color="#ffd6e7"/></linearGradient></defs><rect x="22" y="6" width="196" height="88" rx="2" fill="url(#evsky)"/><circle cx="182" cy="28" r="11" fill="#fff3b0"/><path d="M22 72Q70 50 120 70T218 62V94H22Z" fill="#b8e0c2"/><path d="M22 84Q90 66 160 82T218 80V94H22Z" fill="#9fd3ae"/>`+cloud(70,30,1.1)+g(120,34,`<path d="${heartD}" transform="scale(1.6)" fill="#ff8fab"/>`)+[60,96,150,190].map((x,k)=>sakura(x,86-(k%2)*4,.45,k*30,'#fff')).join(''),
};

/* ------------------------------------------------------------ themes */
const THEMES={
  hoa_hong:{name:'Hoa hồng',seal:'🌹',fx:['petal','petal','heart'],move:'fall',reveal:'bloom'},
  tulip:{name:'Tulip pastel',seal:'🌷',fx:['heart','petal','petal2'],move:'fall',reveal:'bloom'},
  cuc_hoa_mi:{name:'Cúc họa mi',seal:'🌼',fx:['daisy','daisy','leaf'],move:'fall',reveal:'bloom'},
  huong_duong:{name:'Hướng dương',seal:'🌻',fx:['sunpetal','sunpetal','leaf'],move:'fall',reveal:'sun'},
  sen:{name:'Sen hồng',seal:'🪷',fx:['petal','petal','sparkle'],move:'fall',reveal:'bloom'},
  ao_dai:{name:'Áo dài xưa',seal:'🏮',fx:['sparkle','petal','sparkle'],move:'fall',reveal:'shimmer'},
  anh_dao:{name:'Anh đào',seal:'🌸',fx:['sakura','sakura','sakura'],move:'fall',reveal:'bloom'},
  gau_meo:{name:'Gấu & mèo',seal:'🧸',fx:['heart','paw','heart'],move:'fall',reveal:'bounce'},
  tra_sua:{name:'Trà sữa',seal:'🧋',fx:['boba','boba','heart'],move:'rise',reveal:'bounce'},
  bong_bong:{name:'Bóng bay tim',seal:'🎈',fx:['balloon','balloon','heart'],move:'rise',reveal:'bounce'},
  dem_sao:{name:'Đêm sao',seal:'🌙',fx:['star','sparkle','star'],move:'twinkle',reveal:'glow'},
  thu_tay:{name:'Thư tay',seal:'✉️',fx:['leaf','petal','leaf'],move:'fall',reveal:'unfold'},
  polaroid:{name:'Polaroid',seal:'📷',fx:['heart','sparkle','petal2'],move:'fall',reveal:'develop'},
};
const FX={
  petal:'<path d="M0-8C6-6 7 3 0 8-7 3-6-6 0-8Z" fill="var(--p1)"/><path d="M0-6V6" stroke="#ffffff55" stroke-width=".8"/>',
  petal2:'<path d="M0-8C6-6 7 3 0 8-7 3-6-6 0-8Z" fill="var(--p2)"/>',
  heart:`<path d="${heartD}" transform="scale(.8)" fill="var(--p2)"/>`,
  sakura:'<path d="M0 9C-7 3-6-6-2-8L0-5 2-8C6-6 7 3 0 9Z" fill="var(--p1)"/>',
  daisy:[...Array(10)].map((_,k)=>`<ellipse cy="-5" rx="1.6" ry="4" fill="#fff" stroke="#c9c2a6" stroke-width=".4" transform="rotate(${k*36})"/>`).join('')+'<circle r="2.6" fill="#f6c343"/>',
  sunpetal:'<path d="M0-9C-3-4-3 4 0 9 3 4 3-4 0-9Z" fill="#ffc300"/>',
  leaf:'<path d="M-8 0C-3-5 4-5 8 0 4 5-3 5-8 0Z" fill="var(--p3)"/>',
  sparkle:`<path d="${sparkleD}" fill="var(--p3)"/>`,
  star:`<path d="${starD(9,3.8)}" fill="#ffe8a3"/>`,
  paw:'<ellipse cy="3" rx="5" ry="4" fill="var(--p1)"/><circle cx="-5" cy="-4" r="2.2" fill="var(--p1)"/><circle cx="0" cy="-6.5" r="2.2" fill="var(--p1)"/><circle cx="5" cy="-4" r="2.2" fill="var(--p1)"/>',
  boba:'<circle r="5" fill="#4a2c1e"/><circle cx="-1.6" cy="-1.8" r="1.4" fill="#fff" opacity=".45"/>',
  balloon:`<path d="${heartD}" fill="var(--p2)"/><path d="M0 7Q-2 12 1 17" stroke="#b9a" stroke-width=".6" fill="none"/>`,
};
const DIRS={
  nam_nu:{label:'Nam gửi nữ',icon:'💐',badge:'Tặng nàng',kicker:'Chúc mừng ngày 20/10',to:'Ví dụ: Lan, Mẹ, Chị Hai…'},
  nu_nam:{label:'Nữ gửi nam',icon:'🎀',badge:'Tặng chàng',kicker:'Gửi lời thương ngày 20/10',to:'Ví dụ: Minh, Bố, Anh Tư…'},
  khac:{label:'Gửi ai cũng được',icon:'💌',badge:'Tặng bạn',kicker:'Thiệp 20/10',to:'Ví dụ: Cô Hạnh, Bạn thân…'},
};
const IDEAS={
  nam_nu:['Chúc em 20/10 thật xinh, thật vui và luôn được yêu thương. Cảm ơn em đã là điều dễ thương nhất trong ngày của anh 💐',
    'Gửi người con gái đặc biệt: mong mọi điều dịu dàng nhất trên đời đều tìm đến em, hôm nay và mãi sau 🌷',
    'Chúc mẹ luôn khỏe mạnh, bình an và lúc nào cũng cười thật tươi. Con thương mẹ nhiều lắm ❤️',
    '20/10 vui vẻ nhé! Mong em luôn tự tin, rạng rỡ và có thật nhiều khoảnh khắc hạnh phúc ✨'],
  nu_nam:['20/10 là ngày của con gái, nhưng mình vẫn muốn cảm ơn cậu vì luôn kiên nhẫn và tử tế với mình 🎀',
    'Cảm ơn anh đã luôn lắng nghe và làm em cười mỗi ngày. Hôm nay em gửi anh một tấm thiệp nhỏ, nhớ tặng hoa cho em nha 🌹😄',
    'Gửi bố: cảm ơn bố đã luôn thương mẹ và chăm lo cho cả nhà. 20/10 con chúc bố mẹ thật nhiều niềm vui 💌'],
  khac:['Chúc bạn một ngày 20/10 thật nhiều niềm vui, luôn khỏe mạnh và được yêu thương nhé 💐',
    'Cảm ơn vì đã luôn là một người bạn tuyệt vời. 20/10 vui vẻ, rực rỡ như hoa nha 🌸',
    'Gửi cô kính yêu: chúc cô luôn mạnh khỏe, hạnh phúc và mãi giữ lửa với nghề 🌷'],
};
/** Where each sticker sits on the card (percent of the card box; six slots, in order). */
const SLOTS=[[6,30,-12],[88,24,10],[4,70,8],[90,66,-10],[12,92,-6],[84,92,12]];

/* ------------------------------------------------------------ the card */
function cardHTML(c,{preview=false}={}){
  const th=THEMES[c.theme]?c.theme:'hoa_hong',d=DIRS[c.direction]||DIRS.nam_nu;
  const lines=String(c.text||'').trim()?String(c.text).split('\n').map(l=>`<span>${esc(l)}</span>`).join('<br>'):'';
  const stickers=(c.stickers||[]).slice(0,6).map((s,i)=>`<i class="ev-st" style="left:${SLOTS[i][0]}%;top:${SLOTS[i][1]}%;--r:${SLOTS[i][2]}deg">${esc(s)}</i>`).join('');
  return `<article class="ev-card${preview?' is-preview':''}" data-theme="${th}" aria-label="Thiệp gửi ${esc(c.to||'người thương')}">
    <div class="ev-card-art" aria-hidden="true"><svg viewBox="0 0 240 96" preserveAspectRatio="xMidYMid meet">${ART[th]()}</svg></div>
    <span class="ev-badge">${d.icon} ${esc(d.badge)}</span>
    <p class="ev-kicker">${esc(d.kicker)}</p>
    <h2 class="ev-to">Gửi ${esc(c.to||'…')},</h2>
    <p class="ev-text">${lines||'<span class="ev-ph">Lời nhắn của bạn sẽ hiện ở đây…</span>'}</p>
    <p class="ev-from"><small>${c.direction==='khac'?'Thân mến,':'Thương,'}</small><b>${esc(c.sender||'…')}</b></p>
    <div class="ev-sts" aria-hidden="true">${stickers}</div>
  </article>`;
}

/* ------------------------------------------------------------ falling / rising things */
let fxLayer=null;
function fx(theme,{n=18,burst=false}={}){
  if(still())return;
  const t=THEMES[theme]||THEMES.hoa_hong;
  if(!fxLayer){fxLayer=document.createElement('div');fxLayer.className='ev-fx';fxLayer.setAttribute('aria-hidden','true');document.body.append(fxLayer);}
  fxLayer.dataset.theme=theme;fxLayer.dataset.move=t.move;
  if(!burst)fxLayer.textContent='';
  for(let i=0;i<n;i++){
    const k=t.fx[i%t.fx.length],el=document.createElement('i'),s=t.move==='twinkle'?.6+Math.random()*.9:k==='balloon'?1.4+Math.random()*.8:.8+Math.random()*.9;
    el.className=`ev-p ev-${t.move}`;
    el.style.cssText=`--x:${(Math.random()*100).toFixed(1)}vw;--y:${(Math.random()*90).toFixed(1)}vh;--s:${s.toFixed(2)};--d:${(t.move==='twinkle'?2+Math.random()*3:7+Math.random()*7).toFixed(1)}s;--w:${(Math.random()*2-1).toFixed(2)};--delay:${(burst?Math.random()*.6:-Math.random()*12).toFixed(1)}s;--r:${Math.round(Math.random()*360)}deg`;
    el.innerHTML=`<svg viewBox="-10 -10 20 20" width="22" height="22">${FX[k]}</svg>`;
    fxLayer.append(el);
  }
}
function floatHearts(from,count=5){
  if(still())return;
  const r=from.getBoundingClientRect();
  for(let i=0;i<count;i++){
    const h=document.createElement('i');h.className='ev-float';h.setAttribute('aria-hidden','true');h.textContent=['❤️','💗','💖','💕'][i%4];
    h.style.cssText=`left:${r.left+r.width/2+(Math.random()*40-20)}px;top:${r.top}px;--dx:${(Math.random()*80-40).toFixed(0)}px;animation-delay:${(i*.06).toFixed(2)}s`;
    document.body.append(h);setTimeout(()=>h.remove(),1600);
  }
}

/* ------------------------------------------------------------ small helpers */
function toast(text,bad=false){
  let t=$('#ev-toast');
  if(!t){t=document.createElement('div');t.id='ev-toast';t.setAttribute('role','status');t.setAttribute('aria-live','polite');document.body.append(t);}
  t.textContent=text;t.className=bad?'is-bad is-on':'is-on';clearTimeout(toastTimer);toastTimer=setTimeout(()=>{t.className='';},3200);
}
async function api(path,{method='GET',body=null,csrf=false}={}){
  const headers={};if(body){headers['Content-Type']='application/json';}if(csrf&&ME?.csrf)headers['X-Game-CSRF']=ME.csrf;
  let r;
  try{r=await fetch(path,{method,headers,body:body?JSON.stringify(body):null,credentials:'same-origin',cache:'no-store'});}
  catch{throw new Error('Mất kết nối. Kiểm tra mạng rồi thử lại nhé.');}
  let d={};try{d=await r.json();}catch{/* not JSON */}
  if(!r.ok){const e=new Error(d.error||'Chưa được, thử lại sau nhé.');e.status=r.status;e.code=d.code;throw e;}
  return d;
}
const cardURL=id=>`${location.origin}/2010/c/${id}`;
async function copy(text){
  try{await navigator.clipboard.writeText(text);return true;}
  catch{const a=document.createElement('textarea');a.value=text;a.setAttribute('readonly','');a.style.cssText='position:fixed;opacity:0';document.body.append(a);a.select();let ok=false;try{ok=document.execCommand('copy');}catch{/* old */}a.remove();return ok;}
}
const coarse=()=>matchMedia('(pointer: coarse)').matches;
async function share(id,how,to){
  const url=cardURL(id),text=`Mình gửi ${to||'bạn'} một tấm thiệp 20/10, mở ra xem nhé 💌`;
  if(how==='native'||how==='zalo'){
    if(navigator.share){try{await navigator.share({title:'Thiệp 20/10',text,url});return;}catch(e){if(e?.name==='AbortError')return;}}
    if(await copy(url))toast(how==='zalo'?'Đã chép link. Mở Zalo và dán vào tin nhắn nhé 💬':'Đã chép link thiệp 💌');else toast(url);
    return;
  }
  if(how==='copy'){toast(await copy(url)?'Đã chép link thiệp 💌':url);return;}
  if(how==='fb'){window.open(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,'_blank','noopener,width=640,height=560');return;}
  if(how==='msg'){
    if(coarse()){location.href=`fb-messenger://share/?link=${encodeURIComponent(url)}`;return;}
    if(await copy(url))toast('Đã chép link. Mở Messenger và dán vào tin nhắn nhé 💬');
  }
}
const shareRow=(id,to)=>`<div class="ev-share" role="group" aria-label="Chia sẻ thiệp">
  <button type="button" class="ev-sh ev-sh-copy" data-share="copy" data-id="${esc(id)}" data-to="${esc(to)}"><b>🔗</b>Chép link</button>
  ${navigator.share?`<button type="button" class="ev-sh" data-share="native" data-id="${esc(id)}" data-to="${esc(to)}"><b>📤</b>Chia sẻ</button>`:''}
  <button type="button" class="ev-sh ev-sh-zalo" data-share="zalo" data-id="${esc(id)}" data-to="${esc(to)}"><b>Z</b>Zalo</button>
  <button type="button" class="ev-sh ev-sh-msg" data-share="msg" data-id="${esc(id)}" data-to="${esc(to)}"><b>💬</b>Messenger</button>
  <button type="button" class="ev-sh ev-sh-fb" data-share="fb" data-id="${esc(id)}" data-to="${esc(to)}"><b>f</b>Facebook</button>
</div>`;
document.addEventListener('click',e=>{const b=e.target.closest?.('[data-share]');if(b){e.preventDefault();share(b.dataset.id,b.dataset.share,b.dataset.to);}});

/* ------------------------------------------------------------ reading a card */
let hearts=0,pending=0,heartTimer=0;
function sendHearts(id){
  clearTimeout(heartTimer);
  heartTimer=setTimeout(async()=>{
    const n=Math.min(20,pending);if(!n)return;pending-=n;
    try{const d=await api('/api/2010/heart',{method:'POST',body:{id,n}});hearts=Math.max(hearts,d.hearts);paintHearts();}
    catch(e){if(e.status===429)toast(e.message);}
    if(pending)sendHearts(id);
  },700);
}
const paintHearts=()=>{const b=$('#ev-heart-n');if(b)b.textContent=fmt(hearts);};
function readView(c){
  const t=THEMES[c.theme]||THEMES.hoa_hong;hearts=c.hearts||0;
  document.body.dataset.theme=c.theme;
  return `<header class="ev-top"><a class="ev-back" href="/2010">💐 Thiệp 20/10</a><span class="ev-brand">Phố Có Chuyện</span></header>
  <section class="ev-read" data-theme="${esc(c.theme)}">
    <div class="ev-stage" id="ev-stage">
      <button type="button" class="ev-env" id="ev-env" aria-label="Mở thư của ${esc(c.sender)}">
        <span class="ev-env-back"></span><span class="ev-env-letter">${cardHTML(c,{preview:true})}</span>
        <span class="ev-env-front"><span class="ev-env-to">Gửi <b>${esc(c.to)}</b></span><span class="ev-env-from">từ ${esc(c.sender)}</span></span>
        <span class="ev-env-flap"></span><span class="ev-seal">${t.seal}</span>
      </button>
      <p class="ev-tap" id="ev-tap">Chạm vào phong thư để mở 💌</p>
      <div class="ev-opened" id="ev-opened" hidden>${cardHTML(c)}</div>
    </div>
    <div class="ev-after" id="ev-after" hidden>
      <div class="ev-react"><button type="button" class="ev-heart" id="ev-heart" aria-label="Thả tim cho thiệp"><span aria-hidden="true">❤️</span> Thả tim <b id="ev-heart-n">${fmt(hearts)}</b></button></div>
      <p class="ev-sub">Gửi tiếp tấm thiệp này cho người ấy:</p>
      ${shareRow(c.id,c.to)}
      <a class="ev-cta" href="/2010?to=${encodeURIComponent(c.sender)}&dir=${c.direction==='nam_nu'?'nu_nam':c.direction==='nu_nam'?'nam_nu':'khac'}#viet">💌 Viết thiệp tặng lại ${esc(c.sender)}</a>
      <p class="ev-new">Lần đầu ghé <b>Phố Có Chuyện</b>? <a href="/">Vào phố</a> làm đủ nghề, kết bạn, và gửi thiệp 20/10 của riêng bạn.</p>
      <p class="ev-mod" id="ev-mod"><button type="button" class="ev-link" data-act="report">Báo cáo thiệp này</button></p>
    </div>
  </section>`;
}
function openEnvelope(c,{instant=false}={}){
  const env=$('#ev-env');if(!env||env.classList.contains('is-open'))return;
  const t=THEMES[c.theme]||THEMES.hoa_hong;
  const done=()=>{
    env.hidden=true;$('#ev-tap').hidden=true;$('#ev-stage').classList.add('is-opened');
    const o=$('#ev-opened');o.hidden=false;o.firstElementChild.classList.add('ev-reveal',`ev-reveal-${t.reveal}`);
    $('#ev-after').hidden=false;fx(c.theme,{n:t.move==='twinkle'?34:22});
    $('#ev-opened .ev-card')?.focus?.();
  };
  if(instant||still()){done();return;}
  env.classList.add('is-open');$('#ev-tap').textContent='';
  setTimeout(done,1250);
}
function bindRead(c){
  const env=$('#ev-env');
  env?.addEventListener('click',()=>openEnvelope(c));
  fx(c.theme,{n:8});
  $('#ev-heart')?.addEventListener('click',e=>{hearts++;pending++;paintHearts();floatHearts(e.currentTarget,3);e.currentTarget.classList.remove('is-pop');void e.currentTarget.offsetWidth;e.currentTarget.classList.add('is-pop');sendHearts(c.id);});
  $('#ev-opened')?.addEventListener('dblclick',()=>$('#ev-heart')?.click());
  $('#ev-mod')?.addEventListener('click',async e=>{
    const b=e.target.closest('[data-act]');if(!b)return;
    if(b.dataset.act==='report'){
      $('#ev-mod').innerHTML=`<span class="ev-mine">Thiệp này có vấn đề gì?</span><span class="ev-reasons">${[['rude','Lời lẽ khó nghe'],['scam','Lừa đảo'],['private','Lộ thông tin riêng'],['spam','Quảng cáo, spam'],['other','Lý do khác']].map(([k,v])=>`<button type="button" class="ev-chip" data-act="why" data-reason="${k}">${v}</button>`).join('')}</span>`;
    }else if(b.dataset.act==='why'){
      $('#ev-mod').querySelectorAll('button').forEach(x=>{x.disabled=true;});
      try{const d=await api('/api/2010/report',{method:'POST',body:{id:c.id,reason:b.dataset.reason}});$('#ev-mod').innerHTML=`<span class="ev-mine">${esc(d.message)}</span>`;}
      catch(err){toast(err.message,true);$('#ev-mod').querySelectorAll('button').forEach(x=>{x.disabled=false;});}
    }else if(b.dataset.act==='delete'){
      if(!confirm('Xóa tấm thiệp này? Link đã gửi sẽ không mở được nữa.'))return;
      try{await ensureMe();await api('/api/2010/cards',{method:'POST',body:{op:'delete',id:c.id},csrf:true});toast('Đã xóa thiệp.');setTimeout(()=>location.assign('/2010'),900);}catch(err){toast(err.message,true);}
    }
  });
  // Is it mine? (the sender sees "Xóa thiệp" instead of "Báo cáo")
  api(`/api/2010/card?id=${encodeURIComponent(c.id)}`).then(d=>{
    if(typeof d.card?.hearts==='number'){hearts=Math.max(hearts,d.card.hearts);paintHearts();}
    if(d.mine)$('#ev-mod').innerHTML='<span class="ev-mine">Thiệp của bạn · </span><button type="button" class="ev-link" data-act="delete">Xóa thiệp</button>';
  }).catch(()=>{});
}

/* ------------------------------------------------------------ the home: event, writer, my cards */
const W={dir:'nam_nu',theme:'hoa_hong',to:'',text:'',sender:'',stickers:[]};
let idea=0,sending=false;
async function ensureMe(){if(!ME)ME=await api('/api/2010/me');return ME;}
function homeView(){
  delete document.body.dataset.theme;
  const until=DATA.until?dm(DATA.until):'21/10';
  return `<header class="ev-top"><a class="ev-back" href="/">← Về phố</a><span class="ev-brand">Phố Có Chuyện</span></header>
  <section class="ev-hero">
    <div class="ev-hero-art" aria-hidden="true"><svg viewBox="0 0 240 96">${ART.hoa_hong()}</svg></div>
    <p class="ev-eyebrow">20 · 10 · Ngày Phụ nữ Việt Nam</p>
    <h1>Gửi một tấm thiệp<br><em>cho người thương</em></h1>
    <p class="ev-lead">Viết vài dòng, chọn một mẫu thiệp thật xinh rồi gửi link. Người nhận mở được ngay, không cần chơi game.</p>
    ${DATA.open?`<p class="ev-gift">🎁 Phố tặng <b>${fmt(DATA.coins||100000)} xu</b> cho mỗi tài khoản gửi thiệp · đến hết ${until}</p>`
      :`<p class="ev-gift is-over">${esc(DATA.recap||'Mùa viết thiệp 20/10 đã khép lại. Những tấm thiệp đã gửi vẫn mở được bằng link nhé 💐')}</p>`}
  </section>
  <section class="ev-sec" id="viet" aria-labelledby="ev-w-h"><h2 id="ev-w-h">✍️ Viết thiệp</h2><div id="ev-writer"><div class="ev-skel"><i></i><i></i><i></i></div></div></section>
  <section class="ev-sec" id="ev-mine-sec" hidden aria-labelledby="ev-m-h"><h2 id="ev-m-h">💌 Thiệp bạn đã gửi</h2><div id="ev-mine"></div></section>
  <footer class="ev-foot">
    <p>Quà ${fmt(DATA.coins||100000)} xu: mỗi tài khoản nhận một lần, khi gửi tấm thiệp đầu tiên trong mùa 20/10 (nhân vật đã ở phố từ ngày ${DATA.min_life_day||3}). Xu vào ví khi bạn vào phố.</p>
    <p>Thiệp mở được bằng link tới hết ${DATA.read_until?dm(DATA.read_until)+'/'+new Date(DATA.read_until*1000).getFullYear():'tháng 12'}. Lời lẽ khó nghe, số điện thoại, đường link sẽ được che bớt. <a href="/terms">Điều khoản</a> · <a href="/privacy">Quyền riêng tư</a></p>
  </footer>`;
}
function rewardBox(r){
  if(!r)return '';
  const c=fmt(r.coins);
  const m={
    account:`🎁 Đăng nhập tài khoản để nhận <b>${c} xu</b> khi gửi thiệp.`,
    days:`🎁 Quà <b>${c} xu</b> dành cho cư dân đã ở phố từ ngày ${r.min_life_day}. Bạn còn ${r.need} ngày nữa, sau đó quay lại đây bấm nhận nhé. Thiệp vẫn gửi được bình thường.`,
    write:`🎁 Gửi tấm thiệp đầu tiên để nhận <b>${c} xu</b> vào ví.`,
    ready:`🎁 Bạn đã đủ điều kiện nhận <b>${c} xu</b>! <button type="button" class="ev-btn ev-btn-sm" data-act="claim">Nhận quà</button>`,
    paid:r.pending?`🎁 <b>${c} xu</b> đang chờ bạn trong phố. <a class="ev-btn ev-btn-sm" href="/">Vào phố nhận quà</a>`:`🎁 Bạn đã nhận <b>${c} xu</b> quà thiệp. Cảm ơn bạn nhiều nha 💗`,
    ip:'🎁 Quà thiệp của mạng này đã được nhận đủ lượt. Thiệp của bạn vẫn gửi bình thường nhé.',
    closed:'🎁 Quà thiệp đã khép lại cùng mùa 20/10.',
  }[r.state];
  return m?`<p class="ev-reward is-${esc(r.state)}">${m}</p>`:'';
}
function signInView(){
  const guest=ME?.guest;
  return `<div class="ev-signin">
    <div class="ev-signin-art" aria-hidden="true"><svg viewBox="0 0 240 96">${ART.gau_meo()}</svg></div>
    <p>${guest?'Bạn đang ở phố bằng phiên khách. Tạo tài khoản (giữ nguyên tiến trình) để viết thiệp và nhận quà nhé.':'Đăng nhập tài khoản trong phố để viết thiệp và nhận quà nhé.'}</p>
    <a class="ev-btn" data-back href="/?account=${guest?'register':'login'}">${guest?'Tạo tài khoản':'Đăng nhập'}</a>
    ${guest?'':'<a class="ev-btn ev-btn-ghost" data-back href="/?account=register">Tạo tài khoản mới</a>'}
    <p class="ev-small">Xong bạn sẽ được đưa lại về đây, thiệp đang viết dở vẫn còn.</p>
    ${rewardBox(ME?.reward)}
  </div>`;
}
function writerView(){
  const d=DIRS[W.dir],L=ME.limits||{};
  const themes=(ME.themes||Object.keys(THEMES)).filter(k=>THEMES[k]);
  return `${rewardBox(ME.reward)}
  <form class="ev-form" id="ev-form" novalidate>
    <fieldset class="ev-field"><legend>Kiểu thiệp</legend><div class="ev-seg" role="radiogroup">${Object.entries(DIRS).map(([k,v])=>`<button type="button" role="radio" aria-checked="${k===W.dir}" class="ev-seg-b${k===W.dir?' is-on':''}" data-dir="${k}"><span aria-hidden="true">${v.icon}</span>${esc(v.label)}</button>`).join('')}</div></fieldset>
    <fieldset class="ev-field"><legend>Mẫu thiệp <small>${themes.length} mẫu</small></legend><div class="ev-themes" role="radiogroup">${themes.map(k=>`<button type="button" role="radio" aria-checked="${k===W.theme}" class="ev-th${k===W.theme?' is-on':''}" data-theme-pick="${k}" data-theme="${k}"><span class="ev-th-art" aria-hidden="true"><svg viewBox="0 0 240 96">${ART[k]()}</svg></span><span class="ev-th-name">${esc(THEMES[k].name)}</span></button>`).join('')}</div></fieldset>
    <div class="ev-preview" id="ev-preview" aria-live="off"></div>
    <label class="ev-field"><span class="ev-lab">Gửi tới</span><input id="ev-to" class="ev-in" maxlength="${L.to||30}" autocomplete="off" placeholder="${esc(d.to)}" value="${esc(W.to)}"></label>
    <label class="ev-field"><span class="ev-lab">Lời nhắn <button type="button" class="ev-link" data-act="idea">✨ Gợi ý lời chúc</button></span><textarea id="ev-text" class="ev-in" rows="5" maxlength="${L.text||400}" placeholder="Viết vài lời thật lòng…">${esc(W.text)}</textarea><small class="ev-count" id="ev-count"></small></label>
    <label class="ev-field"><span class="ev-lab">Ký tên</span><input id="ev-from" class="ev-in" maxlength="${L.sender||30}" autocomplete="off" placeholder="${esc(ME.name||'Tên của bạn')}" value="${esc(W.sender)}"></label>
    <fieldset class="ev-field"><legend>Hình dán <small id="ev-st-n">${W.stickers.length}/${ME.stickers_max||6}</small></legend><div class="ev-stick">${(ME.stickers||[]).map(s=>`<button type="button" class="ev-stb${W.stickers.includes(s)?' is-on':''}" data-stick="${esc(s)}" aria-pressed="${W.stickers.includes(s)}">${esc(s)}</button>`).join('')}</div></fieldset>
    <button type="submit" class="ev-btn ev-send" id="ev-send">Gửi thiệp 💌</button>
    <p class="ev-small">Hôm nay bạn còn gửi được ${fmt(ME.left)} tấm.</p>
  </form>`;
}
function sentView(out){
  const c=out.card,url=cardURL(c.id);
  return `<div class="ev-sent">
    <p class="ev-sent-h">💌 Thiệp đã sẵn sàng!</p>
    <p>Gửi link này cho <b>${esc(c.to)}</b> nhé. Ai có link cũng mở được, không cần chơi game.</p>
    <div class="ev-url"><input class="ev-in" readonly value="${esc(url)}" aria-label="Link thiệp"><button type="button" class="ev-btn ev-btn-sm" data-share="copy" data-id="${esc(c.id)}" data-to="${esc(c.to)}">Chép</button></div>
    ${shareRow(c.id,c.to)}
    ${out.reward?.granted?`<p class="ev-reward is-paid">🎁 Cảm ơn bạn! <b>${fmt(out.reward.coins)} xu</b> đang chờ trong phố. <a class="ev-btn ev-btn-sm" href="/">Vào phố nhận quà</a></p>`:rewardBox(out.reward&&out.reward.state!=='paid'?out.reward:null)}
    <div class="ev-row"><a class="ev-btn ev-btn-ghost" href="/2010/c/${esc(c.id)}">Xem thiệp</a><button type="button" class="ev-btn ev-btn-ghost" data-act="again">Viết thêm tấm nữa</button></div>
  </div>`;
}
function mineView(){
  const list=ME?.mine||[];
  $('#ev-mine-sec').hidden=!list.length;
  $('#ev-mine').innerHTML=list.map(c=>`<article class="ev-mi" data-theme="${esc(c.theme)}"><span class="ev-mi-seal" aria-hidden="true">${THEMES[c.theme]?.seal||'💌'}</span>
    <div class="ev-mi-t"><b>Gửi ${esc(c.to)}</b><small>${dm(c.at)} · ❤️ ${fmt(c.hearts)}${c.status!=='live'?' · <em>đang tạm ẩn</em>':''}</small></div>
    <a class="ev-btn ev-btn-sm ev-btn-ghost" href="/2010/c/${esc(c.id)}">Xem</a><button type="button" class="ev-btn ev-btn-sm" data-share="${navigator.share?'native':'copy'}" data-id="${esc(c.id)}" data-to="${esc(c.to)}">Gửi link</button></article>`).join('');
}
function paintPreview(){
  const p=$('#ev-preview');if(!p)return;
  p.dataset.theme=W.theme;
  p.innerHTML=cardHTML({theme:W.theme,direction:W.dir,to:W.to.trim(),text:W.text.trim(),sender:W.sender.trim()||ME?.name||'',stickers:W.stickers},{preview:true});
  const n=$('#ev-count');if(n)n.textContent=`${W.text.length}/${ME?.limits?.text||400}`;
  store.set(DRAFT,W);
}
let raf=0;const repaint=()=>{cancelAnimationFrame(raf);raf=requestAnimationFrame(paintPreview);};
async function loadWriter(){
  const box=$('#ev-writer');
  try{ME=await api('/api/2010/me');}
  catch(e){box.innerHTML=`<p class="ev-reward">${esc(e.message)} <button type="button" class="ev-btn ev-btn-sm" data-act="retry">Thử lại</button></p>`;return;}
  mineView();
  if(!ME.open){box.innerHTML=`<p class="ev-reward is-closed">${esc(ME.recap||'Mùa viết thiệp 20/10 đã khép lại. Cảm ơn mọi người đã gửi thật nhiều lời thương 💐')}</p>${rewardBox(ME.reward?.state==='paid'?ME.reward:null)}`;return;}
  if(!ME.can_write){box.innerHTML=signInView();return;}
  if(!W.sender&&ME.name)W.sender='';
  box.innerHTML=writerView();bindWriter();paintPreview();
}
function bindWriter(){
  const f=$('#ev-form');if(!f)return;
  f.addEventListener('input',e=>{
    if(e.target.id==='ev-to')W.to=e.target.value;else if(e.target.id==='ev-text')W.text=e.target.value;else if(e.target.id==='ev-from')W.sender=e.target.value;
    repaint();
  });
  f.addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;
    if(b.dataset.dir){W.dir=b.dataset.dir;f.querySelectorAll('[data-dir]').forEach(x=>{const on=x===b;x.classList.toggle('is-on',on);x.setAttribute('aria-checked',on);});$('#ev-to').placeholder=DIRS[W.dir].to;repaint();}
    else if(b.dataset.themePick){W.theme=b.dataset.themePick;f.querySelectorAll('[data-theme-pick]').forEach(x=>{const on=x===b;x.classList.toggle('is-on',on);x.setAttribute('aria-checked',on);});repaint();
      if(!still())$('#ev-preview').scrollIntoView({block:'nearest',behavior:'smooth'});}
    else if(b.dataset.stick){
      const s=b.dataset.stick,max=ME.stickers_max||6;
      if(W.stickers.includes(s))W.stickers=W.stickers.filter(x=>x!==s);else if(W.stickers.length<max)W.stickers=[...W.stickers,s];else{toast(`Tối đa ${max} hình dán thôi nhé.`);return;}
      b.classList.toggle('is-on',W.stickers.includes(s));b.setAttribute('aria-pressed',W.stickers.includes(s));$('#ev-st-n').textContent=`${W.stickers.length}/${max}`;repaint();
    }else if(b.dataset.act==='idea'){const list=IDEAS[W.dir];W.text=list[idea++%list.length];$('#ev-text').value=W.text;repaint();}
  });
  f.addEventListener('submit',async e=>{
    e.preventDefault();if(sending)return;
    if(!W.to.trim()){toast('Viết tên người nhận nhé.',true);$('#ev-to').focus();return;}
    if(W.text.trim().length<(ME.limits?.text_min||4)){toast('Viết vài lời gửi người ấy nhé.',true);$('#ev-text').focus();return;}
    sending=true;const btn=$('#ev-send');btn.disabled=true;btn.textContent='Đang gửi…';
    try{
      const out=await api('/api/2010/cards',{method:'POST',csrf:true,body:{op:'create',theme:W.theme,direction:W.dir,to:W.to,from:W.sender.trim()||ME.name||'',text:W.text,stickers:W.stickers}});
      store.del(DRAFT);Object.assign(W,{to:'',text:'',stickers:[]});
      ME.mine=[{...out.card,status:'live'},...(ME.mine||[])];ME.left=out.left;if(out.reward)ME.reward=out.reward;mineView();
      $('#ev-writer').innerHTML=sentView(out);fx(out.card.theme,{n:26,burst:true});
      $('#viet').scrollIntoView({block:'start',behavior:still()?'auto':'smooth'});
    }catch(err){toast(err.message,true);btn.disabled=false;btn.textContent='Gửi thiệp 💌';}
    finally{sending=false;}
  });
}
document.addEventListener('click',async e=>{
  const b=e.target.closest?.('[data-act],[data-back]');if(!b)return;
  if(b.hasAttribute('data-back')){store.set(BACK,Date.now());return;}   // the game page sends the player back here once signed in (v4/ev2010.js)
  const act=b.dataset.act;
  if(act==='again'){$('#ev-writer').innerHTML=writerView();bindWriter();paintPreview();}
  else if(act==='retry')loadWriter();
  else if(act==='claim'){
    b.disabled=true;
    try{const d=await api('/api/2010/cards',{method:'POST',csrf:true,body:{op:'claim'}});ME.reward=d.reward;
      if(d.reward?.granted){toast(`🎁 ${fmt(d.reward.coins)} xu đang chờ bạn trong phố!`);fx('bong_bong',{n:20,burst:true});}
      b.closest('.ev-reward').outerHTML=rewardBox(d.reward);}
    catch(err){toast(err.message,true);b.disabled=false;}
  }
});

/* ------------------------------------------------------------ link-preview picture (scripts/build_2010_og.py) */
function ogView(theme){
  document.documentElement.classList.add('ev-og');document.body.dataset.theme=theme;
  return `<div class="ev-og-wrap" data-theme="${esc(theme)}"><div class="ev-og-copy"><p class="ev-eyebrow">Phố Có Chuyện · 20/10</p><h1>Bạn có một<br>tấm thiệp 💌</h1><p>Chạm để mở lời chúc</p></div>
    ${cardHTML({theme,direction:'nam_nu',to:'người thương',text:'Chúc bạn một ngày 20/10 thật vui, thật xinh và luôn được yêu thương ✨',sender:'Một người thương',stickers:['💖','✨','🌷']})}</div>`;
}

/* ------------------------------------------------------------ start */
function goneView(why){
  const msg={expired:'Mùa thiệp 20/10 đã qua, tấm thiệp này đã được cất đi rồi.',hidden:'Tấm thiệp này đang được ban quản lý phố xem lại.',missing:'Không tìm thấy tấm thiệp này. Có thể link bị thiếu chữ, hoặc người gửi đã xóa thiệp.'}[why]||'Thiệp này không còn mở được nữa.';
  return `<header class="ev-top"><a class="ev-back" href="/2010">💐 Thiệp 20/10</a><span class="ev-brand">Phố Có Chuyện</span></header>
  <section class="ev-gone"><div class="ev-hero-art" aria-hidden="true"><svg viewBox="0 0 240 96">${ART.thu_tay()}</svg></div><h1>Ôi, thư lạc mất rồi</h1><p>${esc(msg)}</p>
  ${DATA.open?'<a class="ev-btn" href="/2010#viet">Viết thiệp của bạn 💌</a>':''}<a class="ev-btn ev-btn-ghost" href="/">Vào phố</a></section>`;
}
function start(){
  const root=$('#ev');if(!root)return;
  const q=new URLSearchParams(location.search);
  if(q.get('og')&&THEMES[q.get('og')]){root.innerHTML=ogView(q.get('og'));return;}
  if(DATA.mode==='card'&&DATA.card){
    root.innerHTML=readView(DATA.card);bindRead(DATA.card);
    if(q.has('open'))openEnvelope(DATA.card,{instant:true});
    return;
  }
  if(DATA.mode==='gone'){root.innerHTML=goneView(DATA.why);return;}
  const draft=store.get(DRAFT);
  if(draft&&typeof draft==='object'){for(const k of ['to','text','sender'])if(typeof draft[k]==='string')W[k]=draft[k].slice(0,500);
    if(DIRS[draft.dir])W.dir=draft.dir;if(THEMES[draft.theme])W.theme=draft.theme;if(Array.isArray(draft.stickers))W.stickers=draft.stickers.filter(s=>typeof s==='string').slice(0,6);}
  if(q.get('to'))W.to=q.get('to').slice(0,30);
  if(DIRS[q.get('dir')])W.dir=q.get('dir');
  if(q.get('theme')&&THEMES[q.get('theme')])W.theme=q.get('theme');
  root.innerHTML=homeView();loadWriter();
  if(location.hash==='#viet')setTimeout(()=>$('#viet')?.scrollIntoView({block:'start'}),60);
  if(!still())fx('hoa_hong',{n:12});
}
start();
