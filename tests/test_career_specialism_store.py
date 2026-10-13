import copy
import tempfile
from pathlib import Path
import pytest
from game.storage import Store,Conflict
from game.engine import GameError
from game import career_specialism as sp
from tests.test_career_specialism import prepared


def test_real_store_tuition_replay_reload_stale_and_failed_action_rollback():
    with tempfile.TemporaryDirectory() as d:
        store=Store(Path(d)/'specialism')
        try:
            token,_,_=store.session();s,c=prepared()
            a=store.command(token,'special-import-1',0,'grocery','import_save',{'save':{'format':'mot-ngay-lam-nghe/save-v4','state':s}})
            revision=a['revision'];before=c['money']
            a=store.command(token,'special-enrol-1',revision,'grocery','special_enrol',dict(tier=1))
            b=store.command(token,'special-enrol-1',revision,'grocery','special_enrol',dict(tier=1))
            assert b['replayed'] and b['revision']==a['revision']
            saved,rev,_=store.read(token);assert saved['careers']['grocery']['money']==before-3000
            with pytest.raises(Conflict):store.command(token,'special-stale-1',revision,'grocery','special_practice',dict(tier=1,step=0,answer=1))
            snapshot=copy.deepcopy(saved)
            with pytest.raises(GameError):store.command(token,'special-invalid-1',rev,'grocery','special_practice',dict(tier=1,step=0,answer=True))
            saved,after,_=store.read(token);assert after==rev and saved==snapshot
            for step in range(5):
                result=store.command(token,f'special-practice-{step}',rev,'grocery','special_practice',dict(tier=1,step=step,answer=sp.exercise('grocery',1,step,1)['answer']));rev=result['revision']
            a=store.command(token,'special-offer-1',rev,'grocery','special_offer',dict(tier=1))
            saved,rev,_=store.read(token);o=copy.deepcopy(saved['careers']['grocery']['specialism']['job'])
            store.close_pool();store=Store(Path(d)/'specialism')
            assert store.read(token)[0]['careers']['grocery']['specialism']['job']==o
            a=store.command(token,'special-cancel-1',rev,'grocery','special_cancel',dict(id=o['id']))
            store.command(token,'special-rebook-1',a['revision'],'grocery','special_offer',dict(tier=1))
            assert store.read(token)[0]['careers']['grocery']['specialism']['job']==o
        finally:store.close_pool()
