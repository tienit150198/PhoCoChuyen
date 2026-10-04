import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
globalThis.document={querySelector:()=>({sheet:{}}),addEventListener:()=>{}}; // Imported stylesheets are already loaded in this render harness.
globalThis.addEventListener=()=>{};
const [{feedbackView},{promoView},{careerContext},{default:homestay}]=await Promise.all([
  import('../public/js/v4/views.js'),import('../public/js/v4/promo.js'),
  import('../public/js/v4/careers.js'),import('../public/js/careers/homestay.js')
]);

const f=JSON.parse(readFileSync(0,'utf8'));
const env=state=>({api:{state,content:f.content},ui:{fbPost:f.post},cmd:()=>{},renderSheet:()=>{}});
const threat=feedbackView(env(f.police_before));
assert.match(threat,/data-op="fb_police"/);
assert.match(threat,/data-confirm="[^\"]*trong game/);
const filed=feedbackView(env(f.police_after));
assert.match(filed,/Đã trình báo trong game/);
assert.doesNotMatch(filed,/data-op="fb_police"/);

function home(state,select=[]){
  const x=careerContext(env(state));
  const t=x.room.tasks.find(t=>t.id===x.room.active_task);
  x.ui.selTask=t.id;x.ui.sel=select;
  return homestay.job(t,x);
}
function holdButton(html){return html.match(/<button[^>]*data-command="hs_hold"[^>]*>/)?.[0];}
const free=home(f.home_free,['thong']);
assert.ok(holdButton(free));
assert.doesNotMatch(holdButton(free),/disabled/);
const busy=home(f.home_busy,['thong']);
assert.match(holdButton(busy),/disabled/);
assert.match(busy,/chờ đồng bộ/);
const held=home(f.home_held);
assert.match(held,/hs-cell hold/);
assert.match(held,/data-op="hs_book"/);
const stale=home(f.home_stale);
assert.match(stale,/Lịch giữ phòng đã thay đổi/);
assert.match(stale,/data-command="hs_release"/);

const employee=env(structuredClone(f.police_before));
employee.api.state.careers.milk_tea.promo={track:'emp',rank:1,top:4,pct:8,title:'Nhân viên',next:null};
assert.match(promoView(employee),/Thăng chức tăng lương/);
employee.api.state.careers.milk_tea.promo={track:'own',rank:3,top:4,pct:9,title:'Chủ tiệm',next:null};
const manager=promoView(employee);
assert.match(manager,/Thăng tiến tăng tiền boa/);
assert.match(manager,/giao việc cho đội, kiểm tra kết quả/);

if(process.env.MNL_UI_PREVIEW){
  mkdirSync('output/feedback-0410',{recursive:true});
  const body=[['Trình báo lời đe dọa',threat],['Hồ sơ đã lưu',filed],['Homestay: lịch đã thay đổi',stale],['Thăng tiến',manager]];
  const html=`<!doctype html><html lang="vi" data-layout="phone"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/public/css/app.css"><link rel="stylesheet" href="/public/css/reviews.css"><link rel="stylesheet" href="/public/css/promo.css"><link rel="stylesheet" href="/public/css/careers/homestay.css"><style>body{margin:0;padding:16px;background:#f7f1e7;color:#352c24;font:16px system-ui}section.preview{max-width:720px;margin:0 auto 32px}dialog{position:relative;display:block;margin:0;width:100%;max-width:100%;border:1px solid #ddcfc0;padding:0;border-radius:16px;overflow:hidden;box-sizing:border-box}button,input{font:inherit}h2.preview-title{font-size:18px}</style></head><body>${body.map(([title,view])=>`<section class="preview"><h2 class="preview-title">${title}</h2><dialog open class="v4-sheet wide"><div>${view}</div></dialog></section>`).join('')}</body></html>`;
  writeFileSync('output/feedback-0410/preview.html',html);
}
console.log('Review, homestay calendar and promotion UI passed.');
