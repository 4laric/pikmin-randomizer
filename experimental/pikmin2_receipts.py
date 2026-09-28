"""Versioned per-identity reward descriptors and exactly-once receipt ledger.

Lane 06 defines the shared host-side contract for P2 rewards, cargo and save
receipts. This is a schema/reconciliation slice: it mutates no native save, reads
no retail asset and implements no source family drop behavior. Ordinary
Onion/AP rewards are explicitly kept in a separate ledger from the experimental
Research Pod/Poko economy. Persistence ships with an in-memory fake and a
host-side JSON adapter; neither is the native save file, so native save mutation
stays coordinated with lane 01. See ``docs/PIKMIN2_REWARD_RECEIPTS.md``.
"""
import copy
import json
import os
import re
from pathlib import Path

SCHEMA_VERSION = 'p2-reward-descriptor-v1'
LEDGER_VERSION = 'p2-receipt-ledger-v1'
RECEIPTS_STATE_VERSION = 'p2-receipts-v1'

# Source drop semantics stay with the family lanes; this is the shared vocabulary.
DROP_KINDS = ('corpse', 'pellet', 'treasure', 'none')

# Ordinary P1 Onion/AP behavior must never share a ledger with the experimental
# Research Pod/Poko economy.
LEDGER_ONION = 'onion'
LEDGER_AP = 'ap'
LEDGER_POD = 'pod'
LEDGER_TAGS = (LEDGER_ONION, LEDGER_AP, LEDGER_POD)
ORDINARY_LEDGERS = frozenset((LEDGER_ONION, LEDGER_AP))
EXPERIMENTAL_LEDGERS = frozenset((LEDGER_POD,))

REQUIRED_FIELDS = frozenset(('version', 'identity', 'family', 'drop', 'ledger'))
OPTIONAL_FIELDS = frozenset(('value', 'count'))
DESCRIPTOR_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

_IDENTITY = re.compile(r'[A-Za-z0-9_:/-]{1,90}')
_FAMILY = re.compile(r'[a-z0-9-]{1,40}')
_TOKEN = re.compile(r'[A-Za-z0-9_.:/-]{1,128}')


def _identity(value, label):
    if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
        raise ValueError('Invalid ' + label)
    return value


def _nonnegative(value, label):
    if type(value) is not int or value < 0:
        raise ValueError('Invalid ' + label + ': expected a non-negative integer')
    return value


def _token(value, label):
    if type(value) is int and value >= 0:
        return str(value)
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError('Invalid ' + label + ': expected a non-empty token or non-negative integer')
    return value


def validate_descriptor(descriptor):
    """Return a normalized copy of one reward descriptor or raise ValueError."""
    if not isinstance(descriptor, dict):
        raise ValueError('Reward descriptor must be a mapping')
    keys = set(descriptor)
    unknown = keys - DESCRIPTOR_FIELDS
    if unknown:
        raise ValueError('Unknown reward descriptor field: ' + ', '.join(sorted(unknown)))
    missing = REQUIRED_FIELDS - keys
    if missing:
        raise ValueError('Missing reward descriptor field: ' + ', '.join(sorted(missing)))
    if descriptor['version'] != SCHEMA_VERSION:
        raise ValueError('Unknown reward descriptor version')
    identity = _identity(descriptor['identity'], 'reward identity')
    if not isinstance(descriptor['family'], str) or not _FAMILY.fullmatch(descriptor['family']):
        raise ValueError('Invalid reward family lane')
    if descriptor['drop'] not in DROP_KINDS:
        raise ValueError('Invalid reward drop kind')
    if descriptor['ledger'] not in LEDGER_TAGS:
        raise ValueError('Unknown reward ledger tag')
    result = {'version': SCHEMA_VERSION, 'identity': identity, 'family': descriptor['family'],
              'drop': descriptor['drop'], 'ledger': descriptor['ledger'], 'value': None, 'count': None}
    for field in ('value', 'count'):
        if descriptor.get(field) is not None:
            result[field] = _nonnegative(descriptor[field], 'reward ' + field)
    return result


