/** ✈️ v4/travel.js (#464) on the server's real catalogue and states (tests/travel-fixture.mjs): the places, the fares
 * by day (early = good price, today = dear), the visa reason, the ticket, the cabin's menu by class, the itinerary,
 * the summary and the Sổ du lịch. */
import assert from 'node:assert/strict';
import {travelFixture} from './travel-fixture.mjs';
import {page,_S as S} from '../public/js/v4/travel.js';

const F=travelFixture(),K=F.content;
const env={api:{state:{journey:null},content:{journey:{travel:K}}}};
S.env=env;
const at=(name,ui={})=>{env.api.state.journey=structuredClone(F.states[name]);Object.assign(S,{tab:'go',pick:'',ahead:-1,cls:'eco',airport:-1,mini:null,card:null,summary:null,food:'',drink:'',souv:'',crew:null,cancelArm:false,busy:false,flash:null,stampFx:''},ui);return page();};
const count=(html,re)=>(html.match(re)||[]).length;
const mainBtn=html=>(html.match(/<button[^>]*class="btn primary big sd-main"[^>]*>([^<]*)<\/button>/)||[])[0]||'';
const fmt=n=>Number(n).toLocaleString('vi-VN');

// 🗺️ the places: five in Việt Nam, the rest abroad, each with its cheapest fare
let html=at('list');
assert.equal(count(html,/class="tv-place"/g),K.dests.length);
assert.match(html,/Trong nước/);assert.match(html,/Nước ngoài/);
const dl=K.dests.find(d=>d.id==='da_lat');
assert.match(html,new RegExp(`từ ${fmt(Math.min(...dl.fares.eco))} xu`));
assert.equal(mainBtn(html),'');   // nothing to buy before a place is picked

// 📅 a place: 8 days, today is dear, from the 4th day the good price, the good day picked first
html=at('list',{pick:'da_lat'});
assert.equal(count(html,/class="tv-day[ "]/g),K.max_ahead+1);
assert.equal(count(html,/<i>Giá tốt<\/i>/g),K.max_ahead+1-K.good_ahead);
assert.match(html,/<i>Gấp<\/i>/);
for(const [i,p] of dl.fares.eco.entries())assert.match(html,new RegExp(`data-n="${i}"[^>]*><small>[^<]*</small><b>${fmt(p)}</b>`));
assert.ok(dl.fares.eco[0]>dl.fares.eco[K.good_ahead]);
assert.match(mainBtn(html),new RegExp(`Đặt vé · ${fmt(dl.fares.eco[K.good_ahead])} xu`));
assert.doesNotMatch(mainBtn(html),/disabled/);
at('list',{pick:'da_lat',ahead:0,cls:'biz'});env.api.state.journey.wallet=1000;html=page();
assert.match(mainBtn(html),new RegExp(`Đặt vé · ${fmt(dl.fares.biz[0])} xu`));
assert.match(html,/Còn thiếu/);   // 1,000 xu cannot pay business class today
assert.match(mainBtn(html),/disabled/);
html=at('list',{pick:'han_quoc'});
assert.match(html,/Cần visa Hàn Quốc/);assert.match(html,/data-tv="visa"/);
// ♿ #519: no visa yet, the main button goes to the visa office (not a dimmed "Đặt vé"), its reason read with it
assert.match(mainBtn(html),/🛂 Làm visa/);assert.doesNotMatch(mainBtn(html),/disabled/);assert.match(mainBtn(html),/aria-describedby="tv-why"/);
assert.match(html,/id="tv-why">Cần visa Hàn Quốc/);
html=at('list',{pick:'thai_lan'});
assert.match(html,/Miễn visa/);

// 🎫 the ticket: not yet / today, the refund shown
html=at('booked');
const b=F.states.booked.travel.book;
assert.match(html,new RegExp(b.code));assert.match(html,new RegExp(`>${b.seat}<`));
assert.match(mainBtn(html),/aria-disabled="true"/);assert.doesNotMatch(mainBtn(html),/ disabled/);assert.match(html,/Còn 2 ngày nữa/);   // ♿ focusable, with its reason
assert.match(html,new RegExp(`Hủy vé · hoàn ${fmt(b.back)} xu`));
html=at('today');
assert.match(mainBtn(html),/Ra sân bay/);assert.doesNotMatch(mainBtn(html),/disabled/);
html=at('today',{airport:0});
assert.match(html,/Làm thủ tục/);assert.equal(mainBtn(html),'');
html=at('today',{airport:2});
assert.match(mainBtn(html),/Lên máy bay/);assert.match(html,/ra cửa số/);

// 🛫 the cabin: the economy menu only, the crew, landing
html=at('fly');
assert.match(html,/tv-window/);assert.match(html,/Gọi món/);
const eco=K.meals.food.filter(m=>m.cls==='eco').length+K.meals.drink.filter(m=>m.cls==='eco').length;
assert.equal(count(html,/data-tv="(food|drink)"/g),eco);
assert.equal(count(html,/data-tv="crew"/g),K.crew.length);
assert.match(mainBtn(html),/Hạ cánh/);
html=at('fly',{crew:{ask:'x',say:'Mình còn khoảng 22 phút nữa là hạ cánh ạ.'}});
assert.match(html,/22 phút/);

// 🗺️ at the place: the itinerary, the souvenirs, the way home
html=at('here');
assert.equal(count(html,/data-tv="spot"/g),dl.spots.length);
assert.match(html,new RegExp(dl.greet.slice(0,20)));
assert.match(mainBtn(html),/Ra sân bay về nhà/);
html=at('here2');
assert.equal(count(html,/data-tv="spot"/g),dl.spots.length-1);
assert.match(html,/Đã ghé/);assert.match(html,/×1/);
html=at('here2',{mini:{id:'dl_cho',kind:'food',step:1,pos:0}});
assert.match(html,/Ăn một miếng \(1\/3\)/);assert.equal(mainBtn(html),'');
html=at('here2',{mini:{id:'dl_ga',kind:'photo',step:0,pos:0}});
assert.match(html,/tv-finder/);assert.match(html,/📸 Chụp/);
html=at('here2',{card:{id:'dl_ho',stars:3,new:true}});
assert.match(html,/Bưu thiếp mới/);assert.match(html,/★★★/);
html=at('back');
assert.match(mainBtn(html),/Hạ cánh về nhà/);

// 🏠 the summary, 📕 the book
html=at('done',{summary:F.summary});
assert.match(html,/Tổng kết chuyến đi/);assert.match(html,new RegExp(`${F.summary.cards}/${F.summary.of}`));
html=at('done',{tab:'book'});
assert.equal(count(html,/class="tv-stamp"/g),1);
assert.equal(count(html,/class="tv-stamp empty"/g),K.dests.length-1);
assert.match(html,/class="tv-pc"/);assert.match(html,/Mứt dâu tây/);
assert.match(html,/Chuyến gần đây/);
console.log('travel.mjs: places, fares by day, visa, ticket, cabin, itinerary, summary and Sổ du lịch passed.');
