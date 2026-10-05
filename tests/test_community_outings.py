import copy
import json
import unittest
import tempfile
from pathlib import Path
from game import outings, archive
from game.engine import GameError
from tests.test_wardrobe import story
from game.storage import Store


class CommunityOutings(unittest.TestCase):
    def test_book_clubs_karaoke_and_family_are_playable_and_persist(self):
        s=story(wallet=2000)
        places=outings.content().get('community', [])
        self.assertEqual({p['id'] for p in places}, {'books','art','music','reading','garden','karaoke','family'})
        for place in places:
            start=s['journey']['wallet']
            p=dict(place=place['id'],choice=place['choices'][0]['id'],pay='cash')
            result=outings.action(s,'jr_out_community',p)
            self.assertIn('message',result)
            self.assertEqual(start-s['journey']['wallet'],place['cost'])
            outings.validate(s)
            saved=copy.deepcopy(s)
            result=outings.action(s,'jr_out_community',p)
            self.assertTrue(result['duplicate'])
            self.assertEqual(saved,s)
        loaded=json.loads(json.dumps(s))
        outings.validate(loaded)
        self.assertEqual(len(outings.public(loaded)['community']['memories']),7)

    def test_invalid_choice_cannot_charge_or_grant_memory(self):
        s=story();before=copy.deepcopy(s)
        with self.assertRaises(GameError):
            outings.action(s,'jr_out_community',dict(place='books',choice='forged',pay='cash'))
        self.assertEqual(s,before)

    def test_next_life_day_changes_prompt_and_keeps_previous_memory(self):
        s=story()
        places=outings.content().get('community',[])
        self.assertTrue(places)
        outings.action(s,'jr_out_community',dict(place='books',choice=places[0]['choices'][0]['id']))
        s['journey']['life_day']+=1
        outings.action(s,'jr_out_community',dict(place='books',choice=places[0]['choices'][1]['id']))
        outings.validate(s)
        self.assertEqual(len(outings.public(s)['community']['memories']),2)
        self.assertEqual(outings.public(s)['community']['visits']['books'],2)

    def test_legacy_save_is_read_without_mutating(self):
        s=story();before=copy.deepcopy(s)
        view=outings.public(s)
        self.assertEqual(s,before)
        self.assertIn('community',view)

    def test_forged_memory_or_future_day_is_rejected(self):
        s=story()
        s['journey']['community_outings']={'v':1,'visits':{},'last':{},'memories':[{'place':'fake'}]}
        with self.assertRaises(GameError):outings.validate(s)

    def test_old_memories_are_archived_instead_of_discarded(self):
        s=story(wallet=2000)
        with archive.collect() as records:
            for day in range(1,45):
                s['journey']['life_day']=day
                outings.action(s,'jr_out_community',dict(place='books',choice='letter'))
        outings.validate(s)
        kept=s['journey']['community_outings']['memories']
        saved=[r for owner,kind,r in records.rows if kind=='community.memories']
        self.assertEqual(len(kept),42)
        self.assertEqual([r['day'] for r in saved+kept],list(range(1,45)))


class CommunityPersistence(unittest.TestCase):
    def test_full_command_save_reload_and_retry_charge_once(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            store=Store(Path(directory)/'community.db',story=True)
            self.addCleanup(store.close_pool)
            token,_,_=store.session()
            before,revision,*_=store.read(token)
            payload=dict(place='books',choice='letter',pay='cash')
            first=store.command(token,'community-visit-001',revision,None,'jr_out_community',payload)
            self.assertEqual(first['state']['journey']['wallet'],before['journey']['wallet']-12)
            retry=store.command(token,'community-visit-001',revision,None,'jr_out_community',payload)
            self.assertTrue(retry['replayed'])
            saved,revision,*_=store.read(token)
            self.assertEqual(saved['journey']['community_outings']['visits'],{'books':1})
            same_day=store.command(token,'community-visit-002',revision,None,'jr_out_community',payload)
            self.assertTrue(same_day['result']['duplicate'])
            self.assertEqual(first['state']['journey']['wallet'],same_day['state']['journey']['wallet'])
