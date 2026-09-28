from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from experimental.pikmin2_beasts_checkpoint_reference import BeastsReferenceAdapter
from experimental.pikmin2_beasts_surface_ledger import BeastsSurfaceLedger
from experimental.pikmin2_surface_ledger import SurfaceLedger
from randomizer.session import SessionLock, atomic_write
from tests.test_pikmin2_beasts_checkpoint_reference import audit,party,context,events
from tests.test_pikmin2_surface_ledger import snapshot,CONTENT,CAMPAIGN,TRIP


class BeastsLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name)
        self.adapter=BeastsReferenceAdapter(audit(),CONTENT,{1:{'beasts:key':100},2:{},3:{}})
        self.ledger=self.reopen();self.start=self.ledger.create(snapshot())

    def reopen(self):return BeastsSurfaceLedger(self.directory,CONTENT,CAMPAIGN,self.adapter)

    def floor2(self):
        entered=self.ledger.enter_beasts(0,TRIP)
        payload=dict(squad=party(),health=.7,receipts={**snapshot()['receipts'],'beasts:key':100},conversions=[],destination_context=context(19))
        second=self.reopen().apply_beasts_floor(1,entered['trip']['token'],**payload)
        return entered,second,payload

    def test_restart_every_boundary_and_exact_replay(self):
        entered,second,payload=self.floor2()
        self.assertEqual(self.reopen().read(),second)
        self.assertEqual(second['surface'],snapshot())
        self.assertEqual(second['trip']['checkpoint']['context'],context(19))
        self.assertFalse(self.reopen().launch_requirement()['native_ready'])
        final=dict(squad=party(10,10),health=.625,receipts=payload['receipts'],conversions=events(),destination_context={})
        third=self.reopen().apply_beasts_floor(2,second['trip']['token'],**final)
        self.assertEqual(third['trip']['checkpoint']['floor'],3)
        self.assertEqual(self.reopen().read(),third)
        self.assertEqual(self.reopen().apply_beasts_floor(2,second['trip']['token'],**final),third)
        self.assertEqual(self.reopen().apply_beasts_floor(1,entered['trip']['token'],**payload),third)
        self.assertEqual(self.reopen().enter_beasts(0,TRIP),third)
        self.assertEqual(self.reopen().create(snapshot()),third)
        with self.assertRaises(ValueError):self.reopen().launch_requirement()
        with self.assertRaises(ValueError):self.reopen().return_to_surface(3,TRIP)
        self.assertEqual({p.name for p in self.directory.iterdir()},{'surface-ledger.json','runner.lock'})

    def test_conflict_stale_and_invalid_transition_leave_bytes_unchanged(self):
        entered,second,payload=self.floor2();original=self.ledger.path.read_bytes()
        bad=deepcopy(payload);bad['health']=.6
        for revision,token,request in ((1,entered['trip']['token'],bad),(1,second['trip']['token'],payload),
                                       (2,second['trip']['token'],dict(payload,conversions=[],squad=party(10,10),destination_context={}))):
            with self.subTest(revision=revision),self.assertRaises(ValueError):self.ledger.apply_beasts_floor(revision,token,**request)
            self.assertEqual(self.ledger.path.read_bytes(),original)

    def test_interrupted_replace_and_uncertain_commit(self):
        with patch('randomizer.session.os.replace',side_effect=OSError('before commit')):
            with self.assertRaises(OSError):self.ledger.enter_beasts(0,TRIP)
        self.assertEqual(self.reopen().read(),self.start)
        def committed_then_error(path,text):
            atomic_write(path,text)
            raise OSError('response lost after commit')
        with patch('experimental.pikmin2_surface_ledger.atomic_write',side_effect=committed_then_error):
            with self.assertRaises(OSError):self.ledger.enter_beasts(0,TRIP)
        saved=self.reopen().read()
        self.assertEqual(self.reopen().enter_beasts(0,TRIP),saved)
        payload=dict(squad=party(),health=.7,receipts=snapshot()['receipts'],conversions=[],destination_context=context(19))
        with patch('randomizer.session.os.replace',side_effect=OSError('before floor commit')):
            with self.assertRaises(OSError):self.ledger.apply_beasts_floor(1,saved['trip']['token'],**payload)
        self.assertEqual(self.reopen().read(),saved)

    def test_failure_remains_terminal_after_restart(self):
        entered=self.ledger.enter_beasts(0,TRIP)
        request=dict(squad=[],health=0,receipts=snapshot()['receipts'],conversions=[],destination_context={})
        failed=self.ledger.apply_beasts_floor(1,entered['trip']['token'],**request)
        self.assertEqual(self.reopen().read()['phase'],'failed')
        self.assertEqual(self.reopen().apply_beasts_floor(1,entered['trip']['token'],**request),failed)
        with self.assertRaises(ValueError):self.reopen().launch_requirement()
        with self.assertRaises(ValueError):self.reopen().enter_beasts(2,'d'*32)

    def test_wrong_writer_profile_campaign_and_lock(self):
        self.ledger.enter_beasts(0,TRIP)
        with self.assertRaises(ValueError):SurfaceLedger(self.directory,CONTENT,CAMPAIGN).read()
        other=BeastsReferenceAdapter(audit(),CONTENT,{1:{},2:{},3:{}})
        with self.assertRaises(ValueError):BeastsSurfaceLedger(self.directory,CONTENT,CAMPAIGN,other).read()
        with self.assertRaises(ValueError):BeastsSurfaceLedger(self.directory,CONTENT,'d'*32,self.adapter).read()
        with SessionLock(self.directory):
            with self.assertRaises(ValueError):self.reopen().read()

    def test_existing_tutorial_cannot_migrate(self):
        SurfaceLedger(self.directory,CONTENT,CAMPAIGN).enter_cave(0,TRIP)
        original=self.ledger.path.read_bytes()
        with self.assertRaises(ValueError):self.reopen().read()
        self.assertEqual(self.ledger.path.read_bytes(),original)
