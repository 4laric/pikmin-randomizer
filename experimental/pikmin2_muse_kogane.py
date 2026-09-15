"""Kogane9 natural-throw receiver acceptance (lane 54, #494).

Closes the remaining Kogane gate (attacks_receivers, source ID 9) with a real
thrown-Pikmin / player-controller event path. The legacy lane 17 acceptance
used a forced fixture attack directive (C-stick startAction + AttackMode after
a teleport) with the other beetles and observers held per frame; this runner
removes those substitutes:

  * the captain is staged exactly once beside the TARGET birth anchor
    (P2_KOGANE_THROW_STAGED);
  * every flip trigger is a genuine engine throw-release event pair (Piki
    transit to PIKISTATE_Flying + Navi::throwPiki at the beetle's live
    position, one P2_KOGANE_THROW row each);
  * ballistic flight, landing and engagement are the Pikmin's own AI; the flip
    arrives as InteractAttack through the native pc_p2_kogane_attacked
    receiver (P2_KOGANE_NATURAL_ATTACK);
  * no Pikmin is repositioned or commanded, nothing is pinned per frame.

``audit_fixture_source`` machine-checks the tracked fixture for those
substitutes so a forced-AI fixture can never validate here: a lane17-style
log (natural-attack rows but no throw rows / staged marker) is rejected even
though its flip rows look identical.

Gates 1/2/4/5/6 are preserved from the lane 17 evidence and are NOT
relabelled by this run; only gate 3 is supplied here.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_kogane_arena import prepare
from experimental.pikmin2_kogane_behavior import native_sidecar
from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import run as run_fixture_base
from scripts import build_pikmin2_fixture as builder

TARGET = 219001  # Iridescent Flint Beetle (source ID 9)
CONTROL = 219004
SOURCE_ID = 9
IDS = (219001, 219002, 219003, 219004)
PASS_MARKER = 'PASS P2_KOGANE_NATURAL_THROW flips3 escape1 control_alive'

# Source drop table for ID 9 in P1-host resolution (batch-1 audit):
# flip1: 1x 1-pellet; flip2: 2 nectar; flip3: 3 nectar (spray fallback).
EXPECTED_DROPS_9 = {1: (1, 1, 0), 2: (0, 0, 2), 3: (0, 0, 3)}

FIXTURE_BEGIN = '// MUSE-KOGANE-INCLUDES-BEGIN'
FIXTURE_SPLIT = '// MUSE-KOGANE-INCLUDES-END'
FIXTURE_APP = '// MUSE-KOGANE-APP-BEGIN'
FIXTURE_END = '// MUSE-KOGANE-APP-END'


def fixture_path():
    """Resolve the tracked fixture source through this worktree's native link."""
    root = Path(__file__).resolve().parent.parent
    path = root / 'native' / 'tools' / 'p2_muse_kogane_fixture.cpp'
    if not path.is_file():
        raise ValueError('Missing tracked Kogane throw fixture: ' + str(path))
    return path


def fixture_sections(text=None):
    """Split the tracked fixture into (includes, app) splice sections."""
    text = fixture_path().read_text(encoding='utf-8') if text is None else text
    try:
        includes = text.split(FIXTURE_BEGIN, 1)[1].split(FIXTURE_SPLIT, 1)[0]
        app = text.split(FIXTURE_APP, 1)[1].split(FIXTURE_END, 1)[0]
    except IndexError as error:
        raise ValueError('Kogane throw fixture section markers missing') from error
    if 'class RoomApp : public PlugPikiApp {' not in app:
        raise ValueError('Kogane throw fixture RoomApp missing')
    return includes, app


def audit_fixture_source(text=None):
    """Machine-check that the fixture contains no forced-AI substitute.

    Exactly one repositioning call is allowed (the single staged captain
    placement); no Pikmin attack directive, mode write, injected press path or
    per-frame holder may appear. The genuine throw-release pair must be
    present.
    """
    text = fixture_path().read_text(encoding='utf-8') if text is None else text
    checks = dict(
        single_staged_reposition=text.count('resetPosition') == 1,
        no_attack_directive='startAction' not in text,
        no_mode_write='mMode' not in text,
        no_injected_press='InteractPress' not in text and 'kogane_pressed' not in text,
        no_perframe_holders='pinObservers' not in text and 'holdOthers' not in text
        and 'P2_KOGANE_NATURAL_COMMAND' not in text,
        throw_release_present='throwPiki' in text and 'PIKISTATE_Flying' in text
        and 'findNextThrowPiki' in text and 'P2_KOGANE_THROW_STAGED' in text,
    )
    return dict(passed=all(checks.values()), checks=checks)


