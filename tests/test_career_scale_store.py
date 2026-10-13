"""Database receipts persist scale reservations and prevent duplicate purchases."""
import copy
import tempfile
from pathlib import Path
from game.storage import Store, Conflict
from game.engine import GameError
from tests.test_career_scale_integration import prepared
import pytest


def test_store_purchase_reservation_reconnect_and_replay():
    with tempfile.TemporaryDirectory() as directory:
        store=Store(Path(directory)/'scale')
        try:
            token,_,_=store.session()
            state=prepared('grocery',1)
            result=store.command(token,'scale-import-001',0,'grocery','import_save',
                                 {'save':{'format':'mot-ngay-lam-nghe/save-v1','state':state}})
            rev=result['revision']
            payload={'site':'base','code':__import__('game.career_scale_content',fromlist=['profile']).profile('grocery').materials[0].code,'quantity':2}
            a=store.command(token,'scale-stock-0001',rev,'grocery','scale_stock_buy',payload)
            b=store.command(token,'scale-stock-0001',rev,'grocery','scale_stock_buy',payload)
            assert b['replayed'] and a['revision']==b['revision']
            assert len(store.read(token)[0]['careers']['grocery']['scale_stock']['orders'])==1
            with pytest.raises(Conflict):store.command(token,'scale-stale-0001',rev,'grocery','scale_stock_buy',payload)
            rev=a['revision'];a=store.command(token,'scale-offer-0001',rev,'grocery','scale_offer',{})
            state,rev,_=store.read(token)
            offer=copy.deepcopy(state['careers']['grocery']['scale_contracts']['offer'])
            store.command(token,'scale-cancel-001',rev,'grocery','scale_cancel',{'id':offer['id']})
            state,rev,_=store.read(token)
            a=store.command(token,'scale-offer-0002',rev,'grocery','scale_offer',{})
            state,rev,_=store.read(token)
            assert state['careers']['grocery']['scale_contracts']['offer']==offer
            with pytest.raises(GameError):store.command(token,'scale-bad-0001',rev,'grocery','scale_allocate',{'id':offer['id'],'site':'base','code':payload['code'],'units':999999})
            assert store.read(token)[1]==rev
        finally:store.close_pool()
