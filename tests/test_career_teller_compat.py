"""🏦 Rollback of the bank career (game/careers/teller.py) to 2.4.66 (a808cb79, live when this was written).

* A save that never opened the bank keeps no record of it (engine.DORMANT): 2.4.66 loads it as it is stored.
* A save that played the bank (story mode: hired through the job application, the lessons, the exam and its badge, a full
  day at the counter with the float and the handover, a desk surprise and its lasting mark, Bà Lựu's savings arc, the
  new certificate earned and worn, the bank as the current workplace, a shift left open with a customer half served)
  goes back through scripts/strip_new_careers.py strip --careers teller: 2.4.66 then validates, migrates, renders it and
  plays a whole day at another workplace; nothing of the player's money moves. `restore` on this build puts the bank
  back byte for byte onto the save as 2.4.66 left it.
"""
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

from game import journey as jr
from game.careers import PLUGINS
from game.engine import apply_action, dormant_out, migrate_state, public_state, validate_state

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'a808cb79'   # 2.4.66
sys.path.insert(0, str(ROOT / 'scripts'))
import strip_new_careers as SNC   # noqa: E402

T = PLUGINS.get('teller')
if T is not None:
    from game.careers import teller_content as TC

PROG = '''import json,sys
import game
from game.engine import validate_state,migrate_state,public_state,apply_action,wake,CAREERS
out=[]
for s in json.load(sys.stdin):
    wake(s)   # what 2.4.66's Store.parse_state does on every read: its own dormant careers come back
    validate_state(s);s=migrate_state(s);validate_state(s);public_state(s)
    money=(s['journey']['wallet'],s['journey'].get('bank'))
    s,_=apply_action(s,'milk_tea','select_career',{})
    s,_=apply_action(s,'milk_tea','start_day',{})
    s,_=apply_action(s,'milk_tea','end_day',{})
    validate_state(s);public_state(s)
    out.append(dict(version=game.__version__,teller='teller' in CAREERS,careers=sorted(s['careers']),money=money,state=s))
print(json.dumps(out,ensure_ascii=False))
'''


def act(s, where, action, **p):
    s, r = apply_action(s, where, action, p)
    return s, r


def tdata(s):
    return s['careers']['teller']['ext']['data']


def answer(st, want):
    return T.tray_answer(want) if st['type'] == 'tray' else want


def chapter3(s):
    """The story at chapter 3 (where the bank opens), as chapters 1 and 2 finished leave it."""
    j = s['journey']
    j['done'], j['chapter'] = [1, 2], 3
    for n in (2, 3):
        jr._unlock_chapter(j, n)
    validate_state(s)


def played_save(leave_open=False):
    from game.engine import new_state
    s = new_state()
    jr.enable_story(s, 4242)
    s, _ = act(s, None, 'jr_profile', name='Lan', gender='female')
    chapter3(s)
    s, _ = act(s, 'teller', 'select_career')
    s, _ = act(s, 'teller', 'job_apply', posting='teller-benchu')
    s, _ = act(s, 'teller', 'job_cv', strengths=['careful', 'numbers'], claims=['fresh'])
    from game.employment import question
    for qid in T.SPEC['employment']['postings'][0]['questions']:
        q = T.SPEC['employment']['questions'].get(qid) or question('teller', qid)
        s, _ = act(s, 'teller', 'job_answer', question=qid, option=max(q['options'], key=lambda o: o['score'])['id'])
    s, _ = act(s, 'teller', 'job_accept', confirm=True)
    s, _ = act(s, 'teller', 'tl_intro')
    for les in TC.LESSONS:
        s, _ = act(s, 'teller', 'tl_learn', lesson=les['id'], answer=les['answer'])
    s, _ = act(s, 'teller', 'tl_exam', start=True)
    ex = tdata(s)['exam']
    parts, key = T.exam_parts(ex['attempt'], ex['day'])
    for st in parts:
        s, _ = act(s, 'teller', 'tl_exam', step=st['id'], value=answer(st, key[st['id']]))
    for day in range(2):
        s, _ = act(s, 'teller', 'start_day')
        c = s['careers']['teller']
        steps, k = T.shift_steps(c['day'], 'open')
        for st in steps:
            s, _ = act(s, 'teller', 'tl_shift', part='open', step=st['id'], value=k[st['id']])
        last = leave_open and day == 1
        for t in [t for t in s['careers']['teller']['tasks'] if t['status'] == 'new']:
            s, _ = act(s, 'teller', 'ask', task=t['id'])
            for _ in range(20):
                d = tdata(s)
                if d['desk']['ev']:
                    x = next(x for x in TC.DESK if x['id'] == d['desk']['ev']['script'])
                    s, _ = act(s, 'teller', 'tl_desk', option=next(o['id'] for o in x['options'] if o.get('effects', {}).get('mark')) if any(
                        o.get('effects', {}).get('mark') for o in x['options']) else x['options'][0]['id'])
                tt = next(y for y in s['careers']['teller']['tasks'] if y['id'] == t['id'])
                if tt['status'] == 'completed':
                    break
                _, stp, key2 = T._active(tt)
                st = stp[tt['at']]
                s, _ = act(s, 'teller', 'tl_step', task=t['id'], step=st['id'], value=answer(st, key2[st['id']]))
                if last and tt['at'] >= 0 and st is stp[0]:
                    return finish(s)   # a customer half served, the shift open
        c = s['careers']['teller']
        steps, k = T.shift_steps(c['day'], 'close', tdata(s)['today']['mgr'])
        for st in steps:
            s, _ = act(s, 'teller', 'tl_shift', part='close', step=st['id'], value=k[st['id']])
        s, _ = act(s, 'teller', 'end_day')
    return finish(s)


