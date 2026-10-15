"""Owner 14/10 ("chỗ nghề khi nào coi là 1 ngày để lên"): a real day counts the moment it qualifies.

Mở rộng nghề and Chuyên môn nghề read "Ngày thực đạt chuẩn": a calendar day (0h–24h VN) with ≥3 clean jobs and ≥80% clean.
It used to be credited at 0h; it now counts as soon as it qualifies, once per calendar day, and a later error that
day does not take it back. The mark is an optional career key (career_scale.CREDIT) that 2.4.8 accepts and ignores.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from game import engine as e
from game import career_scale as scale
from game import career_specialism as sp
from game import career_mastery as mastery
from game import promotion as pm

NOW = 1791936000          # 2026-10-14 07:00 VN
DAY = 86400
ROOT = Path(__file__).resolve().parents[1]
BASE_REF = os.environ.get('MNL_DAYGATE_BASE', 'rel-2.4.8')


def fresh(cid='grocery'):
    from game import employment
    s = e.new_state(); c = s['careers'][cid]
    c.update(started=True, open=True, money=500_000_000, xp=90000)
    if employment.required(cid): c['job'] = employment.hired_record(cid)
    scale.ensure(c, cid, NOW)
    return s, c


def finish(c, n, mistakes=0, now=NOW, cid='grocery'):
    task = dict(id=f'{cid}-{c["day"]:04d}-{n}', career=cid, day=c['day'], status='completed', mistakes=mistakes)
    c['tasks'].append(task); c['completed_ids'].append(task['id'])
    return scale.completed(c, cid, task, now)


def got(s, c, now=NOW):
    return scale.public(s, c, 'grocery', now)['next']['requirements'][0]['got']


def test_today_counts_the_moment_it_qualifies_and_only_once():
    s, c = fresh()
    finish(c, 0); finish(c, 1)
    assert got(s, c) == 0 and scale.CREDIT not in c
    finish(c, 2)
    assert got(s, c) == 1 and c[scale.CREDIT] == scale.quota.day(NOW)
    for n in range(3, 9): finish(c, n)           # more clean jobs the same day: still one day
    scale.accepted(c, 'grocery', NOW)            # an acceptance the same day does not add one either
    assert got(s, c) == 1
    assert c['scale']['qualified_days'] == 0, 'the stored count keeps its 2.4.8 meaning (closed days only)'
    scale.validate(c, 'grocery')
    scale.ensure(c, 'grocery', NOW + DAY)         # 0h: the day is closed once, not twice
    assert c['scale']['qualified_days'] == 1 and got(s, c, NOW + DAY) == 1
    scale.ensure(c, 'grocery', NOW + 2 * DAY)
    assert c['scale']['qualified_days'] == 1


def test_the_next_day_still_counts():
    s, c = fresh()
    for n in range(3): finish(c, n)
    c['day'] += 1
    for n in range(3, 6): finish(c, n, now=NOW + DAY)
    assert got(s, c, NOW + DAY) == 2
    scale.ensure(c, 'grocery', NOW + 2 * DAY)
    assert c['scale']['qualified_days'] == 2 and got(s, c, NOW + 2 * DAY) == 2
    scale.validate(c, 'grocery')


def test_an_error_after_the_credit_neither_removes_nor_double_counts():
    s, c = fresh()
    for n in range(3): finish(c, n)
    assert got(s, c) == 1
    finish(c, 3, mistakes=1); finish(c, 4, mistakes=1)     # 3/5 = 60%: no longer qualifies
    row = scale.public(s, c, 'grocery', NOW)['next']['requirements'][0]
    assert row['got'] == 1 and row['hint'] == 'Hôm nay: 3/5 việc sạch · đã tính ✓'
    for n in range(5, 12): finish(c, n)                     # qualifies again: still the same one day
    assert got(s, c) == 1
    scale.ensure(c, 'grocery', NOW + DAY)
    assert c['scale']['qualified_days'] == 1


def test_a_day_that_never_qualified_is_not_credited():
    s, c = fresh()
    finish(c, 0); finish(c, 1, mistakes=1); finish(c, 2); finish(c, 3, mistakes=1); finish(c, 4)
    assert got(s, c) == 0 and scale.CREDIT not in c
    scale.ensure(c, 'grocery', NOW + DAY)
    assert c['scale']['qualified_days'] == 0


def test_contract_day_counts_when_the_acceptance_lands():
    s, c = fresh()
    c['scale'].update(tier=1); c['scale']['today']['requires_contract'] = True
    from game import career_scale_resources as resources
    resources.ensure(c, 'grocery')
    for n in range(3): finish(c, n)
    assert scale.counted(c['scale'], c) == 0
    scale.accepted(c, 'grocery', NOW)
    assert scale.counted(c['scale'], c) == 1 and c[scale.CREDIT] == scale.quota.day(NOW)


def test_mo_rong_nghe_opens_on_the_second_real_day_itself():
    s, c = fresh()
    c['scale']['clean'] = 20
    for n in range(3): finish(c, n)
    c['day'] += 1
    finish(c, 3, now=NOW + DAY); finish(c, 4, now=NOW + DAY)
    nxt = scale.public(s, c, 'grocery', NOW + DAY)['next']
    assert nxt['can_buy'] is False and nxt['reason'] == 'Cần thêm 1 ngày thực đạt chuẩn.'
    assert nxt['requirements'][0]['hint'] == 'Hôm nay: 2/2 việc sạch · còn 1 việc sạch nữa là tính hôm nay'
    finish(c, 5, now=NOW + DAY)
    assert scale.public(s, c, 'grocery', NOW + DAY)['next']['can_buy'] is True
    scale.action(s, c, 'grocery', 'scale_upgrade', {'expected_tier': 0}, NOW + DAY)
    assert c['scale']['tier'] == 1
    # The day that opened the tier stays counted although tier 1 days also need an accepted contract.
    assert scale.counted(c['scale'], c) == 2
    scale.ensure(c, 'grocery', NOW + 2 * DAY)
    assert c['scale']['qualified_days'] == 2
    scale.validate(c, 'grocery')


def test_chuyen_mon_nghe_can_enrol_the_same_day_it_qualifies():
    s, c = fresh()
    c['scale']['clean'] = 20
    for n in range(3): finish(c, n)
    c['day'] += 1
    for n in range(3, 5): finish(c, n, now=NOW + DAY)
    nxt = sp.public(s, c, 'grocery', NOW + DAY)['next']
    assert nxt['can_enrol'] is False and nxt['reason'] == 'Cần thêm 1 ngày thực đạt chuẩn.'
    finish(c, 5, now=NOW + DAY)
    nxt = sp.public(s, c, 'grocery', NOW + DAY)['next']
    assert nxt['can_enrol'] is True, nxt['reason']
    row = next(r for r in nxt['requirements'] if r.get('id') == 'real_days')
    assert (row['got'], row['need'], row['met']) == (2, 2, True)
    sp.action(s, c, 'grocery', 'special_enrol', {'tier': 1}, NOW + DAY)
    assert c[sp.KEY]['study']['tier'] == 1


def test_live_lines():
    s, c = fresh()
    r = c['scale']
    assert scale.today_line(r, c) == 'Hôm nay: 0/0 việc sạch · còn 3 việc sạch nữa là tính hôm nay'
    finish(c, 0); finish(c, 1, mistakes=1)
    assert scale.today_line(r, c) == 'Hôm nay: 1/2 việc sạch · còn 3 việc sạch nữa là tính hôm nay'
    for n in range(2, 5): finish(c, n)
    assert scale.today_line(r, c) == 'Hôm nay: 4/5 việc sạch · đã tính ✓'
    p = scale.public(s, c, 'grocery', NOW)['progress']
    assert p['today']['line'] == 'Hôm nay: 4/5 việc sạch · đã tính ✓' and p['today']['credited'] is True
    assert 'cộng ngay lúc đạt' in scale.DAY_RULE and 'qua 0h' not in scale.DAY_RULE
    assert 'cộng ngay lúc đạt' in scale.DAY_RULE_CONTRACT


def test_mastery_live_line_names_what_is_left():
    from tests.test_career_mastery import career, job
    c = career()
    m = mastery.public(c, 'post_office')
    assert m['today']['line'] == 'Hôm nay: 0/0 việc sạch · còn 3 việc sạch nữa là ngày đạt chuẩn'
    assert next(r for r in m['next']['requirements'] if r['id'] == 'days')['hint'] == m['today']['line']
    for _ in range(3): mastery.completed(c, 'post_office', job(c))
    mastery.completed(c, 'post_office', job(c, mistakes=1))
    assert mastery.public(c, 'post_office')['today']['line'] == 'Hôm nay: 3/4 việc sạch · còn 1 việc sạch nữa là ngày đạt chuẩn'
    mastery.completed(c, 'post_office', job(c))
    assert mastery.public(c, 'post_office')['today']['line'] == 'Hôm nay: 4/5 việc sạch · đã đạt, khép ca là tính ✓'
    mastery.close(c, 'post_office', True)
    assert mastery.public(c, 'post_office')['today']['line'] == 'Hôm nay đã khép ca, ngày nghề sau tính tiếp'
    mastery.validate(c, 'post_office')


def test_promotion_good_day_live_line():
    c = dict(day=4, day_completed=1, feed=[])
    assert pm.good_today(c, 'grocery', {}) == 'Hôm nay: 1 việc xong · còn 1 việc nữa là ngày tốt'
    c['day_completed'] = 2
    assert pm.good_today(c, 'grocery', {}) == 'Hôm nay: 2 việc xong · đã là ngày tốt, khép ngày là tính ✓'
    c['feed'] = [dict(kind='review', day=4, stars=2)]
    assert pm.good_today(c, 'grocery', {}).endswith('dưới 3,5, chưa là ngày tốt')
    assert pm.good_today(c, 'grocery', {'shift': {'size': 3}}) is None
    assert pm.good_today(c, 'corp_accounting', {}) is None


def test_validate_accepts_the_mark_and_rejects_garbage():
    s, c = fresh()
    for n in range(3): finish(c, n)
    scale.validate(c, 'grocery')
    for bad in ('1', -1, True, 1.0, 1200000):
        x = copy.deepcopy(c); x[scale.CREDIT] = bad
        with pytest.raises(e.GameError): scale.validate(x, 'grocery')
    x = copy.deepcopy(c); del x['scale']
    scale.validate(x, 'grocery')                 # an older build may drop the record: the mark alone is harmless


def _played_state():
    """A save after a credited day turned non-qualifying: the case the mark exists for."""
    s = e.new_state(); c = s['careers']['grocery']
    c.update(started=True)
    r = scale.ensure(c, 'grocery', NOW)
    r['today'].update(ids=[f'grocery-0001-{n}' for n in range(5)], total=5, clean=3)
    r['recent_ids'] = list(r['today']['ids']); r['clean'] = 3
    c[scale.CREDIT] = r['today']['day']
    e.validate_state(s)
    return s


def test_old_release_reads_the_save():
    """Rollback: 2.4.8 validates a save carrying the new optional key, and the new build reads 2.4.8's result."""
    tree = os.environ.get('MNL_OLD_TREE')
    tmp = None
    if not tree:
        if not shutil.which('git') or not (ROOT / '.git').exists():
            pytest.skip('needs a git checkout or MNL_OLD_TREE')
        if subprocess.run(['git', 'cat-file', '-e', BASE_REF + '^{commit}'], cwd=ROOT, capture_output=True).returncode:
            pytest.skip(f'{BASE_REF} is not in this clone')
        tmp = tempfile.TemporaryDirectory(prefix='daygate-base-')
        archive = subprocess.run(['git', 'archive', BASE_REF, 'game', 'reference', 'i18n'], cwd=ROOT,
                                 capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', tmp.name], input=archive, check=True)
        tree = tmp.name
    try:
        played = json.dumps(e.dormant_out(_played_state()), ensure_ascii=False)
        prog = ('import json,sys\nfrom game.engine import migrate_state,validate_state\nfrom game import career_scale as sc\n'
                's=migrate_state(json.loads(sys.stdin.read()))\nvalidate_state(s)\n'
                'c=s["careers"]["grocery"];sc.ensure(c,"grocery",%d)\nvalidate_state(s)\n'
                'print(json.dumps(s,ensure_ascii=False))' % (NOW + DAY))
        out = subprocess.run([sys.executable, '-c', prog], input=played, capture_output=True, text=True,
                             encoding='utf-8', cwd=tree, env=dict(os.environ, PYTHONPATH=tree), timeout=300)
        assert out.returncode == 0, out.stderr[-2000:]
        back = e.migrate_state(json.loads(out.stdout))
        e.validate_state(back)
        c = back['careers']['grocery']
        # 2.4.8 ignores the mark: at worst the one day that turned non-qualifying is not added. Never twice.
        assert c['scale']['qualified_days'] in (0, 1)
        assert scale.counted(c['scale'], c) == c['scale']['qualified_days']
    finally:
        if tmp: tmp.cleanup()
