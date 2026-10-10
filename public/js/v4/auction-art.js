/** Miniature artworks shared by auction previews and home decoration.
 * Self-contained SVG: no remote images, ids, filters or fonts; works in exported room photos.
 * Each composition has its own silhouette, not just a different palette. */
import {escapeHTML as esc} from '../icons.js';

export const PAINTINGS={
  tr_nuoc_noi:['water','#7fb3d5','#c8a96a','#e85d3a'],
  tr_pho_5h:['street','#f6b26b','#8e7cc3','#ffd966'],
  tr_ganh_hang:['figure','#d9c27e','#6b4f2a','#c0392b'],
  tr_meo_mai_ton:['cat','#a9c4eb','#8a8a8a','#f1c232'],
  tr_sen_ho:['lotus','#cfe2f3','#6aa84f','#e06666'],
  tr_den_long:['lantern','#1c2541','#3a506b','#ff9f1c'],
  tr_tau_cuoi:['train','#5b6c8f','#3d3d3d','#ffe599'],
  tr_hai_dang:['light','#9fc5e8','#0b5394','#ffffff'],
  tr_cho_tet:['market','#f4cccc','#990000','#ffd966'],
  tr_trang_rang:['moon','#20124d','#38761d','#fff2cc'],
  tr_long_van:['dragon','#241b22','#82342f','#e9bf68'],
  tr_hac_ngoc:['cranes','#b8d6c6','#245951','#fff1ce'],
  tr_vinh_ngoc:['bay','#f5d6a1','#236b70','#df8154'],
  tr_ngan_ha:['galaxy','#171d3b','#616295','#b4e6d5'],
  tr_bac_thang:['terraces','#c9d9d3','#547469','#e5bd61'],
  tr_mua_pho:['rain','#66778d','#374861','#e7a35b'],
  tr_cho_noi:['floating','#f5ceb1','#4b8585','#bc614b'],
  tr_gom_lam:['ceramic','#eadcc3','#325e86','#e9aa70'],
  tr_ca_chep:['koi','#193c40','#306365','#e7ac59'],
  tr_phuong:['phoenix','#51273f','#9b4358','#f0c677'],
  tr_trong_dong:['bronze','#293936','#776047','#d8b46c'],
  tr_cong_que:['gate','#e4d7b2','#74644c','#9caf79'],
  tr_vuon_cuc:['daisies','#d0ddd0','#587a63','#edd495'],
  tr_doi_che:['tea','#d7dfd0','#3e7460','#a8bf74'],
  tr_mua_roi:['puppet','#333f52','#4e8581','#d65d47'],
  tr_vuon_buom:['butterflies','#ece2c5','#537c67','#be708f'],
  tr_ngua_gio:['horse','#d8bd8e','#ad523f','#f1dfaa'],
  tr_ban_cong:['balcony','#e9c591','#6f827c','#c3537b'],
  tr_thuyen_thung:['basket','#bcd9da','#4f9297','#d6ab69'],
  tr_bon_mua:['seasons','#f3dfc0','#485e55','#c57258'],
};
const rect=(x,y,w,h,c,extra='')=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${c}" ${extra}/>`;
const path=(d,c,extra='')=>`<path d="${d}" fill="${c}" ${extra}/>`;
const line=(d,c,w=2,extra='')=>path(d,'none',`stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" ${extra}`);
const circle=(x,y,r,c,extra='')=>`<circle cx="${x}" cy="${y}" r="${r}" fill="${c}" ${extra}/>`;
const ellipse=(x,y,rx,ry,c,extra='')=>`<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${c}" ${extra}/>`;
const ivory='#fff0ce',ink='#263842',gold='#dcaf65',red='#b94237';
const repeat=(n,fn)=>Array.from({length:n},(_,i)=>fn(i)).join('');
const waves=(c,y=120)=>repeat(5,i=>line(`M${12+i%2*13} ${y+i*14}q24 -5 49 0t49 0m24 0q24 -5 49 0t49 0`,c,1,'opacity=".38"'));
const bird=(x,y,s,c)=>`<g transform="translate(${x} ${y}) scale(${s})">${line('M-8 3Q-4 -4 0 1Q4 -4 8 3',c,2)}</g>`;
const boat=(x,y,s,c)=>`<g transform="translate(${x} ${y}) scale(${s})">${path('M-40 0Q0 30 44 -2L28 14H-24Z',c)}${line('M-5 0V-55',ink)}${path('M-9 -54L-36 -6H-9Z',ivory)}${path('M0 -46L27 -6H0Z',c)}</g>`;
const pine=(x,y,s,c)=>`<g transform="translate(${x} ${y}) scale(${s})">${line('M0 0V-65',c,3)}${path('M0 -75L-18 -42H-8L-25 -22H-12L-30 0H30L12 -22H25L8 -42H18Z',c)}</g>`;
const lotus=(x,y,s)=>`<g transform="translate(${x} ${y}) scale(${s})">${ellipse(0,15,28,7,'#315b51')}${path('M0 8Q-29 2 -26 -16Q-6 -16 0 8M0 8Q29 2 26 -16Q6 -16 0 8','#dc7690')}${path('M0 8Q-17 -13 0 -30Q17 -13 0 8','#f3b4bd')}${circle(0,5,4,gold)}</g>`;
const crane=(x,y,s)=>`<g transform="translate(${x} ${y}) scale(${s})">${path('M-2 0Q-24 -8 -42 -37Q-10 -27 6 -6Q30 -29 51 -30Q30 -6 12 5Z',ivory)}${path('M-40 -36L-23 -11L-15 -9M50 -29L27 -6L18 -4',ink)}${line('M9 2Q19 12 26 6Q32 1 39 3',ivory,5)}${circle(39,3,3,red)}${path('M41 3L53 5L42 6',ink)}${line('M0 2L-23 17M4 4L-14 24',ink,1.5)}</g>`;

