"""Cumulative runtime upgrades, reconnect caps and rejected state retractions."""
import sys
import subprocess
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate
from randomizer.session import Session, atomic_write
from randomizer.runner import NativeRun
from randomizer.catalog import ITEM_IDS, REPAIR
from randomizer.stats import upgrade_pool, current_profiles

exe = str(Path(sys.argv[1]).resolve())
for rolled, invalid, counts in ((False, False, None), (False, True, None), (True, False, None), (True, True, None), (True, False, dict(damage=1, movement=0, attack_rate=1, carry=0))):
    with tempfile.TemporaryDirectory() as d:
        session = Session(generate('live', 'ap', progressive_color_stats=True, randomize_color_stats=rolled, starting_flarlic=1, stat_upgrade_counts=counts), d)
        session.bind_ap('room', 0, 1)
        run = NativeRun(session); run.write_state(True)
        log = Path(d) / 'probe.log'
        with log.open('w') as output:
            process = subprocess.Popen([exe, '--randomizer-seed', str(run.bootstrap), '--upgrade-probe'], stdout=output, stderr=subprocess.STDOUT)
            try:
                def wait(marker):
                    deadline = time.monotonic() + 5
                    while time.monotonic() < deadline:
                        run.write_state(True)
                        if marker in log.read_text(): return
                        assert process.poll() is None, log.read_text()
                        time.sleep(.1)
                    raise AssertionError(log.read_text())
                def expected(color, index):
                    p = current_profiles(session.manifest, session.inventory)[color]
                    return f"LIVE_STATS {index} {p['damage']} {p['movement']} {p['attack_rate']} {p['carry']}"
                wait(expected('red', 1))
                run.poll(); assert run.handshaken
                ids = [ITEM_IDS[n] for n in (('Progressive Red Attack Rate', 'Progressive Red Damage') if counts is not None else ('Progressive Red Carry Strength', 'Progressive Red Damage'))]
                session.receive(0, ids); session.receive(0, ids)
                wait(expected('red', 1))
                if invalid:
                    # Same valid identity, but older inventory is rejected.
                    stale = Session(session.manifest, Path(d) / 'stale')
                    deadline = time.monotonic() + 5
                    while process.poll() is None and time.monotonic() < deadline:
                        atomic_write(run.directory / 'state.txt', stale.native_state(run.token, True))
                        time.sleep(.1)
                    assert process.poll() is not None and process.returncode != 0, log.read_text()
                    assert 'retracted stat upgrade' in log.read_text()
                else:
                    session.receive(2, [ITEM_IDS[n] for n in upgrade_pool(session.manifest)] * 2)
                    wait(expected('red', 1))
                    wait(expected('blue', 0))
                    wait(expected('yellow', 2))
                    session.receive(len(session.data['received']), [ITEM_IDS[REPAIR]] * 25)
                    wait('GOAL: Ship repaired!')
                    assert process.wait(timeout=5) == 0, log.read_text()
            finally:
                if process.poll() is None: process.terminate(); process.wait(timeout=5)
print('PASS: live vanilla baseline, independent per-color tiers, duplicate receipt replay, caps, handshake and retraction rejection')
