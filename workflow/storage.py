"""Incremental SQLite documents behind the existing atomic Registry interface.

Format 2 is opt-in. Its header fails closed in old Registry implementations.
The original JSON is retained inside the migration transaction for recovery.
"""
import json
import sqlite3
from contextlib import contextmanager
from .handoff import require

MAPS = [('lanes',), ('leases',), ('queue',), ('actions',),
        ('control', 'launches'), ('throughput', 'jobs'), ('throughput', 'workers'),
        ('control','shepherd'), ('control','notices'), ('control','terminal_recoveries'),
        ('control','decisions'), ('control','model_limit_attempts'),
        ('throughput','assignments'), ('throughput','costs'), ('throughput','snapshots'),
        ('throughput','dispositions'), ('throughput_runtime','launch_specs'),
        ('throughput', 'batches'), ('throughput', 'workstreams'),
        ('throughput_runtime', 'autofill', 'items'),
        ('throughput_runtime', 'autofill', 'prerequisite_recovery'),
        ('consumer_verifications',), ('support_actions',), ('delivery_contracts',),
        ('terminal_cleanup',)]
LISTS = [('events',), ('stage_timing', 'history')]
CHUNK = 128


def container(state, path):
    node = state
    for key in path[:-1]:
        node = node.get(key, {})
    return node


def documents(state):
    # Copy only container spines; never duplicate all historical lane/launch data.
    meta = dict(state)
    rows = {}
    order = {}
    for path in MAPS + LISTS:
        parent = meta
        for key in path[:-1]:
            if key not in parent: break
            parent[key] = dict(parent[key])
            parent = parent[key]
        else:
            if path[-1] not in parent: continue
            value = parent[path[-1]]
            if value is None: continue  # Optional controller observations may be absent.
            section = json.dumps(path)
            if path in MAPS:
                require(isinstance(value, dict), 'Registry map shape changed: ' + section)
                rows.update({(section, key): json.dumps(v) for key, v in value.items()})
                order[section] = list(value)
                parent[path[-1]] = {}
            else:
                require(isinstance(value, list), 'Registry history shape changed: ' + section)
                rows.update({(section, str(i)): json.dumps(value[i:i+CHUNK])
                             for i in range(0, len(value), CHUNK)})
                parent[path[-1]] = []
    rows[('', '')] = json.dumps(meta)
    rows[('', 'order')] = json.dumps(order)
    return rows


def load(db, section_path=None):
    header = db.execute('SELECT body FROM registry WHERE id=1').fetchone()
    require(header is not None, 'Registry not initialized')
    descriptor = json.loads(header[0])
    if descriptor.get('schema') != 2:
        return descriptor, header[0]
    require(descriptor.get('storage') == 'documents-v1', 'Unknown registry storage')
    if section_path is None:
        records=db.execute('SELECT section, key, body FROM registry_documents')
    else:
        wanted=['']+[json.dumps(path) for path in MAPS+LISTS if path[:len(section_path)]==section_path]
        records=db.execute('SELECT section,key,body FROM registry_documents WHERE section IN ('+
                           ','.join('?' for _ in wanted)+')',wanted)
    raw = {(section, key): body for section, key, body in records}
    state = json.loads(raw[('', '')])
    order = json.loads(raw[('', 'order')])
    paths = {section:tuple(json.loads(section)) for section in {s for s,k in raw if s}}
    lists = {}
    for (section, key), body in raw.items():
        if not section: continue
        path = paths[section]
        parent = container(state, path)
        if path in MAPS:
            parent[path[-1]][key] = json.loads(body)
        else:
            require(path in LISTS, 'Unknown registry document section')
            lists.setdefault(path, []).append((int(key), json.loads(body)))
    for path, chunks in lists.items():
        value = container(state, path)[path[-1]]
        for offset, chunk in sorted(chunks):
            require(offset == len(value), 'Incomplete registry history')
            value.extend(chunk)
    for section, keys in order.items():
        path = tuple(json.loads(section))
        if section_path is not None and path[:len(section_path)]!=section_path:continue
        parent = container(state, path)
        values = parent[path[-1]]
        require(set(values) == set(keys), 'Incomplete registry map')
        parent[path[-1]] = {key: values[key] for key in keys}
    require(state.get('root') == descriptor.get('root'), 'Registry storage workspace mismatch')
    return state, raw