function scene(m,a,b,c){
  switch(m){
    case'water':return rect(0,95,320,105,'#477d88')+circle(250,49,24,ivory)+path('M0 98Q66 62 118 94T320 83V110H0',b)
      +waves(ivory,117)+repeat(9,i=>line(`M${i*15} 117q10 -20 4 -34m-4 34q-5 -17 -10 -23`,b,2))
      +`<g transform="translate(185 140)">${path('M-63 0Q0 37 72 -3L46 19H-35Z',ink)}${path('M-20 -3L-8 -30L12 -29L21 -1',c)}${path('M-26 -29L0 -44L23 -30Z',ivory)}${line('M9 -13L54 -63',ink,3)}</g>`;
    case'street':return circle(245,45,28,c)+path('M0 170L163 93L320 151V200H0',b)+path('M121 200L161 106L173 109L220 200',ivory)
      +repeat(6,i=>{const x=i<3?i*44:188+(i-3)*45,y=i<3?40+i*15:73-(i-3)*12,h=150-y;return rect(x,y,40,h,i%2?'#65445b':'#92616b')+path(`M${x-5} ${y}l25 -18 25 18Z`,ink)+rect(x+10,y+18,9,17,c)+rect(x+25,y+18,9,17,c)+rect(x+14,y+h-30,15,30,ink);})
      +line('M0 27Q146 77 320 23',ink,1)+repeat(5,i=>circle(20+i*67,40+Math.sin(i)*10,3,c));
    case'figure':return rect(0,0,320,200,'#ae4436')+circle(230,61,52,'#c75e43')+repeat(8,i=>line(`M${15+i*42} 0V200`,gold,1,'opacity=".16"'))
      +path('M127 200L162 80L184 81L200 200Z',b)+path('M129 70L173 42L208 72Z',ivory)+ellipse(172,80,11,12,ink)
      +line('M68 109Q174 56 268 105',gold,5)+line('M81 104L63 154M81 104L97 154M257 100L237 151M257 100L273 151',ivory,2)
      +path('M44 152Q81 183 117 152Z',gold)+path('M217 151Q257 181 290 151Z',gold)+repeat(6,i=>circle(53+i*10,150-i%2*5,7,i%2?b:ivory));
    case'cat':return circle(245,44,26,ivory)+path('M0 124L99 71L320 130V200H0',b)+repeat(11,i=>line(`M${i*36-50} 105L${i*36} 200`,'#586b80',2))
      +path('M119 152Q104 132 116 111L116 78L131 92L149 88L166 73L166 110Q185 151 157 159Z',c)
      +line('M157 151Q214 178 217 139Q218 123 202 120',c,10)+circle(129,109,2,ink)+circle(152,109,2,ink)
      +line('M136 116h6m-20 0l-20 -4m20 10l-20 3m57 -9l19 -6m-19 11l20 3',ink,1)+bird(49,40,1,ink);
    case'lotus':return rect(0,0,320,200,'#83b7ad')+waves(ivory,40)+repeat(7,i=>ellipse(22+i*49,95+(i%3)*27,28,8,b,'opacity=".7"'))
      +line('M85 161Q83 119 92 101M214 170Q193 136 199 92','#315b51',3)+lotus(85,120,1.3)+lotus(204,90,1.05)+lotus(265,155,.65)
      +line('M39 46L63 40M48 34L56 54',ivory,1.5)+circle(53,43,2,gold);
    case'lantern':return rect(0,110,320,90,b)+waves(c,133)+path('M0 102L32 79L67 105L93 78L125 105L154 79L190 104L219 82L252 107L282 81L320 106V126H0',ink)
      +line('M-5 12Q161 68 325 8',gold,2)+repeat(7,i=>{const x=22+i*46,y=29+Math.sin(i/6*Math.PI)*26;return line(`M${x} ${y-9}v12`,gold,1)+ellipse(x,y+13,12,17,i%2?red:c)+line(`M${x-7} ${y}h14m-14 27h14m-7 0v12`,gold,2)+line(`M${x} 149v${12+i%3*7}`,c,3,'opacity=".5"');});
    case'train':return path('M0 116L71 38L136 105L207 29L320 119V200H0',b)+path('M0 126Q152 74 320 113V140H0','#8296a7')
      +line('M117 124L20 200M194 124L300 200',ivory,3)+repeat(6,i=>line(`M${97-i*13} ${140+i*10}H${219+i*14}`,ink,4))
      +repeat(5,i=>ellipse(159+i*21,76-i*11,22+i*3,11,'#d5d9d4',`opacity="${.65-i*.09}"`))
      +rect(122,101,66,54,ink,'rx="9"')+rect(129,82,52,34,ink,'rx="5"')+rect(136,89,14,17,a)+rect(158,89,14,17,a)
      +circle(155,126,12,c)+circle(155,126,5,ivory)+path('M117 156L108 169H201L188 156Z',red);
    case'light':return rect(0,112,320,88,b)+waves(ivory,125)+path('M0 200L66 121L137 114L197 200Z',ink)
      +path('M78 133L86 50H109L120 134Z',ivory)+path('M80 100H115L116 112H79Z',red)+rect(82,39,32,18,ink)
      +path('M78 38L98 23L118 38Z',red)+rect(89,43,19,9,c)+path('M109 43L315 15V83L109 50Z',ivory,'opacity=".3"')+boat(249,154,.48,red)+bird(187,78,1.1,ink);
    case'market':return path('M0 133L164 74L320 138V200H0','#c4856c')+path('M100 200L152 106L172 107L225 200Z',ivory)
      +repeat(4,i=>{const x=i<2?8+i*63:203+(i-2)*63,y=83+(i%2)*19;return rect(x,y+20,46,57,'#c68d54')+path(`M${x-7} ${y+21}l14 -24h33l12 24Z`,i%2?b:red)+repeat(4,j=>circle(x+7+j*11,y+22,6,c))+rect(x+7,y+44,33,5,ink);})
      +line('M50 87Q72 44 44 11M63 48L92 26M57 43L28 28',ink,3)+repeat(9,i=>circle(32+(i*23)%64,16+(i*17)%50,5,i%2?ivory:'#e8a0a0'));
    case'moon':return circle(214,66,42,c)+circle(201,58,7,'#e8d9ac','opacity=".4"')+path('M0 143Q85 68 177 133T320 102V200H0',b)
      +path('M0 175Q110 103 206 159T320 151V200H0','#183f3d')+path('M183 200Q219 167 177 140Q200 159 164 200Z',c,'opacity=".55"')
      +pine(58,158,1.4,ink)+pine(95,160,.8,ink)+pine(288,174,.9,ink)+repeat(14,i=>circle(15+(i*43)%290,13+(i*17)%68,i%3?1:2,ivory));
    case'dragon':return circle(158,102,74,b)+circle(158,102,65,'none',`stroke="${gold}" stroke-width="1"`)
      +line('M77 132C53 93 128 64 139 117S232 155 221 98S161 51 185 80',gold,20)
      +line('M77 132C53 93 128 64 139 117S232 155 221 98S161 51 185 80',b,9)
      +repeat(13,i=>path(`M${84+i*10} ${96+Math.sin(i*.6)*28}l5 -10 5 7Z`,gold))
      +path('M178 75L187 61L207 65L223 79L200 89L183 85Z',gold)+circle(201,73,3,ink)
      +line('M187 65L178 48L193 53M201 65L207 47M213 81Q247 63 263 78M211 85Q250 102 271 87',gold,2)
      +line('M106 88L99 67L80 61M164 146L155 167L131 175M221 117L245 124L255 112',gold,5)
      +repeat(4,i=>line(`M${12+i*86} ${24+i%2*144}q8 -14 19 -4q14 -7 24 5h-46`,gold,1,'opacity=".65"'));
    case'cranes':return circle(236,51,28,ivory)+path('M0 153Q76 129 135 158T320 145V200H0',b,'opacity=".25"')
      +crane(114,81,1.6)+crane(223,132,1.05)+line('M28 200Q23 151 51 120M24 173L9 149M28 163L54 146',b,3)
      +repeat(7,i=>ellipse(11+i*7,150-i*5,4,13,b,`transform="rotate(${i%2?40:-30} ${11+i*7} ${150-i*5})"`));
    case'bay':return circle(248,43,25,ivory)+rect(0,118,320,82,b)+path('M0 121L12 74L39 58L56 99L81 107L103 33L129 23L146 55L160 121Z','#55918b')
      +path('M155 123L180 81L199 86L208 56L235 64L254 115L278 94L304 105L320 126Z','#347b79')+waves(ivory,132)
      +boat(214,153,.8,c)+bird(57,41,.8,ink)+bird(76,36,.6,ink);
    case'galaxy':return ellipse(163,101,145,40,b,'transform="rotate(-25 163 101)" opacity=".35"')
      +repeat(58,i=>{const t=i*.53,r=5+i*1.7,x=160+Math.cos(t)*r*1.35,y=100+Math.sin(t)*r*.48;return path(`M${x} ${y-3}l4 3 -4 4 -3 -4Z`,i%3?c:ivory,`opacity="${.5+i%4*.12}"`);})
      +repeat(23,i=>circle(10+(i*83)%300,9+(i*47)%182,i%4?1:2,ivory))
      +circle(245,48,18,b)+ellipse(245,48,32,5,'none',`stroke="${c}" stroke-width="2" transform="rotate(-25 245 48)"`)
      +line('M65 125v22m-11 -11h22',ivory,2)+circle(160,100,5,ivory);
    case'terraces':return path('M0 115L54 28L112 89L198 11L277 95L320 58V200H0',b,'opacity=".55"')
      +repeat(7,i=>path(`M-20 ${97+i*19}Q62 ${42+i*22} 146 ${99+i*14}T345 ${83+i*21}V210H-20Z`,i%2?b:c))
      +repeat(6,i=>line(`M-20 ${115+i*17}Q58 ${60+i*20} 146 ${115+i*14}T345 ${101+i*19}`,ivory,1,'opacity=".5"'))
      +path('M199 67L218 57L238 69Z',ink)+rect(205,68,27,17,ivory)+bird(62,31,.8,ink);
    case'rain':return rect(0,131,320,69,b)+repeat(6,i=>rect(i*59-10,35+i%3*12,42,113,ink)+rect(i*59,53+i%3*12,12,29,c))
      +repeat(18,i=>line(`M${i*21} 0l-23 153`,ivory,1,'opacity=".3"'))+repeat(7,i=>line(`M${i*47} 163l-13 24`,c,4,'opacity=".4"'))
      +path('M110 107Q159 33 209 107Q187 99 176 108Q159 99 141 107Q125 100 110 107Z',c)
      +line('M161 107v44q0 8 -8 6',ink,3)+path('M145 143L137 181H176L169 140Z',ink)+circle(155,126,10,ink);
    case'floating':return circle(251,42,26,ivory)+rect(0,89,320,111,b)+waves(ivory,103)
      +repeat(3,i=>`<g transform="translate(${57+i*103} ${113+i%2*45})">${path('M-50 0Q0 37 51 -2L31 18H-31Z',i%2?c:ink)}${repeat(6,j=>circle(-31+j*12,-2-j%2*6,8,j%3===0?c:j%3===1?gold:'#8fa966'))}${line('M11 -4V-71',ink,3)}${ellipse(16,-58,6,10,c)}${path('M-19 -9L-2 -44L20 -9Z',ivory)}</g>`);
    case'ceramic':return rect(31,14,96,118,b)+rect(38,21,82,104,'#a8c4c2')+line('M79 20V126M38 64H120',ivory,4)+rect(0,159,320,41,'#b69b78')
      +path('M166 72H208L202 92Q238 123 216 170H157Q138 123 173 92Z',ivory)
      +ellipse(187,72,22,5,b)+line('M160 143Q185 108 217 144M168 163Q183 135 211 162',b,3)
      +repeat(5,i=>circle(167+i*10,144-i%2*11,4,b))+line('M186 71Q175 30 221 20M190 47L241 45',ink,2)
      +ellipse(215,23,14,5,b)+circle(241,45,8,c)+circle(220,20,7,c)+ellipse(91,172,33,11,ivory)+ellipse(91,168,27,7,b);
    case'koi':return circle(160,100,83,b)+circle(160,100,71,'none',`stroke="${gold}" stroke-width="1" opacity=".5"`)
      +repeat(9,i=>`<g transform="translate(160 100) rotate(${i*40}) translate(0 -57)">${path('M-17 0Q-2 -12 17 0Q0 16 -17 0L-28 -10L-24 11Z',i%3===0?ivory:i%3===1?gold:red)}${path('M-9 -2Q-2 -6 4 -2L0 6Z',i%2?red:b)}${circle(11,0,1.5,ink)}</g>`)
      +lotus(40,154,.65)+lotus(274,39,.7)+line('M149 91q16 -17 29 2q-5 22 -27 16',ivory,1.5);
    case'phoenix':return circle(157,74,50,b)+circle(157,74,42,'none',`stroke="${gold}" stroke-width="1"`)
      +repeat(7,i=>path(`M160 100Q${55+i*24} 128 ${20+i*43} 192Q${93+i*18} 180 164 111Z`,i%2?gold:c,`opacity="${.55+i*.05}"`))
      +path('M157 90Q104 79 35 23Q56 89 121 114L158 117Q223 127 286 31Q217 67 172 91Z',gold)
      +repeat(5,i=>line(`M${64+i*15} ${54+i*8}L${97+i*10} ${91+i*3}`,b,3))
      +path('M156 117Q173 98 161 80Q148 55 172 47L182 53L171 59Q190 90 169 126Z',c)
      +path('M171 48L184 29L174 37L167 24L165 45Z',gold)+circle(173,51,2,ink)+path('M181 52L197 58L180 59Z',gold);
    case'bronze':return circle(160,100,92,b)+repeat(5,i=>circle(160,100,22+i*15,'none',`stroke="${c}" stroke-width="${i===4?4:1.5}"`))
      +repeat(12,i=>`<g transform="translate(160 100) rotate(${i*30})">${path('M0 -32L5 -8L0 -13L-5 -8Z',c)}${path('M-7 -69L12 -63L1 -59L-4 -48L-4 -59L-14 -59Z',c)}${circle(0,-85,2,c)}</g>`)
      +circle(160,100,12,c)+repeat(24,i=>`<g transform="translate(160 100) rotate(${i*15})">${path('M-3 -78L0 -72L3 -78Z',c)}</g>`);
    case'gate':return path('M0 168L160 124L320 167V200H0',c)+path('M99 200L156 123L179 124L228 200Z',ivory)
      +rect(75,61,171,92,b)+path('M123 154V107Q161 63 198 107V154Z',ink)+rect(89,70,16,88,ivory)+rect(216,70,16,88,ivory)
      +path('M56 61L83 46L238 46L264 61L239 69H80Z',red)+path('M105 45L120 30H202L219 45Z',b)+rect(140,59,42,13,c)
      +line('M25 181Q58 112 34 35M37 74L7 46M40 81L74 43',ink,9)+repeat(7,i=>ellipse(12+i*12,27+i%3*15,29,19,b,'opacity=".8"'));
    case'daisies':return path('M0 161Q173 144 320 167V200H0',b,'opacity=".3"')+path('M126 117H192L180 185H140Z',c)
      +repeat(7,i=>{const x=91+(i*29)%142,y=39+(i*23)%79;return line(`M159 140Q${x-10} 102 ${x} ${y}`,b,2)+repeat(8,j=>`<ellipse cx="${x}" cy="${y-9}" rx="4" ry="10" fill="${ivory}" transform="rotate(${j*45} ${x} ${y})"/>`)+circle(x,y,5,gold);})
      +line('M138 155L180 155M142 171L175 171',ivory,2);
    case'tea':return path('M0 110Q53 39 131 89T320 62V200H0',c)+path('M0 156Q171 37 320 141V200H0',b)
      +repeat(8,i=>line(`M-20 ${130+i*16}Q150 ${40+i*19} 340 ${138+i*11}`,i%2?c:'#86a878',6))
      +ellipse(216,56,101,9,ivory,'opacity=".35"')+ellipse(56,79,81,6,ivory,'opacity=".4"')
      +path('M134 126L145 103L155 128Z',red)+path('M132 104L146 91L158 104Z',ivory)+line('M145 127v14',ink,3);
    case'puppet':return rect(0,113,320,87,b)+rect(75,55,170,75,'#9e4938')+path('M46 59L84 30L238 30L274 59L242 68H77Z',gold)
      +path('M64 34L84 16L237 16L257 34Z',red)+rect(103,75,113,52,ink)+line('M87 67v62M234 67v62',gold,5)+waves(ivory,135)
      +`<g transform="translate(158 149)">${circle(0,-27,11,ivory)}${path('M-15 -13Q0 -3 15 -13L23 17H-23Z',c)}${line('M-13 -8L-33 -18M13 -8L33 -18',gold,6)}${path('M-11 -37L0 -45L12 -36Z',c)}</g>`
      +path('M47 164Q69 145 89 164Q68 185 47 164L36 152V176Z',gold)+path('M252 163Q274 144 294 163Q273 184 252 163L241 151V175Z',red);
    case'butterflies':return repeat(6,i=>line(`M${18+i*58} 200Q${i*58} 121 ${44+i*48} ${67+i%2*44}`,b,2))
      +repeat(11,i=>ellipse(22+(i*43)%287,118+(i*19)%66,16,5,b,`transform="rotate(-30 ${22+(i*43)%287} ${118+(i*19)%66})"`))
      +repeat(3,i=>`<g transform="translate(${71+i*90} ${63+i%2*44}) rotate(${i*17-15})">${path('M0 0C-56 -51 -45 20 -6 8C-35 53 -2 39 0 14C18 49 37 37 7 8C54 2 35 -42 0 0Z',i===1?gold:c)}${path('M0 1Q-36 -25 -21 3L-6 8M5 3Q31 -20 24 1L7 8',ivory)}${line('M0 -4V20M0 -4L-8 -14M0 -4L8 -14',ink,2)}</g>`);
    case'horse':return circle(249,46,25,c)+path('M0 143Q79 85 166 139T320 104V200H0',b)
      +path('M85 101Q114 70 166 94L180 72L186 40L202 28L222 51L207 67L198 58L193 97L177 120L151 127L134 164L101 185L91 179L120 157L124 122L103 127L75 156L53 158L51 148L68 143Z',c)
      +path('M169 119L211 141L230 168L219 177L197 152L153 130Z',ivory)+line('M186 42Q156 51 165 86M91 100Q42 64 19 112M88 105Q51 89 26 141',ivory,6)
      +path('M196 36L197 18L204 32Z',c)+circle(210,46,2,ink)+repeat(4,i=>line(`M${36+i*51} ${181+i%2*9}h28`,gold,2));
    case'balcony':return rect(41,0,238,200,'#cfb086')+rect(85,20,127,124,b)+rect(96,31,103,104,ink)+line('M146 31V138M97 70H198',c,3)
      +rect(71,137,162,8,ivory)+line('M75 174H231M81 142V183M111 142V183M141 142V183M171 142V183M201 142V183M228 142V183',ink,3)
      +path('M215 23Q285 54 244 155','none','stroke="#486852" stroke-width="10"')
      +repeat(25,i=>circle(208+(i*23)%67,15+(i*19)%142,6+i%3,c))+rect(47,162,28,26,b)+ellipse(61,157,25,11,b);
    case'basket':return rect(0,89,320,88,b)+path('M0 165Q160 109 320 166V200H0',c)+waves(ivory,103)
      +ellipse(135,159,54,25,ink)+path('M81 152Q135 199 189 152V170Q136 212 81 170Z',gold)+ellipse(135,151,54,20,c)
      +repeat(8,i=>line(`M${91+i*12} ${147+Math.abs(3.5-i)*2}v${25-Math.abs(3.5-i)*4}`,b,1))
      +line('M96 147L189 109',ink,4)+line('M215 167V55M299 165V72M215 57Q258 111 299 73',ink,2)
      +repeat(7,i=>line(`M${219+i*12} ${64+i%4*10}v${81-i%3*9}`,ivory,1,'opacity=".8"'))+bird(55,48,1.1,ink);
    case'seasons':return repeat(4,i=>rect(8+i*78,9,70,181,['#e6cbb9','#9bbdba','#d7b675','#a9b9ad'][i]))
      +line('M27 185Q46 119 28 32M35 105L61 69M30 76L14 57',b,3)+repeat(9,i=>circle(18+(i*13)%46,37+(i*17)%93,5,red))
      +lotus(121,109,.8)+lotus(118,161,.6)+line('M200 180V84M200 136L180 114',b,2)
      +repeat(12,i=>`<ellipse cx="200" cy="81" rx="4" ry="17" fill="${gold}" transform="rotate(${i*30} 200 98)"/>`)+circle(200,98,6,b)
      +line('M272 184V24M292 184V54',b,5)+repeat(5,i=>line(`M263 ${43+i*29}h17M284 ${68+i*24}h16`,ivory,2))
      +repeat(6,i=>ellipse(267+i%2*28,56+i*19,16,4,b,`transform="rotate(${i%2?35:-35} ${267+i%2*28} ${56+i*19})"`));
    default:return waves(ivory);
  }
}

