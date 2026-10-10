"""Every career speaks its own words on the screens all careers share (game/career_voice.py, public/js/v4/terms.js;
the owner 06/10: "nghề mỗi nghề mỗi khác, ví dụ như nhà sư mà nó bảo shop").

A non-shop career's rendered shared texts (the reply strip the server builds, bystanders, the promotion toast, the
daily push, the confirm / close-day / books words the client renders, the team-sheet and visit words) never say
tiệm, quán, phục vụ, voucher, doanh thu…; a shop keeps exactly today's words; police never offers anything of value."""
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import Journey, make_task
from game import career_voice as CV
from game import engine as E
from game import feedback as F
from game import feedback_voices as FV
from game.careers import PLUGINS
from game.content import CAREERS, public_content
from game.engine import public_state, validate_state

ROOT = Path(__file__).resolve().parents[1]
NON_SHOP = [c for c in CAREERS if not CV.commerce(c)]


class Dictionary(unittest.TestCase):
    def test_every_career_has_every_key(self):
        self.assertEqual(set(CV.TERMS or CV.terms('pho') and CV.TERMS), set(CAREERS))
        for cid in CAREERS:
            t = CV.terms(cid)
            self.assertEqual(set(t), set(CV.KEYS), cid)
            self.assertIs(type(t['commerce']), bool, cid)
            self.assertEqual(set(t['offers']), {'drink', 'gift', 'refund'}, cid)
            for k, v in t.items():
                if k not in ('commerce', 'offers'):
                    self.assertIsInstance(v, str, (cid, k))

    def test_the_non_shop_careers(self):
        for cid in ('pagoda', 'nurse', 'police', 'teacher', 'secretary', 'hr_admin', 'library', 'railway', 'garbage'):
            self.assertIn(cid, NON_SHOP)
        for cid in ('pho', 'com', 'milk_tea', 'grocery', 'florist', 'salon', 'clothing'):
            self.assertNotIn(cid, NON_SHOP)

    def test_shops_keep_todays_words(self):
        for cid in CAREERS:
            if CV.commerce(cid):
                self.assertEqual(CV.terms(cid), CV.SHOP, cid)
        self.assertEqual(CV.promotion_line('pho', 'Bếp phó', 5), '🎉 Bạn thành Bếp phó! Khách quen boa thêm 5% doanh thu.')

    def test_terms_reach_the_client_in_the_catalogue(self):
        cat = {c['id']: c for c in public_content()['catalogue']}
        self.assertEqual(cat['pagoda']['terms']['books'], 'Sổ chùa')
        self.assertEqual(cat['pho']['terms'], CV.SHOP)
        json.dumps(cat['police']['terms'], ensure_ascii=False, allow_nan=False)

    def test_client_fallback_equals_the_server_shop_row(self):
        src = (ROOT / 'public/js/v4/terms.js').read_text(encoding='utf-8')
        m = re.search(r'export const SHOP=(\{.*?\});\n', src)
        self.assertIsNotNone(m)
        self.assertEqual(json.loads(m.group(1)), CV.SHOP)

    def test_salaried_close_day_never_mentions_rent_tax_or_the_shop_book(self):
        from game import operations
        sal = CV.salaried_set()
        if hasattr(operations, 'SALARIED'):
            self.assertEqual(set(operations.SALARIED), set(CV._SALARIED))
        self.assertEqual(len(sal), 18)
        for cid in sal:
            if cid not in CAREERS:
                continue
            t = CV.terms(cid)
            self.assertFalse(t['commerce'], cid)
            for k in ('end_text', 'end_title', 'books', 'confirm', 'rail_in'):
                self.assertIsNone(re.search(r'tiền thuê|thuê|thuế|sổ tiệm|mặt bằng', t[k], re.I), (cid, k, t[k]))

    def test_police_never_offers_anything(self):
        self.assertEqual([k for k, v in CV.terms('police')['offers'].items() if v], [])
        for o in ('drink', 'gift', 'refund'):
            self.assertFalse(CV.offer_ok('police', o))
        self.assertTrue(CV.offer_ok('police', 'none'))
        self.assertFalse(CV.offer_ok('pagoda', 'refund'))
        self.assertTrue(CV.offer_ok('pho', 'refund'))


