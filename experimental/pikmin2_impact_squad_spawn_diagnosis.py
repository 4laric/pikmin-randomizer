"""Post-PARK squad-spawn stall classifier for headed chal0 runs (#698).

Reads one native boot log from the p1-challenge-impact-runtime-acceptance
runs and reports which stall signature it shows, with line numbers, so the
fixture-gating stall can be told apart from asset failures, captain
interruptions and genuine progress. Nothing here runs a binary, touches
assets, or claims gameplay: pure read-only log observation with
fail-closed unknowns.

Fixture contract under test
(tools/p2_challenge_guarded_boot_fixture.cpp, #649 lane): the RoomApp
observer parks the captain at observed==1 (P2_CHALLENGE_PARK), counts the
live squad at observed==60 (P2_CHALLENGE_SQUAD), declares boot at
observed>=120 (P2_CHALLENGE_BOOT) and passes at observed>=180. observed
advances only past the movie-skip, pause/UI and navi gates, so a log that
ends at PARK proves the observer froze -- it never proves whether a squad
spawned.
"""
import argparse
import json
import re
from pathlib import Path

PARK = 'P2_CHALLENGE_PARK'
SQUAD = 'P2_CHALLENGE_SQUAD'
BOOT = 'P2_CHALLENGE_BOOT'
GUARDED_PASS = 'PASS P2_CHALLENGE_GUARDED_BOOT'
CAPTAIN_DOWN = 'P2_FIXTURE_CAPTAIN_DOWN'
DVD_FAILED = 'FAILED to open'
WIN_ERROR = 'WinError'
SPAWNED = 'spawned'
ALIVEPIKIS = 'alivePikis'

VERDICTS = ('stall-post-park', 'progressed', 'captain-interrupted',
            'empty-log', 'no-park-marker', 'unknown')


def _lines(text):
    if not isinstance(text, str):
        raise ValueError('Boot log text required')
    return text.splitlines()


def last_marker_line(lines, token):
    """1-based line number of the last line containing token, else None."""
    found = None
    for number, line in enumerate(lines, 1):
        if token in line:
            found = number
    return found


def failed_reads(lines):
    """(line_number, line) for DVD FAILED and WinError read failures."""
    hits = []
    for number, line in enumerate(lines, 1):
        if DVD_FAILED in line or WIN_ERROR in line:
            hits.append((number, line.strip()[:200]))
    return hits


def spawn_evidence(lines):
    """Generator/spawn-count lines showing what the engine actually spawned."""
    hits = []
    for number, line in enumerate(lines, 1):
        if 'spawned' in line and ('generator' in line.lower()
                                  or 'Generator' in line
                                  or 'creature' in line):
            hits.append((number, line.strip()[:200]))
    return hits


def captain_signals(lines):
    """Captain-down/death lines; empty means the captain never interrupted."""
    hits = []
    for number, line in enumerate(lines, 1):
        if CAPTAIN_DOWN in line:
            hits.append((number, line.strip()[:200]))
    return hits


def engine_alive_after(lines, number):
    """True when engine heartbeat lines (FPS/texture stats) follow a marker."""
    for line in lines[number:]:
        if 'FPS:' in line or 'Textures:' in line:
            return True
    return False


def classify_run(text):
    """Classify one headed run log; never invents a verdict for unknowns."""
    lines = _lines(text)
    if not lines or not any(line.strip() for line in lines):
        return {'verdict': 'empty-log',
                'detail': 'log has no content; startup never produced output'}
    if last_marker_line(lines, PARK) is None:
        return {'verdict': 'no-park-marker',
                'detail': 'no PARK marker; stall is before fixture observation'}
    if captain_signals(lines):
        return {'verdict': 'captain-interrupted',
                'detail': 'captain-down interruption present; not a spawn stall',
                'signals': captain_signals(lines)}
    park_line = last_marker_line(lines, PARK)
    squad_line = last_marker_line(lines, SQUAD)
    boot_line = last_marker_line(lines, BOOT)
    pass_line = last_marker_line(lines, GUARDED_PASS)
    if squad_line is not None or boot_line is not None or pass_line is not None:
        return {'verdict': 'progressed',
                'detail': 'observation advanced past PARK; not the stall',
                'park_line': park_line, 'squad_line': squad_line,
                'boot_line': boot_line, 'pass_line': pass_line}
    return {'verdict': 'stall-post-park',
            'detail': 'observer froze after PARK: engine heartbeat continues '
                      'but observed never reached the squad count',
            'park_line': park_line,
            'failed_reads': failed_reads(lines),
            'spawn_evidence': spawn_evidence(lines),
            'captain_signals': captain_signals(lines),
            'engine_alive_after_park': engine_alive_after(lines, park_line)}


def compare_runs(texts):
    """Determinism check across run logs: shape agreement, not byte equality."""
    shapes = []
    for text in texts:
        lines = _lines(text)
        shapes.append({
            'lines': len(lines),
            'park_line': last_marker_line(lines, PARK),
            'failed_reads': len(failed_reads(lines)),
            'verdict': classify_run(text)['verdict'],
        })
    keys = {(s['lines'], s['park_line'], s['failed_reads']) for s in shapes}
    verdicts = {s['verdict'] for s in shapes}
    return {'runs': len(shapes), 'shapes': shapes,
            'identical_shape': len(keys) == 1,
            'unanimous_verdict': len(verdicts) == 1,
            'verdicts': sorted(verdicts)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        text = args.log.read_text(encoding='utf-8', errors='replace')
    except OSError:
        raise SystemExit('cannot read log: ' + str(args.log))
    print(json.dumps(classify_run(text), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
