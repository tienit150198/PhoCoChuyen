"""🎁 Quà mừng mở server (game/journey.py GIFTS): claim once before the deadline, the public
offer, the optional save key, the stored round trip and the admin count. The browser card's
waiting rules are in tests/gift.mjs (run with node when it is installed)."""
import copy
import datetime
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import admin_stats as st
from game import journey as jr
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from game.storage import Store

ROOT = Path(__file__).resolve().parents[1]
GID = 'open2026'
VN = datetime.timezone(datetime.timedelta(hours=7))
BEFORE = datetime.datetime(2026, 10, 1, 9, 0, tzinfo=VN).timestamp()
LAST_SECOND = datetime.datetime(2026, 10, 7, 23, 59, 59, 500000, tzinfo=VN).timestamp()
AFTER = datetime.datetime(2026, 10, 8, 0, 0, 0, tzinfo=VN).timestamp()


def at(ts):
    return mock.patch.object(jr, '_clock', lambda: ts)


def story_state():
    s = new_state()
    jr.enable_story(s, 4242)
    s['journey']['gender'] = 'female'
    validate_state(s)
    return s


def claim(s, gid=GID, **extra):
    return apply_action(s, None, 'jr_gift_claim', dict(id=gid, **extra))


class GiftClaim(unittest.TestCase):
    def test_the_gift_is_150_coins_until_the_end_of_7_october_vietnam_time(self):
        g = jr.GIFTS[GID]
        self.assertEqual(g['amount'], 150)
        self.assertEqual(g['until'].isoformat(), '2026-10-07T23:59:59+07:00')

    def test_claim_adds_150_to_the_wallet_once(self):
        with at(BEFORE):
            s = story_state()
            before = s['journey']['wallet']
            s, r = claim(s)
            self.assertEqual(s['journey']['wallet'], before + 150)
            self.assertEqual(s['journey']['gifts'], [GID])
            self.assertEqual(r['message'], '🎁 Đã nhận 150 xu quà mừng mở server!')
            row = s['journey']['history'][-1]
            self.assertEqual((row['kind'], row['amount'], row['label']), ('gift', 150, 'Quà mừng mở server'))
            validate_state(s)
            # A second claim is refused kindly and changes nothing.
            with self.assertRaises(GameError) as err:
                claim(s)
            self.assertEqual(err.exception.code, 'gift_claimed')
            self.assertIn('đã nhận', str(err.exception))
            self.assertEqual(s['journey']['wallet'], before + 150)

    def test_works_outside_the_story_too(self):
        with at(BEFORE):
            s = new_state()   # tools and tests: no story, the wallet is still there
            w = s['journey']['wallet']
            s, _ = claim(s)
            self.assertEqual(s['journey']['wallet'], w + 150)

    def test_after_the_deadline_no_offer_and_no_claim(self):
        s = story_state()
        with at(LAST_SECOND):
            self.assertIsNotNone(public_state(s)['journey']['gift'])
            ok, _ = claim(copy.deepcopy(s))
            self.assertEqual(ok['journey']['gifts'], [GID])
        with at(AFTER):
            self.assertIsNone(public_state(s)['journey']['gift'])
            with self.assertRaises(GameError) as err:
                claim(s)
            self.assertEqual(err.exception.code, 'gift_expired')
            self.assertNotIn('gifts', s['journey'])
            # A claim made in time stays a harmless record afterwards.
            validate_state(ok)
            self.assertIsNone(public_state(ok)['journey']['gift'])
            ok, _ = apply_action(ok, None, 'jr_equip', {'title': None})
            self.assertEqual(ok['journey']['gifts'], [GID])

    def test_bad_requests_are_refused(self):
        with at(BEFORE):
            s = story_state()
            for payload in ({}, {'id': 'nope'}, {'id': ['open2026']}, {'id': 7}, {'id': GID, 'amount': 9999}):
                with self.subTest(payload=payload), self.assertRaises(GameError):
                    apply_action(s, None, 'jr_gift_claim', payload)
            self.assertNotIn('gifts', s['journey'])


class GiftSave(unittest.TestCase):
    def test_old_save_without_the_key_validates_and_gets_the_offer(self):
        s = story_state()
        self.assertNotIn('gifts', s['journey'])   # new saves do not carry the key either
        old = copy.deepcopy(s)
        old.pop('check', None)
        validate_state(old)
        m = migrate_state(old)
        validate_state(m)
        self.assertNotIn('gifts', m['journey'])
        with at(BEFORE):
            self.assertEqual(public_state(m)['journey']['gift'],
                             dict(id=GID, amount=150, label='Quà mừng mở server', until='2026-10-07T23:59:59+07:00', until_text='07/10'))

    def test_public_flag_before_and_after_the_claim(self):
        with at(BEFORE):
            s = story_state()
            self.assertEqual(public_state(s)['journey']['gift']['id'], GID)
            s, _ = claim(s)
            self.assertIsNone(public_state(s)['journey']['gift'])
            self.assertNotIn('gifts', public_state(s)['journey'])   # the raw list stays server side

    def test_strict_validation_of_the_claimed_list(self):
        for bad in ([GID, GID], ['other'], 'open2026', [7], None, {GID: 1}, [[GID]]):
            s = story_state()
            s['journey']['gifts'] = bad
            with self.subTest(bad=bad), self.assertRaises(GameError):
                validate_state(s)
        s = story_state()
        s['journey']['gifts'] = []
        validate_state(s)

    def test_stored_round_trip_and_replay(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp, at(BEFORE):
            store = Store(Path(tmp) / 'gift.db', story=True)
            try:
                token, _, _ = store.session()
                s, rev, _ = store.read(token)
                r = store.command(token, 'gift-profile-1', rev, None, 'jr_profile', {'name': 'Quà', 'gender': 'male'})
                self.assertEqual(r['state']['journey']['gift']['id'], GID)
                wallet = r['state']['journey']['wallet']
                r = store.command(token, 'gift-claim-1', r['revision'], None, 'jr_gift_claim', {'id': GID})
                self.assertEqual(r['state']['journey']['wallet'], wallet + 150)
                self.assertIsNone(r['state']['journey']['gift'])
                rev = r['revision']
                # The same request again (a retried tap) is a replay: nothing moves.
                again = store.command(token, 'gift-claim-1', rev - 1, None, 'jr_gift_claim', {'id': GID})
                self.assertTrue(again['replayed'])
                self.assertEqual((again['revision'], again['state']['journey']['wallet']), (rev, wallet + 150))
                # A new request is refused.
                with self.assertRaises(GameError):
                    store.command(token, 'gift-claim-2', rev, None, 'jr_gift_claim', {'id': GID})
                reopened = Store(Path(tmp) / 'gift.db', story=True)
                try:
                    raw, rev2, _ = reopened.read(token)
                    self.assertEqual(rev2, rev)
                    self.assertEqual(raw['journey']['gifts'], [GID])
                    self.assertEqual(raw['journey']['wallet'], wallet + 150)
                    validate_state(migrate_state(raw))
                finally:
                    reopened.close_pool()
            finally:
                store.close_pool()


class GiftAdminCount(unittest.TestCase):
    def test_claims_are_counted_in_memory(self):
        before = st.gift_usage()['total'].get(GID, 0)
        st.count_gift(GID)
        st.count_gift(GID)
        use = st.gift_usage()
        self.assertEqual(use['total'][GID], before + 2)
        self.assertEqual(use['days'][-1]['day'], st._today())
        self.assertIn('gifts', st.ai_usage())


class BrowserRules(unittest.TestCase):
    def test_client_rules(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'gift.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