def validate_descriptors(descriptors):
    """Validate a sequence of descriptors; reject duplicate identities."""
    if not isinstance(descriptors, (list, tuple)):
        raise ValueError('Expected a sequence of reward descriptors')
    result = []
    seen = set()
    for descriptor in descriptors:
        normalized = validate_descriptor(descriptor)
        if normalized['identity'] in seen:
            raise ValueError('Duplicate reward identity: ' + normalized['identity'])
        seen.add(normalized['identity'])
        result.append(normalized)
    return result


def receipt_key(seed, identity, slot_or_actor, encounter):
    """Canonical exactly-once key for one grant event."""
    return (_token(seed, 'receipt seed'), _identity(identity, 'receipt identity'),
            _token(slot_or_actor, 'receipt slot/actor'), _token(encounter, 'receipt encounter'))


class ReceiptPersistence:
    """Fake persistence boundary. Native save mutation stays with lane 01."""

    def load(self):
        raise NotImplementedError

    def store(self, state):
        raise NotImplementedError


class InMemoryPersistence(ReceiptPersistence):
    """JSON-shaped in-memory store so replay/restart can be exercised deterministically."""

    def __init__(self, state=None):
        self.state = copy.deepcopy(state)
        self.writes = 0

    def load(self):
        return copy.deepcopy(self.state)

    def store(self, state):
        self.state = copy.deepcopy(state)
        self.writes += 1


