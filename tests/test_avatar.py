"""🙂 Ảnh đại diện: the save block (game/avatar.py), the public face code (live/faces.py, public/js/v4/face-code.js),
the art in node (tests/face.mjs) and the faces in chat end to end (live/chat.py)."""
import copy
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from game import avatar as avt
from game import journey as jr
from game import wardrobe as wd
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from game.storage import Store
from live import faces
from live import street_data as sd
from tests.live_support import LiveCase

ROOT = Path(__file__).resolve().parents[1]
CODE_JS = (ROOT / 'public' / 'js' / 'v4' / 'face-code.js').read_text(encoding='utf-8')


def story(gender='male'):
    s = new_state()
    jr.enable_story(s, 777)
    s['journey']['gender'] = gender
    wd.migrate(s)
    validate_state(s)
    return s


def act(s, action, **p):
    return apply_action(s, None, action, p)


def code(tag='f1', **parts):
    """A face code built like the client does (face-code.js encode)."""
    f = dict(avt.DEFAULT_FACE, **parts)
    vals = [('1' if f[k] else '0') if k == 'freckles' else f[k] for k in
            ('skin', 'shape', 'age', 'hair', 'hc', 'expr', 'glasses', 'head', 'hwc', 'beard', 'freckles', 'extra', 'bg', 'shirt')]
    return '.'.join([tag, *vals, 'm', 'ao_hoodie', 'mint', 'non_la', 'vang'])


class Lists(unittest.TestCase):
    def test_the_three_lists_match(self):
        js = {k: re.findall(r"'([^']*)'", v) for k, v in re.findall(r"^\s+(\w+):\[([^\]]*)\]", CODE_JS.split('export const PARTS={')[1].split('};')[0], re.M)}
        self.assertEqual(js, {k: list(v) for k, v in avt.PARTS.items()})
        live = dict(skin=faces.SKINS, shape=faces.SHAPES, age=faces.AGES, hair=faces.HAIRS, hc=faces.HAIR_COLORS, expr=faces.EXPRS,
                    glasses=faces.GLASSES, head=faces.HEADS, hwc=faces.PALETTE, beard=faces.BEARDS, extra=faces.EXTRAS, bg=faces.BGS,
                    shirt=faces.SHIRTS)
        self.assertEqual(live, avt.PARTS)
        emojis = re.findall(r"'([^']+)'", re.search(r'export const EMOJIS=\[(.*?)\];', CODE_JS, re.S).group(1))
        self.assertEqual(tuple(emojis), avt.EMOJIS)
        self.assertEqual(faces.EMOJIS, avt.EMOJIS)
        self.assertEqual(json.loads(re.search(r'export const DEFAULT_FACE=(\{.*?\});', CODE_JS).group(1)), avt.DEFAULT_FACE)
        # the defaults of the live positions are the save's defaults; the palette is the wardrobe's
        self.assertEqual([d for _, d in faces.FIELDS[:14]],
                         [('1' if avt.DEFAULT_FACE[k] else '0') if k == 'freckles' else avt.DEFAULT_FACE[k] for k in
                          ('skin', 'shape', 'age', 'hair', 'hc', 'expr', 'glasses', 'head', 'hwc', 'beard', 'freckles', 'extra', 'bg', 'shirt')])
        self.assertEqual(set(avt.PALETTE), {c['id'] for c in wd.COLORS})
        self.assertEqual(set(faces.COLOR_IDS), set(avt.PALETTE))
        # the profile emojis of Phố nghề are all choices too (someone who picked one keeps it)
        from live.auth import AVATARS
        self.assertTrue(set(AVATARS) <= set(avt.EMOJIS))

    def test_many_combinations(self):
        self.assertGreater(avt.combinations(), 10 ** 9)


