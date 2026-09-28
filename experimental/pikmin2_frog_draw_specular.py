"""Lane-09 slice 4: the family draw consumes the scene's specular channel.

A live Frog (enemy 17) is spawned via lane 16's generator sidecar and drawn
through `tekibteki.cpp` -> `pc_p2_frog_draw` -> `shape->drawshape`. The renderer
(``pc_gfx``) uploads the scene's specular half-vector (light 7) uniform when a
material draw carries a GX_AF_SPEC COLOR1 channel, and attributes the uploads
inside a family draw to a per-draw delta (``pc_gfx_specular_family_delta_last``).
This module validates the real markers: window (SHOWN + size within tolerance), a
reported readback viewport, a family-registered Frog, a non-black actor capture,
and a per-draw family delta >= 1 (a renderer-global-only delta does not count).
"""
import argparse
import json
import re
from pathlib import Path

from experimental.pikmin2_frog_arena import prepare as frog_arena_prepare

WINDOW_MARKER = 'FROG_DRAW_WINDOW'
VIEWPORT_MARKER = 'FROG_DRAW_WINDOW_VIEWPORT'
READY_MARKER = 'FROG_DRAW_READY'
MARKER = 'FROG_DRAW_SPECULAR'
PASS_LINE = 'PASS FROG_DRAW_SPECULAR'
FROG_GENERATOR = 201001

_INT = re.compile(r'(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)=(?P<value>-?[0-9]+)')
_FLAGS = re.compile(r'flags=(?P<value>SHOWN|HIDDEN)')


def _line(log, prefix):
    for line in log.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix + ' ') or stripped == prefix:
            return stripped
    raise ValueError('%s marker stripped from the captured log' % prefix)


def evidence(log, requested=(960, 540), tolerance=8):
    """Validate the real Frog family-draw markers.

    The window marker must report a real SHOWN SDL flag and a size matching the
    requested window within ``tolerance`` (``centered`` is the fixture's own SDL
    read and is recorded, not hard-gated). The render marker's per-draw
    ``family_delta_last`` must be >= 1 so the specular half-vector upload is
    attributed to the family draw (a renderer-global-only delta does not count),
    ``nonzero_pixels`` must be > 0 so the actor capture is not vacuous, and
    ``replay_equal`` must be a verified byte compare.
    """
    if not isinstance(log, str):
        raise ValueError('Expected a captured log text')

    window = _line(log, WINDOW_MARKER)
    wflags = _FLAGS.search(window)
    if not wflags:
        raise ValueError('window marker does not report the real SDL flag (SHOWN or HIDDEN)')
    if wflags.group('value') != 'SHOWN':
        raise ValueError('window is not visible (flags=HIDDEN); the acceptance window must be SHOWN')
    wfield = {m.group('key'): int(m.group('value')) for m in _INT.finditer(window)}
    w, h = wfield.get('w'), wfield.get('h')
    if w is None or h is None:
        raise ValueError('window marker missing reported size')
    if abs(w - requested[0]) > tolerance or abs(h - requested[1]) > tolerance:
        raise ValueError('window size %dx%d does not match requested %dx%d within %dpx'
                         % (w, h, requested[0], requested[1], tolerance))

    vfield = {m.group('key'): int(m.group('value')) for m in _INT.finditer(_line(log, VIEWPORT_MARKER))}
    if vfield.get('viewport_w', 0) <= 0 or vfield.get('viewport_h', 0) <= 0:
        raise ValueError('readback viewport not reported')

    ready = _line(log, READY_MARKER)
    if 'registered=1' not in ready:
        raise ValueError('READY marker does not report a family-registered Frog')

    fields = {m.group('key'): int(m.group('value')) for m in _INT.finditer(_line(log, MARKER))}
    missing = [k for k in ('family_delta_last', 'family_specular_draws',
                           'total_specular_draws', 'specular_dir_calls',
                           'nonzero_pixels', 'replay_equal') if k not in fields]
    if missing:
        raise ValueError('specular marker missing fields: ' + ', '.join(missing))
    if fields['nonzero_pixels'] < 1:
        raise ValueError('actor capture is all black (nonzero_pixels=0)')
    if fields['family_delta_last'] < 1:
        raise ValueError('family draw did not upload the specular half-vector (family_delta_last)')
    if fields['total_specular_draws'] < 1:
        raise ValueError('scene never uploaded the GX_AF_SPEC half-vector')
    if fields['specular_dir_calls'] < 1:
        raise ValueError('scene never initialized the corrected specular half-vector')
    if fields['replay_equal'] != 1:
        raise ValueError('same-frame replay changed pixels')

    if PASS_LINE not in log.splitlines():
        raise ValueError('PASS line stripped from the captured log')
    return dict(fields, centered=wfield.get('centered'), reported=(w, h),
                viewport=(vfield.get('viewport_w'), vfield.get('viewport_h')))


def stage(assets, bank, output):
    """Stage the profiled Frog arena (generators + p2-frog.txt + profiled MODs)."""
    assets = Path(assets).resolve()
    bank = Path(bank).resolve()
    run = frog_arena_prepare(assets, bank, Path(output))
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('stage')
    for name in ('assets', 'bank', 'output'):
        s.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'stage':
        print(stage(args.assets, args.bank, args.output))