def validate_natural_throw(text, code, fixture_text=None):
    """Validate a natural-throw run log.

    Requires the staged captain marker, one throw row per genuine release,
    the three native receiver flips with the audited drop table for ID 9, the
    source escape, a live control and the completion marker -- plus a clean
    fixture audit. A forced-AI log has identical flip rows but no throw rows
    or staged marker and is rejected.
    """
    audit = audit_fixture_source(fixture_text)
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    staged = re.findall(r'P2_KOGANE_THROW_STAGED nx=(-?\d+\.\d+) ny=(-?\d+\.\d+) nz=(-?\d+\.\d+) '
                        r'bx=(-?\d+\.\d+) by=(-?\d+\.\d+) bz=(-?\d+\.\d+)', text)
    throws = [int(n) for n in re.findall(r'P2_KOGANE_THROW n=(\d+) generator=219001', text)]
    squad = re.findall(r'P2_KOGANE_SQUAD pikis=(\d+)', text)
    naturals = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_NATURAL_ATTACK generator=(\d+) source_id=\d+ flip=(\d)', text))
    flips = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text))
    drops = {(int(g), int(f)): (int(pv), int(pc), int(nc)) for g, f, pv, pc, nc in
             re.findall(r'P2_KOGANE_DROP generator=(\d+) source_id=\d+ flip=(\d) '
                        r'pellet(\d+)=(\d+) nectar=(\d+)', text)}
    escapes = sorted(int(g) for g in re.findall(r'P2_KOGANE_ESCAPE generator=(\d+)', text))
    target_flips = [f for g, f in flips if g == TARGET]
    target_naturals = [f for g, f in naturals if g == TARGET]
    checks = dict(
        fixture_audit=audit['passed'],
        completion=code == 0 and PASS_MARKER in text,
        births=births == list(IDS),
        staged_once=len(staged) == 1,
        starting_squad=[int(s) for s in squad] == [20],
        throws_sequential=throws == list(range(1, len(throws) + 1)) and len(throws) >= 3,
        natural_attacks=target_naturals == [1, 2, 3],
        flips=target_flips == [1, 2, 3],
        drop_tables=all(drops.get((TARGET, f)) == EXPECTED_DROPS_9[f] for f in (1, 2, 3)),
        escape=TARGET in escapes,
        no_forced_markers='P2_KOGANE_NATURAL_COMMAND' not in text
        and 'P2_KOGANE_THROW_BUDGET_EXHAUSTED' not in text,
    )
    return dict(passed=all(checks.values()), checks=checks, audit=audit,
                throws=throws, staged=len(staged),
                naturals=[list(n) for n in naturals],
                flips=[list(f) for f in flips],
                drops={f'{g}:{f}': list(v) for (g, f), v in sorted(drops.items())},
                unmeasured=['ordinary pickup of the three drops (proven by lane 17; '
                            'this free squad may drink nectar)',
                            'restart accounting (proven by lane 17; single-pass run)',
                            'cave relocation (no P2 cave in the P1 host)',
                            'treasure override (disabled: no P2 treasure in P1 host)'])


def build(native, build_dir, output, head, resume=False):
    includes, app = fixture_sections()
    return build_fixture_base(native, build_dir, output, head, resume, app=includes + app)


def run(assets, bank, output, exe):
    # Standard acceptance launch: 960x540 centred window, UTF-8, dummy audio.
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PYTHONUTF8'] = '1'
    fixture_text = fixture_path().read_text(encoding='utf-8')
    run_fixture_base(assets, bank, output, exe, sidecar=native_sidecar(bank),
                     validator=lambda text, code: validate_natural_throw(text, code, fixture_text))
    stage_dirs = sorted(Path(output).resolve().glob('*/native.log'))
    if stage_dirs:
        stage = stage_dirs[-1].parent
        evidence = json.loads((stage / 'runtime-evidence.json').read_text(encoding='utf-8'))
        evidence['fixture_sources'] = builder.snapshot([fixture_path(), Path(__file__).resolve()])
        evidence['fixture_audit'] = audit_fixture_source(fixture_text)
        (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')


def instrument(source):
    includes, app = fixture_sections()
    from experimental.pikmin2_kogane_runtime import instrument as base
    return base(source, includes + app)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, a.bank, a.output, a.exe)
