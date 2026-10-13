"""All-career 90-day mastery pacing; no historical progress or money injection.

Run: python -m tests.career_mastery_simulation
Counts returned flat rewards, not full career income; engine payment is covered
by tests/test_mastery_engine.py.
"""
import json
from pathlib import Path

from game import career_mastery as mastery
from game.content import CAREERS
from tests.test_career_mastery import CareerMastery, career


def simulate():
    fixture = CareerMastery()
    fixture.setUp()
    rows = []
    for cid in CAREERS:
        for daily_jobs in (3, 4):
            c = career()
            awards = []
            bonus = 0
            for day in range(1, 91):
                note = fixture.finish_day(c, clean=daily_jobs, cid=cid)
                bonus += note['bonus']
                if mastery.public(c, cid)['ready']:
                    fixture.exam(c, cid)
                    awards.append(day)
                c = json.loads(json.dumps(c))
                mastery.validate(c, cid)
            expected = [19, 44, 89] if daily_jobs == 3 else [15, 40, 75]
            assert awards == expected, (cid, daily_jobs, awards)
            assert c['mastery']['tier'] == 3
            assert bonus == (710 if daily_jobs == 3 else 870)
            rows.append(dict(career=cid, manual_clean_jobs_per_day=daily_jobs,
                             days=90, clean_jobs=c['mastery']['clean'],
                             qualified_days=c['mastery']['qualified_days'],
                             award_days=awards, final_tier=3, total_flat_reward=bonus))
    return dict(careers=len(CAREERS), scenarios=len(rows),
                assumptions=['Prospective progress from zero; 30 existing XP per manual completion.',
                             'Exactly three or four clean generated jobs every day; all days reward-eligible.',
                             'Assessment passed on first attempt as soon as eligible, after closing the shift.',
                             'Each day serialized and reloaded before continuing.',
                             'Rewards are flat mastery bonuses only; no salary, staff or weekly multiplier.'], rows=rows)


if __name__ == '__main__':
    report = simulate()
    target = Path(__file__).resolve().parents[1] / 'output/new-careers/mastery-simulation.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{report['scenarios']} scenarios / {report['careers']} careers passed: "
          '3 jobs/day awards19,44,89 / bonus710; 4 jobs/day awards15,40,75 / bonus870.')
    print(target)