def _atomic_write(path, text):
    """Write ``text`` to a temp sibling then ``os.replace`` it into place.

    An interrupted write leaves the previous file untouched and at most a stale
    ``<name>.tmp`` behind; the writer never truncates the live state first.
    """
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class JsonReceiptPersistence(ReceiptPersistence):
    """Host-side JSON fake for the receipt state; **not** the native save file.

    This adapter persists the lane 06 receipt ledger to an ordinary JSON document
    for host tests and previews. It must never be pointed at a Pikmin 2 save or
    memory card: native save mutation stays coordinated with lane 01. The file is
    written atomically (temp sibling plus ``os.replace``) so an interrupted write
    cannot corrupt the last good state, and any leftover ``<name>.tmp`` is
    ignored on load. Malformed or unknown-version documents raise ``ValueError``.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.state = self._read()

    def _read(self):
        if not self.path.exists():
            return None
        try:
            document = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise ValueError('Corrupt receipt state file') from exc
        if not isinstance(document, dict) or set(document) != {'schema', 'version', 'receipts'}:
            raise ValueError('Invalid receipt state fields')
        if document['schema'] != RECEIPTS_STATE_VERSION:
            raise ValueError('Unknown receipt state version')
        state = {'version': document['version'], 'receipts': document['receipts']}
        _decode_state(state)
        return state

    def load(self):
        return copy.deepcopy(self.state)

    def store(self, state):
        _decode_state(state)
        document = {'schema': RECEIPTS_STATE_VERSION, 'version': state['version'],
                    'receipts': state['receipts']}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.path, json.dumps(document, sort_keys=True) + '\n')
        self.state = copy.deepcopy(state)


def _decode_state(state):
    if state is None:
        return set()
    if not isinstance(state, dict) or set(state) != {'version', 'receipts'}:
        raise ValueError('Invalid receipt ledger state')
    if state['version'] != LEDGER_VERSION:
        raise ValueError('Unknown receipt ledger version')
    rows = state['receipts']
    if not isinstance(rows, list):
        raise ValueError('Invalid receipt ledger receipts')
    receipts = set()
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 4 or any(not isinstance(v, str) for v in row):
            raise ValueError('Invalid persisted receipt')
        key = tuple(row)
        if key in receipts:
            raise ValueError('Duplicate persisted receipt')
        receipts.add(key)
    return receipts


class ReceiptLedger:
    """Exactly-once receipts over a persistence backend, stable across restart."""

    def __init__(self, persistence):
        if not isinstance(persistence, ReceiptPersistence):
            raise ValueError('Expected a receipt persistence backend')
        self._persistence = persistence
        self._receipts = _decode_state(persistence.load())

    def __len__(self):
        return len(self._receipts)

    def __contains__(self, key):
        return receipt_key(*key) in self._receipts

    @property
    def receipts(self):
        return set(self._receipts)

    def has(self, seed, identity, slot_or_actor, encounter):
        return receipt_key(seed, identity, slot_or_actor, encounter) in self._receipts

    def grant(self, seed, identity, slot_or_actor, encounter):
        """Record one grant; return True only for the first occurrence."""
        key = receipt_key(seed, identity, slot_or_actor, encounter)
        if key in self._receipts:
            return False
        self._receipts.add(key)
        try:
            self._persist()
        except Exception:
            self._receipts.remove(key)
            raise
        return True

    def restart(self):
        """Rebuild a fresh ledger over the same persistence (process restart).

        The reopened ledger sees the persisted receipts, so a prior grant is not
        repeated while a genuinely new event is still granted.
        """
        return ReceiptLedger(self._persistence)

    def reload(self):
        """Alias for ``restart`` kept for callers that reopen in-process."""
        return self.restart()

    def _persist(self):
        self._persistence.store({'version': LEDGER_VERSION,
                                 'receipts': [list(key) for key in sorted(self._receipts)]})


def grant_events(ledger, events):
    """Grant an ordered iterable of ``(seed, identity, slot_or_actor, encounter)``."""
    return tuple(ledger.grant(*event) for event in events)


def reconcile(reward_descriptors, expected_checks, *, refuse_pod_leaks=True):
    """Check ordinary coverage: every expected check has an Onion/AP source.

    Missing sources are reported. A Pod-only descriptor that would cover an
    ordinary expected check is a leak: refused by default, otherwise reported.
    """
    descriptors = validate_descriptors(reward_descriptors)
    expected = []
    seen = set()
    for check in expected_checks:
        value = _identity(check, 'expected check')
        if value in seen:
            raise ValueError('Duplicate expected check: ' + value)
        seen.add(value)
        expected.append(value)
    by_identity = {descriptor['identity']: descriptor for descriptor in descriptors}
    missing_sources = []
    pod_leaks = []
    for check in expected:
        source = by_identity.get(check)
        if source is None:
            missing_sources.append(check)
        elif source['ledger'] not in ORDINARY_LEDGERS:
            pod_leaks.append(check)
    unexpected_sources = sorted(descriptor['identity'] for descriptor in descriptors
                                if descriptor['identity'] not in seen
                                and descriptor['ledger'] in ORDINARY_LEDGERS)
    if pod_leaks and refuse_pod_leaks:
        raise ValueError('Pod-only reward leaks into ordinary ledger: ' + ', '.join(sorted(pod_leaks)))
    return {'ok': not missing_sources and not pod_leaks and not unexpected_sources,
            'expected': expected,
            'ordinary_sources': sorted(d['identity'] for d in descriptors if d['ledger'] in ORDINARY_LEDGERS),
            'experimental_sources': sorted(d['identity'] for d in descriptors if d['ledger'] in EXPERIMENTAL_LEDGERS),
            'missing_sources': missing_sources,
            'pod_leaks': pod_leaks,
            'unexpected_sources': unexpected_sources}


class RewardRegistry:
    """Validated reward descriptors keyed by identity, with coverage checks.

    Holds the layered, versioned descriptors a seed may emit and delegates
    coverage reconciliation to :func:`reconcile`, so callers get identical
    missing-source, pod-leak and invented-check semantics.
    """

    def __init__(self, descriptors=()):
        self._descriptors = {}
        for descriptor in descriptors:
            self.add(descriptor)

    def add(self, descriptor):
        """Validate and store one descriptor; reject a duplicate identity."""
        normalized = validate_descriptor(descriptor)
        identity = normalized['identity']
        if identity in self._descriptors:
            raise ValueError('Duplicate reward identity: ' + identity)
        self._descriptors[identity] = normalized
        return normalized

    def get(self, identity):
        """Return a copy of the descriptor for ``identity`` or ``None``."""
        descriptor = self._descriptors.get(identity)
        return copy.deepcopy(descriptor) if descriptor is not None else None

    @property
    def descriptors(self):
        return [copy.deepcopy(descriptor) for descriptor in self._descriptors.values()]

    def reconcile_all(self, expected_checks, refuse_pod_leaks=True):
        """Reconcile every registered descriptor against ``expected_checks``."""
        return reconcile(self.descriptors, expected_checks, refuse_pod_leaks=refuse_pod_leaks)
