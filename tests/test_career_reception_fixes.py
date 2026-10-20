"""🔑 Review fixes of the reception desk (game/careers/reception.py): the guest of a job is that guest (name, gender,
face on the task; the card, the 2D scene and the review show them, not Chị Diễm), what a guest says fits their voice
and their party, the morning plan always has the two car trips its clash step talks about, a complaint is paid on that
room's own price, the cleaning plan comes from Chị Quyên, and the answers never ride in the public brief."""
import unittest

from tests.test_career_reception import R, RC, normal, slot_of, solve
from game.careers import kit
from game.engine import public_state, validate_state


def arrivals(days=range(1, 40)):
    for day in days:
        for slot in range(8):
            if R.kind_of(day, slot) == 'arrival':
                yield day, slot, R.BUILD['arrival'](kit.rng(R.ID, day, slot), day, slot)
    for day in days:
        for slot in range(3):
            for trial in RC.TRIAL_IDS:
                yield day, slot, R._arrival(kit.rng(R.ID, 'trial', day, slot, trial), day, slot, trial)


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Voices(unittest.TestCase):
    def test_every_need_has_a_line_for_every_guest_and_party(self):
        for tag in RC.SAYS:
            for gender in ('male', 'female'):
                for people in range(1, 5):
                    self.assertTrue(RC.says(tag, gender, people), (tag, gender, people))
        self.assertTrue(RC.chatter('male') and RC.chatter('female'))
        self.assertTrue(set(RC.GUESTS) <= set(RC.GUEST_GENDER))

    def test_what_a_guest_says_fits_their_voice_and_party(self):
        line = {x[0]: (x[1], x[2], x[3]) for rows in RC.SAYS.values() for x in rows}
        chat = {x[0]: x[1] for x in RC.CHATTER}
        asks = {a[1] for a in RC.ASKS}
        n = 0
        for day, slot, (needs, key, title, opening, npc) in arrivals():
            names = [c['name'] for c in needs['cards']]
            self.assertFalse(any('(' in x for x in names), names)   # no "(đi cùng)" in a name: it would reach the handover
            for st in needs['steps']:
                if st['id'] == 'arrival.note':
                    self.assertFalse(any('đi cùng' in o['label'] for o in st['options']))
            for card in needs['cards']:
                g = 'f' if RC.GUEST_GENDER[card['name']] == 'female' else 'm'
                for said in card['said']:
                    n += 1
                    if said in asks:
                        continue
                    if said in chat:
                        self.assertIn(chat[said], ('', g), (card['name'], said))
                        continue
                    who, lo, hi = line[said]
                    self.assertIn(who, ('', g), (card['name'], said))
                    self.assertTrue(lo <= card['people'] <= hi, (card['people'], said))
        self.assertGreater(n, 200)
        self.assertNotIn('chị', ' '.join(a[1] for a in RC.ASKS).split())
        self.assertNotIn('vợ tôi', ' '.join(a[1] for a in RC.ASKS))


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Guests(unittest.TestCase):
    def test_a_check_in_is_about_its_own_guest(self):
        for day, slot, (needs, key, title, opening, npc) in arrivals(range(1, 12)):
            g = needs['guest']
            if needs['regular']:
                self.assertIsNone(g)
                self.assertEqual(npc, 4)   # Ông Tư Bến, one of the desk's people
                continue
            self.assertEqual(g['name'], needs['cards'][0]['name'])
            self.assertEqual(g['gender'], RC.GUEST_GENDER[g['name']])
            self.assertTrue(g['fc'].startswith('f1.') and g['fc'].split('.')[15] == ('f' if g['gender'] == 'female' else 'm'))
            self.assertEqual(npc, RC.GUEST_NPC)
            self.assertIn(g['name'], opening)
        self.assertEqual(R.guest_face('Trần Văn Lộc', 'male'), R.guest_face('Trần Văn Lộc', 'male'))   # one face a name

    def test_every_kind_names_who_speaks(self):
        for day in range(2, 30):
            for slot in range(8):
                kind = R.kind_of(day, slot)
                needs, key, title, opening, npc = R.BUILD[kind](kit.rng(R.ID, day, slot), day, slot)
                g = needs.get('guest')
                if kind == 'checkout':
                    self.assertEqual((g['name'], npc), (needs['name'], RC.GUEST_NPC))
                elif kind == 'complaint':
                    self.assertEqual(npc, RC.GUEST_NPC)
                    self.assertIn(g['name'], opening)
                elif kind == 'lost':
                    if needs['item'] == 'gau':
                        self.assertIsNone(g)
                        self.assertEqual(RC.PEOPLE[npc][0], 'Bé Su')
                        self.assertIn('của con', opening)
                    else:
                        self.assertEqual(npc, RC.GUEST_NPC)
                        self.assertIn('của chị' if g['gender'] == 'female' else 'của anh', opening)
                elif kind == 'rooms':
                    self.assertEqual(RC.PEOPLE[npc][0], 'Chị Quyên')   # she hands over the cleaning plan
                    self.assertIsNone(g)
                elif kind == 'services':
                    self.assertEqual(RC.PEOPLE[npc][0], 'Na')

    def test_desk_surprises_have_their_own_guests(self):
        by = {x['id']: x['npc'] for x in RC.DESK}
        for sid in ('plant', 'threat', 'passport', 'suitcase', 'freeloader_back'):
            self.assertEqual(by[sid], RC.GUEST_NPC)
        self.assertEqual(RC.PEOPLE[by['vip']][0], 'Ông Khang')
        self.assertEqual(RC.PEOPLE[by['surprise']][0], 'Anh Duy')
        self.assertEqual(RC.PEOPLE[5][0], 'Chị Diễm')
        self.assertTrue(all(RC.PEOPLE[by[x]][0] == 'Chị Diễm' for x in ('rehearsal', 'demands', 'switch3')))

    def test_the_card_the_review_and_tomorrow_are_the_guest(self):
        for kind in ('arrival', 'checkout', 'complaint'):
            day = next(d for d in range(3, 40) if (lambda s: s is not None and not R.BUILD['arrival'](kit.rng(R.ID, d, s), d, s)[0]['regular']
                                                       if kind == 'arrival' else s is not None)(next((s for s in range(8) if R.kind_of(d, s) == kind), None)))
            j = normal(day=day, slot=slot_of(kind, day))
            g = j.task['needs']['guest']
            pub = next(t for t in public_state(j.state)['careers']['reception']['tasks'] if t['id'] == j.task['id'])
            self.assertEqual(pub['guest']['name'], g['name'])   # before the slip is read too (the ask card)
            t = solve(j)
            review = next(p for p in j.c['feed'] if p['source'] == t['id'] and p['kind'] == 'review')
            self.assertEqual(review['author'], g['name'], kind)
            self.assertFalse([x for x in j.c['pending'] if x.get('kind') == 'return_note' and x.get('ref') == t['id']])
            validate_state(j.state)


