"""Incremental SQLite documents behind the existing atomic Registry interface.

Format 2 is opt-in. Its header fails closed in old Registry implementations.
The original JSON is retained inside the migration transaction for recovery.
Sectioned reads/writes decode only declared partitions plus the meta row; every
undeclared partition is a Sealed placeholder that refuses any use.
"""
import json
import random
import sqlite3
import time
from contextlib import contextmanager
from .handoff import Rejected, require

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


PARTS = MAPS + LISTS
# Worst case per BEGIN, COMMIT or read stays within the former single 30 s wait: the in-process
# FIFO writer gate is held across the retries, so a longer budget would stall every thread behind it.
BUSY_TIMEOUT, BUSY_ATTEMPTS, BUSY_BUDGET = 9, 3, 30


def backoff(attempt):
    return min(2.0, .2 * 2 ** attempt)


def budget(attempts=None, timeout=None):
    """Worst-case seconds one retried step can wait (SQLite timeouts plus maximal jitter)."""
    attempts, timeout = attempts or BUSY_ATTEMPTS, BUSY_TIMEOUT if timeout is None else timeout
    return attempts * timeout + sum(backoff(a) * 1.5 for a in range(attempts - 1))


class RegistryBusy(sqlite3.OperationalError):
    """The lock stayed busy for the whole retry budget; nothing was committed."""


def busy(exc):
    return isinstance(exc, sqlite3.OperationalError) and any(
        word in str(exc).lower() for word in ('database is locked', 'database is busy', 'database table is locked'))


def retry(step, what, *, attempts=None, sleep=time.sleep, jitter=random.random):
    """Bounded jittered retry of one step that is safe to repeat (BEGIN, COMMIT or a whole read)."""
    attempts = attempts or BUSY_ATTEMPTS
    started = time.monotonic()
    for attempt in range(attempts):
        try:
            return step()
        except sqlite3.OperationalError as exc:
            if not busy(exc): raise
            if attempt + 1 == attempts:
                raise RegistryBusy('Registry busy: %s still locked after %d attempts over %.0f s (%s); nothing was '
                                   'committed, retry later' % (what, attempts, time.monotonic() - started, exc)) from exc
            sleep(backoff(attempt) * (.5 + jitter()))


def begin(db, statement='BEGIN IMMEDIATE'):
    """A busy BEGIN has read and written nothing, so repeating it cannot double-apply."""
    retry(lambda: db.execute(statement), 'writer lock')


def commit(db):
    """A busy COMMIT leaves the transaction open; only a still-open transaction is retried."""
    def step():
        require(db.in_transaction, 'Registry transaction ended before commit; outcome unknown')
        db.commit()
    retry(step, 'commit')


class Sealed:
    """A partition the transaction did not declare: any read, write or copy refuses."""
    __slots__ = ('path',)
    def __init__(self, path): object.__setattr__(self, 'path', path)
    def refuse(self, *args, **kwargs):
        raise Rejected('Registry section not declared for this transaction: ' + '.'.join(self.path))
    __getitem__ = __setitem__ = __delitem__ = __iter__ = __len__ = __contains__ = __bool__ = refuse
    __eq__ = __ne__ = __copy__ = __deepcopy__ = __reduce_ex__ = refuse
    __hash__ = None
    def __getattr__(self, name): self.refuse()
    def __setattr__(self, name, value): self.refuse()
    def __repr__(self): return '<undeclared registry section %s>' % '.'.join(self.path)


class Tail:
    """Append-only history partition: earlier items stay unread and cannot change."""
    __slots__ = ('path', 'base', 'added')
    def __init__(self, path, base): self.path, self.base, self.added = path, base, []
    def append(self, value): self.added.append(value)
    def extend(self, values): self.added.extend(values)
    def __len__(self): return self.base + len(self.added)
    def refuse(self, *args, **kwargs):
        raise Rejected('Registry history is append-only in this transaction: ' + '.'.join(self.path))
    __getitem__ = __setitem__ = __delitem__ = __iter__ = __contains__ = __reversed__ = refuse
    __eq__ = __ne__ = __copy__ = __deepcopy__ = __reduce_ex__ = __iadd__ = refuse
    __hash__ = None
    def __getattr__(self, name): self.refuse()
    def __repr__(self): return '<append-only registry history %s>' % '.'.join(self.path)


