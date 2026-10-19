"""⚔️ Đảo bang (game/bang_island.py): the contract with the Bang branch (the view's checks, unknown ids and keys
dropped, a facility left out is level 0), the derived island view (bands, next level, time left, buttons), the
provider registry (the Bang branch's module, the dev stub, nothing: closed), the HTTP routes behind MNL_BANG_ISLAND
(off by default: 404), membership through the provider, the placeholder buttons, the menu entry in the bootstrap,
and the ids shared with the client map (public/js/bang-island-layout.js) and the live room."""
import json
import os
import re
import shutil
import subprocess
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from game import bang_island as BI
from tests import test_http   # its HTTPTests' helpers, borrowed (importing the class would run its tests here too)

ROOT = Path(__file__).resolve().parents[1]


def good(**over):
    v = dict(bang_id='bang_1', name='Long Môn', emoji='🐉', color='#B8282E', level=3,
             facilities=[dict(id='dai_sanh', level=4, state='done', ready_at=None),
                         dict(id='kho_bang', level=2, state='building', ready_at=time.time() + 90)])
    v.update(over)
    return v


class Contract(unittest.TestCase):
    def test_a_good_view_is_cleaned_and_completed(self):
        v = BI.validate_view(good(members_online=4, extra='ignored'))
        self.assertEqual(v['color'], '#b8282e')
        self.assertEqual([f['id'] for f in v['facilities']], list(BI.FACILITY_IDS))
        f = {x['id']: x for x in v['facilities']}
        self.assertEqual((f['dai_sanh']['level'], f['dai_sanh']['state'], f['dai_sanh']['ready_at']), (4, 'done', None))
        self.assertEqual(f['kho_bang']['state'], 'building')
        self.assertEqual((f['cong_bang']['level'], f['cong_bang']['state']), (0, 'done'), 'left out: level 0, done')
        self.assertEqual(v['members_online'], 4)
        self.assertNotIn('extra', v)

    def test_unknown_facilities_and_keys_are_dropped_not_refused(self):
        v = BI.validate_view(good(facilities=[dict(id='lo_ren', level=3), dict(id='san_pet', level=10, state='done', future=1)]))
        self.assertEqual({f['id']: f['level'] for f in v['facilities']}['san_pet'], 10)
        self.assertNotIn('lo_ren', [f['id'] for f in v['facilities']])

    def test_broken_views_raise_a_contract_error(self):
        now = time.time()
        bad = [None, [], good(bang_id='Bang 1'), good(bang_id=''), good(name=''), good(name='x' * 41), good(emoji=''), good(color='red'),
               good(color='#12345'), good(level=0), good(level=True), good(level=100), good(facilities='x'),
               good(facilities=[dict(id='dai_sanh', level=11)]), good(facilities=[dict(id='dai_sanh', level=-1)]),
               good(facilities=[dict(id='dai_sanh', level=2.0)]), good(facilities=[dict(id='dai_sanh', level=2, state='open')]),
               good(facilities=[dict(id='dai_sanh', level=2, state='building')]),
               good(facilities=[dict(id='dai_sanh', level=2, state='building', ready_at=(now + 60) * 1000)]),
               good(facilities=[dict(id='dai_sanh', level=2, state='building', ready_at=float('nan'))]),
               good(facilities=[dict(id='dai_sanh', level=10, state='building', ready_at=now + 60)]),
               good(facilities=[dict(id='dai_sanh', level=1), dict(id='dai_sanh', level=2)]),
               good(members_online=-1)]
        for raw in bad:
            with self.assertRaises(BI.ContractError, msg=repr(raw)[:120]):
                BI.validate_view(raw)

    def test_text_is_trimmed_and_cannot_carry_markup(self):
        v = BI.validate_view(good(name='  <b>Long</b>   Môn ', facilities=[dict(id='den_vang', level=1, note='Cấp 2: <i>giờ vàng</i> dài hơn')]))
        self.assertEqual(v['name'], '‹b›Long‹/b› Môn')
        self.assertNotIn('<', json.dumps(v, ensure_ascii=False))

    def test_bands_and_the_derived_view(self):
        self.assertEqual([BI.band(n) for n in range(11)], [0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 3])
        now = 1_000_000.0
        raw = good(facilities=[dict(id='dai_sanh', level=3, state='building', ready_at=now + 61.2), dict(id='den_vang', level=10),
                               dict(id='tuong_bang', level=0, state='building', ready_at=now + 5)])
        out = BI.island_view(BI.validate_view(raw), now)
        f = {x['id']: x for x in out['facilities']}
        h = f['dai_sanh']
        self.assertEqual((h['band'], h['band_name'], h['to'], h['next'], h['next_band'], h['left'], h['max']), (1, 'Gỗ', 4, 4, 2, 62, 10))
        self.assertEqual((f['den_vang']['band'], f['den_vang']['next'], f['den_vang']['to'], f['den_vang']['left']), (3, None, None, 0))
        self.assertEqual((f['tuong_bang']['band'], f['tuong_bang']['band_name'], f['tuong_bang']['to']), (0, 'Đất trống', 1))
        self.assertIn('nang_cap', [a['op'] for a in h['actions']])
        self.assertIn('dau_truong', [a['op'] for a in f['san_pet']['actions']])
        self.assertEqual((out['id'], out['color']), ('bang_1', '#b8282e'))

    def test_every_stub_preset_keeps_the_contract(self):
        for preset in ('low', 'mid', 'high', 'build', 'empty', 'mix', 'unknown'):
            v = BI.validate_view(BI.stub_view('b', preset))
            bands = {BI.band(f['level']) for f in v['facilities']}
            if preset in ('low', 'mid', 'high'):
                self.assertEqual(bands, {dict(low=1, mid=2, high=3)[preset]}, preset)
        self.assertTrue(all(f['state'] == 'building' for f in BI.stub_view('b', 'build')['facilities']))


