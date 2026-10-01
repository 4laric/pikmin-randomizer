"""Repeated live surface entries are atomic, token-bound and non-inflating."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experimental import pikmin2_campaign as cave
from experimental.pikmin2_surface_ledger import SurfaceLedger


def transfer(checkpoint, token):
    return cave.entry_text(checkpoint, token).replace('P2_CAVE_ENTRY_1', 'P2_CAVE_TRANSFER_1')


class SurfaceReentryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.ledger=SurfaceLedger(Path(self.tmp.name),'a'*64,'b'*32)
        self.snapshot=dict(region='valley_of_repose',day=2,time=8.5,position=[-210.,80.,1160.],
                           squad=[dict(species='red',maturity=0) for _ in range(20)],health=1.,receipts={})
        self.ledger.create(self.snapshot)

    def entry(self, token, position=None, squad=None, health=.8):
        surface=self.ledger.read()['surface'];cp=cave.initial('a'*64)
        cp.update({k:deepcopy(surface[k]) for k in ('squad','health','receipts')})
        cp['health']=health
        if squad is not None:cp['squad']=squad
        return dict(text=transfer(cp,token),position=position or [-200.,80.,1165.],receipts=cp['receipts'])

    def finish(self, state):
        for _ in range(2):
            trip=state['trip'];cp=trip['checkpoint'];receipts=dict(cp['receipts'],**{'treasure:a':100})
            state=self.ledger.apply_floor(state['revision'],trip['token'],transfer(cp,trip['token']),receipts,{'treasure:a':100})
        return self.ledger.return_to_surface(state['revision'],state['trip']['id'])

    def test_two_visits_capture_current_snapshot_without_recredit(self):
        first='c'*32;payload=self.entry(first)
        returned=self.finish(self.ledger.enter_cave(0,first,native_entry=payload))
        second='d'*32;crew=returned['surface']['squad'][:-1];crew[0]['maturity']=2
        current=self.entry(second,[-180.,80.,1160.],crew,.6)
        entered=self.ledger.enter_cave(4,second,native_entry=current)
        self.assertEqual(entered['trip']['checkpoint']['floor'],1)
        self.assertEqual(entered['surface']['position'],[-180.,80.,1160.])
        self.assertEqual(entered['surface']['squad'],crew)
        self.assertEqual(entered['surface']['health'],.6)
        self.assertEqual(self.ledger.enter_cave(0,first,native_entry=payload),entered)
        final=self.finish(entered)
        self.assertEqual(final['revision'],8)
        self.assertEqual(final['surface']['receipts'],{'treasure:a':100})
        self.assertEqual(self.ledger.enter_cave(4,second,native_entry=current),final)

    def test_old_token_cannot_start_new_visit(self):
        token='c'*32;payload=self.entry(token)
        self.finish(self.ledger.enter_cave(0,token,native_entry=payload))
        with self.assertRaisesRegex(ValueError,'Conflicting replay'):
            self.ledger.enter_cave(4,token,native_entry=payload)
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.ledger.enter_cave(0,'d'*32,native_entry=self.entry('d'*32))

    def test_token_mismatch_and_changed_receipts_rejected(self):
        token='c'*32;payload=self.entry('d'*32)
        with self.assertRaisesRegex(ValueError,'Stale or incomplete'):
            self.ledger.enter_cave(0,token,native_entry=payload)
        payload=self.entry(token);payload['receipts']={'treasure:injected':1}
        with self.assertRaisesRegex(ValueError,'Surface receipts changed'):
            self.ledger.enter_cave(0,token,native_entry=payload)
        self.assertEqual(self.ledger.read()['revision'],0)

    def test_squad_increase_and_conversion_rejected(self):
        token='c'*32
        for crew in (self.snapshot['squad']+[dict(species='red',maturity=0)],
                     [dict(species='purple',maturity=0)]+self.snapshot['squad'][1:]):
            with self.subTest(crew=crew),self.assertRaises(ValueError):
                self.ledger.enter_cave(0,token,native_entry=self.entry(token,squad=crew))

    def test_native_failure_committed_without_position_and_never_revives(self):
        token='c'*32
        payload=dict(text=f'P2_CAVE_TRANSFER_1\n{token}\n1 0 0\n',position=None,receipts={})
        failed=self.ledger.enter_cave(0,token,native_entry=payload)
        self.assertEqual(failed['phase'],'failed');self.assertIsNone(failed['trip']['token'])
        self.assertEqual(failed['trip']['checkpoint']['squad'],[])
        self.assertEqual(self.ledger.enter_cave(0,token,native_entry=payload),failed)
        with self.assertRaisesRegex(ValueError,'already suspended'):
            self.ledger.enter_cave(1,'d'*32)

    def test_missing_position_and_interrupted_write_preserve_previous_state(self):
        token='c'*32;payload=self.entry(token);initial=self.ledger.read()
        payload['position']=None
        with self.assertRaisesRegex(ValueError,'actual native position'):
            self.ledger.enter_cave(0,token,native_entry=payload)
        payload=self.entry(token)
        with patch('randomizer.session.os.replace',side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):self.ledger.enter_cave(0,token,native_entry=payload)
        self.assertEqual(self.ledger.read(),initial)
        self.assertEqual(self.ledger.enter_cave(0,token,native_entry=payload)['revision'],1)


if __name__=='__main__':unittest.main()
