import unittest,subprocess
from pathlib import Path
from game.engine import public_state,validate_state
from game import promotion as pm
from tests.test_promotion import employee,story,run_board

class PilotGuidance(unittest.TestCase):
    def test_pilot_manager_opens_at_rank_three_and_completes_shift(self):
        j=employee('pilot');j.act('end_day',carry_event=True)
        rec=pm.record(j.state,'pilot',True);pm._sync(rec,j.c)
        rec['rank']=2
        self.assertFalse(public_state(j.state)['careers']['pilot']['promo']['mgr'])
        rec['rank']=3
        p=public_state(j.state)['careers']['pilot']['promo']
        self.assertEqual(p['title'],'Cơ trưởng huấn luyện');self.assertTrue(p['mgr'])
        j.act('start_day',manager=True)
        result=run_board(j)
        self.assertEqual(result['manager']['done'],result['manager']['size'])
        validate_state(j.state)

    def test_step_targets_recovery_and_promotion_card(self):
        root=Path(__file__).resolve().parents[1]
        out=subprocess.run(['node','tests/pilot_tutor.mjs'],cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
