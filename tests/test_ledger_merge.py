"""2.4.15 lag fix: staff orders sum into one cash-book row a day per group; totals never change."""
import unittest

from game import operations as ops, archive
from game.engine import new_state, validate_career


def career():
    c=new_state()['careers']['clothing'];c['day']=5
    return c


def wallet_ok(c):
    f=c['ops']['finance']
    return f['opening_balance']+sum(r['amount'] for r in f['ledger'])==c['money']


class LedgerMerge(unittest.TestCase):
    def book(self,c,amount,reason,group,category):
        c['money']+=amount
        ops.record_money(c,amount,reason,'staff-order-clothing-1',category,group=group)

    def test_orders_of_a_day_share_one_row_per_group(self):
        c=career();n0=len(c['ops']['finance']['ledger'])
        for i in range(30):
            self.book(c,-7,'Lương đơn riêng · Nhi','Lương đơn riêng · Nhi','wage')
            self.book(c,-3,'Vật tư đơn riêng · Nhi','Vật tư đơn riêng · Nhi','materials')
            self.book(c,40+i,f'Đơn riêng: {i} áo · Nhi','Doanh thu đơn riêng · Nhi','revenue')
            self.book(c,-7,'Lương đơn riêng · Thảo','Lương đơn riêng · Thảo','wage')
        rows=c['ops']['finance']['ledger'][n0:]
        self.assertEqual(len(rows),4)
        by={r['reason']:r['amount'] for r in rows}
        self.assertEqual(by['Lương đơn riêng · Nhi · 30 đơn'],-210)
        self.assertEqual(by['Doanh thu đơn riêng · Nhi · 30 đơn'],sum(40+i for i in range(30)))
        self.assertTrue(all(r['ref'].startswith(ops.SUM) for r in rows))
        self.assertTrue(wallet_ok(c));validate_career(c,'clothing')

    def test_a_new_day_starts_new_rows(self):
        c=career();n0=len(c['ops']['finance']['ledger'])
        self.book(c,-7,'Lương đơn riêng · Nhi','Lương đơn riêng · Nhi','wage')
        c['day']+=1
        self.book(c,-7,'Lương đơn riêng · Nhi','Lương đơn riêng · Nhi','wage')
        rows=c['ops']['finance']['ledger'][n0:]
        self.assertEqual([r['day'] for r in rows],[5,6])
        self.assertEqual([r['reason'] for r in rows],['Lương đơn riêng · Nhi']*2)

    def test_the_cap_starts_a_new_row(self):
        c=career();n0=len(c['ops']['finance']['ledger'])
        for _ in range(3):self.book(c,ops.MERGE_CAP//2+1,'Doanh thu','Doanh thu đơn riêng · Nhi','revenue')
        rows=c['ops']['finance']['ledger'][n0:]
        self.assertEqual(len(rows),3);self.assertTrue(wallet_ok(c))  # each sum would pass the cap

    def test_rows_without_group_are_never_merged(self):
        c=career();n0=len(c['ops']['finance']['ledger'])
        for _ in range(3):
            c['money']+=5;ops.record_money(c,5,'Lương đơn riêng · Nhi','x','wage')
        self.assertEqual(len(c['ops']['finance']['ledger'])-n0,3)

    def test_full_old_book_is_cut_to_the_new_cap_into_the_archive(self):
        c=career();f=c['ops']['finance']
        f['ledger']=[dict(id=f'old-{i}',day=5,turn=0,amount=1,category='wage',reason='x',ref=None) for i in range(1200)]
        c['money']=f['opening_balance']+1200
        with archive.collect() as box:
            self.book(c,1,'Lương đơn riêng · Nhi','Lương đơn riêng · Nhi','wage')
        self.assertEqual(len(f['ledger']),ops.LEDGER_MAX)
        self.assertEqual(len(box.rows),1201-ops.LEDGER_MAX)  # moved, not lost
        self.assertTrue(wallet_ok(c))


if __name__=='__main__':
    unittest.main()
