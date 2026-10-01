import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from workflow.spend import hourly_spend
from workflow.dashboard import render_dashboard


class HourlySpendTests(unittest.TestCase):
    def test_scoped_completed_window_deduplicates_sessions_and_splits_models(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'cost.db'
            db=sqlite3.connect(path)
            db.execute('CREATE TABLE message(session_id TEXT,time_updated INTEGER,data TEXT)')
            for session,completed,cost,model in [('a',10000,1,'muse'),('a',7000,2,'deepseek'),
                    ('a',6400,99,'muse'),('a',10001,99,'muse'),('other',9000,99,'muse'),
                    ('a',9000,0,'unknown'),('a',None,999,'muse')]:
                db.execute('INSERT INTO message VALUES(?,?,?)',(session,10000000,json.dumps(dict(
                    role='assistant',time=dict(completed=completed*1000 if completed else None),
                    cost=cost,providerID='go',modelID=model))))
            db.commit();db.close()
            state=dict(lanes={'x':dict(task_id='opencode:a'),'y':dict(task_id='opencode:a')},
                       control=dict(launches={'z':dict(session='a')}))
            result=hourly_spend(state,10000,path)
            self.assertEqual(result['amount'],3)
            self.assertEqual(result['sessions'],1)
            self.assertEqual(result['by_model'],{'go/muse':1,'go/deepseek':2})
            self.assertEqual(result['status'],'partial')
            self.assertEqual(result['unpriced_messages'],1)

    def test_missing_database_is_unavailable_not_free(self):
        with tempfile.TemporaryDirectory() as directory:
            result=hourly_spend({},10000,Path(directory)/'absent.db')
            self.assertIsNone(result['amount'])
            self.assertEqual(result['status'],'unavailable')

    def test_dashboard_labels_window_partial_estimate_and_fallback(self):
        html=render_dashboard(dict(hourly_spend=dict(amount=1.234,status='partial',by_model={'<model>':1.234})))
        self.assertIn('Worker spend · last 60 min',html)
        self.assertIn('$1.23 USD · partial',html)
        self.assertIn('&lt;model&gt;',html)
        self.assertIn('excludes Codex',html)
        fallback=render_dashboard(dict(metrics=dict(costs=dict(recorded_by_currency={'USD':2}))))
        self.assertIn('$2.00 USD · partial logs only',fallback)
