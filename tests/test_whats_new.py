"""'Có gì mới' (what's new): the release-notes data, the seen version in the save,
and the browser rules (tests/whats_new.mjs, run with node when it is installed)."""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from game import __version__
from game import whats_new as wn
from game.engine import GameError, apply_action, migrate_state, new_state, validate_state
from game.storage import Store

ROOT = Path(__file__).resolve().parents[1]


def entry(version, date='2026-09-01', n=4, **extra):
    return dict(version=version, date=date, items=tuple(dict(emoji='✨', text=f'Điều mới số {i + 1} ở phố.') for i in range(n)), **extra)


class EntriesData(unittest.TestCase):
    def test_entries_validate_and_run_newest_first(self):
        wn.validate()
        versions = [wn.parse(e['version']) for e in wn.ENTRIES]
        self.assertEqual(versions, sorted(versions, reverse=True))
        self.assertEqual(len(set(versions)), len(versions))
        dates = [e['date'] for e in wn.ENTRIES]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertEqual(wn.LATEST, wn.ENTRIES[0]['version'])
        for e in wn.ENTRIES:
            self.assertTrue(1 <= len(e['items']) <= wn.MAX_ITEMS, e['version'])
            for it in e['items']:
                self.assertTrue(it['emoji'] and it['text'], it)

    def test_notes_never_ahead_of_the_game(self):
        # Quiet releases are fine (the owner decides what is announced); notes for a version not shipped are not.
        self.assertLessEqual(wn.parse(wn.LATEST), wn.parse(__version__),
                             f'the "Có gì mới" entry {wn.LATEST} is newer than game.__version__ {__version__}')

    def test_browser_copy_is_in_sync(self):
        js = (ROOT / 'public' / 'js' / 'v4' / 'whatsnew-data.js').read_text(encoding='utf-8')
        self.assertEqual(js, wn.render_js(), 'run: python -m game.whats_new')
        self.assertEqual(json.loads(js.split('export default ', 1)[1].rstrip().rstrip(';')), wn.public())

    def test_validation_rejects_bad_entries(self):
        good = (entry('1.1.0', '2026-10-02'), entry('1.0.0', '2026-10-01'))
        wn.validate(good)
        bad = {
            'older first': (entry('1.0.0', '2026-10-01'), entry('1.1.0', '2026-10-02')),
            'repeated version': (entry('1.0.0'), entry('1.0.0')),
            'date after a newer entry': (entry('1.1.0', '2026-10-01'), entry('1.0.0', '2026-10-02')),
            'no items': (entry('1.0.0', n=0),),
            'too many items': (entry('1.0.0', n=wn.MAX_ITEMS + 1),),
            'missing date': (dict(version='1.0.0', items=entry('1.0.0')['items']),),
            'unknown field': (entry('1.0.0', note='x'),),
            'bad version': (entry('v1'),),
            'bad date': (entry('1.0.0', date='01/10/2026'),),
            'empty': (),
        }
        for why, entries in bad.items():
            with self.subTest(why), self.assertRaises(ValueError):
                wn.validate(entries)
        for item in (dict(text='Chỉ có chữ thôi nhé.'), dict(emoji='A', text='Chữ cái không phải emoji.'),
                     dict(emoji='✨', text='<b>đậm</b> không được'), dict(emoji='✨', text='ngắn'),
                     dict(emoji='✨', text='x' * 200), dict(emoji='✨', text='Hai\ndòng thì không được'),
                     dict(emoji='✨', text='Thử một nút lạ ở đây.', go='leaderboard'),
                     dict(emoji='✨', text='Thử một nút lạ ở đây.', go=dict(action='a b')),
                     dict(emoji='✨', text='Thử một nút lạ ở đây.', go=dict(action='rank', data=dict(tab=3)))):
            with self.subTest(item=item), self.assertRaises(ValueError):
                wn.validate((dict(version='1.0.0', date='2026-10-01', items=(item,)),))
        wn.validate((dict(version='1.0.0', date='2026-10-01', items=(dict(emoji='🏆', text='Bảng xếp hạng mới.', go=dict(action='rank', data=dict(tab='career'))),)),))