class ServerTexts(unittest.TestCase):
    def assertClean(self, cid, text, where=''):
        self.assertEqual(CV.shop_words(cid, text), [], f'{cid} {where}: {text}')

    def test_terms_rows_are_clean(self):
        for cid in NON_SHOP:
            for k, v in CV.terms(cid).items():
                self.assertClean(cid, json.dumps(v, ensure_ascii=False), k)
            self.assertClean(cid, CV.promotion_line(cid, 'Bậc 2', 5), 'promotion')
            self.assertClean(cid, CV.daily_line(cid), 'push')

    def test_every_reply_row_rendered_for_every_non_shop_career(self):
        for cid in NON_SHOP:
            if not CV.own_replies(cid):
                continue
            for happy in (False, True):
                for tid in FV.TONE_ORDER:
                    for row in CV.tone_rows(cid, tid, happy):
                        text = FV.fill(row, label='thái độ', fact='đã ghi đủ', item='lần này', **CV.fill_args(cid, CV.term(cid, 'who')))
                        self.assertClean(cid, text, tid)
                        self.assertNotIn('{', text, (cid, tid))
        for rows in CV.GUEST_TEXT.values():
            for x in rows:
                for cid in NON_SHOP:
                    self.assertClean(cid, FV.fill(x, host=CV.term(cid, 'owner')), 'guest')
        for x in CV.FAN_TEXT:
            self.assertClean('nurse', x, 'fan')

    def test_tone_strip_through_the_game(self):
        """Real reviews of real jobs, through public_post: the ten tones of every non-shop career."""
        seen = set()
        for cid in NON_SHOP:
            if cid not in PLUGINS and cid not in ('accounting', 'customer_care', 'teacher', 'tour_guide'):
                continue
            try:
                j = Journey(cid)
            except unittest.SkipTest:
                continue
            s, c = j.state, j.c
            for day in (3, 6):
                c['day'] = day
                for slot in range(1, 7):
                    try:
                        t = make_task(cid, day, slot, 1)
                    except Exception:  # noqa: BLE001 - a career whose tasks need a live shift
                        break
                    t.update(status='completed', day=day, mistakes=int(slot % 3 == 0), patience=100 - slot * 9)
                    r = F.make_review(s, c, t, 'completed')
                    if not r or not r.get('feedback'):
                        continue
                    p = E.add_feed(s, c, t['npc'], r['text'], t['id'], r['stars'], 'review')
                    F.attach(p, r)
                    pub = F.public_post(p, cid)
                    # The fills ({fact}, {label}, {item}) are the job's own records and gripes (review content, a later
                    # wave): only the template words around them are checked here.
                    fb = p['feedback']
                    worst = min(fb['criteria'], key=lambda x: x['score'])
                    fills = [fb['unfair']['truth'] if fb.get('unfair') else worst['note'], worst['label'],
                             worst['label'][:1].lower() + worst['label'][1:], fb.get('item') or '']
                    for x in pub['feedback'].get('tones') or []:
                        seen.add(cid)
                        text = x['text']
                        for f in sorted(filter(None, fills), key=len, reverse=True):
                            text = text.replace(f, '…')
                        self.assertClean(cid, text, x['id'])
                        self.assertClean(cid, x['label'], x['id'])
        for cid in ('nurse', 'police', 'secretary', 'garbage', 'library', 'railway'):
            if cid in PLUGINS:
                self.assertIn(cid, seen)

    def test_police_reply_with_a_gift_is_refused(self):
        if 'police' not in PLUGINS:
            raise unittest.SkipTest('police filtered out')
        j = Journey('police')
        s, c = j.state, j.c
        c['day'] = 4
        post = None
        for slot in range(1, 20):
            t = make_task('police', 4, slot, 1)
            t.update(status='completed', day=4, mistakes=1, patience=40)
            r = F.make_review(s, c, t, 'completed')
            if r and r.get('feedback') and r['stars'] and r['stars'] <= 3 and r['feedback']['status'] == 'open':
                post = E.add_feed(s, c, t['npc'], r['text'], t['id'], r['stars'], 'review')
                F.attach(post, r)
                break
        self.assertIsNotNone(post)
        money = c['money']
        with self.assertRaises(Exception):
            j.act('fb_reply', post=post['id'], text='Bên phường xin lỗi anh chị, xin gửi chút quà.', offer='gift', tone='sorry')
        self.assertEqual(j.c['money'], money)
        out = j.act('fb_reply', post=post['id'], text='Bên phường nhận thiếu sót, đã nhắc lại quy trình tiếp dân.', offer='none', tone='sorry')
        self.assertTrue(out.get('message') is not None or out)
        validate_state(j.state)
        pub = next(p for p in public_state(j.state)['careers']['police']['feed'] if p['id'] == post['id'])
        self.assertTrue(pub)

    def test_daily_push_in_the_current_careers_words(self):
        from game import push

        class Row(dict):
            pass

        class DB:
            def __init__(self, shop):
                self.shop = shop

            def execute(self, sql, args):
                rows = [Row(shop=self.shop)] if self.shop is not None else []
                return type('Cur', (), {'fetchone': lambda _s: rows[0] if rows else None})()

        self.assertIn('chùa', push._daily_body(DB(json.dumps({'current': 'pagoda'})), 'x'))
        self.assertIn('Ca trực', push._daily_body(DB(json.dumps({'current': 'nurse'})), 'x'))
        self.assertEqual(push._daily_body(DB(json.dumps({'current': 'pho'})), 'x'), CV.SHOP['daily'])
        self.assertEqual(push._daily_body(DB(None), 'x'), CV.SHOP['daily'])
        self.assertEqual(push._daily_body(DB('{bad'), 'x'), CV.SHOP['daily'])
        self.assertNotIn('Quán', push.TITLES['daily'])

    def test_shop_tones_unchanged(self):
        post = dict(id='p-x', stars=2, feedback=dict(persona='sour', rounds=0, unfair=None, item='ly trà',
                                                    criteria=[dict(key='craft', label='Tay nghề', score=2, note='hơi ngọt')]))
        for cid in ('pho', 'milk_tea', 'grocery', None):
            tones = FV.tone_choices(post, cid)
            want = FV._tone_texts('p-x', 0, False, False, 'bạn', 'Tay nghề', 'hơi ngọt', 'ly trà', F._hash)
            self.assertEqual(tuple(x['text'] for x in tones), want)
            self.assertEqual([x['label'] for x in tones], [FV.TONES[t]['label'] for t in FV.TONE_ORDER])


