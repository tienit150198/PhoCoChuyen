// 🏁 Đường đua Bến Mây (public/js/v4/race-track.js on game/racing.py). In node: every tab renders from a payload the
// server's own code builds (a story save with a tuned motorbike and a car, the static rules, duels of each kind, a run
// and a replay computed by racing.run): the parts with their next stage and price, the driver's choices of both tracks,
// the duels a player may race and the ones that are out of league, the boards and their titles, players' names escaped,
// and every visible line in English through the client's i18n layer (public/i18n/en.json).
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import test from 'node:test';

const ROOT=resolve(import.meta.dirname,'..');
const PY=process.env.PYTHON||'python';
const dump=JSON.parse(execFileSync(PY,['-c',`
import json
from tests.test_bank import story, act
from game import racing as R, lb_titles as lbt
s = story(wallet=100000)
for vid in ('xe_so', 'o_to_mini'):
    s, _ = act(s, 'jr_garage_buy', id=vid, confirm=True)
for mod in ('may', 'may', 'lop', 'phanh'):
    s, _ = act(s, 'jr_tune_buy', id='xe_so', mod=mod)
p = R.perf(s, 'xe_so')
ch = dict(launch='em', shifts=['som', 'tre', 'dung'])
car = R.car_of(s, 'xe_so')
car = R.wear_after(car, 2)
s['journey']['tune']['cars']['xe_so'] = dict(car, fx=dict(may=4))
def duel(i, status, a_pi, cls='bike', b=False, won=None):
    row = dict(id='rd%016x' % i, track='drag' if i % 2 else 'deo', cls=cls, fee=20, status=status, a_sid='A' if i != 3 else 'ME',
               a_pid='pa', a_run=json.dumps(dict(vid='xe_ga' if cls == 'bike' else 'mui_tran')), a_ms=19876, a_pi=a_pi,
               b_sid='ME' if b else '', b_pid='pb' if b else '', b_run='{}', b_ms=20111 if b else 0, b_pi=a_pi if b else 0,
               winner='ME' if won else 'A' if won is False else '', prize=32 if won else 0, created=1.0, done_at=2.0)
    v = R.duel_view(row, 'ME')
    return dict(v, a_name='Lan <Anh>', b_name='Bạn' if b else '', a_vehicle=R._veh_name(json.loads(row['a_run'])['vid']))
boards = {bid: [dict(rank=1, name='Tú & <i>Minh</i>', ms=17890, vehicle=R._veh_name('xe_ga'), me=False),
                dict(rank=2, name='Một người chơi', ms=18010, vehicle=R._veh_name('xe_so'), me=True)] if bid == 'race_drag_bike' else []
          for bid in R.BOARDS}
weekly = {bid: dict(tiers=[dict(t, holders=[dict(name='Tú & <i>Minh</i>', rank=1, me=False)] if t['tier'] == 0 else []) for t in lbt.tiers_of(bid)])
          for bid in R.BOARDS}
home = dict(ok=True, off=False, garage=R.view(s), rules=R.content(), week='2026-W43', today=dict(trials=3, duels=1), old_enough=True,
            open=[duel(3, 'open', p['pi'])], recent=[duel(5, 'done', p['pi'], b=True, won=True), duel(7, 'tie', p['pi'], b=True)],
            others=[duel(9, 'open', p['pi']), duel(11, 'open', p['pi'] * 3), duel(13, 'open', 200, cls='car')],
            boards=boards, best={'race_drag_bike': dict(rank=2, ms=18010)}, weekly=weekly)
run = dict(run=R.run('drag', p, ch, 'rr0123456789abcdef'))
deo = dict(run=R.run('deo', p, dict(brakes=['som', 'vua', 'muon', 'vua', 'muon']), 'rr0123456789abcdee'))
replay = dict(kind='duel', track='drag', runs=[dict(vid='xe_so', vehicle=R._veh_name('xe_so'), run=run['run'], mine=True),
                                              dict(vid='xe_ga', vehicle=R._veh_name('xe_ga'), run=deo['run'], mine=False)])
print(json.dumps(dict(home=home, run=run, deo=deo, replay=replay, perf=p), ensure_ascii=False))
`],{cwd:ROOT,encoding:'utf8',env:{...process.env,PYTHONUTF8:'1'}}));

