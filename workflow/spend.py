"""Read provider-reported cost for workflow sessions, never the whole account."""
import json
import math
import sqlite3
from pathlib import Path


def hourly_spend(state, now, database=None):
    sessions = {l.get('task_id', '').removeprefix('opencode:')
                for l in state.get('lanes', {}).values() if l.get('task_id', '').startswith('opencode:')}
    sessions.update(x['session'] for x in state.get('control', {}).get('launches', {}).values() if x.get('session'))
    result = dict(currency='USD', window_seconds=3600, source='OpenCode completed message costs',
                  scope='Workflow OpenCode sessions only; excludes Codex and unrelated account usage',
                  sessions=len(sessions), priced_messages=0, unpriced_messages=0, by_model={})
    database = Path(database) if database is not None else Path.home()/'.local/share/opencode/opencode.db'
    try:
        db = sqlite3.connect(database.resolve().as_uri()+'?mode=ro', uri=True, timeout=1)
        try:
            # Query per session to use the session index, not scan the account DB.
            for session in sorted(sessions):
                for raw, in db.execute('SELECT data FROM message WHERE session_id=? AND time_updated>=?',
                                       (session, (now-3600)*1000)):
                    message = json.loads(raw)
                    if message.get('role') != 'assistant': continue
                    completed = message.get('time', {}).get('completed')
                    if type(completed) not in (int,float) or not (now-3600)*1000 < completed <= now*1000: continue
                    cost = message.get('cost')
                    if type(cost) not in (int,float) or not math.isfinite(cost) or cost <= 0:
                        result['unpriced_messages'] += 1
                        continue
                    model = str(message.get('providerID', 'unknown')) + '/' + str(message.get('modelID', 'unknown'))
                    result['by_model'][model] = result['by_model'].get(model, 0) + cost
                    result['priced_messages'] += 1
        finally:
            db.close()
    except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
        return dict(result, amount=None, by_model={}, status='unavailable', error=str(exc))
    return dict(result, amount=sum(result['by_model'].values()) if result['priced_messages'] else None,
                status='partial' if result['unpriced_messages'] else 'reported' if result['priced_messages'] else 'unavailable')