/** Complete SVG with a fixed viewBox; nested SVG is safe in home decoration exports. */
export function paintingSVG(id,width='100%',height='100%'){
  const [motif,a,b,c]=PAINTINGS[id]||PAINTINGS.tr_nuoc_noi;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${esc(String(width))}" height="${esc(String(height))}" viewBox="0 0 344 224" aria-hidden="true">`
    +rect(0,0,344,224,'#684b35','rx="3"')+rect(3,3,338,218,gold)+rect(7,7,330,210,'#473d34')
    +`<svg x="12" y="12" width="320" height="200" viewBox="0 0 320 200">${rect(0,0,320,200,a)}${scene(motif,a,b,c)}`
    +repeat(20,i=>line(`M0 ${i*11}H320`,ivory,.5,'opacity=".055"'))
    +rect(298,178,12,14,red,'rx="1"')+line('M301 181h6m-6 4h6m-3 -4v8',ivory,.7)+`</svg></svg>`;
}

export function landmarkSVG(id){
  const motifs={dt_ho:'water',dt_doi:'moon',dt_ben:'bay',dt_vuon:'lotus',dt_cau:'lantern',dt_thac:'light'};
  const m=motifs[id]||'bay';
  const shapes={
    dt_cau:path('M0 135Q156 14 320 135V150Q156 51 0 150Z',ivory)+line('M0 128Q156 7 320 128',ink,4),
    dt_thac:path('M130 50Q169 83 141 124T151 200H199Q167 155 185 116T171 50Z',ivory),
  };
  const landscape=id==='dt_thac'?path('M0 0H320V180L229 157L207 77L169 47L132 60L110 136L51 155L0 180Z','#3f7165')
    +ellipse(170,183,145,20,'#599ca4')+pine(55,146,1,ink)+pine(283,143,1.3,ink):scene(m,'#accfc7','#3f7165',gold);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200" aria-hidden="true">${rect(0,0,320,200,m==='moon'?'#243c52':'#accfc7')}${landscape}${shapes[id]||''}</svg>`;
}
