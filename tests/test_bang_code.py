"""📜 Nội quy bang (game/bang_code.py; owner 21/10 "bang thì thêm cái nội quy bang nữa nhé, thiếu nội quy bang rồi",
"công bố bên ngoài thì có nội quy bang riêng nữa, có text và giới hạn chữ"; PostgreSQL with TEST_DATABASE_URL):
* two texts: 📢 public (≤ 300 characters, ≤ 8 lines) on the card in Tìm bang and the bang's page for visitors, 📜 internal
  (≤ 1200, ≤ 20 lines) for members only; Phó bang and up write them, cleaned like the motto (no link, masked words);
* edits compare-and-set the version (a stale page is refused, the same text again is a no-op, two at once: one wins),
  rate-limited, logged in the bang, kept in an append-only history;
* joining a bang with public rules needs the tick and the version read (a changed version: read again; a 2.4.66 page that
  sends nothing: a clear "tải lại"), on join, request and accepting an invitation; without public rules nothing changes;
* 📜 Nội quy mới for members until they open it; the operator hides / shows each text (kept, logged); MNL_BANG_OFF."""
import os
import threading
from unittest.mock import patch

from game import bang
from game import bang_code as K
from game import marriage as mr
from game import pg_schema
from tests.test_bang import Base

RULES = 'Online góp quỹ mỗi tuần\nKhông chửi bậy trong bang'
INNER = 'Bang chiến Chủ nhật 20:00 phải có mặt\nVắng 7 ngày không báo sẽ bị mời ra'