@contextmanager
def selected(reg, selections):
    """Update existing named records atomically; no partial state is exposed.

The callback gets {(path_tuple, key): value}. Missing records stay None and
cannot be inserted here: creation must also update ordered membership.
"""
    require(not getattr(reg._transaction_local, 'active', False), 'Nested registry write transaction')
    db = sqlite3.connect(reg.path, timeout=30)
    reg._transaction_local.active = True
    from .write_gate import gate
    writer=gate(reg.path);entered=False
    try:
        writer.acquire();entered=True
        db.execute('BEGIN IMMEDIATE')
        raw_header = db.execute('SELECT body FROM registry WHERE id=1').fetchone()[0]
        header = json.loads(raw_header)
        require(header['root'] == str(reg.root) and header['schema'] in (1,2), 'Registry workspace/schema mismatch')
        if header['schema'] == 1:
            values = {(path,key):(header if path==() and key=='' else
                       container(header,path).get(path[-1],{}).get(key)) for path,key in selections}
            present = {k for k,v in values.items() if v is not None}
            yield values
            require(set(values)==set(selections) and {k for k,v in values.items() if v is not None}==present,
                    'Use Registry transaction for record creation/deletion')
            for (path,key), value in values.items():
                if path==() and key=='':header=value
                elif value is not None: container(header,path)[path[-1]][key] = value
            save(db, header, raw_header)
        else:
            require(header.get('storage') == 'documents-v1', 'Unknown registry storage')
            original = {}
            values = {}
            for path,key in selections:
                require(path in MAPS or (path==() and key==''), 'Named map required')
                row=db.execute('SELECT body FROM registry_documents WHERE section=? AND key=?',
                               (json.dumps(path) if path else '',key)).fetchone()
                original[(path,key)]=row[0] if row else None
                values[(path,key)]=json.loads(row[0]) if row else None
            yield values
            require(set(values)==set(original), 'Selected record set changed')
            for (path,key), value in values.items():
                before=original[(path,key)]
                require((before is None)==(value is None), 'Use Registry transaction for record creation/deletion')
                if value is None:continue
                if path==() and key=='':
                    old=json.loads(before)
                    require(value.get('schema')==old.get('schema') and value.get('root')==old.get('root'),
                            'Metadata ownership cannot change')
                    for partition in MAPS+LISTS:
                        was=container(old,partition).get(partition[-1])
                        now=container(value,partition).get(partition[-1])
                        require(was==now or (was is None and now in ({},[])),
                                'Use full transaction to modify partitioned collections')
                after=json.dumps(value)
                if after!=before:
                    db.execute('UPDATE registry_documents SET body=? WHERE section=? AND key=?',
                               (after,json.dumps(path) if path else '',key))
        db.commit()
    except BaseException:
        db.rollback();raise
    finally:
        db.close()
        if entered:writer.release()
        reg._transaction_local.active=False


def read_record(reg, path, key):
    """Read one committed record without decoding historical unrelated rows."""
    db=sqlite3.connect(reg.path,timeout=30)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        header=json.loads(db.execute('SELECT body FROM registry WHERE id=1').fetchone()[0])
        require(header['root']==str(reg.root) and header['schema'] in (1,2),'Registry workspace/schema mismatch')
        if header['schema']==1:
            return header if path==() and key=='' else container(header,path).get(path[-1],{}).get(key)
        require(header.get('storage')=='documents-v1','Unknown registry storage')
        row=db.execute('SELECT body FROM registry_documents WHERE section=? AND key=?',
                       (json.dumps(path) if path else '',key)).fetchone()
        return json.loads(row[0]) if row else None
    finally:db.close()


def save(db, state, previous):
    if isinstance(previous, str):
        encoded = json.dumps(state)
        if encoded != previous:
            db.execute('UPDATE registry SET body=? WHERE id=1', (encoded,))
        return
    current = documents(state)
    db.executemany('DELETE FROM registry_documents WHERE section=? AND key=?',
                   previous.keys() - current.keys())
    db.executemany('INSERT INTO registry_documents VALUES (?,?,?) '
                   'ON CONFLICT(section,key) DO UPDATE SET body=excluded.body',
                   [(section, key, body) for (section, key), body in current.items()
                    if previous.get((section, key)) != body])


def migrate(reg):
    """Atomic exact-state migration; no worker/lane/lease transitions."""
    db = sqlite3.connect(reg.path, timeout=30)
    try:
        db.execute('BEGIN IMMEDIATE')
        state, original = load(db)
        require(state['schema'] == 1 and state['root'] == str(reg.root), 'Registry workspace/schema mismatch')
        if not isinstance(original, str):
            db.rollback()
            return dict(migrated=False, format='documents-v1')
        db.execute('CREATE TABLE registry_documents (section TEXT NOT NULL, key TEXT NOT NULL, '
                   'body TEXT NOT NULL, PRIMARY KEY(section,key)) WITHOUT ROWID')
        db.execute('CREATE TABLE registry_legacy_backup (body TEXT NOT NULL)')
        db.execute('INSERT INTO registry_legacy_backup VALUES (?)', (original,))
        save(db, state, {})
        db.execute('UPDATE registry SET body=? WHERE id=1',
                   (json.dumps(dict(schema=2, root=str(reg.root), storage='documents-v1')),))
        # Old code also fails on schema=2. Prevent direct legacy UPDATE scripts
        # from replacing the header and silently discarding normalized writes.
        db.execute("CREATE TRIGGER registry_legacy_write_guard BEFORE UPDATE ON registry "
                   "BEGIN SELECT RAISE(ABORT, 'Use current Registry API: normalized storage'); END")
        db.execute("CREATE TRIGGER registry_legacy_delete_guard BEFORE DELETE ON registry "
                   "BEGIN SELECT RAISE(ABORT, 'Use current Registry API: normalized storage'); END")
        restored, _ = load(db)
        require(restored == state, 'Registry migration round-trip mismatch')
        db.commit()
        return dict(migrated=True, format='documents-v1', original_bytes=len(original),
                    documents=db.execute('SELECT count(*) FROM registry_documents').fetchone()[0])
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    import argparse
    from pathlib import Path
    from .registry import Registry
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--migrate',action='store_true',required=True)
    args=parser.parse_args()
    reg=Registry(args.root/'output/workflow/registry.sqlite3',args.root)
    print(json.dumps(migrate(reg),indent=2))


if __name__=='__main__':main()