class Registry(unittest.TestCase):
    def tearDown(self):
        BI._provider, BI._looked = None, False

    def test_nothing_registered_means_closed_and_the_stub_needs_its_switch(self):
        BI._provider, BI._looked = None, False
        with patch.dict(os.environ, {'MNL_BANG_ISLAND_STUB': ''}):
            self.assertIsNone(BI.provider())
        BI._provider, BI._looked = None, False
        with patch.dict(os.environ, {'MNL_BANG_ISLAND_STUB': '1', 'MNL_BANG_ISLAND_STUB_SET': 'high'}):
            p = BI.provider()
        self.assertIsInstance(p, BI.StubProvider)
        self.assertEqual(p.bang_of(None, 'a' * 64), 'bang_thu')
        self.assertEqual(BI.band(p.view(None, 'bang_thu')['facilities'][0]['level']), 3)

    def test_the_bang_branch_module_wins(self):
        mod = types.ModuleType('game.bang_island_source')
        mod.PROVIDER = BI.StubProvider(members={'s': ('b', 'bang_chu')})
        BI._provider, BI._looked = None, False
        with patch.dict('sys.modules', {'game.bang_island_source': mod}), patch.dict(os.environ, {'MNL_BANG_ISLAND_STUB': '1'}):
            self.assertIs(BI.provider(), mod.PROVIDER)
        other = BI.StubProvider()
        BI.register(other)
        self.assertIs(BI.provider(), other)

    def test_stub_access(self):
        p = BI.StubProvider(members={'m': ('b1', 'pho_bang')}, guests={'g': {'b1'}})
        self.assertEqual(p.access(None, 'm', 'b1'), {'kind': 'member', 'role': 'pho_bang'})
        self.assertIsNone(p.access(None, 'm', 'b2'))
        self.assertEqual(p.access(None, 'g', 'b1'), {'kind': 'guest', 'role': None})
        self.assertIsNone(p.access(None, 'x', 'b1'))


class SharedIds(unittest.TestCase):
    """The client map, the live room and this module name the same facilities and spots."""
    def test_layout_ids(self):
        js = (ROOT / 'public/js/bang-island-layout.js').read_text(encoding='utf-8')
        ids = re.search(r"export const FACILITY_IDS=\[([^\]]*)\]", js).group(1)
        self.assertEqual(tuple(re.findall(r"'([a-z_]+)'", ids)), BI.FACILITY_IDS)
        spots = re.search(r"const SPOT_INFO=\{(.*?)\n\};", js, re.S).group(1)
        self.assertEqual(tuple(re.findall(r"^  ([a-z_]+):\{", spots, re.M)), BI.SPOTS)
        for fid in BI.FACILITY_IDS:
            self.assertRegex(js, rf"{fid}:slot\('{fid}'")
        from live import bang_island as LB
        self.assertEqual(LB.SPOTS, frozenset(BI.FACILITY_IDS + BI.SPOTS))
        emotes = re.search(r"export const EMOTES=\[(.*?)\];", js).group(1)
        self.assertEqual(set(re.findall(r"\['([a-z]+)'", emotes)), set(LB.EMOTES))


