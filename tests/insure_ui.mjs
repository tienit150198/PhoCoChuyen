// 🛡️ 23/10 (#313, #364): the Sửa nhà tab (v4/reno.js) and the Bảo hiểm page (v4/rui.js) on real server views piped in
// by tests/test_insure_2310.py: an insured sự cố costs 0 xu in Sửa nhà and says so, wear is said to be the player's,
// the waiting days show on both screens, the 80 % upgrades need their base, and there is no 100 % theft cover.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as art from '../public/js/v4/deco-art.js';
import {setup} from '../public/js/v4/home-walk.js';
import * as view from '../public/js/v4/home-view.js';
import {zoomer} from '../public/js/v4/home-zoom.js';   // 🔍 2.6.0 (feat/home-2d): reno.js imports it
import {escapeHTML,icon} from '../public/js/icons.js';

const f=JSON.parse(readFileSync(0,'utf8'));
globalThis.document={body:{classList:{contains:()=>true}},querySelector:()=>null};
globalThis.window={matchMedia:()=>({matches:false})};

/* ---- 🛠️ Sửa nhà ---- */
const renoSrc=readFileSync(new URL('../public/js/v4/reno.js',import.meta.url),'utf8').replace(/^import .*;.*\r?\n/gm,'').replace(/^export /gm,'');
const none=()=>'',many=new Proxy({},{get:()=>()=>[]});
const rn=new Function('A','walkSetup','live','sharedRooms','ownershipOrder','guestSession','icon','esc','Sound','BB','flagSVG','flagBadge','PALETTE','tr','zoomer',
  renoSrc+'\nreturn {S,fixPanel,onClick};')(art,setup,{on:()=>()=>{}},view.sharedRooms,view.ownershipOrder,view.guestSession,icon,escapeHTML,class{},many,none,none,{},t=>t,zoomer);
const sent=[];
const env=reno=>({confirmAction:async()=>true,api:{state:{journey:{reno},settings:{sound:false}},content:{journey:{reno:f.reno_catalogue}},
  command:async(action,payload)=>{sent.push({action,payload});return {message:'ok'};}}});
Object.assign(rn.S,{env:env(f.insured),dlg:null});
let html=rn.fixPanel(f.insured);
assert.match(html,/Bảo hiểm nhà 100%: trả sự cố \(dột, vỡ ống, chập điện, cháy, ngập\)\. Hao mòn và nâng cấp ở đây tự trả\./,'the policy and what it does not pay');
assert.match(html,/🛡️ Có sự cố: bảo hiểm trả 100%/,'the part with the insured sự cố says so');
assert.match(html,/data-dc="fix" data-part="roof"[^>]*>Sửa · 0 xu</,'the insured part can be fixed for 0 xu');
try{await rn.onClick('fix',{part:'roof'});}catch{}   // the render after the command needs a dialog: not here
assert.deepEqual(sent.at(-1),{action:'jr_reno_fix',payload:{part:'roof',cost:0,confirm:true}},'a 0 xu repair is still sent');
html=rn.fixPanel(f.waiting);
assert.match(html,/Bảo hiểm nhà 100%: đang chờ hiệu lực \(còn 3 ngày\)\. Hao mòn/,'the waiting days in Sửa nhà');
html=rn.fixPanel(f.uninsured);
assert.match(html,/Chưa có bảo hiểm nhà\. Bảo hiểm chỉ trả sự cố/,'no policy: what one would pay');

/* ---- 🛡️ Bảo hiểm & rủi ro ---- */
const ruiSrc=readFileSync(new URL('../public/js/v4/rui.js',import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'').replace(/^export /gm,'');
const ui=new Function('icon','esc',ruiSrc+'\nreturn {S,popHTML,ruiPage};')(()=>'',String);
ui.S.env={api:{state:f.rui_waiting,content:{journey:{rui:f.rui_catalogue}}}};
const page=ui.ruiPage();
assert.match(page,/Gói trọn 100%: giá gấp 2 gói thường, trả hết tiền sửa sự cố, tiền khám\./);
assert.match(page,/Không trả hao mòn, nâng cấp, phí bảo trì nhà\./);
assert.match(page,/Đồ chống móc túi, chống hack giảm tối đa 80%, không có loại 100%\./);
assert.match(page,/Đang chờ hiệu lực \(còn 3 ngày\)/,'the waiting days where the policy is bought');
assert.match(page,/Cần túi đeo chéo trước/,'an upgrade needs its base');
assert.match(page,/Cần bảo mật ngân hàng hai lớp trước/);
assert.doesNotMatch(page,/data-id="hai_lop_80"/,'no buy button before the base');
assert.match(page,/Không trả hao mòn, nâng cấp/,'the home policy line says what it does not pay');
const pop=ui.popHTML();
assert.match(pop,/🛡️ Bảo hiểm 100% đang chờ hiệu lực \(còn 3 ngày\)/,'the warning says the policy is still waiting');
ui.S.env.api.state=f.rui_based;
assert.match(ui.ruiPage(),/data-rui="gear" data-id="tui_khoa"[^>]*>Nâng cấp · /,'with the base: the upgrade is on sale');

/* ---- 🇬🇧 the English pack ---- */
const pack=JSON.parse(readFileSync(new URL('../public/i18n/en.json',import.meta.url),'utf8'));
const en=text=>pack.strings[text]||pack.patterns.find(([p])=>new RegExp('^'+p+'$','u').test(text))?.[1];
for(const text of ['Túi khóa chống móc','Bảo mật ngân hàng nâng cao',f.rui_catalogue.policies.find(p=>p.id==='nha').what,
  'Đang chờ hiệu lực (còn 3 ngày)','🛡️ Bảo hiểm 100% đang chờ hiệu lực (còn 3 ngày)','🛡️ Có sự cố: bảo hiểm trả 100%',
  '🛡️ Bảo hiểm nhà 100%: trả sự cố (dột, vỡ ống, chập điện, cháy, ngập). Hao mòn và nâng cấp ở đây tự trả.',
  'Đồ chống móc túi, chống hack giảm tối đa 80%, không có loại 100%.'])
  assert.ok(en(text),`English for: ${text}`);
console.log('Insurance screens (#313 Sửa nhà, #364 80 % gear) passed.');