class Save(unittest.TestCase):
    def test_old_saves_have_no_block_and_validate(self):
        s = story()
        self.assertNotIn('avatar', s)
        validate_state(s)
        self.assertNotIn('avatar', migrate_state(copy.deepcopy(s)))
        self.assertNotIn('avatar', public_state(s))

    def test_save_a_face_and_an_emoji(self):
        s = story()
        s, r = act(s, 'jr_avatar', kind='face', face=dict(hair='afro', skin='s7', freckles=True, head='hijab', hwc='mint'))
        self.assertEqual(r['message'], 'Đã lưu ảnh đại diện.')
        a = s['avatar']
        self.assertEqual((a['v'], a['kind'], a['emoji']), (1, 'face', '🌸'))
        self.assertEqual(a['face'], dict(avt.DEFAULT_FACE, hair='afro', skin='s7', freckles=True, head='hijab', hwc='mint'))
        validate_state(s)
        self.assertEqual(public_state(s)['avatar'], a)
        # an emoji keeps the face for later
        s, _ = act(s, 'jr_avatar', kind='emoji', emoji='🐼')
        self.assertEqual((s['avatar']['kind'], s['avatar']['emoji'], s['avatar']['face']['hair']), ('emoji', '🐼', 'afro'))
        s, _ = act(s, 'jr_avatar', kind='face')
        self.assertEqual(s['avatar']['face']['hair'], 'afro')
        # back to the face that follows the character
        s, r = act(s, 'jr_avatar', reset=True)
        self.assertNotIn('avatar', s)
        validate_state(s)

    def test_refused(self):
        s = story()
        for p in (dict(kind='face', face=dict(hair='mohawk')), dict(kind='face', face=dict(cape='do')), dict(kind='face', face=dict(freckles='1')),
                  dict(kind='face', face=dict(skin=['s1'])), dict(kind='robot'), dict(kind='emoji', emoji='💩'), dict(kind='face', note='x'),
                  dict(reset=True, kind='face'), dict(kind='face', face='s1')):
            with self.assertRaises(GameError, msg=p):
                act(copy.deepcopy(s), 'jr_avatar', **p)

    def test_strict_validation_and_repair(self):
        s = story()
        s, _ = act(s, 'jr_avatar', kind='face', face=dict(hair='bob'))
        for breaks in (lambda a: a.update(v=2), lambda a: a.update(kind='x'), lambda a: a['face'].update(hair='mohawk'),
                       lambda a: a['face'].pop('bg'), lambda a: a.update(emoji='💩'), lambda a: a['face'].update(freckles=0)):
            bad = copy.deepcopy(s)
            breaks(bad['avatar'])
            with self.assertRaises(GameError):
                validate_state(bad)
        # a block from a newer build: what this build knows is kept, the rest takes its default
        newer = copy.deepcopy(s)
        newer['avatar'] = dict(v=2, kind='face', face=dict(hair='bob', skin='s9', wings='yes', freckles=True), emoji='🦄', extra=1)
        m = migrate_state(newer)
        self.assertEqual(m['avatar'], dict(v=1, kind='face', face=dict(avt.DEFAULT_FACE, hair='bob', freckles=True), emoji='🌸'))
        validate_state(m)
        junk = copy.deepcopy(s)
        junk['avatar'] = 'oops'
        self.assertNotIn('avatar', migrate_state(junk))

    def test_through_the_store(self):
        with tempfile.TemporaryDirectory() as td:
            store = Store(Path(td) / 'a.db')
            token, _, _ = store.session()
            store.command(token, 'req-av-0001', store.read(token)[1], None, 'jr_avatar', {'kind': 'face', 'face': {'hair': 'tet', 'age': 'gia'}})
            s, _, _ = store.read(token)
            self.assertEqual((s['avatar']['face']['hair'], s['avatar']['face']['age']), ('tet', 'gia'))
            store.close_pool()


class Code(unittest.TestCase):
    def test_canonical_and_defaults(self):
        c = code(hair='afro', freckles=True)
        self.assertEqual(faces.clean(c), c)
        # unknown ids (a newer client, or junk) take the part's default; extra parts are dropped
        self.assertEqual(faces.clean(c.replace('afro', 'mohawk')), c.replace('afro', 'ngan'))
        short = faces.clean('f1.s3')
        self.assertEqual(short.split('.')[:3], ['f1', 's3', 'tron'])
        self.assertEqual(len(short.split('.')), 20)
        self.assertEqual(faces.clean(c + '.x.y'), c)
        # an accessory that takes no colour keeps none
        self.assertEqual(faces.clean(c.replace('non_la.vang', 'pk_khong.vang')).split('.')[-2:], ['pk_khong', '0'])

    def test_wrong_shapes_and_injection(self):
        for bad in (None, '', 42, ['f1'], 'x1.s1', 'f2.s1', 'f1' + '.s1' * 30, 'e1.💩', 'e1.🐱.x', 'f1.' + 'a' * 300):
            self.assertIsNone(faces.clean(bad), bad)
        evil = faces.clean('f1.<script>.tron.lon.ngan".onload=1.cuoi.0.0.do.0.0.0.kem.tu.m.<img src=x>.mint.non_la.vang')
        self.assertNotIn('<', evil)
        self.assertNotIn('"', evil)
        self.assertTrue(all(re.fullmatch(r'[a-z0-9_]+', p) for p in evil.split('.')))
        self.assertEqual(faces.clean('e1.🐱'), 'e1.🐱')

    def test_automatic_face_keeps_a_chosen_emoji(self):
        a1 = code('a1')
        self.assertEqual(faces.clean(a1, '🌸'), a1)
        self.assertEqual(faces.clean(a1, '🐱'), '')
        self.assertEqual(faces.clean(code('f1'), '🐱'), code('f1'))   # built in the builder: shown


