// 🖼️ Player feedback #508 (lii, 23/10): top frames that look alike or like an everyday frame, auction "độc bản" frames
// that were a top board's art, and an auction frame (🏮 Đèn Lồng Vàng) missing from the frame chooser.
//   node tests/honour_frames_508.mjs
import assert from 'node:assert/strict';
import {TABLES,ofId,look,pick,choices,chooser,avatar,bubble,logo,uqSpec,uqSvg,uqBadge} from '../public/js/v4/honour-frames.js';
import {FRAMES} from '../public/js/v4/honour-frames-data.js';
import {itemArt} from '../public/js/v4/auction-display.js';

const {TIERS,LOOK,FREE,UQ}=TABLES;
const freeArt=new Set(Object.values(FREE).map(k=>k[0]));

// 1. 🏅 every (board, rank tier) of a top title looks like no other, and never like an everyday frame
const seen=new Map(),halos=new Map();
for(const b of Object.keys(TIERS)){
  assert.ok(LOOK[b],`${b}: its own look`);
  assert.ok(!halos.has(LOOK[b][1]),`${b}: its halo is ${halos.get(LOOK[b][1])}'s`);halos.set(LOOK[b][1],b);
  for(let r=1;r<=10;r++){
    const f=ofId(`lb_${b}_${r}`);if(f.n===undefined&&TIERS[b].length<3&&r>3)continue;   // 🏁 a race board titles its top 3 only
    assert.ok(f&&FRAMES[f.n],`lb_${b}_${r}: art`);
    assert.ok(!freeArt.has(f.n),`lb_${b}_${r}: wears the everyday frame ${f.n}`);
    const L=look(f);assert.ok(L&&L.medal&&/drop-shadow/.test(L.fx),`lb_${b}_${r}: halo and medal`);
    const key=`${f.n}|${L.hue}|${L.metal}`,who=`${b}:${f.tier}`;
    if(seen.has(key))assert.equal(seen.get(key),who,`${who} looks like ${seen.get(key)} (${key})`);else seen.set(key,who);
  }
  const L1=look(ofId(`lb_${b}_1`));assert.equal(L1.metal,'g',`${b}: top 1 is gold`);
}
assert.equal(look(ofId('lb_all_2')).metal,'s');assert.equal(look(ofId('lb_all_7')).metal,'b');
assert.equal(look(ofId('lb_all_7')).medal,'7');assert.equal(look(ofId('lb_pet_war_8')).medal,'2');
assert.ok(new Set(Object.keys(TIERS).map(b=>TIERS[b].join())).size>=Object.keys(TIERS).length-6,'most boards have their own art');
for(const k of Object.keys(FREE)){const f=pick([k],{});assert.equal(f.tier,6);assert.equal(look(f),null,`${k}: an everyday frame stays plain`);
  assert.doesNotMatch(avatar([k],{},'<i></i>'),/hf-top|data-hf-rank|hf-uq/);}
assert.match(avatar(['lb_wealth_1'],{},'<i></i>'),/class="hf-av hf-top hf-mg" .*data-hf-rank="1"/);
assert.match(bubble(['lb_titles_3'],{}).cls,/ hf hf-top hf-ms/);assert.match(bubble(['lb_titles_3'],{}).attrs,/data-hf-rank="3"/);
assert.match(logo('wings',1),/hue-rotate\(200deg\)/);   // 🪽 shares the 🏅 board's art, recoloured

// 2. 👑 an auction title's frame is its own: drawn, never an art file, no two alike, the same every time
const ids=Object.keys(UQ),svgs=ids.map(uqSvg);
assert.equal(new Set(svgs).size,ids.length,'no two auction frames alike');
assert.equal(new Set(ids.map(i=>UQ[i].slice(1,4).join())).size,ids.length,'nor their colours');
for(const id of ids){const f=ofId(id);assert.deepEqual(f,{n:null,tier:4,uq:id});assert.equal(uqSvg(id),svgs[ids.indexOf(id)]);
  assert.doesNotMatch(decodeURIComponent(uqSvg(id)),/undefined|NaN|webp/);}