class Code(Base):
    def setUp(self):
        super().setUp()
        self.a = self.player(name='Lan')
        self.bid = self.found(self.a)

    def later(self, s=60):
        self.t[0] += s

    def write(self, tok, kind, text, ver=None):
        if ver is None:
            ver = self.ver(kind)
        out = self.op(tok, 'code', kind=kind, text=text, ver=ver)
        self.later()
        return out

    def ver(self, kind):
        r = self.one('SELECT ver FROM bang_code WHERE bang=? AND kind=?', (self.bid, kind))
        return int(r['ver']) if r else 0

    def card(self):
        bang._VIEW.clear()
        return next(c for c in bang.search(self.store, None) if c['id'] == self.bid)

    def visitor_page(self, tok):
        return bang.page(self.store, self.sid(tok), self.bid)

    def member(self, name='Minh'):
        tok = self.player(name=name)
        self.op(tok, 'join', bang=self.bid, **self.agree())
        return tok

    def agree(self):
        with self.store.connect() as db:
            c = K.public_of(db, self.bid)
        return dict(agree=True, code_ver=c['ver']) if c['text'] else {}

    def code(self, tok):
        return bang.page(self.store, self.sid(tok))['code']

    def test_schema_step(self):
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 73)
        names = {t['name'] for t in pg_schema.TABLES}
        self.assertTrue({'bang_code', 'bang_code_hist', 'bang_code_seen'} <= names)

    def test_two_texts_who_sees_what(self):
        self.write(self.a, 'pub', RULES)
        self.write(self.a, 'in', INNER)
        c = self.card()
        self.assertEqual(c['code'], dict(text=RULES, ver=1))                   # 📢 on the card in Tìm bang
        v = self.player(name='Khách')
        p = self.visitor_page(v)
        self.assertFalse(p['member'])
        self.assertEqual(p['bang']['code']['text'], RULES)                    # …and on its page for a visitor
        self.assertNotIn('code', p)
        self.assertNotIn(INNER, repr(p))                                      # 📜 never outside the bang
        self.assertNotIn(INNER, repr(bang.get_view(self.store, v, {'list': 1})))
        m = self.member()
        code = self.code(m)
        self.assertEqual((code['pub']['text'], code['in']['text']), (RULES, INNER))
        self.assertEqual(code['pub']['by'], 'Lan')
        self.assertFalse(code['edit'])
        self.assertNotIn('tips', code)
        mine = self.code(self.a)
        self.assertTrue(mine['edit'])
        self.assertEqual(len(mine['tips']), len(K.TIPS))
        self.assertEqual((mine['max'], mine['lines']), ({'pub': 300, 'in': 1200}, {'pub': 8, 'in': 20}))
        log = [r['text'] for r in self.rows("SELECT text FROM bang_log WHERE bang=? AND kind='code' ORDER BY id", (self.bid,))]
        self.assertEqual(log, ['📜 Lan cập nhật nội quy công khai của bang.', '📜 Lan cập nhật nội quy nội bộ của bang.'])

    def test_limits_and_cleaning(self):
        self.refused_op(self.a, 'code', 'code_long', kind='pub', text='a' * 301, ver=0)
        self.refused_op(self.a, 'code', 'code_long', kind='pub', text='\n'.join('dòng' for _ in range(9)), ver=0)
        self.write(self.a, 'pub', 'a' * 300, 0)
        self.write(self.a, 'in', '\n'.join(f'Điều {i}' for i in range(20)), 0)
        self.refused_op(self.a, 'code', 'code_long', kind='in', text='b' * 1201, ver=1)
        self.refused_op(self.a, 'code', 'code_long', kind='in', text='\n'.join('x' for _ in range(21)), ver=1)
        msg = self.refused_op(self.a, 'code', 'blocked_link', kind='in', text='Vào nhóm www.abc.com nhé', ver=1)
        self.assertIn('nội quy', msg)
        self.refused_op(self.a, 'code', 'blocked_contact', kind='in', text='Gọi 0912 345 678', ver=1)
        self.write(self.a, 'in', '  Không   fuck nhau  \r\n\r\n\r\n\r\n  Hòa đồng  ')
        got = self.code(self.a)['in']['text']
        self.assertNotIn('fuck', got)
        self.assertEqual(got.split('\n')[0].split(' ')[0], 'Không')
        self.assertNotIn('\n\n\n', got)
        self.assertTrue(got.endswith('\nHòa đồng'))
        for bad in (dict(kind='x', text='a', ver=0), dict(kind='pub', text=5, ver=1), dict(kind='pub', ver=1),
                    dict(kind='pub', text='a', ver=1, extra=1)):
            self.refused_op(self.a, 'code', None, **bad)

    def test_who_writes(self):
        pho, lao, tv = self.member('Minh'), self.member('Tú'), self.member('Dũng')
        self.op(self.a, 'role', pid=self.pid(pho), role='pho')
        self.op(self.a, 'role', pid=self.pid(lao), role='lao')
        self.write(pho, 'pub', RULES, 0)                                         # Phó bang: yes
        self.refused_op(lao, 'code', 'role', kind='pub', text='x', ver=1)       # Trưởng lão: no
        self.refused_op(tv, 'code', 'role', kind='in', text='x', ver=0)
        outsider = self.player(name='Khách')
        self.refused_op(outsider, 'code', 'not_member', kind='in', text='x', ver=0)

    def test_compare_and_set_and_rate(self):
        self.write(self.a, 'pub', RULES, 0)
        msg = self.refused_op(self.a, 'code', 'code_conflict', kind='pub', text='Bản khác', ver=0)   # a stale page
        self.assertIn('người khác sửa', msg)
        self.assertEqual(self.op(self.a, 'code', kind='pub', text=RULES, ver=0)['done']['message'], 'Không có gì thay đổi.')  # a retry
        self.assertEqual(self.ver('pub'), 1)
        self.op(self.a, 'code', kind='pub', text='Bản 2', ver=1)
        self.refused_op(self.a, 'code', 'code_slow', kind='pub', text='Bản 3', ver=2)   # too soon after
        self.op(self.a, 'code', kind='in', text=INNER, ver=0)                          # the other text: its own gap
        self.later(K.EDIT_GAP)
        self.op(self.a, 'code', kind='pub', text='Bản 3', ver=2)
        n = self.one("SELECT COUNT(*) AS n FROM bang_code_hist WHERE bang=? AND what='edit'", (self.bid,))['n']
        for i in range(K.EDIT_DAY - n):
            self.later(K.EDIT_GAP)
            self.op(self.a, 'code', kind='in', text=f'Bản {i}', ver=self.ver('in'))
        self.later(K.EDIT_GAP)
        self.assertIn(f'{K.EDIT_DAY} lần', self.refused_op(self.a, 'code', 'code_slow', kind='in', text='Nữa', ver=self.ver('in')))
        hist = self.rows('SELECT ver, text FROM bang_code_hist WHERE bang=? AND kind=? ORDER BY id', (self.bid, 'pub'))
        self.assertEqual([h['text'] for h in hist], [RULES, 'Bản 2', 'Bản 3'])   # every version kept
        self.later(86400)
        self.op(self.a, 'code', kind='in', text='Hôm sau', ver=self.ver('in'))

    def test_two_edits_at_once_one_wins(self):
        pho = self.member('Minh')
        self.op(self.a, 'role', pid=self.pid(pho), role='pho')
        got, errs = [], []

        def go(tok, text):
            try:
                self.op(tok, 'code', kind='in', text=text, ver=0)
                got.append(text)
            except bang.BangError as e:
                errs.append(e.code)
        th = [threading.Thread(target=go, args=x) for x in ((self.a, 'Của Lan'), (pho, 'Của Minh'))]
        [t.start() for t in th]
        [t.join() for t in th]
        self.assertEqual((len(got), errs), (1, ['code_conflict']))
        self.assertEqual(self.ver('in'), 1)
        self.assertEqual(self.code(self.a)['in']['text'], got[0])

    def test_join_needs_the_tick_and_the_version(self):
        old = self.player(name='Cũ')
        self.op(old, 'join', bang=self.bid)                                      # no public rules: as before (2.4.66)
        self.assertEqual(self.mine(old)['bang'], self.bid)
        self.write(self.a, 'pub', RULES, 0)
        b = self.player(name='Minh')
        msg = self.refused_op(b, 'join', 'code_agree', bang=self.bid)            # a 2.4.66 page sends nothing
        self.assertIn('Tải lại game', msg)
        self.assertIn('Tôi đã đọc', self.refused_op(b, 'join', 'code_agree', bang=self.bid, agree=False, code_ver=1))
        self.write(self.a, 'pub', 'Nội quy mới hơn')                            # changed while they read
        with self.assertRaises(bang.BangError) as cm:
            self.op(b, 'join', bang=self.bid, agree=True, code_ver=1)
        self.assertEqual((cm.exception.code, cm.exception.status), ('code_changed', 409))
        self.assertIsNone(self.mine(b))
        self.op(b, 'join', bang=self.bid, agree=True, code_ver=2)
        self.assertEqual(self.mine(b)['bang'], self.bid)
        seen = self.one('SELECT * FROM bang_code_seen WHERE sid=? AND bang=?', (self.sid(b), self.bid))
        self.assertEqual((seen['agreed'], seen['pub'], seen['inn']), (2, 2, 0))
        self.assertFalse(self.code(b)['fresh'])                                 # read the public version they agreed to

    def test_requests_and_invitations(self):
        self.op(self.a, 'rules', mode='ask')
        self.write(self.a, 'pub', RULES, 0)
        b = self.player(name='Minh')
        self.refused_op(b, 'join', 'code_agree', bang=self.bid)
        self.assertEqual(self.op(b, 'join', bang=self.bid, agree=True, code_ver=1)['done']['asked'], self.bid)
        self.write(self.a, 'pub', 'Nội quy sửa sau khi xin vào')
        self.op(self.a, 'approve', pid=self.pid(b))                              # the officer decides: no new tick needed
        self.assertEqual(self.mine(b)['bang'], self.bid)
        code = self.code(b)
        self.assertEqual((code['fresh'], code['news']), (True, ['pub']))        # but they see 📜 Nội quy mới
        # an invitation: accepting it is joining
        c = self.player(name='Tú')
        self.op(self.a, 'invite', code=mr.ensure_person(self.store, self.sid(c))['code'])
        self.assertTrue(bang.me_view(self.store, c)['invites'][0]['code'])
        self.refused_op(c, 'accept', 'code_agree', bang=self.bid)
        self.op(c, 'accept', bang=self.bid, agree=True, code_ver=2)
        self.assertEqual(self.mine(c)['bang'], self.bid)

    def test_new_rules_badge(self):
        m = self.member()
        self.assertFalse(bang.me_view(self.store, m)['mine']['code_new'])
        self.sent.clear()
        self.write(self.a, 'in', INNER, 0)
        self.assertIn(self.pid(m), [p for e in self.sent if e.get('op') == 'bang' for p in e.get('pids') or []])   # their bang_me
        self.assertTrue(bang.me_view(self.store, m)['mine']['code_new'])
        self.assertFalse(bang.me_view(self.store, self.a)['mine']['code_new'])   # the editor read what they wrote
        code = self.code(m)
        self.assertEqual(code['news'], ['in'])
        out = self.op(m, 'code_seen', pub=0, **{'in': code['in']['ver']})
        self.assertEqual(set(out), {'done'})                                     # a read mark: no page sent back
        self.assertFalse(out['done']['fresh'])
        self.assertFalse(bang.me_view(self.store, m)['mine']['code_new'])
        self.op(m, 'code_seen', pub=0, **{'in': 99})                              # never past the current version
        self.assertEqual(self.one('SELECT inn FROM bang_code_seen WHERE sid=?', (self.sid(m),))['inn'], 1)
        self.op(m, 'code_seen', pub=0, **{'in': 0})                               # nor back
        self.assertEqual(self.one('SELECT inn FROM bang_code_seen WHERE sid=?', (self.sid(m),))['inn'], 1)
        self.write(self.a, 'in', INNER + '\nThêm một điều')
        self.assertTrue(bang.me_view(self.store, m)['mine']['code_new'])
        self.write(self.a, 'in', '')                                             # cleared by the leader: no badge for nothing
        self.assertFalse(bang.me_view(self.store, m)['mine']['code_new'])
        self.assertIn('📜 Lan xóa nội quy nội bộ của bang.', [r['text'] for r in self.rows('SELECT text FROM bang_log WHERE bang=?', (self.bid,))])
        self.assertEqual(self.one('SELECT COUNT(*) AS n FROM bang_code_hist WHERE bang=?', (self.bid,))['n'], 3)   # the old text kept

    def test_operator_hides_and_shows(self):
        self.write(self.a, 'pub', RULES, 0)
        self.write(self.a, 'in', INNER, 0)
        row = next(b for b in bang.admin_view(self.store)['bangs'] if b['id'] == self.bid)
        self.assertEqual((row['code']['pub']['text'], row['code']['in']['text']), (RULES, INNER))
        bang.admin_act(self.store, 'mod', dict(op='code_hide', id=self.bid, kind='pub'))
        self.assertEqual(self.card()['code']['text'], '')
        row = next(b for b in bang.admin_view(self.store)['bangs'] if b['id'] == self.bid)
        self.assertEqual((row['code']['pub']['text'], row['code']['pub']['hidden']), (RULES, True))   # kept, never deleted
        self.assertEqual(self.code(self.a)['in']['text'], INNER)                                       # the other one stays
        b = self.player(name='Minh')
        self.op(b, 'join', bang=self.bid)                                       # nothing to agree to while hidden
        self.assertEqual(self.mine(b)['bang'], self.bid)
        self.assertEqual(self.code(self.a)['pub']['hidden'], True)
        self.refused_op(self.a, 'code', 'code_hidden', kind='pub', text=RULES, ver=self.ver('pub'))   # not the same text again
        bang.admin_act(self.store, 'mod', dict(op='code_show', id=self.bid, kind='pub'))
        self.assertEqual(self.card()['code'], dict(text=RULES, ver=3))
        log = [r['text'] for r in self.rows("SELECT text FROM bang_log WHERE bang=? AND kind='admin' ORDER BY id", (self.bid,))]
        self.assertEqual(log, ['📜 Quản trị ẩn nội quy công khai của bang.', '📜 Quản trị hiện lại nội quy công khai của bang.'])
        self.assertEqual(self.rows("SELECT what FROM bang_code_hist WHERE bang=? AND kind='pub' ORDER BY id", (self.bid,)),
                         [dict(what='edit'), dict(what='hide'), dict(what='show')])
        with self.assertRaises(bang.BangError):
            bang.admin_act(self.store, 'mod', dict(op='code_hide', id=self.bid, kind='nope'))

    def test_kill_switch(self):
        self.write(self.a, 'pub', RULES, 0)
        with patch.dict(os.environ, {'MNL_BANG_OFF': '1'}):
            self.assertTrue(bang.me_view(self.store, self.a).get('off'))
            with self.assertRaises(bang.BangError):
                bang.get_view(self.store, self.a, {'list': 1})
            self.refused_op(self.a, 'code', 'off', kind='pub', text='x', ver=1)

    def test_erasure_keeps_the_text(self):
        pho = self.member('Minh')
        self.op(self.a, 'role', pid=self.pid(pho), role='pho')
        self.write(pho, 'in', INNER, 0)
        self.store.transaction(lambda db: bang.forget(db, self.sid(pho)))
        r = self.one("SELECT text, by_sid FROM bang_code WHERE bang=? AND kind='in'", (self.bid,))
        self.assertEqual((r['text'], r['by_sid']), (INNER, ''))
        self.assertEqual(self.one('SELECT COUNT(*) AS n FROM bang_code_hist WHERE by_sid=?', (self.sid(pho),))['n'], 0)
        self.assertEqual(self.code(self.a)['in']['by'], '')
