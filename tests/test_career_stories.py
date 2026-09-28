"""Truyện nghề: one short story arc per workplace (game/career_stories.py)."""
import copy
import re
import unittest

from game import career_stories as cst
from game.content import CAREERS, NPC_INDEX
from game.engine import GameError, apply_action, migrate_state, needs_migration, new_state, public_state, validate_state


def act(s, where, action, **p):
    return apply_action(s, where, action, p)


def day(s, cid, served=None):
    """One shift at `cid`; `served` fixes the finished-task counter first."""
    s, _ = act(s, cid, 'start_day')
    if served is not None:
        s['careers'][cid]['metrics']['served'] = served
    return act(s, cid, 'end_day', carry_event=True)


def queued(s, cid=None):
    return [q for q in s['stories']['queue'] if cid is None or q['career'] == cid]


def ledger_ok(c):
    f = c['ops']['finance']
    return f['opening_balance'] + sum(x['amount'] for x in f['ledger']) == c['money']


class ContentTest(unittest.TestCase):
    def test_every_career_has_an_arc(self):
        self.assertEqual(set(cst.ARCS), set(CAREERS))
        self.assertEqual(len(cst.ARCS), 20)

    def test_beats_are_well_formed(self):
        ids = set()
        for cid, arc in cst.ARCS.items():
            self.assertTrue(arc['title'] and arc['emoji'] and arc['keepsake']['name'], cid)
            self.assertEqual(len(arc['beats']), 5, cid)
            choices = 0
            for i, b in enumerate(arc['beats']):
                self.assertEqual(b['id'], f'{cid}_{i + 1}')
                self.assertNotIn(b['id'], ids)
                ids.add(b['id'])
                self.assertTrue(b['title'] and b['emoji'] and b['hint'], b['id'])
                self.assertTrue(3 <= len(b['lines']) <= 6, b['id'])
                w = b['when']
                self.assertEqual(set(w), {'served', 'days', 'level', 'gap', 'metric'})
                if i:
                    self.assertGreaterEqual(w['gap'], 1, b['id'])  # at most one beat per workplace day
                    prev = arc['beats'][i - 1]['when']
                    self.assertGreaterEqual((w['days'], w['served']), (prev['days'], prev['served']), b['id'])
                if b['choice']:
                    choices += 1
                    opts = b['choice']['options']
                    self.assertEqual(len(opts), 2, b['id'])
                    self.assertEqual(len({o['id'] for o in opts}), 2)
                    for o in opts:
                        self.assertTrue(o['label'] and 1 <= len(o['reply']) <= 2, b['id'])
                        self.assertTrue(0 <= o['coins'] <= cst.MAX_COINS, b['id'])
                        if o['rel']:
                            npc = arc['cast'][o['rel']].get('npc')
                            self.assertIn(npc, NPC_INDEX, b['id'])
                            self.assertEqual(NPC_INDEX[npc]['career_id'], cid)
            self.assertTrue(1 <= choices <= 3, cid)

    def test_speakers_and_npc_links_are_valid(self):
        for cid, arc in cst.ARCS.items():
            for key, p in arc['cast'].items():
                self.assertTrue(p['name'] and p['emoji'] and p['role'], (cid, key))
                if p['npc']:
                    self.assertEqual(NPC_INDEX[p['npc']]['career_id'], cid, (cid, key))
                    self.assertIn(NPC_INDEX[p['npc']]['display_name'], p['name'], (cid, key))   # same person as the career's NPC
            for i, b in enumerate(arc['beats']):
                rows = b['lines'] + [r for o in (b['choice'] or {}).get('options', []) for r in o['reply']]
                for row in rows:
                    self.assertTrue(row['who'] == 'me' or row['who'] in arc['cast'], (b['id'], row['who']))
                    if row['need']:
                        ref = next(x for x in arc['beats'][:i] if x['id'] == row['need'][0])
                        self.assertIn(row['need'][1], [o['id'] for o in ref['choice']['options']])

    def test_text_resolves_for_every_gender(self):
        for arc in cst.ARCS.values():
            for b in arc['beats']:
                texts = [r['text'] for r in b['lines']]
                if b['choice']:
                    texts += [b['choice']['prompt']] + [o['label'] for o in b['choice']['options']]
                    texts += [r['text'] for o in b['choice']['options'] for r in o['reply']]
                for text in texts:
                    for g in ('male', 'female', 'none'):
                        out = cst.resolve(text, g, 'Mây')
                        self.assertTrue(out.strip(), b['id'])
                        self.assertIsNone(re.search(r'[{}]', out), (b['id'], out))
                        self.assertLessEqual(len(out), 160, (b['id'], out))
        self.assertEqual(cst.resolve('{Anh} ơi', 'male'), 'Anh ơi')
        self.assertEqual(cst.resolve('{Anh} ơi', 'female'), 'Chị ơi')
        self.assertEqual(cst.resolve('{thay} ơi', 'male'), 'thầy ơi')
        self.assertEqual(cst.resolve(dict(male='A', female='B', none='C'), 'none'), 'C')


