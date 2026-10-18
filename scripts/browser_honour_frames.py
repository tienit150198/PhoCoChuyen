"""🖼️ Khung danh hiệu in the real chat and leaderboard modules (public/js/v4/chat.js, leaderboard.js, honour-frames.js)
with controlled socket frames: the holders of top titles wear their avatar frame and chat bubble (theirs and mine),
fair titles and plain players stay plain; every frame picture loads; no horizontal overflow at 360 px; the light,
dark and isometric looks; the leaderboard's rank logos, coloured chips and weekly tiers. No database or live service.

Run: python scripts/browser_honour_frames.py [--shots DIR]
"""
import argparse
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

PUBLIC = Path(__file__).resolve().parents[1] / 'public'
ME = 'aaaaaaaaaaaaaaaa'


class Assets(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def guess_type(self, path):
        return 'image/webp' if str(path).endswith('.webp') else super().guess_type(path)

    def do_GET(self):
        if self.path.split('?')[0] in ('/', '/lb'):
            body = (b'<!doctype html><html lang="vi" data-layout="phone"><head><meta charset="utf-8">'
                    b'<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css">'
                    b'<link rel="stylesheet" href="/css/chat.css"></head><body></body></html>')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, *_):
        pass


CHAT = """async ([me]) => {
  const {live}=await import('/js/v4/live.js');
  const handlers=new Map();
  Object.assign(live,{state:'open',welcomed:true,me:{pid:me,account:true,name:'Mình'},flags:{chat:true},friends:[],limits:{},chans:[]});
  live.on=(type,fn)=>handlers.set(type,fn);
  live.send=()=>true;
  const {openChat}=await import('/js/v4/chat.js');
  const t0=1791370800;let n=0;
  const msg=(pid,name,av,text,extra={})=>({t:'msg',ch:'town',id:++n,pid,name,av,text,at:t0+n*400,...extra});
  const q={id:1,pid:'p1',name:'Trùm Cuối',text:'Chào cả phố, tuần này mình giữ top 1 nha 👑'};
  const msgs=[
    msg('p1','Trùm Cuối','👑',q.text,{tt:['lb_all_1','lb_wealth_3','f_bao']}),
    msg('p2','Đại Gia Mới Nổi','💰','Ai bán vàng không, mua hết 😎',{tt:['lb_wealth_2']}),
    msg('p3','Cô Ba Trà Sữa','🧋','Trân châu đã sẵn sàng rồi nha! Ghé quán mình uống thử, hôm nay giảm giá cho cả phố luôn, nhắn mình để giữ chỗ nhé 💕',{tt:['lb_milk_tea_1','f_dart'],reply:q}),
    msg('p4','Anh Sửa Đồ','🔧','ok',{tt:['lb_repair_1']}),
    msg('p5','Người Dựng Công Viên','🌳','Công viên ven sông xong rồi đó mọi người\\nRa chơi cuối tuần nha\\nCó cả ghế đá mới',{st:{t:'t_ct_cong_vien'}}),
    msg('p6','Hội Săn','🎖️','Hội săn danh hiệu điểm danh!',{tt:['lb_titles_6']}),
    msg('p7','Chợ Đen','🌪️','Mình vừa trúng bão bầu cua 🌪️ (không khung)',{tt:['f_bao','f_king','w_vip']}),
    msg('p8','Khách quen','🍵','Không có danh hiệu thì vẫn như cũ'),
    msg('p9','Nhà Sưu Tầm','🏺','Bình gốm này đẹp không cả nhà?',{tt:['lb_collection_1']}),
    msg('p10','Thầy Chùa','🪷','A Di Đà Phật (không khung: việc chùa)',{tt:['lb_pagoda_1']}),
    msg(me,'Mình','🙂','Mình là thủ khoa của phố tuần này 🎓',{tt:['lb_certs_1']}),
    msg(me,'Mình','🙂','Tin thứ hai liền sau',{tt:['lb_certs_1']}),
    msg('p11','Bỏ tin','🙈','',{tt:['lb_all_2'],del:true}),
    msg('p12','Cất Khung','🙅','Mình cất khung rồi (không khung)',{tt:['hf_off','lb_all_3']}),
    msg('p13','Chọn Công Viên','🎡','Mình chọn khung công viên',{tt:['t_ct_cong_vien','lb_wealth_1'],st:{t:'t_ct_cong_vien'}}),
    msg('p14','Hết Đeo','🎈','Đã thôi đeo nên khung tài phú',{tt:['t_ct_cong_vien','lb_wealth_1'],st:{}}),
    msg('p15','Khung Mèo','🐱','Mình chưa có top nhưng chọn khung mèo nè',{tt:['k_02']}),
  ];
  window.H={emit:(type,f)=>handlers.get(type)?.(f)};
  await openChat({api:{content:{careers:{repair:{meta:{icon:'wrench',short:'Tiệm sửa đồ'}}}}}},{ch:'town'});
  H.emit('joined',{ch:'town',msgs,more:false,why:'ok',wait:0,n:12,pin:null});
}"""