# Literal shell phrases that used to be hard-coded in the shared client files: each now comes from v4/terms.js.
SHELL = {
    'public/js/operations-ui.js': ('Đội của tiệm', 'Bảng tìm người phụ tiệm', 'Mời về tiệm', 'Hiên tiệm đang yên',
                                   'an ninh của tiệm', 'SỔ TIỆM', 'Doanh thu nghề kỳ này'),
    'public/js/v4/workplace-visit.js': ("'Chủ tiệm phục vụ'", "'Chủ tiệm'", 'xem chủ tiệm đang làm gì', 'Chủ tiệm: '),
    'public/js/v4/social.js': ('Chấm quán', 'Chủ quán:', 'Hiện quán', 'Tìm tên quán', 'Chặn quán'),
    'public/js/v4/promo.js': ('Khách quen boa thêm', 'doanh thu đội'),
    'public/js/v4/money.js': ("return 'Quỹ tiệm'",),
    'public/js/app.js': ("'Sổ tiệm'", 'Doanh thu cả kỳ'),
    'game/push.py': ('Quán đang chờ bạn mở cửa ☀️',),
    'game/promotion.py': ('Khách quen boa thêm {pct}% doanh thu', "'doanh thu đội'"),
}


class ClientTexts(unittest.TestCase):
    def test_shared_files_read_the_terms(self):
        for path, phrases in SHELL.items():
            src = (ROOT / path).read_text(encoding='utf-8')
            for x in phrases:
                self.assertNotIn(x, src, f'{path}: "{x}" is hard-coded again; use v4/terms.js / career_voice')

    def test_scene_words_rendered_for_every_career(self):
        """public/js/scenes/index.js wordsFor() in node with the real catalogue: the confirm dialog, the close-day
        dialog, the books and the menu say each career's words."""
        node = shutil.which('node')
        if not node:
            raise unittest.SkipTest('node not installed')
        cat = public_content()['catalogue']
        script = ("const [root,file]=process.argv.slice(2);const fs=await import('node:fs');"
                  "const {wordsFor}=await import(root+'/public/js/scenes/index.js');"
                  "const {termsSource,T,offersOf}=await import(root+'/public/js/v4/terms.js');"
                  "const cat=JSON.parse(fs.readFileSync(file,'utf8'));termsSource(()=>cat);const out={};"
                  "for(const c of cat){const w=wordsFor(c.id);out[c.id]={w:[w.confirm_title,w.end_title,w.end_text,w.rail_in,w.books,w.more_aria],"
                  "t:['team','hire_board','hire','calm','security','revenue','host','by_owner','by_staff','rate','served','placeholder','fund','tip'].map(k=>T(c.id,k)),"
                  "o:offersOf(c.id).map(x=>x[1])};}"
                  "console.log(JSON.stringify(out));")
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'cat.json'
            f.write_text(json.dumps(cat, ensure_ascii=False), encoding='utf-8')
            js = Path(tmp) / 'w.mjs'
            js.write_text(script, encoding='utf-8')
            res = subprocess.run([node, str(js), ROOT.as_uri(), str(f)], capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        for cid in NON_SHOP:
            for text in out[cid]['w'] + out[cid]['t'] + out[cid]['o']:
                self.assertEqual(CV.shop_words(cid, text), [], f'{cid}: {text}')
        for cid in CV.salaried_set():
            if cid in out:   # the close-day dialog of a salaried job: no rent, no tax, no shop book
                self.assertIsNone(re.search(r'thuê|thuế|sổ tiệm', ' '.join(out[cid]['w']), re.I), (cid, out[cid]['w']))
        self.assertEqual(out['pagoda']['w'][0], 'Xác nhận việc chùa')
        self.assertEqual(out['pagoda']['w'][4], 'Sổ chùa')
        self.assertEqual(out['police']['w'][0], 'Xác nhận việc trực ban')
        self.assertEqual(out['police']['o'], [])
        # A shop still says shop words where it should.
        self.assertEqual(out['milk_tea']['w'][0], 'Xác nhận việc của tiệm')
        self.assertEqual(out['milk_tea']['w'][4], 'Sổ tiệm')
        self.assertEqual(out['milk_tea']['t'][0], 'Đội của tiệm')


if __name__ == '__main__':
    unittest.main()
