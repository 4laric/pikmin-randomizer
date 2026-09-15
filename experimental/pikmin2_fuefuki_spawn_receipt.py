"""Run-log reader for Fuefuki gate-1 natural spawn (source 41).

Gate 1 requires the SAME generator co-occurrence across three native
markers: placement slot, seed resolve for source 41, and Fuefuki native
ready/bind. Dependency-free pure function over log text; stdlib only.
Missing lines yield False/-1.
"""
import json
import sys

PLACEMENT = "P2_PLACEMENT_SLOT"
SEED_RESOLVE = "P2_SEED_RESOLVE"
FUEFUKI_PREFIX = "P2_FUEFUKI_TEKI_"
HARDLANES_READY = "P2_HARDLANES_READY"

_GEN_KEYS = ("generator", "gen", "generator_id", "target", "target_id")


def _fields(tokens):
    fields = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if sep:
            fields[key] = value
    return fields


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _gen_id(fields):
    for key in _GEN_KEYS:
        if key in fields:
            num = _int(fields[key])
            if num is not None:
                return num
    return None


def parse(text: str) -> dict:
    """Return gate-1 natural-spawn verdict for the given run-log text."""
    placement = False
    seed_resolve_41 = False
    native_ready = False
    placement_gen = None
    seed_gen = None
    ready_gen = None

    for line in (text or "").splitlines():
        tokens = line.split()
        if not tokens:
            continue
        fields = _fields(tokens)
        if PLACEMENT in tokens:
            placement = True
            gid = _gen_id(fields)
            if gid is not None:
                placement_gen = gid
        if SEED_RESOLVE in tokens:
            if fields.get("source_id") == "41":
                seed_resolve_41 = True
                gid = _gen_id(fields)
                if gid is not None:
                    seed_gen = gid
        has_fuefuki_marker = any(
            tok.startswith(FUEFUKI_PREFIX) for tok in tokens
        )
        if has_fuefuki_marker:
            native_ready = True
            gid = _gen_id(fields)
            if gid is not None:
                ready_gen = gid
        if HARDLANES_READY in tokens and "Fuefuki" in line:
            native_ready = True
            gid = _gen_id(fields)
            if gid is not None:
                ready_gen = gid

    ids = []
    if placement:
        ids.append(placement_gen)
    if seed_resolve_41:
        ids.append(seed_gen)
    if native_ready:
        ids.append(ready_gen)
    if placement and seed_resolve_41 and native_ready:
        numeric = [i for i in ids if i is not None]
        same_generator = (
            len(numeric) == 3 and numeric[0] == numeric[1] == numeric[2]
        )
    else:
        same_generator = False

    if same_generator:
        generator = placement_gen
    else:
        generator = -1

    gate1_ok = bool(
        placement and seed_resolve_41 and native_ready and same_generator
    )
    return {
        "placement": placement,
        "seed_resolve_41": seed_resolve_41,
        "native_ready": native_ready,
        "generator": generator,
        "same_generator": same_generator,
        "gate1_ok": gate1_ok,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run-log path (defaults to stdin)")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(parse(text), indent=2))


if __name__ == "__main__":
    main()
