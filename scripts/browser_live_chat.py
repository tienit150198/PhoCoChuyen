#!/usr/bin/env python3
"""💬 Chat in two browsers (dev tool, needs `pip install playwright websockets` + chromium).

Starts a game server (story mode, SQLite) and the live service (live/, `python3 -m live`) on the same
database, then plays two phones (390×844) that become friends, plus a brand-new guest:
  * the chat button and its badge appear only once the service says chat is on;
  * Cả phố: A posts, the send button counts down (10 s slow mode), B reads and answers; the new guest reads
    but cannot post yet;
  * Bạn bè: B sees A online, opens a DM, A gets the badge (button, tab, menu entry) and answers;
  * groups: A makes a group with B, both write;
  * A takes back a message (B sees "đã thu hồi"), B reports one, B turns "Hiện online" off;
  * dark theme; the admin "Chat" tab with the reported message.
Fails on console errors, page errors or HTTP 5xx.

  python scripts/browser_live_chat.py [--shots DIR]
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PW = 'matkhau-rat-dai'


def free_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_http(url: str, secs: float = 60) -> None:
    end = time.time() + secs
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=1)
            return
        except Exception:  # noqa: BLE001
            time.sleep(0.15)
    raise SystemExit(f'not answering: {url}')


@contextlib.contextmanager
def servers(tmp: str):
    gp, lp = free_port(), free_port()
    db = os.path.join(tmp, 'g.sqlite3')
    env = dict(os.environ, QUIET='1', PUSH_DISABLED='1', LIVE_URL=f'ws://127.0.0.1:{lp}/live', ADMIN_USERS='op_admin')
    for k in ('MNL_DEV', 'MNL_CAREERS', 'LLM_API_KEY', 'DATABASE_URL'):
        env.pop(k, None)
    game = subprocess.Popen([sys.executable, 'server.py', '--port', str(gp), '--db', db], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_http(f'http://127.0.0.1:{gp}/api/health')
    lenv = dict(env, LIVE_CHAT='1', LIVE_ORIGINS=f'http://127.0.0.1:{gp}', LIVE_PORT=str(lp))
    log = open(os.path.join(tmp, 'live.log'), 'w')
    live = subprocess.Popen([sys.executable, '-m', 'live', '--db', db], cwd=ROOT, env=lenv, stdout=log, stderr=log)
    wait_http(f'http://127.0.0.1:{lp}/live/health')
    try:
        yield f'http://127.0.0.1:{gp}', db, os.path.join(tmp, 'live.log')
    finally:
        for p in (live, game):
            p.terminate()
            with contextlib.suppress(Exception):
                p.wait(5)
        log.close()


API = """async ([path, body]) => {
  const boot = await fetch('/api/bootstrap?lite=1').then(r => r.json());
  const r = await fetch(path, body === null ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Game-CSRF': boot.csrf}, body: JSON.stringify(body)});
  return {status: r.status, data: await r.json().catch(() => ({}))};
}"""


class Phone:
    def __init__(self, ctx, page, name, problems):
        self.ctx, self.page, self.name, self.problems = ctx, page, name, problems

    async def api(self, path, body=None):
        out = await self.page.evaluate(API, [path, body])
        if out['status'] >= 400:
            raise AssertionError(f'{self.name}: {path} -> {out}')
        return out['data']

    async def shot(self, shots: Path, name: str):
        await self.page.wait_for_timeout(350)
        await self.page.screenshot(path=str(shots / f'{name}.png'))

    async def chat_button(self, timeout=25000):
        await self.page.wait_for_selector('.live-fab:not([hidden])', timeout=timeout)


async def phone(browser, base, name, problems, intro=True) -> Phone:
    ctx = await browser.new_context(viewport=dict(width=390, height=844), has_touch=True, is_mobile=True, device_scale_factor=2)
    page = await ctx.new_page()
    tag = name
    page.on('console', lambda m: m.type == 'error' and problems.append(f'{tag} console: {m.text[:200]}'))
    page.on('pageerror', lambda e: problems.append(f'{tag} exception: {str(e)[:200]}'))
    page.on('response', lambda r: r.status >= 500 and problems.append(f'{tag} HTTP {r.status} {r.url}'))
    await page.goto(base + '/')
    await page.wait_for_selector('#app:not([hidden])', timeout=30000)
    if intro:
        await page.click('[data-action=jrGender][data-gender=female]', timeout=10000)
        await page.fill('#jr-name', name)
        await page.click('form[data-jr-form=start] button[type=submit]')
        await page.wait_for_timeout(2500)
        for _ in range(8):
            if not await page.evaluate("!!document.querySelector('#sheet[open],#confirmDialog[open]')"):
                break
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(500)
    return Phone(ctx, page, name, problems)


async def text_of(page, sel):
    return await page.evaluate(f"[...document.querySelectorAll({json.dumps(sel)})].map(e=>e.innerText).join(' | ')")


async def send(p: Phone, text: str):
    await p.page.fill('.chat-sheet textarea', text)
    await p.page.click('.chat-sheet .ch-send')


async def run(shots: Path) -> list:
    from playwright.async_api import async_playwright
    problems: list = []
    checks: list = []

    def check(cond, what):
        checks.append(('PASS' if cond else 'FAIL') + ' ' + what)
        if not cond:
            problems.append('check: ' + what)

    with tempfile.TemporaryDirectory(prefix='mnl-live-') as tmp, servers(tmp) as (base, db, live_log):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            a = await phone(browser, base, 'Lan Anh', problems)
            b = await phone(browser, base, 'Minh Tú', problems)
            # accounts and friendship through the game's own API
            await a.api('/api/account/register', dict(username='lananh_t', password=PW, confirm=PW, display='Lan Anh'))
            await b.api('/api/account/register', dict(username='minhtu_t', password=PW, confirm=PW, display='Minh Tú'))
            await a.api('/api/marriage/friend_request', dict(username='minhtu_t'))
            view = await b.api('/api/marriage')
            rid = view['friends']['incoming'][0]['id']
            await b.api('/api/marriage/friend_respond', dict(id=rid, answer='accept'))
            # both are long-time players (not "new"): their save was born before today
            with sqlite3.connect(db) as con:
                con.execute("UPDATE stat_births SET day='2026-01-01'")
            for p in (a, b):
                await p.page.reload()
                await p.page.wait_for_selector('#app:not([hidden])', timeout=30000)
                await p.chat_button()
            check(True, 'the chat button shows once the service says chat is on')
            await a.shot(shots, '01-phone-chat-button')

            # ---- Cả phố ----
            await a.page.click('.live-fab')
            await a.page.wait_for_selector('.chat-sheet[open] .ch-tabs')
            await a.page.wait_for_timeout(600)
            await a.shot(shots, '02-town-empty')
            await send(a, 'Chào cả phố! Tối nay ai ra chợ đêm không? 🏮')
            await a.page.wait_for_selector('.ch-msg.mine')
            await a.page.wait_for_timeout(300)
            cd = await text_of(a.page, '.ch-send.wait')
            check(cd.strip().isdigit() and 7 <= int(cd.strip()) <= 10, f'slow mode countdown on the send button ({cd!r})')
            await a.shot(shots, '03-town-sent-countdown')
            await b.page.click('.live-fab')
            await b.page.wait_for_selector('.chat-sheet[open] .ch-msg')
            got = await text_of(b.page, '.ch-msg:not(.mine) .ch-bub')
            check('Chào cả phố' in got, 'B reads A on Cả phố')
            await send(b, 'Có mình! Gặp ở cổng chợ nhé vl 😆')
            await a.page.wait_for_function("document.querySelectorAll('.ch-msg:not(.mine)').length>0", timeout=5000)
            check('Gặp ở cổng chợ' in await text_of(a.page, '.ch-msg:not(.mine) .ch-bub'), 'A gets B live (GenZ slang kept)')
            await b.shot(shots, '04-town-two-players')
            await send(b, 'zalo mình 0912 345 678 nha')
            await b.page.wait_for_timeout(600)
            check('0912' not in await text_of(b.page, '.ch-bub'), 'B: wait for slow mode, nothing sent early')
            await b.page.wait_for_timeout(10500)
            await b.page.click('.chat-sheet .ch-send')
            await a.page.wait_for_function("[...document.querySelectorAll('.ch-bub')].some(e=>e.innerText.includes('zalo'))", timeout=5000)
            masked = await text_of(a.page, '.ch-bub')
            check('0912' not in masked and '•••' in masked, 'phone numbers are masked')

            # ---- a guest (no account) reads but cannot post (owner, 01/10) ----
            c = await phone(browser, base, 'Bé Mới', problems)
            await c.chat_button()
            await c.page.click('.live-fab')
            await c.page.wait_for_selector('.chat-sheet[open] .ch-ro:not([hidden])', timeout=8000)
            ro = await text_of(c.page, '.ch-ro')
            check('Tạo tài khoản' in ro, f'a guest reads Cả phố but cannot post: read-only line ({ro!r})')
            check('Chào cả phố' in await text_of(c.page, '.ch-bub'), 'the guest reads Cả phố')
            await c.shot(shots, '05-town-guest-read-only')
            await c.page.click('.chat-sheet .ch-ro [data-ch-act=account]')
            await c.page.wait_for_selector('#sheet[open] #accountRegisterForm', timeout=8000)
            check(True, '"Tạo tài khoản" opens the register form')
            await c.shot(shots, '05b-guest-register-form')

            # ---- Bạn bè + DM ----
            await b.page.click('[data-ch-act=tab][data-tab=friends]')
            await b.page.wait_for_selector('.ch-row .ch-on', timeout=5000)
            check(True, 'B sees A online (green dot)')
            await b.shot(shots, '06-friends-online')
            await b.page.click('.ch-row[data-ch-act=dm]')
            await b.page.wait_for_selector('.ch-head .ch-title')
            await send(b, 'Lan Anh ơi, tối nay 7h nha!')
            await b.page.wait_for_selector('.ch-msg.mine')
            await a.page.wait_for_selector('.ch-tabs .badge', timeout=5000)
            check((await text_of(a.page, '.ch-tabs .badge')).strip() == '1', 'A: unread badge on Tin nhắn')
            await a.shot(shots, '07-unread-badge-tab')
            await a.page.click('[data-ch-act=tab][data-tab=inbox]')
            await a.page.wait_for_selector('.ch-row[data-ch-act=open]')
            await a.shot(shots, '08-inbox')
            await a.page.click('.ch-row[data-ch-act=open]')
            await a.page.wait_for_selector('.ch-msg:not(.mine)')
            await send(a, 'Okela, hẹn 7h ở cổng chợ 👍')
            await b.page.wait_for_function("[...document.querySelectorAll('.ch-bub')].some(e=>e.innerText.includes('Okela'))", timeout=5000)
            check(True, 'DM both ways')
            await a.shot(shots, '09-dm-thread')
            # A takes back a message; B sees it gone
            await a.page.click('.ch-msg.mine .ch-bub')
            await a.page.click('[data-ch-act=del]')
            await a.page.click('[data-ch-act=del].warn')   # "Thu hồi thật?" (🗑️ since 03/10)
            await b.page.wait_for_selector('.ch-bub.del', timeout=5000)
            check(True, 'delete own: the other side sees "đã thu hồi"')
            await b.shot(shots, '10-dm-deleted')

            # ---- badge on the chat button and the menu while the dialog is closed ----
            await a.page.keyboard.press('Escape')
            await send(b, 'Nhớ mang áo khoác nha')
            await a.page.wait_for_selector('.live-fab .badge:not([hidden])', timeout=5000)
            check((await text_of(a.page, '.live-fab .badge')).strip() == '1', 'chat button badge')
            await a.shot(shots, '11-chat-button-badge')
            await a.page.evaluate("document.querySelector('[data-action=v4Menu]')?.click()")
            await a.page.wait_for_timeout(700)
            await a.page.wait_for_selector('#rail [data-action=liveChat]:visible', timeout=5000)   # Chat is first in the menu, one tap
            menu = await text_of(a.page, '#rail [data-action=liveChat]')
            check('Chat' in menu, f'menu entry "Chat" ({menu!r})')
            await a.shot(shots, '12-menu-entry')
            await a.page.click('#rail [data-action=liveChat]')
            await a.page.wait_for_selector('.chat-sheet[open]')
            await a.shot(shots, '12b-reopened-where-left')   # back in the chat it was on
            await a.page.click('[data-ch-act=back]')

            # ---- groups ----
            await a.page.click('[data-ch-act=tab][data-tab=inbox]')
            await a.page.click('[data-ch-act=groupNew]')
            await a.page.fill('[data-ch-field=gtitle]', 'Hội chợ đêm')
            await a.page.check('[data-ch-field=pick]')
            await a.shot(shots, '13-group-new')
            await a.page.click('[data-ch-act=groupMake]')
            await a.page.wait_for_selector('.ch-head .ch-title small', timeout=5000)
            await send(a, 'Nhóm đi chợ đêm nè mọi người')
            await b.page.click('[data-ch-act=back]')
            await b.page.click('[data-ch-act=tab][data-tab=inbox]')
            await b.page.wait_for_function("[...document.querySelectorAll('.ch-row b')].some(e=>e.innerText.includes('Hội chợ đêm'))", timeout=5000)
            await b.page.click('.ch-row:has-text("Hội chợ đêm")')
            await b.page.wait_for_selector('.ch-msg:not(.mine)')
            await send(b, 'Có mặt!')
            await a.page.wait_for_function("[...document.querySelectorAll('.ch-bub')].some(e=>e.innerText.includes('Có mặt'))", timeout=5000)
            check(True, 'group: both write')
            await a.shot(shots, '14-group-thread')

            # ---- report, appear offline, dark theme ----
            await b.page.click('[data-ch-act=back]')
            await b.page.click('[data-ch-act=tab][data-tab=town]')
            await b.page.wait_for_selector('.ch-msg:not(.mine) .ch-bub')
            n = await b.page.evaluate('''()=>new Promise(ok=>{let n=0;const o=new MutationObserver(()=>n++);o.observe(document.querySelector('.ch-body'),{childList:true,subtree:true});setTimeout(()=>{o.disconnect();ok(n);},1500);})''')
            check(n < 3, f'the list is not redrawn while nothing happens ({n} redraws in 1.5 s)')
            await b.page.click('.ch-msg:not(.mine) .ch-bub')
            await b.page.click('[data-ch-act=report]')
            await b.shot(shots, '15-report-reasons')
            await b.page.click('[data-ch-act=reason][data-reason=spam]')
            await b.page.wait_for_selector('.ch-flash:not([hidden])', timeout=5000)
            await b.page.click('[data-ch-act=tab][data-tab=friends]')
            await b.page.click('.ch-switch')
            await a.page.click('[data-ch-act=back]')
            await a.page.click('[data-ch-act=tab][data-tab=friends]')
            await a.page.wait_for_function("!document.querySelector('.chat-sheet .ch-rows .ch-on')", timeout=5000)
            check(True, '"Hiện online" off: A sees B offline')
            await b.page.evaluate("document.documentElement.dataset.theme='dem'")
            await b.shot(shots, '16-friends-dark-online-off')
            await b.page.click('.ch-row[data-ch-act=dm]')
            await b.page.wait_for_selector('.ch-msg')
            await b.shot(shots, '17-dm-dark')

            # ---- admin "Chat" tab ----
            ad = await phone(browser, base, 'Vận Hành', problems, intro=False)
            await ad.api('/api/account/register', dict(username='op_admin', password=PW, confirm=PW, display='Vận Hành'))
            await ad.page.set_viewport_size(dict(width=1200, height=820))
            await ad.page.goto(base + '/admin#chat')
            await ad.page.wait_for_selector('.chat-admin', timeout=15000)
            await ad.page.click('[data-act=chatTab][data-value=town]')
            await ad.shot(shots, '18-admin-chat-town')
            await ad.page.click('[data-act=chatTab][data-value=queue]')
            await ad.shot(shots, '19-admin-chat-queue')
            await browser.close()
        print(Path(live_log).read_text()[-600:], file=sys.stderr)
    for line in checks:
        print(line)
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shots', type=Path, default=Path(tempfile.gettempdir()) / 'mnl-live-shots')
    args = ap.parse_args()
    args.shots.mkdir(parents=True, exist_ok=True)
    problems = asyncio.run(run(args.shots))
    print(json.dumps(dict(ok=not problems, problems=problems, shots=str(args.shots)), ensure_ascii=False, indent=2))
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