def parent_of(state, path):
    """The existing dict holding path[-1], or None; never creates containers."""
    node = state
    for key in path[:-1]:
        node = node.get(key) if isinstance(node, dict) else None
    return node if isinstance(node, dict) else None


def fetch(db, only=None, append=()):
    """Raw rows inside the caller's transaction; decode() may run after it ends.

only=None fetches every partition, otherwise just those (plus the meta and order
rows); each append path fetches only its last history chunk."""
    header = db.execute('SELECT body FROM registry WHERE id=1').fetchone()
    require(header is not None, 'Registry not initialized')
    descriptor = json.loads(header[0])
    if descriptor.get('schema') != 2:
        return descriptor, header[0]
    require(descriptor.get('storage') == 'documents-v1', 'Unknown registry storage')
    if only is None:
        records = db.execute('SELECT section, key, body FROM registry_documents')
    else:
        wanted = [''] + [json.dumps(path) for path in only]
        records = db.execute('SELECT section,key,body FROM registry_documents WHERE section IN (' +
                             ','.join('?' for _ in wanted) + ')', wanted)
    raw = {(section, key): body for section, key, body in records}
    for path in append:
        section = json.dumps(path)
        offsets = [int(k) for (k,) in db.execute('SELECT key FROM registry_documents WHERE section=?', (section,))]
        if offsets:
            raw[('tail:' + section, str(max(offsets)))] = db.execute(
                'SELECT body FROM registry_documents WHERE section=? AND key=?', (section, str(max(offsets)))).fetchone()[0]
    return descriptor, raw


def decode(descriptor, raw, only=None):
    """Assemble a state from fetched rows; every fetched map must match its recorded order."""
    if isinstance(raw, str):
        return descriptor
    state = json.loads(raw[('', '')])
    lists = {}
    for (section, key), body in raw.items():
        if not section or section.startswith('tail:'): continue
        path = tuple(json.loads(section))
        require(path in PARTS, 'Unknown registry document section')
        parent = container(state, path)
        if path in MAPS:
            parent[path[-1]][key] = json.loads(body)
        else:
            lists.setdefault(path, []).append((int(key), json.loads(body)))
    for path, chunks in lists.items():
        value = container(state, path)[path[-1]]
        for offset, chunk in sorted(chunks):
            require(offset == len(value), 'Incomplete registry history')
            value.extend(chunk)
    order = json.loads(raw[('', 'order')]) if only is None or any(p in MAPS for p in only) else {}
    for section, keys in order.items():
        path = tuple(json.loads(section))
        if only is not None and path not in only: continue
        parent = container(state, path)
        values = parent[path[-1]]
        require(set(values) == set(keys), 'Incomplete registry map')
        parent[path[-1]] = {key: values[key] for key in keys}
    require(state.get('root') == descriptor.get('root'), 'Registry storage workspace mismatch')
    return state


def load(db, section_path=None):
    only = None if section_path is None else [p for p in PARTS if p[:len(section_path)] == section_path]
    descriptor, raw = fetch(db, only)
    return decode(descriptor, raw, only), raw


def declared(sections, append=()):
    sections = tuple(dict.fromkeys(tuple(p) for p in sections))
    append = tuple(dict.fromkeys(tuple(p) for p in append))
    require(all(p in PARTS for p in sections) and all(p in LISTS for p in append) and not set(sections) & set(append),
            'Unknown registry section declaration; declare documents-v1 partitions (storage.MAPS/LISTS)')
    return sections, append


def seal(state, raw, sections, append=()):
    """Replace every undeclared partition with a placeholder; remember what it stood for."""
    marks = {}
    for path in PARTS:
        if path in sections: continue
        parent = parent_of(state, path)
        if parent is None or parent.get(path[-1]) is None:
            marks[path] = ('absent',)
            continue
        value = parent[path[-1]]
        if path in append:
            require(isinstance(value, list), 'Registry history shape changed: ' + '.'.join(path))
            if isinstance(raw, str): chunk, base = None, len(value)
            else:
                tail = [(int(k), json.loads(b)) for (s, k), b in raw.items() if s == 'tail:' + json.dumps(path)]
                chunk = tail[0] if tail else (0, [])
                base = chunk[0] + len(chunk[1])
            placeholder = Tail(path, base); marks[path] = ('tail', placeholder, value, chunk)
        else:
            placeholder = Sealed(path); marks[path] = ('sealed', placeholder, value)
        parent[path[-1]] = placeholder
    return marks


