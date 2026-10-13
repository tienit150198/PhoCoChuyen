"""Unlimited private blessing cards, bounded saves and durable archive receipts."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from game import archive as ar
from game import chua as cg
from game import needs as nd
from game.engine import GameError, validate_state
from tests.test_chua import story, do, spirit, feast
from game.storage import Store


class Cards(unittest.TestCase):
    def test_meal_repeats_until_full_on_feast_day(self):
        s = story(life_day=feast())
        needs = nd.ensure(s)
        needs['full'] = 0
        for _ in range(3):
            s, _ = do(s, act='com')
        self.assertEqual(s['journey']['chua']['did'], ['com'])
        with self.assertRaises(GameError) as error:
            do(s, act='com')
        self.assertEqual(error.exception.code, 'too_full')

    def test_free_actions_all_repeat_without_quotas(self):
        s = story()
        actions = [dict(act=a) for a in ('huong', 'chuong', 'ngoi', 'quet')]
        actions += [dict(act='nguyen', wish='nha'), dict(act='khan', who='ca_nha', what='may_man'),
                    dict(act='tung', beat=12)]
        for _ in range(2):
            for payload in actions:
                s, _ = do(s, **payload)
        self.assertEqual(len(s['journey']['chua']['did']), 7)
        self.assertEqual(s['journey']['chua']['n'], 14)
        self.assertEqual(s['journey']['wallet'], 40)
        validate_state(s)

    def test_public_gain_is_actual_at_spirit_capacity(self):
        for value in (99, 100):
            view = cg.public(story(value))
            self.assertTrue(all(a['spirit'] == 100-value for a in view['acts'] + view['more']))

    def test_composed_card_survives_rollover_and_public_is_read_only(self):
        s, result = do(story(), act='nguyen', recipient='cha_me', blessing='may_man',
                       name='  Ba Mẹ  ', message='  Mong cả nhà vui khỏe.  ')
        card = s['journey']['chua']['cards'][0]
        self.assertEqual(card['name'], 'Ba Mẹ')
        self.assertEqual(card['message'], 'Mong cả nhà vui khỏe.')
        self.assertIn('may mắn', card['text'])
        self.assertIn(card['text'], result['message'])
        self.assertEqual(spirit(s), 53)
        s['journey']['life_day'] += 1
        before = copy.deepcopy(s)
        view = cg.public(s)
        self.assertEqual(s, before)
        self.assertEqual(view['cards'], [card])
        view['cards'][0]['message'] = 'client mutation'
        self.assertEqual(s, before)
        s, _ = do(s, act='huong')
        self.assertEqual(s['journey']['chua']['cards'], [card])
        self.assertEqual(s['journey']['chua']['did'], ['huong'])
        validate_state(s)

    def test_presets_and_hundred_cards_archive_without_counter_id_collisions(self):
        s = story(100)
        s['journey']['chua'] = dict(v=1, day=1, did=[], n=10**6)
        made = []
        with ar.collect() as box:
            for _ in range(100):
                s, result = do(s, act='nguyen', wish='nha')
                made.append(s['journey']['chua']['cards'][-1])
                self.assertNotIn('tinh thần +', result['message'])
        self.assertEqual(len({c['id'] for c in made}), 100)
        self.assertEqual(len(s['journey']['chua']['cards']), 40)
        self.assertEqual(s['journey']['chua']['n'], 10**6)
        self.assertEqual(box.rows, [(ar.JOURNEY, 'chua.cards', c) for c in made[:60]])
        self.assertEqual(ar.in_save(s, ar.JOURNEY, 'chua.cards'), made[60:])
        self.assertIsNone(ar.in_save(s, 'grocery', 'chua.cards'))
        self.assertEqual(made[0]['text'], cg.WISHES['nha'])
        validate_state(s)

    def test_luck_is_available_for_every_living_recipient(self):
        for who in cg.KHAN_WHO:
            if who != 'ong_ba':
                s, _ = do(story(), act='khan', who=who, what='may_man')
                s, _ = do(s, act='nguyen', recipient=who, blessing='may_man')
                self.assertEqual(spirit(s), 56)
        self.assertEqual(cg.KHAN_WHO['ong_ba'][1], ('yen_nghi',))

    def test_invalid_payloads_are_atomic_and_typed(self):
        base = dict(act='nguyen', recipient='ca_nha', blessing='khoe')
        for patch in (dict(recipient=[]), dict(blessing={}), dict(recipient='ghost'), dict(blessing='yen_nghi'),
                      dict(name='x'*41), dict(message='x'*141), dict(name=1), dict(message=None),
                      dict(name='<b>mẹ</b>'), dict(message='a\x00'*141), dict(wish='nha'), dict(beat=2)):
            s = story()
            before = copy.deepcopy(s)
            with self.assertRaises(GameError, msg=patch):
                do(s, **(base | patch))
            self.assertEqual(s, before)
        for payload in (dict(act=[]), dict(act='nguyen', wish=[]), dict(act='khan', who=[], what='khoe')):
            with self.assertRaises(GameError):
                do(story(), **payload)

    def test_old_save_and_full_daily_history_are_valid(self):
        s = story()
        self.assertEqual(cg.public(s)['cards'], [])
        self.assertIn('card_choices', cg.public(s))
        self.assertNotIn('chua', s['journey'])
        s['journey']['chua'] = dict(v=1, day=1, did=list(cg.ACTS), n=len(cg.ACTS))
        validate_state(s)
        s, _ = do(s, act='huong')
        self.assertEqual(s['journey']['chua']['did'], list(cg.ACTS))

    def test_strict_card_rows(self):
        s, _ = do(story(), act='nguyen', recipient='ca_nha', blessing='khoe')
        card = s['journey']['chua']['cards'][0]
        for patch in (dict(day=2), dict(day=True), dict(id=''), dict(recipient=[]), dict(blessing='yen_nghi'),
                      dict(name='x'*41), dict(message='x'*141), dict(text='forged'), dict(extra=True)):
            bad = copy.deepcopy(s)
            bad['journey']['chua']['cards'] = [card | patch]
            with self.assertRaises(GameError, msg=patch):
                validate_state(bad)
        for rows in ('bad', [card, card], [dict(card, id=str(i)) for i in range(41)]):
            bad = copy.deepcopy(s)
            bad['journey']['chua']['cards'] = rows
            with self.assertRaises(GameError):
                validate_state(bad)


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL') and not os.environ.get('DATABASE_URL'),
                     'requires isolated TEST_DATABASE_URL without DATABASE_URL')
class StoredCards(unittest.TestCase):
    def test_store_replay_and_archive_keep_each_card_once_and_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'cards.db')
            self.addCleanup(store.close_pool)
            token, _, _ = store.session()
            other, _, _ = store.session()
            with store.connect() as db:
                db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(story()), store.key(token)))
            revision, ids = 0, []
            payload = dict(act='nguyen', recipient='ca_nha', blessing='may_man', message='Bình an nhé.')
            for i in range(43):
                rid = f'temple-card-{i:04d}'
                result = store.command(token, rid, revision, None, 'jr_chua_do', payload)
                replay = store.command(token, rid, revision, None, 'jr_chua_do', payload)
                self.assertTrue(replay['replayed'])
                self.assertFalse(result['replayed'])
                self.assertEqual(replay['revision'], result['revision'])
                self.assertEqual(replay['result'], result['result'])
                self.assertEqual(replay['state']['chua'], result['state']['chua'])
                revision = result['revision']
                state, _, _ = store.read(token)
                ids.append(state['journey']['chua']['cards'][-1]['id'])
            self.assertEqual(len(set(ids)), 43)
            state, _, _ = store.read(token)
            self.assertEqual(state['journey']['chua']['n'], 43)
            self.assertEqual(len(state['journey']['chua']['cards']), 40)
            page = store.archive_page(token, ar.JOURNEY, 'chua.cards', limit=100)
            self.assertEqual(page['total'], 43)
            self.assertEqual([r['row']['id'] for r in reversed(page['rows'])], ids)
            self.assertEqual(store.archive_page(other, ar.JOURNEY, 'chua.cards')['total'], 0)
            archived = [r for r in store.archive_export(token) if r['kind'] == 'chua.cards']
            self.assertEqual(len(archived), 3)
            before = copy.deepcopy(state)
            with self.assertRaises(GameError):
                store.command(token, 'temple-invalid', revision, None, 'jr_chua_do', payload | {'name': 'x'*41})
            state, _, _ = store.read(token)
            self.assertEqual(state['journey']['chua'], before['journey']['chua'])
            self.assertEqual(len([r for r in store.archive_export(token) if r['kind'] == 'chua.cards']), 3)

