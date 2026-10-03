"""Refund + apology to a low review (chat 03/10: "Khách đánh giá 1 sao mình hoàn tiền 20 xu rồi xin lỗi nó mà nó vẫn
giữ nguyên đánh giá"): the reviewer answers back, and with a fair, seeded chance edits the stars up (never above
4★, never past the facts); one offer per review, so the chance cannot be bought twice; an AI that disagrees with
the game's decision does not change the stars."""
import unittest

from game import engine, feedback as F
from game.engine import GameError, public_state, validate_state
from tests.helpers import Journey
from tests.test_feedback_reviews import make_post


class Amends(unittest.TestCase):
    def setUp(self):
        self.j = Journey('milk_tea')
        self.j.c['day'] = 8

    def get(self, pid):
        return next(p for p in self.j.c['feed'] if p['id'] == pid)

    def rating(self):
        return public_state(self.j.state)['careers']['milk_tea']['rating']

    def post_rolling(self, win, persona='sour', stars=1, score=1):
        """A low review whose amends roll wins (or loses): the roll is fixed by the post id."""
        for i in range(400):
            post = make_post(self.j, persona, stars=stars, score=score, pid_hint=f'am{win}{i}')
            chance = F.AMENDS_CHANCE['refund'] // 2 - (F.AMENDS_HARSH if persona in F.HARSH else 0)   # a warm reply without "xin lỗi"
            if (F._hash('amends', post['id']) % 100 < chance) == win:
                return post
            self.j.c['feed'].remove(post)
        raise AssertionError('no roll')

    def reply(self, post, text, offer, tone='warm'):
        r = self.j.act('fb_reply', post=post['id'], text=text, offer=offer, tone=tone)
        self.j.act('advance')
        self.j.act('advance')
        return r

    def test_without_amends_a_sour_reviewer_keeps(self):
        post = make_post(self.j, 'sour', stars=1, score=1, pid_hint='plain')
        self.reply(post, 'Cảm ơn bạn đã ghé tiệm ạ.', 'none')
        self.assertEqual(self.get(post['id'])['stars'], 1)

    def test_refund_wins_the_review_back_and_says_so(self):
        post = self.post_rolling(True)
        before = self.rating()
        money = self.j.c['money']
        self.reply(post, 'Cảm ơn bạn đã ghé tiệm ạ, tiệm gửi lại tiền ly nước.', 'refund')
        p = self.get(post['id'])
        self.assertEqual(self.j.c['money'], money - F.OFFERS['refund'])
        self.assertGreater(p['stars'], 1)
        self.assertLessEqual(p['stars'], F.AMENDS_CAP)
        self.assertGreater(self.rating(), before)          # the average uses the new stars
        last = p['feedback']['thread'][-1]
        self.assertEqual((last['role'], last['decision']), ('customer', 'revise_up'))
        self.assertIn(last['text'], F.AMENDS_UP['customer'])
        self.assertEqual(p['feedback']['status'], 'closed')  # one change per review
        with self.assertRaises(GameError):
            self.j.act('fb_reply', post=post['id'], text='Xin lỗi lần nữa ạ.', offer='gift')
        validate_state(self.j.state)

    def test_the_answer_names_the_change(self):
        post = self.post_rolling(True)
        self.j.act('fb_reply', post=post['id'], text='Cảm ơn bạn đã ghé tiệm ạ.', offer='refund', tone='warm')
        state, r = engine.apply_action(self.j.state, 'milk_tea', 'fb_resolve', dict(post=post['id'], mode='scripted'), internal=True)
        self.j.state = state
        new = self.get(post['id'])['stars']
        self.assertTrue(r['message'].startswith(f'{post["author"]} đã sửa đánh giá: ★1 → ★{new}.'), r['message'])

    def test_a_lost_roll_still_answers_the_refund(self):
        post = self.post_rolling(False)
        self.reply(post, 'Cảm ơn bạn đã ghé tiệm ạ.', 'refund')
        p = self.get(post['id'])
        self.assertEqual(p['stars'], 1)
        self.assertIn(p['feedback']['thread'][-1]['text'], F.AMENDS_KEEP['customer'])

    def test_the_roll_is_fixed_per_review(self):
        a = make_post(self.j, 'picky', stars=1, score=1, pid_hint='same')
        d1 = F.amends(dict(a, feedback=dict(a['feedback'], thread=[dict(role='owner', text='x', day=8, offer='gift')])),
                      dict(decision='keep', stars=1, text='k'), 'warm', 'Cảm ơn bạn ạ.')
        d2 = F.amends(dict(a, feedback=dict(a['feedback'], thread=[dict(role='owner', text='y', day=8, offer='gift')])),
                      dict(decision='keep', stars=1, text='k'), 'warm', 'Một câu khác hẳn ạ.')
        self.assertEqual(d1['decision'], d2['decision'])

    def test_never_above_four_and_never_for_fakes_or_rudeness(self):
        post = make_post(self.j, 'sour', stars=3, score=3, pid_hint='cap')
        post['feedback']['thread'].append(dict(role='owner', text='x', day=8, offer='refund'))
        ups = 0
        for i in range(60):
            post['id'] = f'cap-{i}'
            d = F.amends(post, dict(decision='keep', stars=3, text='k'), 'sorry', 'Tiệm xin lỗi bạn ạ.')
            self.assertLessEqual(d['stars'], 4)
            ups += d['decision'] == 'revise_up'
        self.assertTrue(0 < ups < 60)                      # a fair chance, never a sure thing
        fake = make_post(self.j, 'troll', stars=1, score=5, twist='competitor', pid_hint='fake')
        fake['feedback']['thread'].append(dict(role='owner', text='x', day=8, offer='refund'))
        rude = make_post(self.j, 'sour', stars=1, score=1, pid_hint='rude')
        rude['feedback']['thread'].append(dict(role='owner', text='x', day=8, offer='refund'))
        for i in range(60):
            fake['id'] = rude['id'] = f'n-{i}'
            self.assertEqual(F.amends(fake, dict(decision='keep', stars=1, text='k'), 'sorry', 'Xin lỗi ạ.')['decision'], 'keep')
            self.assertEqual(F.amends(rude, dict(decision='keep', stars=1, text='k'), 'free', 'Đồ ngu, cầm tiền rồi đi.')['decision'], 'keep')
            self.assertEqual(F.amends(rude, dict(decision='keep', stars=1, text='k'), 'sassy', 'Dạ tiệm nhận góp ý ạ.')['decision'], 'keep')

    def test_nothing_given_nothing_changes(self):
        post = make_post(self.j, 'sour', stars=1, score=1, pid_hint='none')
        post['feedback']['thread'].append(dict(role='owner', text='x', day=8, offer='none'))
        d = dict(decision='keep', stars=1, text='k')
        self.assertIs(F.amends(post, d, 'sorry', 'Xin lỗi ạ.'), d)

    def test_ai_that_disagrees_does_not_move_the_stars(self):
        post = self.post_rolling(True)
        self.j.act('fb_reply', post=post['id'], text='Cảm ơn bạn đã ghé tiệm ạ.', offer='refund', tone='warm')
        pending = self.get(post['id'])['feedback']['pending']
        self.assertEqual(pending['decision'], 'revise_up')
        state, _ = engine.apply_action(self.j.state, 'milk_tea', 'fb_resolve',
                                       dict(post=post['id'], decision='keep', stars=1, text='Giữ nguyên.', mode='ai'), internal=True)
        self.j.state = state
        p = self.get(post['id'])
        self.assertEqual(p['stars'], pending['stars'])
        self.assertEqual(p['feedback']['thread'][-1]['mode'], 'scripted')

    def test_ai_that_agrees_writes_the_words_the_game_keeps_the_stars(self):
        post = self.post_rolling(True)
        self.j.act('fb_reply', post=post['id'], text='Cảm ơn bạn đã ghé tiệm ạ.', offer='refund', tone='warm')
        pending = self.get(post['id'])['feedback']['pending']
        state, _ = engine.apply_action(self.j.state, 'milk_tea', 'fb_resolve',
                                       dict(post=post['id'], decision='revise_up', stars=5, text='Ok quán, mình sửa nha.', mode='ai'), internal=True)
        self.j.state = state
        p = self.get(post['id'])
        self.assertEqual(p['stars'], pending['stars'])
        self.assertEqual(p['feedback']['thread'][-1]['text'], 'Ok quán, mình sửa nha.')


if __name__ == '__main__':
    unittest.main()
