"""Native-probe evidence stamping layer for p2-placement documents.

This complements `p2_placement` (which answers "is this allowed?" with a
default *deny*) with a small side channel for recorded native placement
evidence: a probe produced by the native runtime observation pass. A probe
does not choose positions or identities, it only attests which evidence axes
(`xyz`, `terrain`, `route`) a native probe observed for a slot uid.

The probe is a separate `p2-placement-probe-v1` document. `stamp_evidence`
merges a probe into a copy of a validated placement document, only ever
upgrading evidence keys to True; `audit_native` stamps and then runs the
standard audit without needing evidence baked into the source document.
"""
import json

from . import p2_placement

PROBE_SCHEMA = 'p2-placement-probe-v1'
PROBE_SLOT_KEYS = ('uid', 'xyz', 'terrain', 'route')
EVIDENCE_KEYS = ('xyz', 'terrain', 'route')


def _fail(message):
    raise ValueError(message)


def _is_bool(value):
    return isinstance(value, bool)


def normalize_probe(data):
    """Validate and normalize a probe document, returning a pruned dict."""
    if not isinstance(data, dict):
        _fail('probe must be an object')
    if data.get('schema') != PROBE_SCHEMA:
        _fail(f'probe schema must be {PROBE_SCHEMA}')
    slots = data.get('slots')
    if not isinstance(slots, list) or not slots:
        _fail('probe slots must be a non-empty list')
    normalized = []
    seen = set()
    for item in slots:
        if not isinstance(item, dict):
            _fail('probe slot must be an object')
        unknown = [key for key in item if key not in PROBE_SLOT_KEYS]
        if unknown:
            _fail(f'probe slot has unknown field(s): {", ".join(sorted(unknown))}')
        missing = [key for key in PROBE_SLOT_KEYS if key not in item]
        if missing:
            _fail(f'probe slot missing required field(s): {", ".join(missing)}')
        uid = item['uid']
        if not isinstance(uid, int) or isinstance(uid, bool) or uid < 0:
            _fail('probe slot uid must be a non-negative integer')
        for key in EVIDENCE_KEYS:
            if not _is_bool(item[key]):
                _fail(f'probe slot {key} must be a boolean')
        if uid in seen:
            _fail('probe has duplicate slot uids')
        seen.add(uid)
        normalized.append({
            'uid': int(uid),
            'xyz': bool(item['xyz']),
            'terrain': bool(item['terrain']),
            'route': bool(item['route']),
        })
    return {'schema': PROBE_SCHEMA, 'slots': normalized}


def stamp_evidence(document, probe):
    """Merge native probe evidence into a copy of a validated document.

    Evidence is only ever upgraded to True: an existing True value is never
    downgraded by a False probe value. Probe uids absent from the document are
    silently ignored. The result is re-validated before it is returned.
    """
    probe = normalize_probe(probe)
    stamped = json.loads(json.dumps(document))
    by_uid = {slot['uid']: slot for slot in stamped.get('slots', [])}
    for probe_slot in probe['slots']:
        slot = by_uid.get(probe_slot['uid'])
        if slot is None:
            continue
        evidence = slot.setdefault('evidence', {})
        for key in EVIDENCE_KEYS:
            evidence[key] = bool(evidence.get(key, False)) or probe_slot[key]
    return p2_placement.validate_document(stamped)


def audit_native(document, probe, identities=None):
    """Stamp native evidence into the document and audit the result."""
    return p2_placement.audit(stamp_evidence(document, probe), identities=identities)


def slot_evidence_summary(document):
    """Return per-slot evidence keyed by the string form of each slot uid."""
    summary = {}
    for slot in document['slots']:
        evidence = slot.get('evidence', {})
        summary[str(slot['uid'])] = {
            key: bool(evidence.get(key, False)) for key in EVIDENCE_KEYS
        }
    return summary
