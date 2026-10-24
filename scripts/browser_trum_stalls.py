"""🏆 #514 Trùm frames and 🏪 #501/#507 counter goods, in the real modules at 390x844 (no database, no live service).

* public/js/v4/honour-frames.js: the drawn "Trùm <nghề>" frames (🎬 Trùm hãng phim's film strip, one per family) around an
  avatar and as a chat bubble; every picture loads, nothing overflows.
* public/js/v4/quay-scene.js: a cart, a stall and a kiosk of 💄 Mỹ phẩm, 🎀 Phụ kiện dễ thương and 🍢 Cá viên chiên, their
  goods on the counter (GOODS), the menu board from game/quay_self.py.

Run: python scripts/browser_trum_stalls.py [--shots DIR]
"""
import argparse
import http.server
import json
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
sys.path.insert(0, str(ROOT))


class Assets(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def guess_type(self, path):
        return 'image/webp' if str(path).endswith('.webp') else super().guess_type(path)

    def do_GET(self):
        if self.path.split('?')[0] == '/':
            body = (b'<!doctype html><html lang="vi" data-layout="phone"><head><meta charset="utf-8">'
                    b'<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/css/app.css">'
                    b'<link rel="stylesheet" href="/css/chat.css"></head><body style="padding:12px"></body></html>')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            super().do_GET()

    def log_message(self, *_):
        pass


FRAMES = """async () => {
  const {avatar,bubble,TABLES}=await import('/js/v4/honour-frames.js');
  const pick=['actor','pho','nail','singer','vet','repair','secretary','farm','babysitter','kol','lighthouse','jewelry','milk_tea'];
  const av=b=>`<figure style="display:grid;justify-items:center;gap:4px;margin:0">${avatar([`lb_${b}_1`],{},'<span style="display:grid;place-items:center;width:64px;height:64px;border-radius:50%;background:#f3e6d6;font-size:30px">🙂</span>')}<figcaption style="font:600 11px sans-serif">${b}</figcaption></figure>`;
  const bub=(b,text)=>{const x=bubble([`lb_${b}_1`],{});return `<div class="ch-msg" style="display:flex;margin:22px 8px"><div class="ch-bub${x.cls}"${x.attrs}>${text}</div></div>`;};
  document.body.innerHTML=`<h3 style="margin:0 0 12px">🏆 Trùm frames (#514)</h3>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:18px 6px">${pick.map(av).join('')}</div>
    ${bub('actor','Phim mới ra rạp rồi nha cả phố 🎞️⭐')}${bub('pho','Phở nóng đây!')}`;
  await new Promise(r=>setTimeout(r,500));
  const urls=[...document.querySelectorAll('[style*="--hf-img"]')].map(e=>/--hf-img:url\\('([^']+)'\\)/.exec(e.getAttribute('style'))?.[1]).filter(Boolean);
  const loads=await Promise.all(urls.map(u=>new Promise(r=>{const i=new Image();i.onload=()=>r(i.naturalWidth);i.onerror=()=>r(0);i.src=u;})));
  return {n:pick.length,drawn:Object.keys(TABLES.CAREER_DRAWN).length+1,loaded:loads.filter(Boolean).length,urls:urls.length,
    fits:document.documentElement.scrollWidth<=innerWidth+1};
}"""

STALLS = """async (menus) => {
  const {paintCounter}=await import('/js/v4/quay-scene.js');
  const rows=[['cosmetics','xe','Son Xinh','#ec7fa3'],['cute_acc','sap','Nơ Hồng','#8f63c2'],['ca_vien','kiot','Cá Viên Cô Ba','#ef8a3c'],
    ['cosmetics','kiot','Mỹ Phẩm Mây','#d9534f'],['cute_acc','xe','Kẹp Xinh','#3f86c9'],['ca_vien','xe','Xiên Que','#e8b923']];
  document.body.innerHTML='<h3 style="margin:0 0 8px">🏪 Quầy mới (#501/#507)</h3>'+rows.map((r,i)=>`<canvas data-i="${i}" style="display:block;width:100%;margin:0 0 8px;border-radius:12px"></canvas>`).join('');
  rows.forEach(([trade,place,name,color],i)=>{
    const cv=document.querySelector(`canvas[data-i="${i}"]`);
    paintCounter(cv,{place,trade,name,color,decor:i%2?['long_den','cay']:['co_day'],tables:1,menu:menus[trade].slice(0,4),me:null,staff:1,
      actors:[{seed:3+i,state:'waiting'},{seed:9+i,state:'waiting'}],online:i===2,closed:false});
  });
  await new Promise(r=>setTimeout(r,400));
  return {canvases:document.querySelectorAll('canvas').length,fits:document.documentElement.scrollWidth<=innerWidth+1};
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', default='')
    args = ap.parse_args()
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    from game import quay_self as qs
    menus = {t: [dict(emoji=d[1], name=d[2], price=d[3]) for d in rows] for t, rows in qs.MENUS.items()}
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Assets)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'
    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, theme in (('light', ''), ('dark', 'dem')):
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            page = ctx.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.goto(base + '/')
            page.evaluate("t=>{if(t)document.documentElement.dataset.theme=t;}", theme)
            r = page.evaluate(FRAMES)
            print(name, 'frames', r)
            if r['loaded'] != r['urls'] or not r['fits']:
                failures.append(f'{name}: frames {r}')
            if shots:
                page.screenshot(path=str(shots / f'trum-frames-{name}.png'), full_page=True)
            r = page.evaluate(STALLS, menus)
            print(name, 'stalls', r)
            if r['canvases'] != 6 or not r['fits']:
                failures.append(f'{name}: stalls {r}')
            if shots:
                page.screenshot(path=str(shots / f'stalls-{name}.png'), full_page=True)
            if errors:
                failures.append(f'{name}: {errors}')
            ctx.close()
        browser.close()
    server.shutdown()
    print('OK' if not failures else 'FAIL\n' + '\n'.join(failures))
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