LB = """async ([board]) => {
  const {leaderboardView}=await import('/js/v4/leaderboard.js');
  const names=['Trùm Cuối','Chiến Thần','Á Quân','Dân Cày 4','Dân Cày 5','Dân Cày 6','Dân Cày 7','Dân Cày 8','Dân Cày 9','Dân Cày 10','Hạng 11'];
  const T={all:[['👑','Trùm cuối của phố'],['🔥','Chiến thần cày cuốc'],['⚡','Dân cày top 10']],wealth:[['💎','Đại gia của phố'],['💰','Đại gia mới nổi'],['🤑','Hội nhà giàu']],
    collection:[['🏺','Bộ sưu tập huyền thoại'],['🔨','Nhà sưu tầm đấu giá'],['💠','Hội sưu tầm']],
    online:[['🦉','Cú đêm của phố'],['🌙','Thức cùng ánh trăng'],['🏮','Hội cú đêm']]}[board]||null;
  const tierOf=r=>r===1?0:r<=3?1:2;
  const rows=names.map((name,i)=>{const rank=i+1,t=T?(rank<=10?T[tierOf(rank)]:null):(rank===1?['🏆','Trùm trà sữa']:null);
    return {rank,name,score:9000-i*500,me:rank===3,days:12,level:5,...(t?{title:{emoji:t[0],name:t[1]}}:{})};});
  const tiers=T?T.map(([emoji,name],i)=>({tier:i,label:['Top 1','Top 2–3','Top 4–10'][i],emoji,name,lo:[1,2,4][i],hi:[1,3,10][i],holders:[{rank:[1,2,4][i],name:names[[0,1,3][i]],me:false}]})):
    [{tier:0,label:'Top 1',emoji:'🏆',name:'Trùm trà sữa',lo:1,hi:1,holders:[{rank:1,name:'Trùm Cuối',me:false}]}];
  const data={rows,total:120,me:{rank:3,visible:true,score:8000},weekly:{week:'2026-W42',updated:1791370800,ends:Date.now()/1000+3*86400,tiers},at:Date.now()};
  const own=['certs','titles','wealth','collection','online'].includes(board);
  const ui={view:'rank',lb:{kind:own?board:'exp',board:own?'all':board,data:{[board]:data},busy:{}}};
  const env={api:{content:{catalogue:[{id:'milk_tea',short:'Tiệm trà sữa',place:'Tiệm trà sữa'}]},state:{careers:{milk_tea:{}},journey:{}},json:()=>new Promise(()=>{})},ui,renderSheet(){}};
  document.body.innerHTML=`<div class="sheet open" style="position:static;max-width:100%">${leaderboardView(env)}</div>`;
  await new Promise(r=>setTimeout(r,600));
}"""