@unittest.skipUnless(R, 'reception filtered out by MNL_CAREERS')
class Content(unittest.TestCase):
    def test_the_morning_plan_always_has_the_two_car_trips(self):
        for day in range(1, 40):
            for slot in range(8):
                if R.kind_of(day, slot) != 'services':
                    continue
                needs, key, *_ = R.BUILD['services'](kit.rng(R.ID, day, slot), day, slot)
                self.assertIn('bus', key['services.plan'])
                self.assertIn('air', key['services.plan'])
                clash = next(st for st in needs['steps'] if st['id'] == 'services.clash')
                self.assertIn('hai chuyến', clash['evidence'])

    def test_a_complaint_is_paid_on_that_rooms_price(self):
        seen = 0
        for day in range(1, 60):
            for slot in range(8):
                if R.kind_of(day, slot) != 'complaint':
                    continue
                needs, key, *_ = R.BUILD['complaint'](kit.rng(R.ID, day, slot), day, slot)
                price = RC.ROOM[needs['room']]['price']
                self.assertEqual(needs['rate'], price)
                comp = next(st for st in needs['steps'] if st['id'] == 'complaint.comp')
                self.assertIn(f'Phòng {needs["room"]} giá {price} xu/đêm', comp['evidence'])
                cid = needs['issue']
                if key['complaint.result'] == 'fault' and cid != 'charge':
                    self.assertEqual(key['complaint.comp'], price * RC.COMPLAINTS[cid][4] // 100)
                    seen += 1
        self.assertGreater(seen, 0)
        self.assertIn('nút xanh', RC.COMPLAINTS['water'][3][1])

    def test_answers_stay_off_the_public_brief(self):
        for kind, gone in (('complaint', 'issue'), ('lost', 'seen')):
            j = normal(slot=slot_of(kind))
            j.act('ask', task=j.task['id'])
            pub = next(t for t in public_state(j.state)['careers']['reception']['tasks'] if t['id'] == j.task['id'])
            self.assertNotIn(gone, pub['needs'])
            self.assertIn(gone, j.task['needs'])   # the server keeps it


if __name__ == '__main__':
    unittest.main()
