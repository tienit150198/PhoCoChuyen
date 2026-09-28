// Original vector UI and item artwork. No external fonts, stock packs or CDN.
export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
 briefcase:'M3 7h18v13H3V7ZM8 7V4h8v3M3 12h18M11 12v2h2v-2',
 map:'M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2ZM9 4v14M15 6v14',
 compass:'M12 2a10 10 0 100 20 10 10 0 000-20ZM16 8l-2.5 5.5L8 16l2.5-5.5L16 8Z',
 alert:'M12 3 2 20h20L12 3ZM12 10v4M12 17h.01',
 store:'M4 10v10h16V10M3 10l2-6h14l2 6M3 10a3 3 0 006 0 3 3 0 006 0 3 3 0 006 0M10 20v-5h4v5',
 truck:'M2 6h12v10H2V6ZM14 9h4l3 4v3h-7V9ZM6 19a2 2 0 100-4 2 2 0 000 4ZM17 19a2 2 0 100-4 2 2 0 000 4Z',
 bowl:'M3 11h18a9 9 0 01-18 0ZM8 21h8M9 7c0-2 2-2 2-4M13 7c0-2 2-2 2-4',
 music:'M9 18V5l11-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0ZM20 16a3 3 0 11-6 0 3 3 0 016 0Z',
 globe:'M12 2a10 10 0 100 20 10 10 0 000-20ZM2 12h20M12 2c3 3 4 6 4 10s-1 7-4 10c-3-3-4-6-4-10s1-7 4-10Z',
 palette:'M12 2a10 10 0 000 20c1 0 2-1 2-2s-1-2 0-3 2-1 3-1h2a3 3 0 003-3c0-6-5-11-10-11ZM7 12h.01M9 7h.01M15 7h.01',
 layout:'M3 3h18v18H3V3ZM3 9h18M9 9v12',
 flower:'M12 8a3 3 0 110-6 3 3 0 010 6ZM12 8v14M12 14c-4 0-6-2-6-5 3 0 6 2 6 5ZM12 16c4 0 6-2 6-5-3 0-6 2-6 5Z',
 wrench:'M14 6a4 4 0 015-4l-3 3 1 2 2 1 3-3a4 4 0 01-5 5L7 20a2 2 0 01-3-3L14 6Z',
 bike:'M5 18a3 3 0 100-6 3 3 0 000 6ZM19 18a3 3 0 100-6 3 3 0 000 6ZM5 15l4-7h6l4 7M9 8l3 7h2M14 5h3',
 bed:'M3 18V6M3 14h18v4M21 14v-3a3 3 0 00-3-3h-7v6M7 11a2 2 0 100-4 2 2 0 000 4Z',
 paw:'M12 13c-3 0-5 3-5 5 0 2 2 2 5 1 3 1 5 1 5-1 0-2-2-5-5-5ZM6 10a2 2 0 100-4 2 2 0 000 4ZM18 10a2 2 0 100-4 2 2 0 000 4ZM9 6a2 2 0 100-4 2 2 0 000 4ZM15 6a2 2 0 100-4 2 2 0 000 4Z',
 calculator:'M5 2h14v20H5V2ZM8 6h8v3H8V6ZM8 13h.01M12 13h.01M16 13h.01M8 17h.01M12 17h.01M16 17h.01',
 building:'M4 21V3h11v18M15 9h5v12M8 7h3M8 11h3M8 15h3M3 21h18',
 cart:'M3 3h2l3 12h11l2-8H6M9 20a1 1 0 100-2 1 1 0 000 2ZM18 20a1 1 0 100-2 1 1 0 000 2Z',
 cake:'M4 21h16v-8H4v8ZM4 16c2 1 3-1 4 0s2 1 4 0 3-1 4 0 3 1 4 0M12 13V9M12 6c-1-1 0-3 0-3s1 2 0 3Z',
 tractor:'M3 17a3 3 0 106 0 3 3 0 00-6 0ZM16 18a2 2 0 104 0 2 2 0 00-4 0ZM6 14V8h6l2 5h6v4M9 8V5',
 user:'M12 12a5 5 0 100-10 5 5 0 000 10ZM3 22c0-5 4-8 9-8s9 3 9 8',
 inbox:'M3 13l3-9h12l3 9v7H3v-7ZM3 13h5l2 3h4l2-3h5',
 menu:'M3 6h18M3 12h18M3 18h18',
 home:'M3 10l9-7 9 7M5 9v12h14V9M9 21v-8h6v8',
 leaf:'M20 3C8 2 2 7 5 14c3 7 14 4 15-11ZM4 21l10-11',
 gift:'M3 8h18v4H3zM5 12v9h14v-9M12 8v13M12 8C4 9 5 1 9 3c2 1 3 5 3 5Zm0 0c8 1 7-7 3-5-2 1-3 5-3 5Z',
 bag:'M5 7h14l2 14H3L5 7ZM8 8V5a4 4 0 018 0v3',
 cross:'M8 3h8v5h5v8h-5v5H8v-5H3V8h5V3Z',
 headphones:'M4 14v-2a8 8 0 0116 0v2M4 12H2v7h4v-7H4Zm16 0h2v7h-4v-7h2ZM18 19c0 3-2 3-6 3',
 book:'M3 3h7a3 3 0 012 2 3 3 0 012-2h7v17h-7a3 3 0 00-2 2 3 3 0 00-2-2H3V3ZM12 5v17M6 7h3M6 11h3M15 7h3M15 11h3',
 phone:'M7 2h10a2 2 0 012 2v16a2 2 0 01-2 2H7a2 2 0 01-2-2V4a2 2 0 012-2ZM10 5h4M11 19h2',
 people:'M16 21v-2c0-3-2-5-6-5s-6 2-6 5v2M10 11a4 4 0 100-8 4 4 0 000 8ZM18 4a4 4 0 010 7M20 21v-2c0-2-1-4-3-5',
 settings:'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1 1-3ZM12 8a4 4 0 100 8 4 4 0 000-8Z',
 coin:'M12 2a10 10 0 100 20 10 10 0 000-20ZM15 7h-4a3 3 0 000 6h2a2 2 0 010 4H9M12 5v14',
 star:'M12 3l2.8 5.8 6.4.9-4.6 4.5 1.1 6.3L12 17.5l-5.7 3 1.1-6.3-4.6-4.5 6.4-.9L12 3Z',
 sun:'M12 8a4 4 0 100 8 4 4 0 000-8ZM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19',
 cloud:'M6 19a5 5 0 01-1-10 7 7 0 0113-1 6 6 0 010 11H6Z',
 clock:'M12 2a10 10 0 100 20 10 10 0 000-20ZM12 6v6l4 3',
 chevron:'M9 5l7 7-7 7',arrow:'M4 12h16M13 5l7 7-7 7', back:'M20 12H4M11 5l-7 7 7 7',
 plus:'M12 5v14M5 12h14',minus:'M5 12h14',check:'M4 12l5 5L20 6',x:'M6 6l12 12M18 6L6 18',
 chat:'M21 11a9 9 0 01-9 9c-2 0-3-.5-4-1L3 21l1-6a9 9 0 1117-4ZM8 10h8M8 14h5',
 search:'M10 3a7 7 0 100 14 7 7 0 000-14ZM15 15l6 6',
 sparkle:'M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3 3-7Z',
 eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12ZM12 9a3 3 0 100 6 3 3 0 000-6',
 lock:'M5 10h14v11H5V10ZM8 10V6a4 4 0 018 0v4M12 14v3',
 box:'M3 7l9-5 9 5v11l-9 5-9-5V7ZM3 7l9 5 9-5M12 12v11M7 5l9 5',
 clipboard:'M9 4H5v17h14V4h-4M9 2h6v5H9V2ZM8 12h8M8 16h6',
 folder:'M3 5h7l2 3h9v13H3V5Z',
 link:'M10 14l4-4M8 16l-2 2a4 4 0 01-6-6l5-5a4 4 0 016 0M16 8l2-2a4 4 0 016 6l-5 5a4 4 0 01-6 0',
 question:'M12 2a10 10 0 100 20 10 10 0 000-20ZM9 8a3 3 0 015 2c-1 1-2 1-2 4M12 17h.01',
 trash:'M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7',
 camera:'M3 7h5l2-3h4l2 3h5v14H3V7ZM12 10a4 4 0 100 8 4 4 0 000-8Z',
 play:'M8 4l12 8-12 8V4Z',pause:'M7 4h3v16H7zM14 4h3v16h-3z',
 volume:'M3 9h4l5-5v16l-5-5H3V9ZM16 8a6 6 0 010 8M19 5a10 10 0 010 14',
 mute:'M3 9h4l5-5v16l-5-5H3V9ZM17 9l5 6M22 9l-5 6',
 grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
 flag:'M4 22V3M4 3c6-4 10 4 16 0v11c-6 4-10-4-16 0',
 award:'M12 2a7 7 0 100 14 7 7 0 000-14ZM7 14l-1 8 6-3 6 3-1-8',
 calendar:'M3 5h18v16H3V5ZM7 2v6M17 2v6M3 10h18M7 14h2M12 14h2M7 18h2',
 mail:'M3 5h18v14H3V5ZM3 5l9 8 9-8',
 send:'M22 2L2 9l8 4 4 9 8-20ZM10 13L22 2',
 expand:'M3 9V3h6M15 3h6v6M21 15v6h-6M9 21H3v-6',
 download:'M12 3v12M7 10l5 5 5-5M4 16v5h16v-5',upload:'M12 16V4M7 9l5-5 5 5M4 16v5h16v-5',
 shield:'M12 2l9 4v6c0 5-9 10-9 10S3 17 3 12V6l9-4ZM8 12l3 3 5-6',
 plant:'M12 15V7M12 12C3 12 3 4 3 4s9 0 9 8ZM12 9c0-7 9-7 9-7s0 7-9 7ZM6 15h12l-2 7H8l-2-7Z',
 rug:'M4 5h16v14H4V5ZM7 8h10v8H7V8ZM4 2v3M9 2v3M15 2v3M20 2v3M4 19v3M9 19v3M15 19v3M20 19v3',
 lamp:'M8 3h8l4 10H4L8 3ZM12 13v8M7 21h10',
 chair:'M5 3h14v10H5V3ZM3 13h18v5H3V13ZM5 18v4M19 18v4',
 shelf:'M3 2v20M21 2v20M3 9h18M3 17h18M7 3v6M11 4v5M16 3v6M6 12v5M10 11v6M17 12v5',
 board:'M3 3h18v14H3V3ZM12 17v5M7 22l5-5 5 5M7 7h5M7 11h10',
 image:'M3 3h18v18H3V3ZM3 17l6-6 4 4 3-3 5 6M15 7h.01',
 heart:'M20 4c-3-3-7-1-8 2-1-3-5-5-8-2-4 5 2 10 8 16 6-6 12-11 8-16Z',
 cat:'M5 10L4 3l6 4h4l6-4-1 7c4 7 0 11-7 11S1 17 5 10ZM8 12h.01M16 12h.01M11 16l1 1 1-1',
 coffee:'M4 4h13v12a5 5 0 01-5 5H9a5 5 0 01-5-5V4ZM17 5h3a3 3 0 010 6h-3M7 1v1M11 1v1',
 note:'M5 3h14v18l-4-2-3 2-3-2-4 2V3ZM8 7h8M8 11h8M8 15h5',
 bell:'M5 16V9a7 7 0 0114 0v7l2 3H3l2-3ZM9 22h6',
 refresh:'M20 7a9 9 0 10-1 12M20 2v6h-6',
 exit:'M9 3H3v18h6M9 12h12M16 7l5 5-5 5',
 move:'M12 2v20M2 12h20M8 6l4-4 4 4M8 18l4 4 4-4M6 8l-4 4 4 4M18 8l4 4-4 4',
 scissors:'M5 4a3 3 0 100 6 3 3 0 000-6ZM5 14a3 3 0 100 6 3 3 0 000-6ZM8 8l13 13M8 16L21 3',
};
export function icon(name,size=20,cls='') {return `<svg class="icon ${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.sparkle}"/></svg>`;}
export const palettes={cream:'#e9d6b5',mint:'#adc6a5',blue:'#a3c6d7',rose:'#ddaab7',brown:'#bd9468'};
export function itemArt(id,size=80,color='cream') {
 const fill=palettes[color]||color;
 const arts={
 bunny:`<ellipse cx="33" cy="21" rx="7" ry="18" fill="#e7d7b8"/><ellipse cx="53" cy="21" rx="7" ry="18" fill="#e7d7b8"/><ellipse cx="33" cy="20" rx="3" ry="12" fill="#dca9a1"/><ellipse cx="53" cy="20" rx="3" ry="12" fill="#dca9a1"/><ellipse cx="43" cy="65" rx="22" ry="24" fill="#f3e9d0"/><circle cx="43" cy="43" r="24" fill="#f3e9d0"/><circle cx="34" cy="42" r="2.6" fill="#655546"/><circle cx="52" cy="42" r="2.6" fill="#655546"/><path d="M40 48q3 4 6 0" fill="none" stroke="#8d6b5b" stroke-width="2"/><ellipse cx="28" cy="49" rx="5" ry="3" fill="#e5b1a0"/><ellipse cx="58" cy="49" rx="5" ry="3" fill="#e5b1a0"/><path d="M43 65l-11-5v12l11-5 11 5V60Z" fill="#91a786"/>`,
 bear:`<circle cx="24" cy="25" r="12" fill="#b78b5d"/><circle cx="62" cy="25" r="12" fill="#b78b5d"/><ellipse cx="43" cy="65" rx="23" ry="25" fill="#c49a70"/><circle cx="43" cy="41" r="27" fill="#c49a70"/><ellipse cx="43" cy="49" rx="12" ry="9" fill="#f1dec1"/><circle cx="33" cy="38" r="2.7" fill="#574637"/><circle cx="53" cy="38" r="2.7" fill="#574637"/><ellipse cx="43" cy="46" rx="4" ry="3" fill="#574637"/><path d="M25 66h36v10H25" fill="#8c9c85"/>`,
 bag:`<path d="M30 34V24c0-19 26-19 26 0v10" fill="none" stroke="#9b8268" stroke-width="7"/><path d="M18 30h50l5 51H13Z" fill="#ecdabd"/><path d="M29 51l-1-9 10 5h11l10-5-1 9c9 21-40 21-29 0Z" fill="#b29476"/><circle cx="37" cy="54" r="2" fill="#fff3de"/><circle cx="50" cy="54" r="2" fill="#fff3de"/><path d="M41 59l3 2 3-2" fill="none" stroke="#fff3de" stroke-width="2"/>`,
 shirt:`<path d="M29 16l-19 12 10 17 9-5v42h30V40l9 5 10-17-19-12c-5 12-25 12-30 0Z" fill="${fill}"/><path d="M32 16c1 16 24 16 24 0" fill="none" stroke="#fff8e9" stroke-width="5"/><path d="M34 53a7 7 0 0112-5 6 6 0 016 10H35a5 5 0 01-1-10" fill="#fff8ef"/>`,
 cloth:`<rect x="14" y="28" width="63" height="50" rx="9" fill="${fill}"/><path d="M22 30v44M25 35h46" fill="none" stroke="#f8f1df" stroke-width="3"/><path d="M45 30v48" stroke="#e6d8b5" stroke-width="10"/><path d="M44 38C20 31 36 19 45 34c9-15 24-3-1 4Z" fill="#e6d8b5"/>`,
 blocks:`<rect x="13" y="52" width="28" height="28" rx="3" fill="#ba8d63"/><rect x="46" y="53" width="26" height="27" rx="3" fill="#9cb5b8"/><path d="M11 48l30-35 29 35Z" fill="#c8917f"/><circle cx="39" cy="67" r="8" fill="#d6be8c"/><path d="M39 27v14" stroke="#f4e7ce" stroke-width="3"/>`,
 card:`<path d="M16 24h57v51H16Z" fill="#f6e8cd"/><path d="M16 24l28 23 29-23" fill="#e6d5b5"/><path d="M35 44c-9-10-18 4 9 21 27-17 18-31 9-21-4-5-11-5-18 0" fill="#bc8174"/>`,
 box:`<path d="M23 20l37-5 11 10v51l-39 6-12-11Z" fill="${fill}"/><path d="M32 29l39-4v51l-39 6Z" fill="${fill}"/><path d="M23 20l9 9 39-4-11-10Z" fill="#f9f2e3"/><path d="M21 22l11 7v53l-12-11Z" fill="#425c5120"/><rect x="41" y="39" width="19" height="19" rx="5" fill="#fff8e8"/><path d="M51 43v11M46 49h10" stroke="#7b9e91" stroke-width="3"/><path d="M40 67l23-3" stroke="#fff8e8" stroke-width="3"/>`,
 };
 const art=arts[id]||arts.box;
 return `<svg class="item-art" width="${size}" height="${size}" viewBox="0 0 88 96" role="img" aria-label="Minh họa vật phẩm"><ellipse cx="44" cy="85" rx="29" ry="6" fill="#4c463214"/>${art}</svg>`;
}
export function portrait(npc,size=52) {
 const key=typeof npc==='object'?(npc?.id||npc?.display_name||''):String(npc);
 const n=Number(key.slice(-2))||0;
 const cid=key.split('_npc_')[0];
 const colors=['#879477','#bfa090','#8e97b3','#b5a1b6','#8bafac','#bda269'];
 const clothes=colors[n%colors.length];
 const old=n===2&&cid==='mother_baby'||n===2&&cid==='pharmacy';
 const hair=old?'#b6b4a8':n%2===0?'#5b5548':'#6d5143';
 const long=n%2===1;
 return `<svg class="portrait" width="${size}" height="${size}" viewBox="0 0 80 80" role="img" aria-label="Nhân vật"><rect width="80" height="80" rx="26" fill="${colors[(n+2)%6]}25"/><path d="M11 80c1-28 57-29 58 0" fill="${clothes}"/>${long?`<path d="M18 41C10-1 74-4 62 64H19" fill="${hair}"/>`:''}<rect x="33" y="51" width="14" height="16" rx="5" fill="#e0b591"/><ellipse cx="40" cy="35" rx="23" ry="26" fill="${hair}"/><ellipse cx="40" cy="39" rx="20" ry="23" fill="#f2cba8"/><path d="M19 30Q24 3 47 14Q59 17 61 33Q47 27 43 20Q36 31 19 30Z" fill="${hair}"/><ellipse cx="32" cy="38" rx="3.2" ry="4" fill="#4b3936"/><ellipse cx="48" cy="38" rx="3.2" ry="4" fill="#4b3936"/><circle cx="31.3" cy="36.7" r="1.1" fill="#fff9eb"/><circle cx="47.3" cy="36.7" r="1.1" fill="#fff9eb"/><ellipse cx="26" cy="45" rx="4" ry="2.5" fill="#d89083" opacity=".5"/><ellipse cx="54" cy="45" rx="4" ry="2.5" fill="#d89083" opacity=".5"/><path d="M35 48q5 5 10 0" fill="none" stroke="#a57260" stroke-width="1.8" stroke-linecap="round"/>${old?'<path d="M23 34h15v10H23zM43 34h15v10H43zM38 38h5" stroke="#756b58" fill="none" stroke-width="1.3"/>':''}<path d="M27 62l13 9 13-9" fill="none" stroke="#fff3de" stroke-width="4"/></svg>`;
}
