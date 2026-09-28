import copy
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from workflow.registry import Registry
from workflow.storage import migrate


class StorageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.reg = Registry(self.root/'output/registry.sqlite3', self.root)
        self.reg.init()
        with self.reg.transaction() as s:
            s['lanes'] = {'z': {'state':'blocked'}, 'a': {'state':'done'}}
            s['events'] = [{'i':i} for i in range(260)]
            s['control'] = {'launches': {'z':{'status':'running'}, 'a':{'status':'exited'}}}
            s['stage_timing'] = {'history':[{'i':i} for i in range(140)]}
        self.before = self.reg.snapshot()

    def test_exact_roundtrip_order_idempotence_and_legacy_guard(self):
        self.assertTrue(migrate(self.reg)['migrated'])
        self.assertEqual(self.before, self.reg.snapshot())
        self.assertEqual(list(self.reg.snapshot()['lanes']), ['z','a'])
        self.assertEqual(self.reg.snapshot(section=('control',)),self.before['control'])
        self.assertFalse(migrate(self.reg)['migrated'])
        db=sqlite3.connect(self.reg.path)
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE registry SET body='{}'")
            db.rollback()
            self.assertTrue(db.execute('SELECT body FROM registry_legacy_backup').fetchone())
        finally: db.close()

    def test_atomic_mutations_and_rollback(self):
        migrate(self.reg)
        with self.assertRaises(RuntimeError):
            with self.reg.transaction() as s:
                s['events'].append({'new':True}); s['lanes']['a']['state']='running'
                raise RuntimeError('interrupted')
        self.assertEqual(self.before,self.reg.snapshot())
        with self.reg.transaction() as s:
            del s['lanes']['z']; s['lanes']['new']={'state':'ready'}
            s['events'].append({'new':True}); s['stage_timing']['history']=s['stage_timing']['history'][-3:]
            expected=copy.deepcopy(s)
        self.assertEqual(expected,self.reg.snapshot())

    def test_optional_document_map_can_be_none_then_restored(self):
        with self.reg.transaction() as s:s['control']['shepherd']=None
        migrate(self.reg)
        self.assertIsNone(self.reg.control_status()['shepherd'])
        with self.reg.transaction() as s:s['control']['shepherd']={'id':'packet'}
        self.assertEqual(self.reg.control_status()['shepherd'],{'id':'packet'})
        with self.reg.transaction() as s:s['control']['shepherd']=None
        self.assertIsNone(self.reg.control_status()['shepherd'])

    def test_reader_sees_previous_commit_and_parallel_writes_preserve_updates(self):
        migrate(self.reg)
        with self.reg.transaction() as s:
            s['settings']['max_heavy_builds']=99
            self.assertEqual(self.reg.snapshot()['settings']['max_heavy_builds'],2)
        errors=[]
        def work():
            try:
                reg=Registry(self.reg.path,self.root)
                for _ in range(10):
                    with reg.transaction() as s:s['counter']=s.get('counter',0)+1
            except Exception as exc: errors.append(exc)
        threads=[threading.Thread(target=work) for _ in range(3)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(errors,[]); self.assertEqual(self.reg.snapshot()['counter'],30)

    def test_small_write_changes_only_relevant_documents(self):
        migrate(self.reg)
        db=sqlite3.connect(self.reg.path)
        try:
            db.execute('CREATE TABLE changes (section TEXT, key TEXT)')
            db.execute('CREATE TRIGGER audit_write AFTER UPDATE ON registry_documents BEGIN '
                       'INSERT INTO changes VALUES (new.section,new.key); END')
            db.commit()
            with self.reg.transaction() as s:s['lanes']['a']['heartbeat_at']=5
            self.assertEqual(db.execute('SELECT section,key FROM changes').fetchall(),[('["lanes"]','a')])
        finally:db.close()

    def test_selected_update_rolls_back_and_rejects_new_or_deleted_records(self):
        from workflow.storage import selected
        from workflow.handoff import Rejected
        migrate(self.reg)
        for change in ('raise','add','delete'):
            with self.assertRaises((RuntimeError,Rejected)):
                with selected(self.reg,[(('lanes',),'z')]) as rows:
                    rows[(('lanes',),'z')]['state']='running'
                    if change=='raise':raise RuntimeError('crash')
                    if change=='add':rows[(('lanes',),'new')]={}
                    if change=='delete':rows[(('lanes',),'z')]=None
            self.assertEqual(self.reg.snapshot(),self.before)

    def test_metadata_update_preserves_partitioned_history(self):
        from workflow.storage import selected,read_record
        from workflow.handoff import Rejected
        migrate(self.reg)
        with selected(self.reg,[((), '')]) as rows:rows[((), '')]['control']['ram_paused']=True
        self.assertTrue(self.reg.control_status()['ram_paused'])
        self.assertEqual(read_record(self.reg,('lanes',),'a'),self.before['lanes']['a'])
        with self.assertRaises(Rejected):
            with selected(self.reg,[((), '')]) as rows:rows[((), '')]['lanes']['bad']={}
        self.assertEqual(self.reg.snapshot()['lanes'],self.before['lanes'])




if __name__=='__main__':unittest.main()
