"""Expired nearby speech is bounded without discarding pending moderation evidence."""
import time

from tests.live_support import LiveCase


class TownSocialRetention(LiveCase):
    cfg_extra = dict(town=True)

    async def asyncSetUp(self):
        await super().asyncSetUp()
        token, _ = self.account('Retention test')
        await self.connect(token)

    async def message(self, channel, at, reports=0, reviewed=None):
        row = await self.app.db.fetchrow(
            'INSERT INTO chat_messages(channel,pid,text,at,reports,reviewed_at) VALUES(?,?,?,?,?,?) RETURNING id',
            (channel, 'author', 'retained evidence', at, reports, reviewed))
        return int(row['id'])

    async def test_expired_rows_dependencies_and_pending_reports(self):
        now = time.time()
        old = now - 86401
        gone = await self.message('iso-talk:old', old, reports=1, reviewed=now - 100)
        pending = await self.message('iso-talk:pending', old, reports=1)
        fresh = await self.message('iso-talk:fresh', now - 30)
        other = await self.message('dm:unrelated', old)
        for mid in (gone, pending):
            await self.app.db.execute(
                "INSERT INTO reports(reporter,kind,target,reason,at) VALUES('reader','chat',?,'other',?)",
                (str(mid), old))
            await self.app.db.execute("INSERT INTO chat_reacts(msg,pid,emoji,at) VALUES(?,'reader','❤️',?)", (mid, old))
            await self.app.db.execute("INSERT INTO chat_hides(pid,msg,at) VALUES('reader',?,?)", (mid, old))
            self.app.chat.reacts.put(mid, {'❤️': 1})
        # A different report kind with the same numeric target is not chat evidence.
        await self.app.db.execute(
            "INSERT INTO reports(reporter,kind,target,reason,at) VALUES('reader','profile',?,'other',?)",
            (str(gone), old))
        town = self.app.by_name['town']
        self.assertTrue(hasattr(town, 'prune_social_messages'), 'nearby speech needs a retention cleanup')
        self.assertEqual(await town.prune_social_messages(now=now), 1)
        remaining = {int(r['id']) for r in await self.app.db.fetch('SELECT id FROM chat_messages')}
        self.assertEqual(remaining, {pending, fresh, other})
        for table in ('chat_reacts', 'chat_hides'):
            self.assertEqual([int(r['msg']) for r in await self.app.db.fetch(f'SELECT msg FROM {table}')], [pending])
        reports = {(r['kind'], r['target']) for r in await self.app.db.fetch('SELECT kind,target FROM reports')}
        self.assertEqual(reports, {('chat', str(pending)), ('profile', str(gone))})
        self.assertNotIn(gone, self.app.chat.reacts)
        self.assertIn(pending, self.app.chat.reacts)

    async def test_one_cleanup_cannot_exceed_batch(self):
        now = time.time()
        for n in range(5):
            await self.message(f'iso-talk:{n}', now - 86401)
        town = self.app.by_name['town']
        self.assertTrue(hasattr(town, 'prune_social_messages'), 'nearby speech needs a retention cleanup')
        self.assertEqual(await town.prune_social_messages(now=now, batch=2), 2)
        self.assertEqual(await self.app.db.fetchval('SELECT COUNT(*) FROM chat_messages'), 3)
        self.assertEqual(await town.prune_social_messages(now=now, batch=2), 2)
        self.assertEqual(await town.prune_social_messages(now=now, batch=2), 1)
        self.assertEqual(await town.prune_social_messages(now=now, batch=2), 0)