class SeenVersionInTheSave(unittest.TestCase):
    def test_a_new_save_starts_unread(self):
        # A brand-new save has read nothing yet (also after "Bắt đầu lại"); naming it marks them read (below).
        self.assertEqual(new_state()['settings']['whatsNewSeen'], '')
        s, _ = apply_action(new_state(), None, 'reset_all', {'confirm': 'BAT DAU LAI'})
        self.assertEqual(s['settings']['whatsNewSeen'], '')

    def test_naming_a_new_story_save_marks_the_notes_read(self):
        # Release notes are for returning players: a brand-new player never gets them.
        from game import journey as jr
        s = new_state()
        jr.enable_story(s, 3)
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan'})   # no look yet: still unnamed
        self.assertEqual(s['settings']['whatsNewSeen'], '')
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan', 'gender': 'female'})
        self.assertEqual(s['settings']['whatsNewSeen'], wn.LATEST)
        validate_state(copy.deepcopy(s))
        # A player past the intro who renames keeps what they had read.
        s['journey']['intro'] = True
        s['settings']['whatsNewSeen'] = '0.9.0'
        s, _ = apply_action(s, None, 'jr_profile', {'name': 'Lan Anh', 'gender': 'female'})
        self.assertEqual(s['settings']['whatsNewSeen'], '0.9.0')
        # No story (sandbox): untouched.
        s, _ = apply_action(new_state(), None, 'jr_profile', {'name': 'Lan', 'gender': 'male'})
        self.assertEqual(s['settings']['whatsNewSeen'], '')

    def test_seen_version_is_stored_and_never_goes_back(self):
        s = new_state()
        s['settings']['whatsNewSeen'] = '0.5.0'
        s, _ = apply_action(s, None, 'settings', {'whatsNewSeen': '0.9.0'})
        self.assertEqual(s['settings']['whatsNewSeen'], '0.9.0')
        s, _ = apply_action(s, None, 'settings', {'whatsNewSeen': '0.5.0'})  # a tab on an older release
        self.assertEqual(s['settings']['whatsNewSeen'], '0.9.0')
        s, _ = apply_action(s, None, 'settings', {'whatsNewSeen': wn.LATEST})
        self.assertEqual(s['settings']['whatsNewSeen'], wn.LATEST)
        validate_state(copy.deepcopy(s))

    def test_junk_is_rejected(self):
        for bad in ('abc', '1', '1.2.3.4', '0.9.1 ', ' 0.9.1', '0.9.1<script>', '0..1', '1234.0.0', 'x' * 40, 7, 0.9, None, True, ['0.9.1'], {}):
            with self.subTest(bad=bad), self.assertRaises(GameError):
                apply_action(new_state(), None, 'settings', {'whatsNewSeen': bad})
        s = new_state()
        s['settings']['whatsNewSeen'] = '<img src=x>'
        with self.assertRaises(GameError):
            validate_state(s)

    def test_old_saves_load_and_see_the_notes(self):
        s = new_state()
        del s['settings']['whatsNewSeen']
        s.pop('check', None)
        validate_state(copy.deepcopy(s))  # a save without the key is still valid
        m = migrate_state(s)
        self.assertEqual(m['settings']['whatsNewSeen'], '')  # a returning player: the card is due
        validate_state(m)
        m, _ = apply_action(m, None, 'settings', {'whatsNewSeen': wn.LATEST})
        self.assertEqual(m['settings']['whatsNewSeen'], wn.LATEST)
        # A save stamped by an older build goes through the migration too.
        old = new_state()
        del old['settings']['whatsNewSeen']
        old['check'] = dict(build='older-build')
        self.assertEqual(migrate_state(old)['settings']['whatsNewSeen'], '')

    def test_seen_version_persists_in_the_stored_save(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            store = Store(Path(tmp) / 'game.db')
            try:
                token, _, _ = store.session()
                s, rev, _ = store.read(token)
                self.assertEqual(s['settings']['whatsNewSeen'], '')  # a new session is a new player: the notes are due
                # An old backup (read the notes of 0.5.0 only) comes back through import.
                old = copy.deepcopy(s)
                old['settings']['whatsNewSeen'] = '0.5.0'
                old.pop('check', None)
                r = store.command(token, 'wn-import-01', rev, None, 'import_save', {'save': {'format': 'mot-ngay-lam-nghe/save-v1', 'state': old}})
                self.assertEqual(r['state']['settings']['whatsNewSeen'], '0.5.0')
                r = store.command(token, 'wn-seen-01', r['revision'], None, 'settings', {'whatsNewSeen': wn.LATEST})
                again = Store(Path(tmp) / 'game.db')
                try:
                    self.assertEqual(again.read(token)[0]['settings']['whatsNewSeen'], wn.LATEST)
                finally:
                    again.close_pool()
            finally:
                store.close_pool()


class BrowserRules(unittest.TestCase):
    def test_client_rules(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'whats_new.mjs')], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


if __name__ == '__main__':
    unittest.main()
