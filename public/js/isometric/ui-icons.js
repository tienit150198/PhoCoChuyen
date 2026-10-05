/** Original rounded, two-tone illustrations for the paper-and-wood town controls. */
const paper='var(--iso-paper-top, #fff9ed)',leaf='var(--iso-leaf-soft, #e4e9cc)',ochre='var(--iso-icon-ochre, #e8c584)',clay='var(--iso-icon-clay, #dd9b7f)';
const marks={
  map:`<path d="m3.5 5 5-1.5 7 2 5-1.5v15l-5 1.5-7-2-5 1.5Z" fill="${leaf}"/><path d="M8.5 4v14.5M15.5 5.5v14"/><path d="m11 12 2-3 2 3-2 2Z" fill="${clay}"/>`,
  briefcase:`<rect x="3" y="7" width="18" height="13" rx="3" fill="${ochre}"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12q9 4 18 0"/><path d="M10 12h4v4h-4z" fill="${paper}"/>`,
  bag:`<path d="M6 8h12l2 10a2 2 0 0 1-2 3H6a2 2 0 0 1-2-3Z" fill="${ochre}"/><path d="M8 9V6a4 4 0 0 1 8 0v3M9 15q3 2 6 0"/>`,
  store:`<path d="M5 10v10h14V10" fill="${ochre}"/><path d="m3 9 2-5h14l2 5q-1 4-4.5 1-2 4-4.5 0-2.5 4-4.5 0Q4 13 3 9Z" fill="${clay}"/><path d="M10 20v-6h5v6" fill="${paper}"/>`,
  user:`<circle cx="12" cy="8" r="4.5" fill="${ochre}"/><path d="M4 21c0-9 16-9 16 0Z" fill="${leaf}"/><path d="M9 7.5h.01M15 7.5h.01"/>`,
  people:`<circle cx="9" cy="8" r="3.5" fill="${ochre}"/><path d="M2.5 20c0-8 13-8 13 0Z" fill="${leaf}"/><path d="M16 5a3.5 3.5 0 0 1 0 7M18 14c2.5 1 3.5 3 3.5 6"/>`,
  menu:`<circle cx="5" cy="12" r="2" fill="${ochre}"/><circle cx="12" cy="12" r="2" fill="${ochre}"/><circle cx="19" cy="12" r="2" fill="${ochre}"/>`,
  settings:`<path d="m10 3 4 0 1 3 3 1 2 3v4l-3 2-1 3-4 2-4-2-1-3-3-2v-4l2-3 3-1Z" fill="${ochre}"/><circle cx="12" cy="12" r="3.5" fill="${paper}"/>`,
  clipboard:`<rect x="5" y="4" width="14" height="17" rx="2.5" fill="${ochre}"/><rect x="8" y="2.5" width="8" height="5" rx="2" fill="${paper}"/><path d="m8 12 1.5 1.5L12 11M14 12h2M8 17h8"/>`,
  note:`<path d="M5 3.5h14V21l-4-2-3 2-3-2-4 2Z" fill="${ochre}"/><path d="M8 8h8M8 12h8M8 16h4"/>`,
  clock:`<circle cx="12" cy="12" r="9" fill="${paper}"/><path d="M12 6v6l4 2"/><path d="M6 3 3 6M18 3l3 3"/>`,
  leaf:`<path d="M20 3C8 1 2 9 6 16c5 7 15 1 14-13Z" fill="${leaf}"/><path d="M4 21 15 10M9 16l-1-5M9 16l5 1"/>`,
  chats:`<path d="M12 10c0-5 10-5 10 1 0 2-.5 3-1.5 4L22 20l-4-1.5c-4 1-7-1-7-4" fill="${ochre}"/><path d="M2.5 9c0-8 15-8 15 0 0 5-4 7-9 5.5L3 17l1-5c-1-1-1.5-2-1.5-3Z" fill="${leaf}"/><path d="M6.5 8h7M6.5 11h4"/>`,
  fish:`<path d="M4 12c4-8 10-8 14 0-4 8-10 8-14 0Z" fill="${ochre}"/><path d="m18 12 4-4v8Z" fill="${clay}"/><circle cx="8" cy="11" r=".6" fill="currentColor"/><path d="M12 6v12"/>`,
  boat:`<path d="m3 15 3 5h12l3-5Z" fill="${ochre}"/><path d="M11 14V3l8 9h-8" fill="${leaf}"/><path d="M3 22q3-2 6 0 3-2 6 0 3-2 6 0"/>`,
  pool:`<path d="M7 17V6a3 3 0 0 1 6 0M14 17V6a3 3 0 0 1 6 0M7 9h7M7 13h7"/><path d="M2 19q3-2 6 0 3-2 6 0 3-2 6 0M2 22q3-2 6 0 3-2 6 0 3-2 6 0"/>`,
  compass:`<circle cx="12" cy="12" r="9" fill="${paper}"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5Z" fill="${clay}"/>`,
  overview:`<path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3M21 16v3a2 2 0 0 1-2 2h-3"/><path d="m7 14 4-7 6 3 1 5-8 2Z" fill="${leaf}"/>`,
  plus:'<path d="M12 5v14M5 12h14"/>',minus:'<path d="M5 12h14"/>',
  arrow:'<path d="M4 12h15m-5-5 5 5-5 5"/>',x:'<path d="m6 6 12 12M18 6 6 18"/>',
};
export function uiIcon(name,size=20){
  const dimension=Math.max(12,Math.min(64,Number(size)||20));
  return `<svg class="icon illustrated-ui-icon" width="${dimension}" height="${dimension}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${marks[name]||marks.leaf}</svg>`;
}
