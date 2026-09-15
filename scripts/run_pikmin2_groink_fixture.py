"""Run the private stationary Groink fixture in a fresh local asset overlay.

Requires original local assets, a converted room, a staged Groink pose, and a
provenance-checked native fixture build. No assets or executable are distributed.
Machine PASS covers collision/readback; visual fidelity requires image review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preview_pikmin2_room import prepare


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_fixture(assets, room, stage, fixture, output, expected_contact):
    fixture = fixture.resolve()
    provenance = json.loads((fixture / 'provenance.json').read_text(encoding='utf-8'))
    exe = fixture / 'fixture.exe'
    expected = provenance.get('artifacts', {}).get(str(exe), {}).get('sha256')
    if provenance.get('status') != 'built' or expected != digest(exe):
        raise ValueError('Fixture does not match successful build provenance')
    model = stage / 'assets/dataDir/courses/pikmin2room/groink_attack.mod'
    profile = stage / 'p2-groink-arena.txt'
    inputs = {str(p.resolve()): digest(p) for p in (model, profile, room / 'room.mod', room / 'room.ini')}
    run = prepare(assets, room, output)
    target = run / 'assets/dataDir/courses/pikmin2room/groink_attack.mod'
    if target.exists():
        raise ValueError('Overlay already contains Groink model; refusing overwrite')
    shutil.copy2(model, target)
    shutil.copy2(profile, run / profile.name)
    record = dict(schema=1, run=str(run), fixture=str(exe), fixture_sha256=expected,
                  inputs=inputs, expected_contact=expected_contact, status='failed',
                  visual_review='required; nonblack readback does not prove model fidelity')
    try:
        with (run / 'native.log').open('wb') as log:
            process = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=run,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=75)
        record['exit_code'] = process.returncode
        text = (run / 'native.log').read_text(encoding='utf-8', errors='replace')
        match = re.search(r'P2_GROINK_FLIGHT_PASS ticks=(\d+) traces=(\d+) floors=(\d+) walls=(\d+)', text)
        if process.returncode or 'P2_GROINK_MAP_PROBES_PASS' not in text or 'PASS GROINK_RUNTIME' not in text or not match:
            raise ValueError('Native fixture failed; inspect native.log')
        record['flight'] = dict(zip(('ticks', 'traces', 'floors', 'walls'), map(int, match.groups())))
        if not record['flight'][expected_contact + 's']:
            raise ValueError('Shell did not hit requested contact type')
        captures = [run / ('groink-weighted-' + name + '.ppm') for name in ('flight', 'terminal')]
        record['captures'] = {str(p): digest(p) for p in captures}
        record['status'] = 'passed'
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        record['error'] = str(error)
    finally:
        (run / 'runtime-verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'room', 'stage', 'fixture', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--expected-contact', choices=('floor', 'wall'), required=True)
    args = parser.parse_args()
    result = run_fixture(**vars(args))
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['status'] == 'passed' else 1)
