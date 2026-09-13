"""Host-side surface/cave handoffs; not a native surface/world save or launcher.

One ledger owns the suspended surface snapshot and nested schema-1 cave state.
Never run the standalone cave writer against this directory concurrently.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import uuid

from experimental.pikmin2_campaign import initial, transition, validate as validate_cave
from randomizer.session import SessionLock, atomic_write


def _hex(value, length):
    return isinstance(value, str) and len(value) == length and all(c in '0123456789abcdef' for c in value)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _surface(snapshot, content):
    if not isinstance(snapshot, dict) or set(snapshot) != {'region', 'day', 'time', 'position', 'squad', 'health', 'receipts'}:
        raise ValueError('Invalid surface snapshot fields')
    if (not isinstance(snapshot['region'], str) or not snapshot['region'] or len(snapshot['region']) > 100
            or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789_-' for c in snapshot['region'])
            or type(snapshot['day']) is not int or not 1 <= snapshot['day'] <= 1000000
            or type(snapshot['time']) not in (int, float) or not math.isfinite(snapshot['time']) or not 0 <= snapshot['time'] <= 24
            or not isinstance(snapshot['position'], list) or len(snapshot['position']) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 100000 for x in snapshot['position'])):
        raise ValueError('Invalid surface destination')
    cave = initial(content)
    cave.update({k: snapshot[k] for k in ('squad', 'health', 'receipts')})
    validate_cave(cave)
    return snapshot


def validate(state):
    if not isinstance(state, dict) or set(state) != {'schema', 'campaign', 'content', 'origin', 'revision', 'phase', 'surface', 'trip', 'events'}:
        raise ValueError('Invalid surface ledger fields')
    if (type(state['schema']) is not int or state['schema'] != 1 or not _hex(state['campaign'], 32)
            or not _hex(state['content'], 64) or not _hex(state['origin'], 64)):
        raise ValueError('Invalid surface ledger identity')
    events = state['events']
    if (not isinstance(events, dict) or len(events) > 4096 or type(state['revision']) is not int
            or state['revision'] != len(events)):
        raise ValueError('Invalid surface ledger revision/history')
    for key, value in events.items():
        if (not isinstance(key, str) or ':' not in key or key.split(':', 1)[0] not in ('enter', 'floor', 'return')
                or not _hex(key.split(':', 1)[1], 32) or not _hex(value, 64)):
            raise ValueError('Invalid surface ledger event')
    _surface(state['surface'], state['content'])
    if state['phase'] == 'surface':
        if state['trip'] is not None:
            raise ValueError('Surface has an active cave trip')
    elif state['phase'] in ('cave', 'return_ready', 'failed'):
        trip = state['trip']
        if (not isinstance(trip, dict) or set(trip) != {'id', 'cave', 'token', 'checkpoint'}
                or not _hex(trip['id'], 32) or trip['cave'] != 'tutorial_1' or f'enter:{trip["id"]}' not in events):
            raise ValueError('Invalid cave trip identity')
        checkpoint = validate_cave(trip['checkpoint'])
        expected = {'cave': 'active', 'return_ready': 'exited', 'failed': 'failed'}[state['phase']]
        if checkpoint['content'] != state['content'] or checkpoint['status'] != expected:
            raise ValueError('Cave checkpoint disagrees with surface ledger')
        if (state['phase'] == 'cave' and not _hex(trip['token'], 32)) or (state['phase'] != 'cave' and trip['token'] is not None):
            raise ValueError('Invalid native handoff token')
        for key, value in state['surface']['receipts'].items():
            if checkpoint['receipts'].get(key) != value:
                raise ValueError('Suspended surface receipts regressed')
    else:
        raise ValueError('Invalid surface ledger phase')
    return state


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate surface ledger field')
        result[key] = value
    return result


class SurfaceLedger:
    """Mutation calls hold an OS lock and replace exactly one authoritative file.

    Reuse the same expected_revision and payload when retrying an uncertain call.
    An exact replay returns the latest ledger without repeating its effect.
    """
    def __init__(self, directory, content, campaign):
        if not _hex(content, 64) or not _hex(campaign, 32):
            raise ValueError('Invalid campaign/content identity')
        self.directory = Path(directory)
        self.path = self.directory/'surface-ledger.json'
        self.content, self.campaign = content, campaign

    def _read(self):
        state = self._validate(json.loads(self.path.read_text(encoding='utf-8'), object_pairs_hook=_unique))
        if state['content'] != self.content or state['campaign'] != self.campaign:
            raise ValueError('Surface ledger belongs to different content/campaign')
        return state

    def _validate(self, state):
        return validate(state)

    def read(self):
        with SessionLock(self.directory):
            return self._read()

    def create(self, snapshot):
        snapshot = deepcopy(_surface(snapshot, self.content))
        origin = _digest(snapshot)
        with SessionLock(self.directory):
            if self.path.exists():
                state = self._read()
                if state['origin'] != origin:
                    raise ValueError('Conflicting initial surface snapshot')
                return state
            if any(p.name != 'runner.lock' for p in self.directory.iterdir()):
                raise ValueError('Missing ledger in an existing session; refusing reset')
            state = dict(schema=1, campaign=self.campaign, content=self.content, origin=origin,
                         revision=0, phase='surface', surface=snapshot, trip=None, events={})
            atomic_write(self.path, json.dumps(self._validate(state), indent=2))
            return state

    def _change(self, expected_revision, key, request, apply):
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('Invalid expected revision')
        request = _digest(dict(revision=expected_revision, payload=request))
        with SessionLock(self.directory):
            state = self._read()
            if key in state['events']:
                if state['events'][key] != request:
                    raise ValueError('Conflicting replay of a committed handoff')
                return state
            if state['revision'] != expected_revision:
                raise ValueError('Stale surface ledger revision')
            candidate = deepcopy(state)
            apply(candidate)
            candidate['events'][key] = request
            candidate['revision'] += 1
            atomic_write(self.path, json.dumps(self._validate(candidate), indent=2))
            return candidate

    def enter_cave(self, expected_revision, trip_id, *, native_entry=None):
        """Optionally consume a live surface transfer in the same entry transaction.

        The source token is the trip ID, so a native entry cannot be reused for a
        later visit. Omitted native_entry preserves the original request digest.
        Surface acquisition is not implemented: receipt keys/values must match.
        """
        if not _hex(trip_id, 32):
            raise ValueError('Invalid cave trip ID')
        if native_entry is not None:
            native_entry = deepcopy(native_entry)
            if (not isinstance(native_entry, dict) or set(native_entry) != {'text', 'position', 'receipts'}
                    or not isinstance(native_entry['text'], str) or not isinstance(native_entry['receipts'], dict)):
                raise ValueError('Invalid native surface entry fields')
        def apply(state):
            if state['phase'] != 'surface':
                raise ValueError('Surface is already suspended')
            if len(state['events']) > 4092:
                raise ValueError('Ledger history full; cannot start another cave trip')
            checkpoint = initial(self.content)
            checkpoint.update({k: deepcopy(state['surface'][k]) for k in ('squad', 'health', 'receipts')})
            if native_entry is not None:
                if native_entry['receipts'] != state['surface']['receipts']:
                    raise ValueError('Surface receipts changed; surface acquisition is unsupported')
                handed = transition(checkpoint, trip_id, native_entry['text'], native_entry['receipts'], {})
                if native_entry['position'] is not None:
                    destination = deepcopy(state['surface'])
                    destination['position'] = deepcopy(native_entry['position'])
                    _surface(destination, self.content)
                elif handed['status'] != 'failed':
                    raise ValueError('Living surface entry requires actual native position')
                if handed['status'] == 'failed':
                    # Do not replace the suspended surface with an invalid empty
                    # active snapshot. The authoritative terminal trip prevents revival.
                    state['phase'] = 'failed'
                    state['trip'] = dict(id=trip_id, cave='tutorial_1', token=None, checkpoint=handed)
                    return
                state['surface']['position'] = deepcopy(native_entry['position'])
                for key in ('squad', 'health', 'receipts'):
                    state['surface'][key] = deepcopy(handed[key])
                    checkpoint[key] = deepcopy(handed[key])
            state['phase'] = 'cave'
            state['trip'] = dict(id=trip_id, cave='tutorial_1', token=uuid.uuid4().hex, checkpoint=checkpoint)
        request = dict(trip=trip_id)
        if native_entry is not None:
            request['native_entry'] = native_entry
        return self._change(expected_revision, f'enter:{trip_id}', request, apply)

    def apply_floor(self, expected_revision, token, text, receipts, allowed):
        if not _hex(token, 32):
            raise ValueError('Invalid native handoff token')
        receipts, allowed = deepcopy(receipts), deepcopy(allowed)
        def apply(state):
            trip = state['trip']
            if state['phase'] != 'cave' or trip['token'] != token:
                raise ValueError('Wrong or stale cave handoff')
            checkpoint = transition(trip['checkpoint'], token, text, receipts, allowed)
            trip['checkpoint'] = checkpoint
            state['phase'] = {'active': 'cave', 'exited': 'return_ready', 'failed': 'failed'}[checkpoint['status']]
            trip['token'] = uuid.uuid4().hex if state['phase'] == 'cave' else None
        payload = dict(token=token, text=text, receipts=receipts, allowed=allowed)
        return self._change(expected_revision, f'floor:{token}', payload, apply)

    def return_to_surface(self, expected_revision, trip_id):
        if not _hex(trip_id, 32):
            raise ValueError('Invalid cave trip ID')
        def apply(state):
            if state['phase'] != 'return_ready' or state['trip']['id'] != trip_id:
                raise ValueError('No successful cave result ready for this trip')
            checkpoint = state['trip']['checkpoint']
            for key in ('squad', 'health', 'receipts'):
                state['surface'][key] = deepcopy(checkpoint[key])
            state['phase'], state['trip'] = 'surface', None
        return self._change(expected_revision, f'return:{trip_id}', dict(trip=trip_id), apply)
