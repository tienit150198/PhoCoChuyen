"""A delayed knife command cannot land on a new run at the same level."""
import copy
from game.engine import GameError
from tests.test_fair import FairBase, story
from tests.test_fair_knife import safe_taps
from game import fair


class KnifeIdentity(FairBase):
    def ready(self):
        state, result = self.act(story(100), 'fair_kn_start', stake=10)
        run = state['journey']['fair_kn']['run']
        taps = safe_taps(fair._kn_sched(run, state['journey']), 3)
        self.clock.t += taps[-1] / 1000
        return state, result['fair']['run']['id'], taps

    def test_current_identity_accepts_partial_taps(self):
        state, identity, taps = self.ready()
        state, result = self.act(state, 'fair_kn_throw', id=identity, lv=1, taps=taps)
        self.assertEqual(result['fair']['run']['tp'], taps)
        self.assertEqual(result['fair']['run']['id'], identity)

    def test_old_run_at_same_level_is_refused_without_mutation(self):
        state, identity, taps = self.ready()
        # Another tab has paid for a new run, still at level one.
        state['journey']['fair_kn']['run']['sd'] += 1
        before = copy.deepcopy(state)
        with self.assertRaises(GameError) as error:
            self.act(state, 'fair_kn_throw', id=identity, lv=1, taps=taps)
        self.assertEqual(error.exception.code, 'fair_kn_over')
        self.assertEqual(state, before)

    def test_legacy_client_without_identity_still_works(self):
        state, _, taps = self.ready()
        _, result = self.act(state, 'fair_kn_throw', lv=1, taps=taps)
        self.assertEqual(result['fair']['run']['tp'], taps)