class TriggerTest(unittest.TestCase):
    def setUp(self):
        s = new_state()
        s, _ = act(s, 'milk_tea', 'select_career')
        self.s = s

    def test_beats_fire_in_order_once_each(self):
        s, r = act(self.s, 'milk_tea', 'start_day')
        self.assertEqual(queued(s), [])                 # nothing served yet
        s['careers']['milk_tea']['metrics']['served'] = 1
        s, r = act(s, 'milk_tea', 'end_day', carry_event=True)
        self.assertEqual([q['beat'] for q in queued(s)], ['milk_tea_1'])
        self.assertEqual(r['story']['career'], 'milk_tea')
        # More days pass without answering: still one beat, never the next one.
        for _ in range(3):
            s, r = day(s, 'milk_tea', served=30)
            self.assertNotIn('story', r)
        self.assertEqual([q['beat'] for q in queued(s)], ['milk_tea_1'])
        qid = queued(s)[0]['id']
        s, r = act(s, None, 'st_seen', id=qid)
        self.assertEqual(s['stories']['arcs']['milk_tea']['seen'], ['milk_tea_1'])
        self.assertEqual(queued(s), [])
        with self.assertRaises(GameError):              # no double answer
            act(s, None, 'st_seen', id=qid)
        s, r = day(s, 'milk_tea', served=30)
        self.assertEqual([q['beat'] for q in queued(s)], ['milk_tea_2'])
        self.assertIn('Truyện nghề · Vị khách giờ tan học', [x['text'] for x in s['careers']['milk_tea']['journal']])
        validate_state(s)

    def test_gap_and_thresholds(self):
        s = self.s
        c = s['careers']['milk_tea']
        c['metrics']['served'] = 1
        self.assertTrue(cst.due(s, 'milk_tea'))
        cst.check(s, 'milk_tea')
        self.assertFalse(cst.due(s, 'milk_tea'))        # already queued
        st = s['stories']
        st['arcs']['milk_tea']['seen'].append(st['queue'].pop()['beat'])
        c['metrics']['served'] = 50
        c['day'] = 3
        st['arcs']['milk_tea']['last'] = 3
        self.assertFalse(cst.due(s, 'milk_tea'))        # gap: same workplace day
        c['day'] = 4
        self.assertTrue(cst.due(s, 'milk_tea'))
        # reset_career sent the workplace back to day 1: the gap counts as passed, the threshold still holds.
        c['day'] = 1
        self.assertFalse(cst.due(s, 'milk_tea'))        # beat 2 needs 2 closed days
        st['arcs']['milk_tea']['last'] = 9
        c['day'] = 3
        self.assertTrue(cst.due(s, 'milk_tea'))

    def test_only_the_acting_workplace_is_checked(self):
        s = self.s
        s['careers']['grocery']['metrics']['served'] = 5
        s, _ = act(s, 'milk_tea', 'start_day')
        self.assertEqual(queued(s, 'grocery'), [])
        s, _ = act(s, 'grocery', 'select_career')
        s, _ = act(s, 'grocery', 'start_day')
        self.assertEqual([q['beat'] for q in queued(s, 'grocery')], ['grocery_1'])

    def test_full_arc_and_keepsake(self):
        s = self.s
        picks = {}
        for n in range(1, 6):
            for _ in range(12):
                if queued(s):
                    break
                s, _ = day(s, 'milk_tea', served=10 * n + 20)
            (item,) = queued(s)
            self.assertEqual(item['beat'], f'milk_tea_{n}')
            beat = cst.ARCS['milk_tea']['beats'][n - 1]
            if beat['choice']:
                s, r = act(s, None, 'st_choose', id=item['id'], option='b')
                picks[beat['id']] = 'b'
            else:
                s, r = act(s, None, 'st_seen', id=item['id'])
        self.assertIn('keepsake', r['story'])
        self.assertIn('Trọn truyện', r['message'])
        a = s['stories']['arcs']['milk_tea']
        self.assertEqual(len(a['seen']), 5)
        self.assertEqual(a['picks'], picks)
        for _ in range(3):
            s, _ = day(s, 'milk_tea', served=200)
        self.assertEqual(queued(s), [])                 # nothing after the last beat
        arc = next(x for x in public_state(s)['stories']['arcs'] if x['career'] == 'milk_tea')
        self.assertTrue(arc['done'])
        self.assertEqual(arc['keepsake']['name'], cst.ARCS['milk_tea']['keepsake']['name'])
        validate_state(s)