assert.ok(!ids.some(id=>avatar([id],{},'<i></i>').includes('/icons/frames/')),'never a raster frame');
const fresh=uqSvg('dh_not_yet_in_this_build');assert.ok(fresh.startsWith('data:image/svg+xml,')&&!svgs.includes(fresh),'a newer title: one of its own too');
assert.equal(uqSpec('dh_x').length,6);assert.equal(ofId('dh_Bad'),null);assert.equal(ofId('dh_'),null);
const lantern=avatar(['dh_den_long','lb_all_1'],{},'<i></i>');
assert.match(lantern,/class="hf-av hf-uq"/);assert.match(lantern,/data-hf-icon="🏮"/);assert.doesNotMatch(lantern,/data-hf-rank/);
const ub=bubble(['dh_den_long'],{});assert.equal(ub.cls,' hf-uq');assert.match(ub.attrs,/--uq-b:#e8412c;.*--uq-emo:'🏮'/);
assert.notEqual(bubble(['dh_ngan_ha'],{}).attrs,ub.attrs);
assert.match(itemArt({kind:'title',item:'dh_den_long',emoji:'🏮',tier:1}),/hf-uq-big/);   // the lot card shows the frame it gives
assert.equal(uqBadge('lb_all_1','x'),'');assert.doesNotMatch(itemArt({kind:'title',emoji:'<script>'}),/<script>/);

// 3. 🏮 an auction title owned shows in the chooser (journey.uniq.own as every save since 07/10 has it), can be worn and taken off
const content={journey:{auction:{items:[{id:'dh_den_long',kind:'title',emoji:'🏮',name:'Chủ Nhân Đèn Lồng Vàng'}]}}};
const own={dh_den_long:{k:'title',t:'Chủ Nhân Đèn Lồng Vàng',p:6000},pl_may1975:{k:'plate',t:'Mây-1975',p:5000},
  dh_Bad:{k:'title',t:'x'},dh_ca_phe:null,dh_mua_sao:{k:'art',t:'not a title'}};
const api=(pick_,more={})=>({state:{journey:{...(pick_?{hf_pick:pick_}:{}),uniq:{own}}},content,lbTitles:[{board:'wealth',rank:2,emoji:'💰',name:'Đại gia mới nổi',label:'Top 2 Tài phú'}],...more});
const L=choices(api());
assert.deepEqual(L.map(x=>x.id),['dh_den_long','lb_wealth_2']);
assert.equal(L[0].emoji,'🏮');assert.equal(L[0].name,'Chủ Nhân Đèn Lồng Vàng');
let html=chooser(api());
assert.match(html,/data-id="dh_den_long" aria-pressed="false"/);assert.match(html,/Độc bản · Nhà đấu giá/);
assert.match(html,/class="hf-opt on" data-action="jrFrame" data-id="auto"/);
html=chooser(api('dh_den_long'));
assert.match(html,/class="hf-opt on" data-action="jrFrame" data-id="dh_den_long" aria-pressed="true"/);
assert.doesNotMatch(html,/không còn giữ/,'a held auction frame is known');
assert.match(chooser(api('off')),/class="hf-opt on" data-action="jrFrame" data-id="off"/);
// without its catalogue row (an older content cache): still listed, with its own emoji
assert.equal(choices({state:{journey:{uniq:{own:{dh_ngan_ha:{k:'title',t:'Chủ Nhân Dải Ngân Hà',p:1}}}}}})[0].emoji,'🌌');
// only an auction title: its frame alone is enough for the chooser's top group
assert.match(chooser({state:{journey:{uniq:{own:{dh_ky_lan:{k:'title',t:'Kỳ Lân Phố Mây',p:1}}}}}}),/Khung danh hiệu top và độc bản.*data-id="dh_ky_lan"/s);
// what live/honours.py sends: the pick first (chosen()), then the rest
assert.equal(pick(['dh_den_long','lb_wealth_2'],{}).uq,'dh_den_long');
assert.equal(pick(['lb_wealth_2','dh_den_long'],{}).board,'wealth');
assert.equal(pick(['hf_off','dh_den_long'],{}),null);
assert.deepEqual(choices({state:{journey:{}}}),[]);assert.deepEqual(choices(null),[]);
console.log(`#508: ${seen.size} top looks distinct, ${ids.length} one-of-a-kind frames, auction titles in the chooser passed.`);