CHECK = """() => {
  const out={};
  out.framedBubbles=[...document.querySelectorAll('.ch-bub.hf')].map(b=>b.closest('.ch-msg').querySelector('.ch-name')?.textContent?.trim().slice(0,14)||(b.closest('.ch-msg.mine')?'mine':'?'));
  out.plainOk=[...document.querySelectorAll('.ch-msg')].filter(m=>/không khung|vẫn như cũ/.test(m.textContent)).every(m=>!m.querySelector('.hf,.hf-av'));
  out.deletedPlain=[...document.querySelectorAll('.ch-bub.del')].every(b=>!b.classList.contains('hf'));
  out.avFrames=document.querySelectorAll('.ch-msg .hf-av').length;
  const art=name=>{const m=[...document.querySelectorAll('.ch-msg')].find(m=>m.querySelector('.ch-name')?.textContent?.includes(name));const e=m?.querySelector('.ch-bub.hf');return e?/frames\/(\d+)_chat/.exec(e.getAttribute('style'))?.[1]:null;};
  out.chosen=[art('Chọn Công Viên'),art('Hết Đeo'),art('Khung Mèo')];
  out.icon=[...document.querySelectorAll('.hf-av[data-hf-icon]')].map(e=>e.dataset.hfIcon);
  const b=document.querySelector('.ch-body');
  out.overflow=[...document.querySelectorAll('.ch-bub,.ch-name,.hf-av')].filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+0.5;}).length;
  out.bodyFits=!b||b.scrollWidth<=b.clientWidth+1;out.docFits=document.documentElement.scrollWidth<=innerWidth+1;
  const urls=new Set();for(const e of document.querySelectorAll('[style*="--hf-img"]')){const m=/--hf-img:url\\('([^']+)'\\)/.exec(e.getAttribute('style'));if(m)urls.add(m[1]);}
  out.urls=[...urls];
  return out;
}"""

