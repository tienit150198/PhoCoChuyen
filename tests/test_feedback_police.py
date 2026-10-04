"""A simulated report preserves evidence without buying/removing a review."""
import copy
import json
import unittest

from game import engine, feedback as F
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey
from tests.test_feedback_reviews import find


class PoliceReportTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 15

    def post(self, kind='bocphot'):
        t = find(kind)
        made = F.make_review(self.j.state, self.j.c, t, 'completed')
        p = engine.add_feed(self.j.state, self.j.c, t['npc'], made['text'], t['id'], made['stars'], 'review')
        F.attach(p, made)
        return p

    def get(self, pid):
        return next(p for p in self.j.c['feed'] if p['id'] == pid)

    def public(self, pid):
        return next(p for p in public_state(self.j.state)['careers']['milk_tea']['feed'] if p['id'] == pid)['feedback']

    def report(self, pid):
        try:
            return self.j.act('fb_police', post=pid, confirm=True)
        except GameError as error:
            self.fail(f'An extortion threat should allow a police report: {error}')

    def test_threat_shows_report_but_plain_criticism_does_not(self):
        threat, plain = self.post(), self.post('plain')
        self.assertTrue(self.public(threat['id']).get('can_police'))
        self.assertFalse(self.public(plain['id']).get('can_police'))
        with self.assertRaises(GameError):
            self.j.act('fb_police', post=plain['id'], confirm=True)

    def test_drama_voice_with_money_for_silence_can_be_reported(self):
        p = self.post('plain')
        p['feedback']['persona'] = 'drama'
        p['text'] = 'Đã chụp màn hình, tối nay lên group bóc phốt. Muốn yên thì hoàn tiền.'
        self.assertTrue(self.public(p['id']).get('can_police'))
        self.report(p['id'])

    def test_drama_voice_without_a_money_threat_cannot_be_reported(self):
        p = self.post('plain')
        p['feedback']['persona'] = 'drama'
        p['text'] = 'Nếu không có lời giải thích, mình sẽ bóc phốt đó.'
        self.assertFalse(self.public(p['id']).get('can_police'))
        with self.assertRaises(GameError):
            self.j.act('fb_police', post=p['id'], confirm=True)

    def test_report_preserves_evidence_stars_money_and_roundtrip(self):
        p = self.post()
        stars, money, text, count = p['stars'], self.j.c['money'], p['text'], len(self.j.c['feed'])
        result = self.report(p['id'])
        p = self.get(p['id'])
        self.assertEqual(result['police'], 'filed')
        self.assertEqual(p['feedback']['police']['text'], text)
        self.assertEqual(p['feedback']['police']['stars'], stars)
        self.assertEqual(p['feedback']['status'], 'closed')
        self.assertEqual((p['stars'], self.j.c['money'], len(self.j.c['feed'])), (stars, money, count))
        self.assertFalse(self.public(p['id'])['can_police'])
        self.assertFalse(self.public(p['id'])['can_report'])
        validate_state(json.loads(json.dumps(self.j.state)))
        with self.assertRaises(GameError):
            self.j.act('fb_police', post=p['id'], confirm=True)
        with self.assertRaises(GameError):
            self.j.act('fb_report', post=p['id'])

    def test_report_requires_confirmation_without_mutation(self):
        p = self.post()
        before = copy.deepcopy(self.j.state)
        with self.assertRaises(GameError):
            self.j.act('fb_police', post=p['id'])
        self.assertEqual(self.j.state, before)

    def test_report_cancels_pending_reply_and_keeps_the_exchange(self):
        p = self.post()
        self.j.act('fb_reply', post=p['id'], text='Mình xin đối chiếu phiếu và trao đổi rõ sự việc ạ.')
        p = self.get(p['id'])
        thread = copy.deepcopy(p['feedback']['thread'])
        self.assertEqual(p['feedback']['status'], 'awaiting')
        self.report(p['id'])
        p = self.get(p['id'])
        self.assertEqual(p['feedback']['police']['thread'], thread)
        self.assertIsNone(p['feedback']['pending'])
        self.assertEqual(p['feedback']['thread'], thread)
        self.j.act('advance')
        self.assertEqual(self.get(p['id'])['feedback']['thread'], thread)

    def test_malformed_report_is_rejected_on_import(self):
        p = self.post()
        p['feedback']['police'] = {'day': -1}
        with self.assertRaises(GameError):
            validate_state(self.j.state)


if __name__ == '__main__':
    unittest.main()
