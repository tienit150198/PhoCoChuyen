"""Paid business progression courses, with legacy certificates left intact."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

from game import certificates as ct, price_index as pi
from game.engine import GameError, public_state, validate_state
from tests.test_certificates import act, sit, story


IDS = ('business_basics', 'business_advanced', 'business_chain')


class BusinessCertificates(unittest.TestCase):
    def require_courses(self):
        self.assertTrue(set(IDS) <= set(ct.INDEX), 'business courses must exist')

    def earned(self, s, gid):
        s['journey']['certificates'][gid] = dict(score=67, best=67, earned_day=1, attempts=1)

    def test_catalogue_describes_sequential_paid_levels_and_indexed_fees(self):
        self.require_courses()
        groups = {g['id']: g for g in ct.content()['groups']}
        for level, (gid, base) in enumerate(zip(IDS, (500, 2000, 5000)), 1):
            g = groups[gid]
            self.assertEqual(g['allowed_modes'], ['class'])
            self.assertEqual(g['prerequisite'], IDS[level - 2] if level > 1 else None)
            self.assertEqual(g['business_level'], level)
            self.assertTrue(g['level_benefit'])
            self.assertEqual(g['fee'], pi.price(base))
            self.assertEqual(g['retake_fee'], (pi.price(base) + 1) // 2)
            self.assertFalse(g['hire'])
            self.assertTrue(g['perk'])
        self.assertEqual(groups['work_safety']['allowed_modes'], ['class', 'self'])

    def test_each_level_teaches_six_lessons_and_separate_exam_bank(self):
        self.require_courses()
        for gid in IDS:
            g = ct.INDEX[gid]
            self.assertEqual(len(g['notes']), 6)
            self.assertEqual(len(g['practice']), 6)
            self.assertEqual(len(g['bank']), 12)
            self.assertFalse({q['text'] for q in g['practice']} & {q['text'] for q in g['bank']})
            for q in g['practice'] + g['bank']:
                self.assertTrue(q['why'])
                self.assertIn(q['answer'], [o['id'] for o in q['options']])
        self.assertEqual((ct.DRAW, ct.PASS_MARK), (6, 4))

    def test_exam_answers_do_not_follow_ids_or_repeat_practice_positions(self):
        self.require_courses()
        patterns = []
        for gid in IDS:
            group = ct.INDEX[gid]
            exam = ''.join(q['answer'] for q in group['bank'])
            practice = ''.join(q['answer'] for q in group['practice'])
            self.assertNotEqual(exam, practice * 2, gid)
            for period in range(1, 7):
                self.assertNotEqual(exam, (exam[:period] * 12)[:12], (gid, period))
            patterns.append(exam)
        self.assertEqual(len(set(patterns)), len(IDS))

    def test_inventory_lessons_match_immediate_paid_restocking(self):
        self.require_courses()
        for gid in IDS:
            group = ct.INDEX[gid]
            content = json.dumps(group, ensure_ascii=False).lower()
            for deferred in ('đang giao', 'đang về', 'đơn giao', 'chờ hàng', 'chưa giao', 'hàng chưa tới', 'đơn nhập'):
                self.assertNotIn(deferred, content, (gid, deferred))
            self.assertIn('vào kho ngay', content, gid)
            self.assertIn('sức chứa', content, gid)

    def test_self_study_rejected_for_every_business_level_before_debit(self):
        self.require_courses()
        s = story(wallet=20000)
        for gid in IDS:
            before = copy.deepcopy(s)
            with self.assertRaisesRegex(GameError, 'học phí'):
                ct.action(s, 'jr_cert_enrol', dict(cert=gid, mode='self'))
            self.assertEqual(s, before)

    def test_missing_or_failed_prerequisite_rejected_before_debit(self):
        self.require_courses()
        for gid, prereq in zip(IDS[1:], IDS):
            for failed in (False, True):
                s = story(wallet=20000)
                if failed:
                    s['journey']['certificates'][prereq] = dict(score=50, best=50, earned_day=None, attempts=1)
                before = copy.deepcopy(s)
                with self.assertRaisesRegex(GameError, ct.INDEX[prereq]['name']):
                    ct.action(s, 'jr_cert_enrol', dict(cert=gid, mode='class'))
                self.assertEqual(s, before)

    def test_enrolment_debits_once_and_exam_answers_never_debit(self):
        self.require_courses()
        s = story(wallet=20000)
        for gid in IDS:
            before = s['journey']['wallet']
            s, _ = act(s, None, 'jr_cert_enrol', cert=gid, mode='class')
            cost = ct.tuition(gid)
            self.assertEqual(s['journey']['wallet'], before - cost)
            with self.assertRaises(GameError):
                act(s, None, 'jr_cert_enrol', cert=gid, mode='class')
            self.assertEqual(s['journey']['wallet'], before - cost)
            s, result = sit(s, gid, 4)
            self.assertTrue(result['cert']['passed'])
            self.assertEqual(s['journey']['wallet'], before - cost)
            self.assertTrue(ct.earned(s['journey'], gid))
            validate_state(s)

    def test_failed_retake_preserves_earned_certificate_and_costs_half(self):
        self.require_courses()
        s = story(wallet=20000)
        s, _ = act(s, None, 'jr_cert_enrol', cert=IDS[0], mode='class')
        s, _ = sit(s, IDS[0], 4)
        earned = copy.deepcopy(s['journey']['certificates'][IDS[0]])
        before = s['journey']['wallet']
        s, _ = act(s, None, 'jr_cert_enrol', cert=IDS[0], mode='class')
        self.assertEqual(s['journey']['wallet'], before - ct.retake_fee(IDS[0]))
        s, result = sit(s, IDS[0], 0)
        self.assertNotIn('tự học miễn phí', result['message'])
        rec = s['journey']['certificates'][IDS[0]]
        self.assertEqual((rec['earned_day'], rec['best']), (earned['earned_day'], earned['best']))
        self.assertTrue(ct.earned(s['journey'], IDS[0]))

    def test_retake_rounds_odd_indexed_fee_up(self):
        self.require_courses()
        with patch.object(pi, 'price', return_value=551):
            self.assertEqual(ct.retake_fee(IDS[0]), 276)

    def test_insufficient_funds_never_suggests_free_business_course(self):
        self.require_courses()
        s = story(wallet=0)
        with self.assertRaises(GameError) as raised:
            act(s, None, 'jr_cert_enrol', cert=IDS[0], mode='class')
        self.assertNotIn('Tự học', str(raised.exception))

    def test_business_certificates_do_not_change_hiring(self):
        self.require_courses()
        s = story()
        before = {cid: ct.held_for(s, cid) for cid in s['careers']}
        for gid in IDS:
            self.earned(s, gid)
        self.assertEqual(before, {cid: ct.held_for(s, cid) for cid in s['careers']})
        self.assertFalse(set(IDS) & set(ct.BY_CAREER.values()))

    def test_validation_and_public_serials_accept_new_certificates(self):
        self.require_courses()
        s = story()
        for gid in IDS:
            self.earned(s, gid)
        validate_state(s)
        view = public_state(json.loads(json.dumps(s)))['journey']
        self.assertEqual(set(view['certificates']), set(IDS))
        self.assertTrue(all(view['cert_serials'][gid].startswith('PCC-') for gid in IDS))

    def test_validation_rejects_forged_free_business_study(self):
        self.require_courses()
        s, _ = act(story(wallet=20000), None, 'jr_cert_enrol', cert=IDS[0], mode='class')
        st = s['journey']['study']
        st.update(mode='self', ready=st['start'] + ct.SELF_DAYS, fee=0)
        with self.assertRaises(GameError):
            ct.validate(s)

    @unittest.skipUnless(shutil.which('node'), 'node is needed to render certificate UI')
    def test_ui_business_courses_have_paid_action_and_prerequisite_navigation(self):
        self.require_courses()
        fixture = dict(catalogue=ct.content(), journey=public_state(story(wallet=20000))['journey'])
        script = r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {certsView} from './public/js/v4/certificates.js';
const f=JSON.parse(fs.readFileSync(0,'utf8'));
const env={ui:{},api:{content:{catalogue:[],journey:{certs:f.catalogue}},state:{careers:{},journey:f.journey}}};
env.ui.businessReturn=true;
assert.ok(certsView(env).includes('data-resume="true"'), 'Return to pending shop choice');
const html=certsView(env);
function card(id){return html.split(`id="ct-${id}"`)[1].split('</article>')[0];}
assert.doesNotMatch(card('business_basics'),/data-mode="self"/);
assert.match(card('business_basics'),/data-mode="class"/);
assert.match(card('business_basics'),/gồm 1 lần thi/);
assert.match(card('business_advanced'),/data-action="jrCerts" data-cert="business_basics"/);
assert.doesNotMatch(card('business_advanced'),/data-action="jrCertEnrol"/);
assert.match(card('work_safety'),/data-mode="self"/);
env.api.state.journey.cert_paper={cert:'business_basics',passed:false,right:0,score:0,day:1,review:[]};
const result=certsView(env).split('ct-result')[1].split('</section>')[0];
assert.doesNotMatch(result,/data-mode="self"/);
assert.match(result,/data-mode="class"/);
'''
        result = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps(fixture),
                                text=True, capture_output=True, encoding='utf-8', cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