class Art(unittest.TestCase):
    def test_in_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'face.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        res = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual(res['failures'], [])


class ChatFaces(LiveCase):
    async def test_faces_in_chat(self):
        fa = code('f1', hair='afro', skin='s7')
        ta, sa = self.account('Mây Hồng')
        tb, sb = self.account('Gió')
        # a client of this release says its face in the hello
        a = await self.connect(ta, hello=False)
        await a.send(t='hello', v=1, fc=fa)
        a.welcome = await a.expect('welcome')
        self.assertEqual(a.welcome['me']['fc'], fa)
        # an older client: no fc in its hello, the `fc` key still tells a newer client the service knows faces
        b = await self.connect(tb)
        self.assertEqual(b.welcome['me']['fc'], '')
        await a.call('join', 'joined', ch='town')
        await b.call('join', 'joined', ch='town')
        await a.send(t='send', ch='town', text='chào cả phố', cid='c1')
        mine = await a.expect('msg', cid='c1')
        self.assertEqual(mine['fc'], fa)
        seen = await b.expect('msg')
        self.assertEqual((seen['fc'], seen['av']), (fa, '🌸'))
        await b.send(t='send', ch='town', text='chào bạn', cid='c2')
        self.assertNotIn('fc', await b.expect('msg', cid='c2'))
        # a change of clothes: everyone on Cả phố hears it, and the old line shows the face of now
        fa2 = fa.replace('ao_hoodie', 'ao_dai')
        reply = await a.call('face', 'faced', fc=fa2)
        self.assertEqual((reply['pid'], reply['fc']), (self.pid(sa), fa2))
        self.assertEqual((await b.expect('faced'))['fc'], fa2)
        h = await b.call('history', 'history', ch='town')
        self.assertEqual([m.get('fc') for m in h['msgs']], [fa2, None])
        c = await self.connect(self.account('Lá')[0])
        j = await c.call('join', 'joined', ch='town')
        self.assertEqual([m.get('fc') for m in j['msgs']], [fa2, None])
        # kept in chat_faces: a reconnect without fc (an older tab) keeps it
        await a.close()
        a2 = await self.connect(ta)
        self.assertEqual(a2.welcome['me']['fc'], fa2)
        # refused shapes; '' goes back to the emoji
        e = await a2.call('face', 'error', fc='<b>hi</b>')
        self.assertEqual(e['code'], 'bad')
        self.assertEqual((await a2.call('face', 'faced', fc=''))['fc'], '')
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT code FROM chat_faces WHERE pid=?', (self.pid(sa),)).fetchone())

    async def test_friends_and_peers_wear_their_faces(self):
        fa = code('f1', hair='bim')
        ta, sa = self.account('Mây')
        tb, sb = self.account('Gió')
        self.befriend(sa, sb)
        a = await self.connect(ta, hello=False)
        await a.send(t='hello', v=1, fc=fa)
        await a.expect('welcome')
        b = await self.connect(tb)
        self.assertEqual([f.get('fc') for f in b.welcome['friends']], [fa])
        await b.send(t='send', to=self.pid(sa), text='hi', cid='d1')
        await b.expect('msg', cid='d1')
        st = await b.call('sync', 'state')
        peer = [c['peer'] for c in st['chans'] if c['kind'] == 'dm'][0]
        self.assertEqual(peer['fc'], fa)
        # a friend online hears a change
        await a.call('face', 'faced', fc='e1.🐼')
        self.assertEqual((await b.expect('faced'))['fc'], 'e1.🐼')

    async def test_automatic_face_of_an_emoji_profile(self):
        ta, sa = self.account('Mây')
        with self.store.connect() as db:
            db.execute("INSERT INTO profiles(pid, sid, avatar, created, updated, seen) VALUES(?, ?, '🐱', 0, 0, 0)", (self.pid(sa), sa))
        a = await self.connect(ta, hello=False)
        await a.send(t='hello', v=1, fc=code('a1'))
        w = await a.expect('welcome')
        self.assertEqual((w['me']['av'], w['me']['fc']), ('🐱', ''))
        # built on purpose: shown
        self.assertEqual((await a.call('face', 'faced', fc=code('f1')))['fc'], code('f1'))