const {_view}=await import('../public/js/v4/race-track.js');
const {S,page}=_view;
const draw=(tab,extra={})=>{Object.assign(S,{home:dump.home,tab,vid:'xe_so',track:'drag',fee:20,ch:{drag:{launch:'vua',shifts:['dung','dung','dung']},deo:{brakes:['vua','vua','vua','vua','vua']}},run:null,replay:null,busy:false,flash:null,board:'race_drag_bike'},extra);return page();};
const text=html=>html.replace(/<(script|style)[\s\S]*?<\/\1>/g,'').split(/<[^>]+>/).map(x=>x.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').trim()).filter(Boolean);
const attrsOf=html=>[...html.matchAll(/(?:title|aria-label)="([^"]*)"/g)].map(m=>m[1].replace(/&amp;/g,'&')).filter(Boolean);

test('the tune tab: every part, its wear, the next stage and its price, the hand-tune', ()=>{
  const html=draw('tune'),car=dump.home.garage.cars.find(c=>c.id==='xe_so');
  for(const m of car.mods){
    assert.ok(html.includes(m.name),m.name);
    if(m.next)assert.ok(html.includes(`data-mod="${m.id}"`)&&html.includes(`${m.next.price.toLocaleString('vi-VN')} xu`),m.id);
  }
  assert.match(html,/Map ECU|Pô và lọc gió/);
  assert.match(html,/Map tay \+3% mã lực · còn 4 lượt/);
  assert.match(html,/data-rc="fix"/,'worn parts: the service button');
  assert.match(html,/rc-wear" style="--w:\d+%/);
  assert.equal((html.match(/data-rc="car"/g)||[]).length,2,'a motorbike and a car to choose from');
});

test('the trial tab: both tracks, the choices, the notebook, the fee and the run leg by leg', ()=>{
  let html=draw('trial');
  assert.equal((html.match(/data-slot="launch"/g)||[]).length,3);
  assert.equal((html.match(/data-slot="shift"/g)||[]).length,9);
  assert.match(html,/Sổ tay đường đua/);
  assert.match(html,/Chạy · 5 xu/);
  assert.match(html,/kỷ lục tuần của bạn 18,010 giây \(hạng 2\)/);
  assert.match(html,/hôm nay chạy được thêm 17 lượt/);
  html=draw('trial',{track:'deo',run:dump.deo});
  assert.equal((html.match(/data-slot="brake"/g)||[]).length,15);
  for(const leg of dump.deo.run.legs)assert.ok(html.includes(leg.label)&&html.includes(leg.note),leg.label);
  assert.match(html,/class="miss"/,'a wrong braking point shows');
});

test('the duel tab: fees, the open duels (in league or not), mine, the results, a replay; names escaped', ()=>{
  const html=draw('duel',{replay:dump.replay});
  assert.equal((html.match(/data-rc="fee"/g)||[]).length,3);
  assert.ok(html.includes('Lan &lt;Anh&gt;')&&!html.includes('Lan <Anh>'));
  const accept=[...html.matchAll(/<button[^>]*data-rc="accept"[^>]*>/g)].map(m=>m[0]);
  assert.equal(accept.length,3);
  assert.ok(!accept[0].includes('disabled'),'same class, close numbers: open');
  assert.match(accept[1],/disabled[^>]*title="Chênh quá 20% chỉ số đua"/);
  assert.match(accept[2],/disabled[^>]*title="Khác hạng xe"/);
  assert.match(html,/data-rc="cancel"/);
  assert.match(html,/🏆 Thắng \+32 xu/);
  assert.match(html,/🤝 Hòa/);
  assert.match(html,/Xem lại/);
  assert.match(html,/rc-replay/);
});

test('the board tab: the four boards, the week\'s times, me highlighted, the titles', ()=>{
  const html=draw('board');
  assert.equal((html.match(/data-rc="board"/g)||[]).length,4);
  assert.ok(html.includes('Tú &amp; &lt;i&gt;Minh&lt;/i&gt;'),'escaped');
  assert.match(html,/rc-row me/);
  assert.match(html,/Vua drag xe máy tuần/);
  assert.match(html,/17,890 giây/);
  assert.match(draw('board',{board:'race_deo_car'}),/chưa ai chạy tính giờ/);
});

test('the payload never carries a session id', ()=>{
  const raw=JSON.stringify(dump.home);
  assert.ok(!/"(a_sid|b_sid|sid|winner)"/.test(raw));
});

test('every visible line has its English (public/i18n/en.json through v4/i18n.js)', async()=>{
  globalThis.Node??={ELEMENT_NODE:1,TEXT_NODE:3};globalThis.NodeFilter??={SHOW_TEXT:4,SHOW_ELEMENT:1};
  globalThis.document??={documentElement:{lang:'vi'},body:{nodeType:1,closest(){return false;}},createTreeWalker:()=>({nextNode(){return null;}}),title:''};
  globalThis.MutationObserver??=class {observe(){}};
  globalThis.__mnlBoot={...(globalThis.__mnlBoot||{}),i18n:Promise.resolve(JSON.parse(readFileSync(resolve(ROOT,'public/i18n/en.json'),'utf8')))};
  const {setLanguage,t}=await import('../public/js/v4/i18n.js');await setLanguage('en');
  const VI=/[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
  const names=new Set(['Lan <Anh>','Tú & <i>Minh</i>','Một người chơi','Bạn']);
  // place and people's names stay Vietnamese in English (Tư Pít-tông's garage, Bến Mây, Mây Bay Pass)
  const bad=s=>(s.replace(/Pít-tông|Bến Mây|Mây Bay/g,'').match(/\p{L}+/gu)||[]).some(w=>VI.test(w)&&w===w.toLowerCase());
  const lines=new Set();
  for(const [tab,extra] of [['tune',{}],['trial',{run:dump.run}],['trial',{track:'deo',run:dump.deo}],['duel',{replay:dump.replay}],['duel',{track:'deo'}],['board',{}],['board',{board:'race_deo_car'}]]){
    const html=draw(tab,extra);for(const x of [...text(html),...attrsOf(html)])if(!names.has(x))lines.add(x);
  }
  for(const n of dump.home.rules.notes)lines.add(n);
  const miss=[...lines].filter(s=>bad(t(s)));
  assert.deepEqual(miss,[]);
  assert.equal(t('Độ xe & đua xe'),'Tuning & racing');
  assert.equal(t('⏱️ Chạy giờ'),'⏱️ Time trial');
});
