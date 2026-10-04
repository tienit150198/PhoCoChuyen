"""Chat friend lookup shares only a public player code after message/account/block checks."""
import unittest
import subprocess
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from live.chat import ChatFeature
from live.protocol import LiveError


class FriendCard(unittest.IsolatedAsyncioTestCase):
    def setup_feature(self, account=True, hidden=False):
        p = SimpleNamespace(pid='me', sid='save-me', account=account, hidden={'other'} if hidden else set())
        other = SimpleNamespace(pid='other', sid='save-other', account=True)
        db = SimpleNamespace(fetchrow=AsyncMock(return_value={'pid':'other','channel':'town','hidden':0,'deleted':0}),
                             fetchval=AsyncMock(side_effect=[False, 'PCC-ABC234']))
        app = SimpleNamespace(db=db, hub=SimpleNamespace(players={'other':other}), cfg=SimpleNamespace())
        feature = ChatFeature.__new__(ChatFeature)
        feature.app, feature.hub, feature.cfg = app, app.hub, app.cfg
        feature.member_chan = AsyncMock(return_value=SimpleNamespace(cleared={}))
        feature.load_hidden = AsyncMock()
        feature.my_hides = AsyncMock(return_value=set())
        return feature, SimpleNamespace(player=p)

    async def test_public_code_without_private_identity(self):
        f,c=self.setup_feature()
        out=await f.friend_card(c, {'id':12})
        self.assertEqual(out, {'t':'friend_card','id':12,'pid':'other','code':'PCC-ABC234'})
        f.member_chan.assert_awaited_once_with(c.player,'town')

    async def test_guest_blocked_hidden_and_private_messages_denied(self):
        for account,hidden in [(False,False),(True,True)]:
            f,c=self.setup_feature(account,hidden)
            with self.assertRaises(LiveError): await f.friend_card(c, {'id':12})
        f,c=self.setup_feature()
        f.member_chan.side_effect=LiveError('no_chat')
        with self.assertRaises(LiveError): await f.friend_card(c, {'id':12})
        f,c=self.setup_feature()
        f.db.fetchrow.return_value['deleted']=1
        with self.assertRaises(LiveError): await f.friend_card(c, {'id':12})

    async def test_guest_target_cannot_be_added(self):
        f,c=self.setup_feature();f.hub.players['other'].account=False
        with self.assertRaises(LiveError): await f.friend_card(c, {'id':12})

    async def test_cleared_conversation_message_cannot_expose_code(self):
        f,c=self.setup_feature()
        f.member_chan.return_value.cleared={'me':12}
        with self.assertRaises(LiveError): await f.friend_card(c,{'id':12})
        f.db.fetchval.assert_not_awaited()

    async def test_social_blocks_are_reloaded_before_lookup(self):
        for blocker in ('me','other'):
            f,c=self.setup_feature()
            db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
            try:
                db.execute('CREATE TABLE blocks(pid TEXT,target TEXT)')
                db.execute('CREATE TABLE marriage_blocks(sid TEXT,target TEXT)')
                db.execute('INSERT INTO blocks VALUES(?,?)',(blocker,'other' if blocker=='me' else 'me'))
                f.db.fetch=AsyncMock(side_effect=lambda query,params:db.execute(query,params).fetchall())
                f.load_hidden=ChatFeature.load_hidden.__get__(f,ChatFeature)
                with self.subTest(blocker=blocker),self.assertRaises(LiveError):
                    await f.friend_card(c,{'id':12})
                f.db.fetchval.assert_not_awaited()
            finally:
                db.close()

    async def test_self_malformed_and_bidirectional_block_denied(self):
        for mid in (None,True,0,'12'):
            f,c=self.setup_feature()
            with self.assertRaises(LiveError): await f.friend_card(c, {'id':mid})
        f,c=self.setup_feature();f.db.fetchrow.return_value['pid']='me'
        with self.assertRaises(LiveError): await f.friend_card(c, {'id':12})
        f,c=self.setup_feature();f.db.fetchval.side_effect=[True]
        with self.assertRaises(LiveError): await f.friend_card(c, {'id':12})

    async def test_offline_account_public_code_lookup(self):
        f,c=self.setup_feature();f.hub.players={}
        f.db.fetchval.side_effect=['save-other',False,'PCC-ABC234']
        self.assertEqual((await f.friend_card(c,{'id':12}))['code'],'PCC-ABC234')

    async def test_public_code_created_once_when_absent(self):
        f,c=self.setup_feature();f.db.execute=AsyncMock()
        f.db.fetchval.side_effect=[False,None,'PCC-ABC234']
        result=await f.friend_card(c,{'id':12})
        self.assertEqual(result['code'],'PCC-ABC234')
        f.db.execute.assert_awaited_once()
        self.assertNotIn('sid',result)


class RoomInput(unittest.TestCase):
    def test_ascii_and_composition_in_real_binding(self):
        subprocess.run(['node','tests/booth_input.mjs'],cwd=Path(__file__).resolve().parents[1],check=True,capture_output=True)