class BangIslandHTTP(unittest.TestCase):
    setUpClass = classmethod(test_http.HTTPTests.setUpClass.__func__)
    tearDownClass = classmethod(test_http.HTTPTests.tearDownClass.__func__)
    setUp = test_http.HTTPTests.setUp
    req = test_http.HTTPTests.req
    bootstrap = test_http.HTTPTests.bootstrap

    def tearDown(self):
        BI._provider, BI._looked = None, False

    def signed_in(self, name):
        self.cookie = self.csrf = None
        self.bootstrap()
        with patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw):
            status, headers, body = self.req('/api/account/register', 'POST', dict(username=name, password='matkhau-dai-lam', confirm='matkhau-dai-lam', display=name.title()))
        self.assertEqual(status, 200, body)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        return self.server.store.key(self.cookie.split('=', 1)[1])

    def get(self, q=''):
        status, _, body = self.req('/api/bang-island' + q)
        return status, json.loads(body)

    def test_off_by_default(self):
        self.bootstrap()
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': ''}):
            self.assertEqual(self.get()[0], 404)
            self.assertEqual(self.req('/api/bang-island/act', 'POST', {'bang': 'b1', 'facility': 'dai_sanh', 'op': 'nang_cap'})[0], 404)
            self.assertIsNone(BI.content())

    def test_members_guests_and_strangers(self):
        sid = self.signed_in('thanhvien')
        stub = BI.StubProvider(views={'b1': BI.stub_view('b1', 'mix')}, members={sid: ('b1', 'bang_chu')})
        BI.register(stub)
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': '1'}):
            status, out = self.get()
            self.assertEqual(status, 200, out)
            self.assertEqual((out['bang']['id'], out['me'], out['cap']), ('b1', {'kind': 'member', 'role': 'bang_chu', 'role_name': 'Bang chủ'}, 40))
            self.assertEqual(len(out['bang']['facilities']), 7)
            self.assertEqual(self.get('?bang=b1')[1]['bang']['id'], 'b1')
            self.assertEqual(self.get('?bang=b2')[0], 403)
            self.assertEqual(self.get('?bang=B%20X')[0], 400)
            # A button without the Bang branch's act: the placeholder line, and the view again.
            stub_act, BI.StubProvider.act = BI.StubProvider.act, None
            try:
                status, _, body = self.req('/api/bang-island/act', 'POST', {'bang': 'b1', 'facility': 'kho_bang', 'op': 'gop_quy'})
            finally:
                BI.StubProvider.act = stub_act
            out = json.loads(body)
            self.assertEqual(status, 200, out)
            self.assertTrue(out['done']['placeholder'])
            self.assertIn('Góp quỹ', out['done']['message'])
            self.assertEqual(out['bang']['id'], 'b1')
            # With act: the provider answers.
            status, _, body = self.req('/api/bang-island/act', 'POST', {'bang': 'b1', 'facility': 'san_pet', 'op': 'dau_truong'})
            self.assertEqual(status, 200, body)
            self.assertEqual(stub.acts, [(sid, 'b1', 'san_pet', 'dau_truong')])
            for bad in ({'bang': 'b1', 'facility': 'dai_sanh', 'op': 'gop_quy'}, {'bang': 'b1', 'facility': 'xx', 'op': 'nang_cap'},
                        {'bang': 'b1', 'facility': 'dai_sanh', 'op': 'nang_cap', 'evil': 1}, {'facility': 'dai_sanh', 'op': 'nang_cap'}):
                self.assertEqual(self.req('/api/bang-island/act', 'POST', bad)[0], 400, bad)
            self.assertEqual(self.req('/api/bang-island/act', 'POST', {'bang': 'b2', 'facility': 'dai_sanh', 'op': 'nang_cap'})[0], 403)
            self.assertEqual(self.req('/api/bang-island/other', 'POST', {})[0], 404)
            csrf, self.csrf = self.csrf, 'wrong'
            self.assertEqual(self.req('/api/bang-island/act', 'POST', {'bang': 'b1', 'facility': 'dai_sanh', 'op': 'nang_cap'})[0], 403)
            self.csrf = csrf
            # A guest the bang let in; someone in no bang.
            stub.members.pop(sid)
            stub.guests[sid] = {'b1'}
            self.assertEqual(self.get()[1]['bang'], None)
            self.assertEqual(self.get('?bang=b1')[1]['me'], {'kind': 'guest', 'role': None, 'role_name': None})

    def test_needs_an_account_and_a_provider_and_a_sound_view(self):
        self.bootstrap()
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': '1'}):
            BI.register(BI.StubProvider(everyone=True, views={'bang_thu': BI.stub_view()}))
            self.assertEqual(self.get()[0], 401, 'a guest save without an account')
            sid = self.signed_in('nguoimoi')
            BI.register(None)
            self.assertEqual(self.get()[0], 503)
            BI.register(BI.StubProvider(everyone=True, views={'bang_thu': dict(BI.stub_view(), color='blue')}))
            with patch('builtins.print'):
                self.assertEqual(self.get()[0], 502, 'a view that breaks the contract')
            self.assertTrue(sid)


NODE = shutil.which('node')


@unittest.skipUnless(NODE and (ROOT / 'node_modules' / 'esbuild').exists(), 'needs node and npm ci (esbuild)')
class Client(unittest.TestCase):
    def test_both_interfaces_in_node(self):
        out = subprocess.run([NODE, '--test', str(ROOT / 'tests' / 'bang-island.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=180)
        self.assertEqual(out.returncode, 0, out.stdout[-4000:] + out.stderr[-2000:])


class Content(unittest.TestCase):
    def test_menu_entry_only_while_on(self):
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': '1'}):
            c = BI.content()
        self.assertEqual([f['id'] for f in c['facilities']], list(BI.FACILITY_IDS))
        self.assertEqual(c['cap'], BI.CAP)
        from game import content
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': '0'}):
            self.assertNotIn('bang_island', content._bang_island())
        with patch.dict(os.environ, {'MNL_BANG_ISLAND': '1'}):
            self.assertIn('bang_island', content._bang_island())


if __name__ == '__main__':
    unittest.main()