def finish(s):
    """The new certificate earned and worn (the paper itself is certificates.py's own business)."""
    j = s['journey']
    j['certificates']['teller_service'] = dict(score=100, best=100, earned_day=j['life_day'], attempts=1)
    j['worn'] = list(j.get('worn') or []) + ['cert:teller_service']
    validate_state(s)
    return json.loads(json.dumps(s))


def names(o, path=''):
    """Every place that still names the bank (a key or a value starting with 'teller', not the certificate's id)."""
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(k, str) and k.startswith('teller') and k != 'teller_service':
                yield f'{path}/{k}'
            yield from names(v, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from names(v, f'{path}[{i}]')
    elif isinstance(o, str) and o.startswith('teller') and o != 'teller_service':
        yield path


@unittest.skipUnless(T, 'teller filtered out by MNL_CAREERS')
class RollbackTo2466(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='mnl-2466-')
        try:
            data = subprocess.run(['git', 'archive', RELEASE, 'game', 'reference'], cwd=ROOT, capture_output=True, timeout=120,
                                  check=True).stdout
        except (OSError, subprocess.SubprocessError):
            cls.old = None
            return
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(cls.tmp, filter='data')
        cls.old = Path(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def run_old(self, saves):
        if not self.old:
            self.skipTest(f'no git tree with {RELEASE}')
        env = {k: v for k, v in os.environ.items() if k != 'MNL_CAREERS'}
        env.update(PYTHONPATH=str(self.old), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', PROG], input=json.dumps(saves, ensure_ascii=False), capture_output=True,
                             text=True, cwd=self.old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout.strip().splitlines()[-1])

    def test_an_untouched_bank_reads_on_2_4_66_as_stored(self):
        from game.engine import new_state
        s = new_state()
        jr.enable_story(s, 99)
        s, _ = act(s, None, 'jr_profile', name='Lan', gender='female')
        chapter3(s)
        stored = json.loads(json.dumps(dormant_out(s)))
        self.assertNotIn('teller', stored['careers'])
        got = self.run_old([stored])[0]
        self.assertEqual(got['version'], '2.4.66')
        self.assertFalse(got['teller'])

    def test_a_played_bank_goes_back_with_the_strip_and_comes_back_with_restore(self):
        saves = [played_save(), played_save(leave_open=True)]
        for s in saves:
            d = tdata(s)
            self.assertIn(d['stage'], ('training', 'teller'))
            self.assertIn('teller', s['journey']['unlocked'])
        full = saves[0]
        self.assertTrue(tdata(full)['badge'])
        self.assertGreaterEqual(tdata(full)['stats']['jobs'], 3)
        self.assertTrue(tdata(full)['desk']['log'])
        self.assertEqual(saves[1]['current'], 'teller')
        self.assertTrue(saves[1]['careers']['teller']['open'])
        stripped, removed = [], []
        for s in saves:
            new, rem = SNC.strip(s, ['teller'])
            self.assertIn('teller', rem)
            self.assertNotIn('teller', new['careers'])
            self.assertNotIn('teller_service', new['journey']['certificates'])
            self.assertNotIn('cert:teller_service', new['journey']['worn'])
            self.assertEqual((new['journey']['wallet'], new['journey'].get('bank')), (s['journey']['wallet'], s['journey'].get('bank')))
            # Only a life card waiting at the bank still names it (2.4.66 reads an unknown workplace there as none).
            self.assertEqual([p for p in names(new) if p != '/journey/life/pending/career'], [])
            stripped.append(new)
            removed.append(rem)
        got = self.run_old(stripped)
        for s, g, rem in zip(saves, got, removed):
            self.assertEqual(g['version'], '2.4.66')
            self.assertFalse(g['teller'])
            self.assertEqual(g['money'][0], s['journey']['wallet'])   # nothing moved on the way out
            back, problems = SNC.restore(g['state'], rem)
            self.assertEqual(problems, [])
            m = migrate_state(back)
            validate_state(m)
            public_state(m)
            self.assertEqual(json.dumps(m['careers']['teller'], sort_keys=True, ensure_ascii=False),
                             json.dumps(s['careers']['teller'], sort_keys=True, ensure_ascii=False))
            self.assertEqual(m['journey']['certificates']['teller_service'], s['journey']['certificates']['teller_service'])
            self.assertIn('cert:teller_service', m['journey']['worn'])
            self.assertIn('teller', m['journey']['unlocked'])
            # …and the bank plays on after the round trip.
            m, _ = act(m, 'teller', 'select_career')
            validate_state(m)


if __name__ == '__main__':
    unittest.main()
