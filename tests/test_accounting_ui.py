import json
import shutil
import subprocess
import unittest
from pathlib import Path

from game import accounting_school as school,accounting_content as content,accounting_company as company
from game.engine import new_state

ROOT=Path(__file__).resolve().parents[1]


class AccountingUITests(unittest.TestCase):
    def test_safe_render_and_answer_controls(self):
        node=shutil.which('node')
        if not node:self.skipTest('node not installed')
        questions={}
        for l in content.LESSONS.values():
            for q in l['questions']:questions.setdefault(q['kind'],school._safe_question(q))
        data=dict(questions=list(questions.values()),school_state=dict(accounting_school=school.public(new_state()),name='Học viên'),book=company.public(company.initial()))
        out=subprocess.run([node,str(ROOT/'tests/accounting_school.mjs')],input=json.dumps(data,ensure_ascii=False),text=True,encoding='utf-8',
                           cwd=ROOT,capture_output=True,timeout=60)
        self.assertEqual(out.returncode,0,out.stderr+out.stdout)


if __name__=='__main__':unittest.main()
