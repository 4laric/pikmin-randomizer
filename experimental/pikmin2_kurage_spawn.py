"""Focused log validator for gate ``identity_spawn`` for source ID 57 (Kurage).

Parses log *text* only. It never builds native code, reads logs from disk,
touches absolute paths, or accesses the network.

Recognised markers (substring/regex search per line):

- ``P2_SEED_RESOLVE source_id=57 target=<token>`` (birth-time source resolution)
- ``P2_KURAGE_TEKI_READY generator=<digits> ...`` (ordinary bind)
- ``P2_PLACEMENT_SLOT ...`` (optional generated placement route)

PASS means the seed marker and the bind marker are both present and refer to
the same generator: the ``target=`` token from the seed marker equals the
``generator=`` digits from the bind marker. Only when the seed ``target=`` is a
non-generator (non-numeric) token, the caller may pass an explicitly documented
``target_to_generator`` mapping (``{target_token: generator}``, values as int
or digit-string) that resolves that token to the bound generator digits.
"""

import re

SOURCE_ID = 57

SEED_RE = re.compile(r"P2_SEED_RESOLVE\s+source_id=57\s+target=(\S+)")
BIND_RE = re.compile(r"P2_KURAGE_TEKI_READY\s+generator=(\d+)")
PLACEMENT_TOKEN = "P2_PLACEMENT_SLOT"

SEED_MISSING = "P2_SEED_RESOLVE source_id=57"
BIND_MISSING = "P2_KURAGE_TEKI_READY generator="


def _clean_token(raw):
    """Strip trailing log punctuation (``','``/``';'``) from a raw token."""
    return raw.rstrip(",;")


def parse_markers(lines):
    """Return structured facts parsed from log text lines.

    Returns a dict with ``source_id``, ``seed_marker`` (bool),
    ``seed_target`` (raw ``target=`` token or ``None``), ``bind_marker``
    (bool), ``generator`` (int or ``None``), ``placement_marker`` (bool),
    and ``placement_lines`` (list of matching lines).
    """
    seed_target = None
    generator = None
    placement_lines = []
    for line in lines:
        if seed_target is None:
            match = SEED_RE.search(line)
            if match:
                seed_target = _clean_token(match.group(1))
        if generator is None:
            match = BIND_RE.search(line)
            if match:
                generator = int(match.group(1))
        if PLACEMENT_TOKEN in line:
            placement_lines.append(line)
    return {
        "source_id": SOURCE_ID,
        "seed_marker": seed_target is not None,
        "seed_target": seed_target,
        "bind_marker": generator is not None,
        "generator": generator,
        "placement_marker": bool(placement_lines),
        "placement_lines": list(placement_lines),
    }


def _mapping_resolves(mapping, seed_target, generator):
    """Return True when ``mapping`` explicitly resolves a non-numeric target."""
    if not mapping:
        return False
    if seed_target not in mapping:
        return False
    try:
        return int(str(mapping[seed_target])) == generator
    except (TypeError, ValueError):
        return str(mapping[seed_target]) == str(generator)


def validate_natural_spawn(lines, target_to_generator=None):
    """Validate that natural spawn and bind co-occur for source ID 57.

    ``target_to_generator`` is an optional explicitly documented mapping used
    only when the seed ``target=`` token is a non-generator (non-numeric)
    token, of the form ``{target_token: generator}`` where each value is the
    expected ``generator=`` digits (int or digit-string).

    Returns a dict with ``ok``, ``source_id``, ``generator``, ``seed_marker``,
    ``bind_marker``, ``same_generator``, and ``missing`` (list of strings;
    empty means PASS). Also includes ``seed_target`` and ``placement_marker``
    for context; the placement route is optional and never gates PASS.
    """
    facts = parse_markers(lines)
    seed_target = facts["seed_target"]
    generator = facts["generator"]
    seed_marker = facts["seed_marker"]
    bind_marker = facts["bind_marker"]

    same_generator = False
    if seed_marker and bind_marker:
        if seed_target.isdigit():
            same_generator = int(seed_target) == generator
        else:
            same_generator = _mapping_resolves(
                target_to_generator, seed_target, generator
            )

    missing = []
    if not seed_marker:
        missing.append(SEED_MISSING)
    if not bind_marker:
        missing.append(BIND_MISSING)
    if seed_marker and bind_marker and not same_generator:
        missing.append(
            "generator mismatch (seed_target=%r generator=%r)" % (seed_target, generator)
        )

    return {
        "ok": bool(seed_marker and bind_marker and same_generator),
        "source_id": SOURCE_ID,
        "generator": generator,
        "seed_marker": seed_marker,
        "bind_marker": bind_marker,
        "same_generator": same_generator,
        "missing": missing,
        "seed_target": seed_target,
        "placement_marker": facts["placement_marker"],
    }


def default_sample_log():
    """Representative passing log (source 57, generator 201001, with route)."""
    return (
        "P2_SEED_RESOLVE source_id=57 target=201001\n"
        "P2_KURAGE_TEKI_READY generator=201001 type=0 binding=private_adapter\n"
        "P2_PLACEMENT_SLOT generator=201001 slot=3 route=generated\n"
    )
