"""Lane 18 Giant/small Breadbug coexistence validator (#168/#220).

Host-side parser for the combined arena produced by the additive small-proxy
observation in ``scripts/pikmin2_giant_breadbug_actor_fixture.cpp``. The fixture
declares the Giant and its nest generator pair first, then (optionally) one small
PanModoki P1 ``TEKI_Collec`` proxy generator and its engineered position. It
emits ``P2_GIANT_COEXIST`` only when both actors are alive and independent, and
keeps the existing Giant PASS line so the Giant's cargo/nest behavior is still
required to be unchanged.

The validator checks the log against :func:`pikmin2_breadbug_contest.
coexistence_report`: the Giant, small and nest generator ids must be pairwise
disjoint, there is exactly one nest per Giant and no small actor is claimed as a
nest. It does **not** model shared cargo: the small proxy keeps the P1
``TEKI_Collec`` host's own cargo pointer (see
``pikmin2_breadbug_contest_observation``), and this module never claims P2
contest semantics or shared cargo ownership.

The combined stage itself is not built here. ``staging_plan()`` records exactly
which pieces a runnable coexistence stage needs and which one is still missing;
see ``docs/PIKMIN2_BREADBUG_ACTOR_RUNTIME.md``.
"""
import argparse
import json
import re
from pathlib import Path

from experimental import pikmin2_breadbug_contest as contest

# The private small PanModoki proxy generator already used by
# ``experimental/pikmin2_breadbug_arena``; a coexistence stage may pick any
# disjoint id, this is only the default the arena file renders.
DEFAULT_SMALL_GENERATOR = 186081

READY_MARKER = 'P2_GIANT_BREADBUG_ACTOR_READY'
COEXIST_MARKER = 'P2_GIANT_COEXIST'
PASS_MARKER = 'PASS P2_GIANT_BREADBUG_ARENA'

SCOPE = ('Giant/small Breadbug coexistence identity check; the small proxy keeps '
         'its P1 TEKI_Collec host cargo; no P2 pull channel, shared cargo or '
         'contest semantics claimed')

# What a runnable combined Giant/small/nest stage requires. `missing` names the
# one piece this lane cannot commit: the committed Giant actor arena stager that
# produced the 187001/187002 generator rows in the private stage.
STAGING_PLAN = (
    'Original P1 Impact Site overlay keyed off the committed small proxy arena '
    '(experimental.pikmin2_breadbug_arena.prepare).',
    'Giant actor generator pair from the private giant-actor arena '
    '(giant TEKI_Collec + nest TEKI_Hollec, e.g. 187001/187002) with the '
    'p2-giant-breadbug-actor.txt config and lane_ootake_*/lane_nest_* models.',
    'One small PanModoki P1 TEKI_Collec proxy generator (e.g. 186081) plus the '
    'p2-breadbug-actor.txt config and breadbug_actor_* models from the lane-03 '
    'import, keeping generator ids disjoint from the Giant/nest pair.',
    'A giant-arena.txt listing giant/nest ids, their XYZ and the optional small '
    'id + XYZ consumed by the fixture.',
)
MISSING = ('The committed Giant actor arena stager. The Giant/nest generator '
           'rows (187001/187002) and p2-giant-breadbug-actor.txt config exist '
           'only in the private output stage '
           '(output/p2-lifecycle-batch/giant-actor-native-14/stages/...), so a '
           'combined Giant + small stage cannot be rebuilt from committed '
           'sources yet.')

_READY = re.compile(r'P2_GIANT_BREADBUG_ACTOR_READY generator=(\d+) nest=(\d+)')
_COEXIST = re.compile(r'P2_GIANT_COEXIST small=(\d+) giant=(\d+) nest=(\d+) '
                      r'small_alive=(\d+) giant_alive=(\d+) independent=(\d+)')


def arena_config(giant_id, nest_id, giant_xyz, nest_xyz, small_id=None,
                 small_xyz=None):
    """Render the ``giant-arena.txt`` the fixture consumes.

    Lines are ``giantId nestId`` / giant XYZ / nest XYZ and, when ``small_id`` is
    given, ``smallId`` + small XYZ. The generator roles are checked with the host
    coexistence model so an overlapping arena cannot be rendered.
    """
    if small_id is None:
        if small_xyz is not None:
            raise ValueError('small_xyz requires a small_id')
        smalls = []
    else:
        if small_xyz is None:
            raise ValueError('small_id requires a small_xyz')
        smalls = [small_id]
    report = contest.coexistence_report([giant_id], smalls, [nest_id])
    if not report['ok']:
        raise ValueError('Invalid coexistence arena: ' + '; '.join(report['violations']))
    lines = ['%d %d' % (giant_id, nest_id),
             '%.3f %.3f %.3f' % tuple(giant_xyz),
             '%.3f %.3f %.3f' % tuple(nest_xyz)]
    if small_id is not None:
        lines.append('%d %.3f %.3f %.3f' % (small_id, small_xyz[0], small_xyz[1],
                                            small_xyz[2]))
    return '\n'.join(lines) + '\n'


def validate(text):
    """Parse a fixture host log into a coexistence report.

    Raises ``ValueError`` when the Giant READY line or the ``P2_GIANT_COEXIST``
    marker is missing/duplicated, when the marker disagrees with the registered
    Giant/nest ids, or when the roles are not disjoint. The Giant PASS line is
    required so coexistence cannot pass while the Giant behavior regressed.
    """
    ready = _READY.findall(text)
    if len(ready) != 1:
        raise ValueError('Expected one Giant actor READY line')
    giant, nest = int(ready[0][0]), int(ready[0][1])
    coexist = _COEXIST.findall(text)
    if len(coexist) != 1:
        raise ValueError('Expected one P2_GIANT_COEXIST marker')
    small, mark_giant, mark_nest, small_alive, giant_alive, independent = coexist[0]
    small, mark_giant, mark_nest = int(small), int(mark_giant), int(mark_nest)
    if mark_giant != giant or mark_nest != nest:
        raise ValueError('Coexist marker ids disagree with the registered actors')
    report = contest.coexistence_report([giant], [small], [nest])
    if not report['ok']:
        raise ValueError('Invalid coexistence: ' + '; '.join(report['violations']))
    alive = bool(int(small_alive)) and bool(int(giant_alive))
    passed = bool(alive and int(independent) and PASS_MARKER in text)
    return {
        'passed': passed,
        'coexist_marker': True,
        'small_id': small,
        'giant_id': giant,
        'nest_id': nest,
        'small_alive': bool(int(small_alive)),
        'giant_alive': bool(int(giant_alive)),
        'independent': bool(int(independent)),
        'giant_unchanged': PASS_MARKER in text,
        'coexistence': report,
        'p2_contest_semantics': False,
        'shared_cargo': False,
        'scope': SCOPE,
    }


def staging_plan():
    """Return the combined-stage requirements and the one missing piece."""
    return {'steps': list(STAGING_PLAN), 'missing': MISSING,
            'runnable_from_committed_sources': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.log.read_text(errors='replace'))))


if __name__ == '__main__':
    main()
