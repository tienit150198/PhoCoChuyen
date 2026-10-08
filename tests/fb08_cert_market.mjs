// F#267 (where is the certificate exam) and F#263/#264 (all my clothing counters in a downturn), browser side.
import assert from 'node:assert/strict';
import {certsFor,certMissing,certBadge,certPlaceLine,certsEntry} from '../public/js/v4/certificates.js';
import {marketNow,marketHTML,marketBanner} from '../public/js/v4/business-economy-ui.js';

const groups=[
  {id:'pool_rescue',emoji:'🛟',name:'Chứng chỉ Cứu hộ hồ bơi',short:'Cứu hộ',careers:['lifeguard'],fee:20,retake_fee:10,hire:true,perk:''},
  {id:'ice_cream_craft',emoji:'🍨',name:'Chứng chỉ làm kem',short:'Làm kem',careers:['ice_cream'],fee:15,retake_fee:8,hire:false,perk:'Kem khoai môn'},
];
const api=(over={})=>({content:{catalogue:[{id:'lifeguard',place:'Hồ bơi Sóng Xanh'},{id:'ice_cream',place:'Tiệm kem'}],
    journey:{certs:{groups,by_career:{lifeguard:'pool_rescue'},draw:6,pass_mark:4,bonus:50}}},
  state:{current:'lifeguard',careers:{lifeguard:{job:{status:'hired'}},ice_cream:{job:{status:'none'}}},
    journey:{story:true,unlocked:['lifeguard','ice_cream'],certificates:{},study:null,wallet:50,...over}}});

// A workplace lists its certificates, the hire one first; the craft one counts too.
assert.deepEqual(certsFor(api(),'lifeguard').map(x=>x.g.id),['pool_rescue']);
assert.deepEqual(certsFor(api(),'ice_cream').map(x=>x.g.id),['ice_cream_craft']);
assert.deepEqual(certsFor(api({story:false}),'lifeguard'),[]);

// Hired at the pool without the certificate: the nudge, the dot and a direct "Đi thi ngay".
let a=api();
assert.deepEqual(certMissing(a),{cid:'lifeguard',g:groups[0]});
assert.equal(certBadge(a),'dot');
let html=certPlaceLine({api:a},'lifeguard');
assert.match(html,/data-action="jrCerts" data-cert="pool_rescue" data-career="lifeguard"/);
assert.match(html,/Đi thi ngay/);assert.match(html,/🎓 Cứu hộ · chưa có/);assert.match(html,/ct-place due/);
html=certsEntry({api:a});
assert.match(html,/Bạn làm ở Hồ bơi Sóng Xanh mà chưa có Chứng chỉ Cứu hộ hồ bơi/);
assert.match(html,/data-cert="pool_rescue"/);assert.match(html,/Đi thi ngay/);

// After a first try the dot stops (the entry still says it); a pass turns the line into the diploma.
a=api({certificates:{pool_rescue:{score:50,best:50,earned_day:null,attempts:1}}});
assert.equal(certBadge(a),0);assert.ok(certMissing(a));
a=api({certificates:{pool_rescue:{score:83,best:83,earned_day:3,attempts:1}}});
assert.equal(certMissing(a),null);assert.equal(certBadge(a),0);
assert.match(certPlaceLine({api:a},'lifeguard'),/data-action="jrCertDiploma"[^>]*>.*Cứu hộ · 83 điểm/);
// An exam open today: the dot comes back and the line says "Vào thi".
a=api({study:{cert:'pool_rescue',ready_now:true,ready:3,days_left:0}});
assert.equal(certBadge(a),'dot');assert.match(certPlaceLine({api:a},'lifeguard'),/📝 Vào thi/);
// Not hired: no nudge, the card still offers the exam.
a=api();a.state.careers.lifeguard.job.status='none';
assert.equal(certMissing(a),null);assert.match(certPlaceLine({api:a},'lifeguard'),/Đi thi ngay/);
assert.doesNotMatch(certPlaceLine({api:a},'lifeguard'),/ct-place due/);

// The market: one town-wide calendar; the browser's clock picks the run, so a slightly old state is still right.
const T=1791439200;   // a downturn half hour
const market={state:'downturn',label:'Suy thoái',demand_factor:.45,town:true,day_percent:113,down_minutes:120,runs:[
  {state:'downturn',label:'Suy thoái',demand_factor:.45,starts_at:T,ends_at:T+1800},
  {state:'stable',label:'Ổn định',demand_factor:1,starts_at:T+1800,ends_at:T+3600},
  {state:'boom',label:'Hưng thịnh',demand_factor:1.51,starts_at:T+3600,ends_at:T+5400}]};
assert.equal(marketNow(market,T+60).label,'Suy thoái');
assert.equal(marketNow(market,T+1801).label,'Ổn định');
assert.equal(marketNow(market,T+1801).next.label,'Hưng thịnh');
html=marketHTML({market,price_effect:100},T+60);
assert.match(html,/Chợ cả phố:/);assert.match(html,/khách 45% mức thường/);assert.match(html,/còn 29 phút/);
assert.match(html,/Sau đó: Ổn định 100%/);assert.match(html,/Không phải do giá của bạn/);assert.match(html,/khoảng 2 giờ mỗi ngày/);
assert.match(html,/trung bình 113%/);assert.match(html,/Giá menu quầy này vừa phải/);
assert.match(marketHTML({market,price_effect:40},T+60),/khách mua còn 40%/);
assert.match(marketHTML({market,price_effect:160},T+60),/mềm: khách mua 160%/);
// Stale state read later: the boom shows, no downturn words.
html=marketHTML({market},T+4000);
assert.match(html,/Hưng thịnh/);assert.doesNotMatch(html,/Không phải do giá/);
// One banner over all the counters, only while the town is down.
const stalls=[{business:{market}},{business:{market}}];
assert.match(marketBanner(stalls,T+60),/Chợ cả phố đang suy thoái tới/);
assert.equal(marketBanner(stalls,T+2000),'');
assert.equal(marketBanner([{business:{market:{label:'Suy thoái',demand_factor:.4}}}],T),'');   // an older server: no banner
console.log('F#267 certificate entry points and F#263/#264 town market UI passed.');