def unseal(state, marks):
    """Refuse if an undeclared partition was replaced, created or removed; restore the originals."""
    appended = {}
    for path, mark in marks.items():
        parent = parent_of(state, path)
        changed = 'Undeclared registry section changed in a sectioned transaction: ' + '.'.join(path)
        if mark[0] == 'absent':  # Creating the parent container is fine; filling the partition is not.
            require(parent is None or parent.get(path[-1]) is None, changed)
            continue
        require(parent is not None and parent.get(path[-1]) is mark[1], changed)
        parent[path[-1]] = mark[2]
        if mark[0] == 'tail' and mark[1].added:
            appended[path] = (mark[1].added, mark[3])
    return appended


def open_sections(db, sections, append=()):
    """Inside the caller's transaction: (state, raw, marks) for save_sections()."""
    descriptor, raw = fetch(db, sections, append)
    state = decode(descriptor, raw, sections)
    return state, raw, seal(state, raw, sections, append)


def save_sections(db, state, raw, sections, marks):
    """Write back only the meta row, declared partitions, their order entries and appended chunks."""
    appended = unseal(state, marks)
    if isinstance(raw, str):
        for path, (added, _) in appended.items():
            container(state, path)[path[-1]].extend(added)
        return save(db, state, raw)
    current = documents(state)
    writes, deletes = [], []
    if current[('', '')] != raw[('', '')]: writes.append(('', '', current[('', '')]))
    for path in sections:
        section = json.dumps(path)
        before = {k: b for (s, k), b in raw.items() if s == section}
        after = {k: b for (s, k), b in current.items() if s == section}
        deletes += [(section, k) for k in before.keys() - after.keys()]
        writes += [(section, k, b) for k, b in after.items() if before.get(k) != b]
    if any(path in MAPS for path in sections):
        order, new = json.loads(raw[('', 'order')]), json.loads(current[('', 'order')])
        for path in sections:
            if path not in MAPS: continue
            if json.dumps(path) in new: order[json.dumps(path)] = new[json.dumps(path)]
            else: order.pop(json.dumps(path), None)
        order = json.dumps({json.dumps(p): order[json.dumps(p)] for p in MAPS if json.dumps(p) in order})
        if order != raw[('', 'order')]: writes.append(('', 'order', order))
    for path, (added, (offset, chunk)) in appended.items():
        items = chunk + added  # A full last chunk stays as stored; appends start the next one.
        writes += [(json.dumps(path), str(offset + i), json.dumps(items[i:i+CHUNK]))
                   for i in range(0, len(items), CHUNK) if i + CHUNK > len(chunk)]
    db.executemany('DELETE FROM registry_documents WHERE section=? AND key=?', deletes)
    db.executemany('INSERT INTO registry_documents VALUES (?,?,?) '
                   'ON CONFLICT(section,key) DO UPDATE SET body=excluded.body', writes)


@contextmanager
def selected(reg, selections):
    """Update existing named records atomically; no partial state is exposed.

The callback gets {(path_tuple, key): value}. Missing records stay None and
cannot be inserted here: creation must also update ordered membership.
"""
    require(not getattr(reg._transaction_local, 'active', False), 'Nested registry write transaction')
    db = sqlite3.connect(reg.path, timeout=BUSY_TIMEOUT)
    reg._transaction_local.active = True
    from .write_gate import gate
    writer=gate(reg.path);entered=False
    try:
        writer.acquire();entered=True
        begin(db)
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
        commit(db)
    except BaseException:
        db.rollback();raise
    finally:
        db.close()
        if entered:writer.release()
        reg._transaction_local.active=False


def read_record(reg, path, key):
    """Read one committed record without decoding historical unrelated rows."""
    def read():
        db=sqlite3.connect(reg.path,timeout=BUSY_TIMEOUT)
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
    return retry(read,'registry read')


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