LOADS = """async (urls) => Promise.all(urls.map(u=>new Promise(r=>{const i=new Image();i.onload=()=>r([u,i.naturalWidth]);i.onerror=()=>r([u,0]);i.src=u;})))"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default='')
    args = ap.parse_args()
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'
    failures, bad_requests = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, vw, vh, theme, game in (('phone', 360, 800, '', ''), ('phone-dark', 360, 800, 'dem', ''), ('iso', 390, 844, '', 'isometric'),
                                          ('desktop', 1100, 900, '', '')):
            ctx = browser.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=2)
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('response', lambda r: r.status >= 400 and bad_requests.append(f'{r.status} {r.url}'))
            page.goto(base + '/')
            page.evaluate("([t,g])=>{if(t)document.documentElement.dataset.theme=t;if(g)document.documentElement.dataset.game=g;}", [theme, game])
            page.evaluate(CHAT, [ME])
            page.wait_for_selector('.ch-bub.hf')
            page.wait_for_timeout(700)
            r = page.evaluate(CHECK)
            loads = page.evaluate(LOADS, r['urls'])
            print(name, {k: v for k, v in r.items() if k != 'urls'}, 'pictures', len(loads))
            want = {'Trùm Cuối', 'Đại Gia Mới', 'Cô Ba Trà Sữa', 'Anh Sửa Đồ', 'Người Dựng Côn', 'Hội Săn', 'Nhà Sưu Tầm', 'mine'}
            got = {x[:len(w)] for x in r['framedBubbles'] for w in want if x.startswith(w[:6])} | ({'mine'} if 'mine' in r['framedBubbles'] else set())
            missing = [w for w in want if not any(x.startswith(w[:6]) for x in r['framedBubbles'])]
            if missing:
                failures.append(f'{name}: no bubble frame for {missing}')
            if not r['plainOk'] or not r['deletedPlain']:
                failures.append(f'{name}: a plain or deleted message wears a frame')
            if r['chosen'] != ['62', '28', '02']:
                failures.append(f'{name}: chosen frames {r["chosen"]} (want the park 62, then wealth 28, the cat 02)')
            if '🔧' not in r['icon']:
                failures.append(f'{name}: the shared Trùm frame has no workplace icon')
            if r['overflow'] or not r['bodyFits'] or not r['docFits']:
                failures.append(f'{name}: horizontal overflow {r}')
            if any(w == 0 for _, w in loads):
                failures.append(f'{name}: pictures not loaded {[u for u, w in loads if not w]}')
            if errors:
                failures.append(f'{name}: errors {errors}')
            if shots:
                page.screenshot(path=str(shots / f'chat-{name}.png'), full_page=True)
                for i, at in enumerate((0, 0.45)):
                    page.evaluate("(at)=>{const b=document.querySelector('.ch-body');b.scrollTop=at*b.scrollHeight;}", at)
                    page.wait_for_timeout(150)
                    page.screenshot(path=str(shots / f'chat-{name}-{i}.png'))
            ctx.close()
        # 🖼️ the chooser (Hành trình → Danh hiệu): automatic, each frame held, none; the chosen one pressed
        ctx = browser.new_context(viewport={'width': 360, 'height': 800}, device_scale_factor=2)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(base + '/lb')
        r = page.evaluate("""async () => {
          const {chooser}=await import('/js/v4/honour-frames.js');
          const api={lbTitles:[{board:'wealth',rank:2,emoji:'💰',name:'Đại gia mới nổi',label:'Top 2–3'},{board:'milk_tea',rank:1,emoji:'🏆',name:'Trùm trà sữa',label:'Top 1'},
            {board:'pagoda',rank:1,emoji:'🪷',name:'Siêng việc chùa nhất tuần',label:'Top 1'}],
            state:{journey:{hf_pick:'lb_milk_tea_1',spend:{wear:{title:'t_ct_cong_vien'}}}},content:{journey:{spend:{titles:[{id:'t_ct_cong_vien',emoji:'🌳',name:'Người dựng công viên'}]}}}};
          document.body.innerHTML=`<div class="sheet open" style="position:static"><div class="sheet-body">${chooser(api)}</div></div>`;
          const box=document.createElement('div');box.innerHTML=chooser({lbTitles:[{board:'pagoda',rank:1}],state:{journey:{}},content:{}});
          const none={ids:[...box.querySelectorAll('.hf-opt')].map(b=>b.dataset.id),on:[...box.querySelectorAll('.hf-opt.on')].map(b=>b.querySelector('b').textContent)};
          await new Promise(r=>setTimeout(r,500));
          return {ids:[...document.querySelectorAll('.hf-opt')].map(b=>b.dataset.id),on:[...document.querySelectorAll('.hf-opt.on')].map(b=>b.dataset.id),
            none,fits:document.documentElement.scrollWidth<=innerWidth+1};}""")
        print('chooser', r)
        free = ['k_01', 'k_02', 'k_05', 'k_19', 'k_22', 'k_23', 'k_24']
        if (r['ids'] != ['auto', 'lb_wealth_2', 'lb_milk_tea_1', 't_ct_cong_vien', *free, 'off'] or r['on'] != ['lb_milk_tea_1']
                or r['none'] != {'ids': [*free, 'auto'], 'on': ['Không dùng khung']} or not r['fits'] or errors):
            failures.append(f'chooser: {r} {errors}')
        if shots:
            page.screenshot(path=str(shots / 'chooser.png'), full_page=True)
        ctx.close()
        for board in ('all', 'wealth', 'collection', 'online', 'milk_tea'):
            ctx = browser.new_context(viewport={'width': 360, 'height': 900}, device_scale_factor=2)
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(base + '/lb')
            page.evaluate(LB, [board])
            r = page.evaluate("""() => ({logos:document.querySelectorAll('.lb-list .hf-logo').length,
              chips:[...document.querySelectorAll('.lb-held')].map(e=>e.className.replace('lb-held hn-chip','').trim()),
              week:document.querySelectorAll('.lb-week-emoji .hf-logo').length,
              fits:document.documentElement.scrollWidth<=innerWidth+1,
              urls:[...new Set([...document.querySelectorAll('[style*="--hf-img"]')].map(e=>/url\\('([^']+)'\\)/.exec(e.getAttribute('style'))[1]))]})""")
            loads = page.evaluate(LOADS, r['urls'])
            print('lb', board, {k: v for k, v in r.items() if k != 'urls'})
            n = 1 if board == 'milk_tea' else 10
            if r['logos'] != n or len(r['chips']) != n or not r['fits'] or any(w == 0 for _, w in loads) or errors:
                failures.append(f'lb {board}: {r} {errors}')
            if board != 'milk_tea' and r['chips'][:4] != ['hn-top', 'hn-t1', 'hn-t1', 'hn-t2']:
                failures.append(f'lb {board}: chip colours {r["chips"][:4]}')
            if shots:
                page.screenshot(path=str(shots / f'lb-{board}.png'), full_page=True)
                page.locator('.lb-list').first.screenshot(path=str(shots / f'lb-{board}-list.png'))
            ctx.close()
        browser.close()
    server.shutdown()
    frames = [u for u in bad_requests if '/icons/frames/' in u]
    if frames:
        failures.append(f'missing pictures {frames}')
    print('FAIL' if failures else 'OK', *failures, sep='\n')
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