class ChoiceTest(unittest.TestCase):
    def at_beat(self, cid, n, gender=None):
        s = new_state()
        if gender:
            s['journey']['gender'] = gender
        st = s['stories']
        ids = [b['id'] for b in cst.ARCS[cid]['beats']]
        st['arcs'][cid] = dict(seen=ids[:n - 1], picks={}, last=1)
        for b in cst.ARCS[cid]['beats'][:n - 1]:
            if b['choice']:
                st['arcs'][cid]['picks'][b['id']] = 'a'
        st['seq'] = 1
        st['queue'] = [dict(id='s1', career=cid, beat=ids[n - 1], day=1)]
        validate_state(s)
        return s

    def test_choice_applies_relationship_and_reply(self):
        s = self.at_beat('milk_tea', 2, 'female')
        npc = cst.ARCS['milk_tea']['cast']['linh']['npc']
        before = s['careers']['milk_tea']['relationships'].get(npc, 0)
        s2, r = act(s, None, 'st_choose', id='s1', option='a')
        self.assertEqual(s2['careers']['milk_tea']['relationships'][npc], before + cst.REL_BUMP)
        self.assertEqual(s2['stories']['arcs']['milk_tea']['picks'], {'milk_tea_2': 'a'})
        self.assertIn('chị', r['story']['reply'][0]['text'])   # {anh} for a female character
        self.assertEqual(r['story']['reply'][0]['name'], 'Linh')
        self.assertIn('Linh', r['story']['note'])

    def test_coins_go_to_the_fund_with_a_ledger_line(self):
        s = self.at_beat('farm', 4)
        money = s['careers']['farm']['money']
        s2, r = act(s, None, 'st_choose', id='s1', option='b')
        c = s2['careers']['farm']
        self.assertEqual(c['money'], money + 8)
        self.assertEqual(c['ops']['finance']['ledger'][-1]['category'], 'story_reward')
        self.assertTrue(ledger_ok(c))
        self.assertIn('+8 xu', r['story']['note'])

    def test_later_lines_follow_an_earlier_pick(self):
        for pick, word in (('a', 'Mái che'), ('b', 'rãnh')):
            s = self.at_beat('farm', 3)
            s['stories']['arcs']['farm']['picks']['farm_2'] = pick
            lines = [x['text'] for x in public_state(s)['stories']['due'][0]['lines']]
            self.assertTrue(any(word in t for t in lines), (pick, lines))
            self.assertEqual(len(lines), 4)

    def test_misuse_is_rejected(self):
        s = self.at_beat('milk_tea', 2)
        with self.assertRaises(GameError):
            act(s, None, 'st_seen', id='s1')                      # needs a choice
        with self.assertRaises(GameError):
            act(s, None, 'st_choose', id='s1', option='z')
        with self.assertRaises(GameError):
            act(s, None, 'st_choose', id='nope', option='a')
        with self.assertRaises(GameError):
            act(s, None, 'st_choose', id='s1', option='a', extra=1)
        with self.assertRaises(GameError):
            act(s, None, 'st_other', id='s1')
        s = self.at_beat('milk_tea', 1)
        with self.assertRaises(GameError):
            act(s, None, 'st_choose', id='s1', option='a')        # plain beat

    def test_public_view(self):
        s = self.at_beat('teacher', 2, 'male')
        s['name'] = 'Bin'
        v = public_state(s)['stories']
        (d,) = v['due']
        self.assertEqual((d['career'], d['step'], d['total']), ('teacher', 2, 5))
        self.assertIn('Thầy ơi', d['lines'][0]['text'])
        self.assertEqual(len(d['choice']['options']), 2)
        self.assertFalse(d['last'])
        self.assertEqual(len(v['arcs']), 20)
        t = next(x for x in v['arcs'] if x['career'] == 'teacher')
        self.assertEqual((t['seen'], t['pending'], t['done']), (1, 's1', False))
        self.assertEqual(t['beats'][0]['title'], cst.ARCS['teacher']['beats'][0]['title'])
        me = [x for x in public_state(self.at_beat('teacher', 1))['stories']['due'][0]['lines'] if x['who'] == 'me']
        self.assertTrue(me and me[0]['name'] == 'Mây')


