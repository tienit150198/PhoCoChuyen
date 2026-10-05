from tests.test_marriage import Base
from game import marriage as mr


class RingResale(Base):
    def test_owned_ring_returns_eighty_percent_once(self):
        a=self.user('resale');ring=self.ring(a)
        view=self.view(a)['rings'][0];before=self.wallet(a)
        self.assertEqual(view['sell_price'],view['price']*80//100)
        self.act(a,'ring_sell',ring=ring)
        self.assertEqual(self.wallet(a),before+view['sell_price'])
        self.assertFalse(self.view(a)['rings'])
        self.act(a,'ring_sell',ring=ring)
        self.assertEqual(self.wallet(a),before+view['sell_price'])

    def test_cannot_sell_someone_elses_or_proposed_ring(self):
        a=self.user('resale_a');b=self.user('resale_b');ring=self.ring(a)
        wa,wb=self.wallet(a),self.wallet(b)
        with self.assertRaises(mr.MarriageError):self.act(b,'ring_sell',ring=ring)
        self.act(a,'propose',code=self.code(b),ring=ring,message='hem',announce=False)
        with self.assertRaises(mr.MarriageError):self.act(a,'ring_sell',ring=ring)
        self.assertEqual((self.wallet(a),self.wallet(b)),(wa,wb))

    def test_engaged_couple_can_sell_spare_but_not_their_shared_ring(self):
        a=self.user('engage_a');b=self.user('engage_b')
        spare=self.ring(b);shared=self.engage(a,b,announce=False)
        with self.assertRaises(mr.MarriageError):self.act(a,'ring_sell',ring=shared)
        before=self.wallet(b);value=next(r['price'] for r in self.view(b)['rings'] if r['id']==spare)*80//100
        self.act(b,'ring_sell',ring=spare)
        self.assertEqual(self.wallet(b),before+value)
        self.assertEqual(self.view(b)['couple']['ring']['id'],shared)

    def test_failed_atomic_sale_does_not_credit_wallet(self):
        from unittest.mock import patch
        a=self.user('atomic');ring=self.ring(a);before=self.wallet(a)
        with patch.object(mr,'_insert_effects',side_effect=RuntimeError('failed write')):
            with self.assertRaises(RuntimeError):self.act(a,'ring_sell',ring=ring)
        self.assertEqual(self.wallet(a),before)
        self.assertEqual(self.view(a)['rings'][0]['status'],'owned')
