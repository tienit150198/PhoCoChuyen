import {illustratedIcon} from './illustrated-icons.js';
export {iconNames,hasIcon,careerIconNames} from './illustrated-icons.js';
// Original vector UI and item artwork. No external fonts, stock packs or CDN.
export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function icon(name,size=20,cls='') {return illustratedIcon(name,size,cls);}
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
