"""Run-log reader for the Fuefuki natural-combat real-GL runtime fixture.

The Fuefuki natural-combat fixture prints a small family of
``P2_FUEFUKI_COMBAT_RT_*`` markers, each followed by trailing ``key=value``
fields, and finally a single ``PASS FUEFUKI_COMBAT_RUNTIME`` line when the
runtime acceptance completes. This module is the host-side reader for that
log: a dependency-free, importable pure function over the log text that
returns a flat verdict dict. It mutates no native state, reads no retail
asset and authors no source family drop behavior.

Every boolean defaults to False and every integer to -1 when the responsible
line is absent, so a partial or truncated log still yields a complete verdict.
"""
import json
import sys

WINDOW = 'P2_FUEFUKI_COMBAT_RT_WINDOW'
READY = 'P2_FUEFUKI_COMBAT_RT_READY'
STAGE = 'P2_FUEFUKI_COMBAT_RT_STAGE'
PRESS = 'P2_FUEFUKI_COMBAT_RT_PRESS'
STRUGGLE = 'P2_FUEFUKI_COMBAT_RT_STRUGGLE'
DEATH = 'P2_FUEFUKI_COMBAT_RT_DEATH'
RELEASE = 'P2_FUEFUKI_COMBAT_RT_RELEASE'
PASS_MARKER = 'PASS FUEFUKI_COMBAT_RUNTIME'


def _fields(tokens):
    """Map the trailing ``key=value`` tokens that follow a marker token."""
    fields = {}
    for token in tokens:
        key, sep, value = token.partition('=')
        if sep:
            fields[key] = value
    return fields


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse(text):
    """Return the Fuefuki natural-combat verdict for the given run-log text."""
    window = False
    ready = False
    receiver_wired = False
    struggle = False
    death = False
    release_present = False
    released = -1
    held_after = -1

    for line in text.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        marker = tokens[0]
        current = _fields(tokens[1:])
        if marker == WINDOW:
            window = current.get('size') == '960x540' and current.get('centered') == '1'
        elif marker == READY:
            ready = True
        elif marker == PRESS:
            count = _int(current.get('press_count'))
            if current.get('injected') == '1' and count is not None and count >= 1:
                receiver_wired = True
        elif marker == STRUGGLE:
            if current.get('state') == '8':
                struggle = True
        elif marker == DEATH:
            if current.get('injected') == '1':
                death = True
        elif marker == RELEASE:
            release_present = True
            released = _int(current.get('released'))
            if released is None:
                released = -1
            held_after = _int(current.get('held'))
            if held_after is None:
                held_after = -1

    release_ok = release_present and held_after == 0 and released > 0
    return {
        'window': window,
        'ready': ready,
        'receiver_wired': receiver_wired,
        'struggle': struggle,
        'death': death,
        'released': released,
        'held_after': held_after,
        'release_ok': release_ok,
        'passed': PASS_MARKER in text,
    }


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', help='Run-log path (defaults to stdin)')
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, encoding='utf-8', errors='replace') as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    print(json.dumps(parse(text), indent=2))


if __name__ == '__main__':
    main()
