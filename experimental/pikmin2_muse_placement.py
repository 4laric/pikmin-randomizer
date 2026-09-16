"""Muse placement (#492) generated-bind observer for 41/57/58/78.

Pure log-correlation helpers shared by the four gate observers (#497-#500)
and their tests. For each candidate identity this requires the three native
birth markers to agree on the SAME generated slot uid:

- ``P2_SEED_RESOLVE source_id=<n> target=<uid>`` (seed bridge source resolve),
- ``P2_GENERATED_PLACEMENT source_id=<n> target=<uid> ... bound=1``
  (this lane's narrow native binding path),
- the lane-04 placement probe ``P2_PLACEMENT_SLOT`` / ``P2_PLACEMENT_PROBE``
  line covering the same uid.

A ``bound=0`` bind marker (slot-rejected / bad-request / registry-full) is a
fail-closed placement refusal, not a bind: it is reported as a mismatch with
its reason. Markers from injected or synthetic logs must be labelled by the
caller; nothing here distinguishes natural from injected evidence.
"""
import re

MUSE_COHORT = (41, 57, 58, 78)

MUSE_IDENTITY = {
    41: 'Fuefuki',
    57: 'Kurage',
    58: 'BombSarai',
    78: 'MiniHoudai',
}

MUSE_ACCEPTED_SLOT = {
    41: 1254096625,
    57: 689702860,
    58: 1787125272,
    78: 328297937,
}

_RESOLVE_RE = re.compile(r'P2_SEED_RESOLVE source_id=(\d+) target=(\d+)')
_BIND_RE = re.compile(
    r'P2_GENERATED_PLACEMENT source_id=(\d+) target=(\d+)'
    r'(?: generator=(\d+))? bound=(\d)(?: reason=(\S+))?')


def _last_match(pattern, text, source_id):
    found = None
    for match in pattern.finditer(text):
        if int(match.group(1)) == source_id:
            found = match
    return found


def placement_markers_present(text):
    """True when the lane-04 placement probe ran at all in this log."""
    return ('P2_PLACEMENT_SLOT generator=' in text
            or 'P2_PLACEMENT_PROBE actors=' in text)


def observe_identity(text, source_id):
    """Correlate resolve/bind markers for one candidate source id.

    Returns a dict with `resolved_uid`, `bound_uid`, `bound`,
    `refusal_reason` and the `correlated` verdict: True only when the
    seed resolve and a bound=1 bind marker name the same uid, and that
    uid is the profile's accepted generated slot.
    """
    if source_id not in MUSE_COHORT:
        raise ValueError(f'source id {source_id} is not a muse #492 candidate')
    resolve = _last_match(_RESOLVE_RE, text, source_id)
    bind = _last_match(_BIND_RE, text, source_id)
    resolved_uid = int(resolve.group(2)) if resolve else None
    bound_uid = int(bind.group(2)) if bind else None
    bound = bind is not None and bind.group(4) == '1'
    reason = None
    if bind is not None and not bound:
        reason = bind.group(5) or 'unbound'
    accepted = MUSE_ACCEPTED_SLOT[source_id]
    correlated = (
        bound
        and resolved_uid is not None
        and resolved_uid == bound_uid == accepted
    )
    if bound and not correlated:
        if resolved_uid != bound_uid:
            reason = 'resolve-bind-uid-mismatch'
        elif bound_uid != accepted:
            reason = 'slot-not-accepted'
    return {
        'source_id': source_id,
        'identity': MUSE_IDENTITY[source_id],
        'resolved_uid': resolved_uid,
        'bound_uid': bound_uid,
        'bound': bound,
        'accepted_uid': accepted,
        'refusal_reason': reason,
        'correlated': correlated,
    }


def observe_cohort(text, cohort=MUSE_COHORT):
    """Correlate every cohort identity; unknown ids raise ValueError."""
    return {source_id: observe_identity(text, source_id) for source_id in cohort}


def summary(rows):
    """Deterministic pass/fail rollup over `observe_cohort` rows."""
    correlated = sorted(sid for sid, row in rows.items() if row['correlated'])
    missing = sorted(sid for sid, row in rows.items() if not row['correlated'])
    return {
        'correlated': correlated,
        'missing': missing,
        'all_correlated': not missing,
    }
