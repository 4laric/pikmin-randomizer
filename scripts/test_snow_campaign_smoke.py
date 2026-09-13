"""Owned hidden normal-campaign boot/fixture check in a fresh disposable session."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import _winapi
from randomizer.runner import NativeRun
from randomizer.session import Session


def smoke(exe, assets, manifest, output, fixture=False):
    output.mkdir(parents=True, exist_ok=False)
    session = Session(manifest, output / 'session')
    run = NativeRun(session)
    _winapi.CreateJunction(str(assets), str(run.directory / 'assets'))
    env = dict(os.environ, PIKMIN_RANDOMIZER_TEST_BACKGROUND='1', SDL_AUDIODRIVER='dummy',
               PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    expected = hashlib.sha256(exe.read_bytes()).hexdigest()
    started = time.monotonic()
    log = run.directory / 'native.log'
    passed = False
    with log.open('w') as stream:
        process = subprocess.Popen([str(exe), '--randomizer-seed', str(run.bootstrap)],
                                   cwd=run.directory, env=env, stdout=stream, stderr=subprocess.STDOUT)
        try:
            while time.monotonic() - started < 90:
                run.poll()
                run.write_state(run.handshaken)
                text = log.read_text(errors='replace')
                if process.poll() is not None:
                    passed = fixture and process.returncode == 0 and 'PASS snow campaign:' in text
                    break
                if not fixture and run.handshaken and 'P2_SNOW_CAMPAIGN_READY' in text and time.monotonic() - started > 8:
                    passed = True
                    break
                time.sleep(.1)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    report = dict(passed=passed, fixture=fixture, handshaken=run.handshaken,
                  native_log=str(log), exe_sha256=expected,
                  exe_unchanged=hashlib.sha256(exe.read_bytes()).hexdigest() == expected,
                  ending='fixture exit' if fixture else 'owned process stopped after boot smoke',
                  exit_code=process.returncode)
    report['passed'] = report['passed'] and report['exe_unchanged']
    (output / 'result.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'assets', 'manifest', 'output'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--fixture', action='store_true')
    a = p.parse_args()
    result = smoke(a.exe.resolve(), a.assets.resolve(), json.loads(a.manifest.read_text()), a.output.resolve(), a.fixture)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
