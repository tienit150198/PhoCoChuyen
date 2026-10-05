import os
from unittest.mock import patch
from tests.test_system_gift import Base
from game import system_gift as sg


class FairTownGift(Base):
    def test_additional_300_after_old_town_gift_is_paid_only_once(self):
        token=self.guest()
        gift=next(b for b in sg.BROADCASTS if b['prefix']=='fair1005')
        self.assertEqual(gift['coins'],300)
        with patch.dict(os.environ,{'MNL_BROADCAST_OFF':'0'}), patch.object(sg,'now',return_value=1791151200):
            with patch.object(sg,'BROADCASTS',(sg.BROADCASTS[0],)):
                self.load(token)
            before=self.wallet(token)
            changed,shown=self.load(token)
            self.assertTrue(changed)
            self.assertEqual(self.wallet(token),before+300)
            fair=[r for r in shown if r['id'].startswith('fair1005-')]
            self.assertEqual(len(fair),1)
            self.assertEqual(fair[0]['coins'],300)
            self.load(token)
            self.assertEqual(self.wallet(token),before+300)

    def test_prequeued_offline_gift_survives_broadcast_expiry(self):
        token=self.guest();sid=self.store.key(token)
        gift=next(b for b in sg.BROADCASTS if b['prefix']=='fair1005')
        gid=sg._broadcast_id(gift['prefix'],sid)
        sg.grant(self.store,sid,300,gift['title'],gift['text'],gid=gid)
        before=self.wallet(token)
        with patch.object(sg,'now',return_value=gift['until']+86400):
            self.load(token);self.load(token)
        self.assertEqual(self.wallet(token),before+300)