class SaveTest(unittest.TestCase):
    def test_old_save_migrates(self):
        s = new_state()
        s, _ = act(s, 'milk_tea', 'select_career')
        s, _ = day(s, 'milk_tea', served=4)
        old = copy.deepcopy(s)
        old.pop('stories')
        self.assertTrue(needs_migration(old))
        m = migrate_state(old)
        self.assertEqual(m['stories'], cst.initial())
        validate_state(m)
        self.assertFalse(needs_migration(m))
        # The next action starts the arc from its first beat.
        m, _ = act(m, 'milk_tea', 'start_day')
        self.assertEqual([q['beat'] for q in queued(m)], ['milk_tea_1'])
        # A partial book from a future version keeps its data and gains missing keys.
        part = copy.deepcopy(s)
        part['stories'] = dict(version=1, arcs={}, queue=[])
        self.assertEqual(migrate_state(part)['stories']['seq'], 0)

    def test_validate_rejects_bad_state(self):
        def bad(mutate):
            s = new_state()
            s['stories']['arcs']['farm'] = dict(seen=['farm_1'], picks={}, last=2)
            s['stories']['queue'] = [dict(id='s1', career='farm', beat='farm_2', day=2)]
            validate_state(s)
            mutate(s)
            with self.assertRaises(GameError):
                validate_state(s)
        bad(lambda s: s['stories'].update(version=2))
        bad(lambda s: s.pop('stories'))
        bad(lambda s: s['stories']['arcs']['farm'].update(seen=['farm_2']))            # not a prefix
        bad(lambda s: s['stories']['arcs']['farm'].update(picks={'farm_1': 'a'}))      # farm_1 has no choice
        bad(lambda s: s['stories']['arcs']['farm'].update(picks={'farm_3': 'a'}))      # not seen yet
        bad(lambda s: s['stories']['arcs'].update(nowhere=dict(seen=[], picks={}, last=0)))
        bad(lambda s: s['stories']['queue'][0].update(beat='farm_3'))                  # not the next beat
        bad(lambda s: s['stories']['queue'].append(dict(id='s2', career='farm', beat='farm_2', day=2)))
        bad(lambda s: s['stories']['queue'][0].update(extra=1))
        bad(lambda s: s['stories'].update(seq=-1))
        bad(lambda s: s['stories']['arcs']['farm'].update(last=None))

    def test_reset_all_gives_an_empty_book(self):
        s = new_state()
        s['stories']['arcs']['farm'] = dict(seen=['farm_1'], picks={}, last=2)
        s, _ = act(s, None, 'reset_all', confirm='BAT DAU LAI')
        self.assertEqual(s['stories'], cst.initial())


if __name__ == '__main__':
    unittest.main()
