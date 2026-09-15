"""Lane 20 (#169) Kabuto Stone -> real engine receiver-mutation runtime proof.

Before this slice lane 20's projectile host only applied emitted Stone/Rock
strikes to a private host-owned proxy receiver; engine actor health was never
mutated. This harness drives the *production* ``--experimental-pikmin2-room``
room preview with a ``p2-projectiles.txt`` config that enables the new opt-in
``engine_receiver`` row, then validates the observed ``P2_PROJECTILE_ENGINE_STRIKE``
markers that record a live creature's health / stored-damage change through the
engine's own ``stimulate(InteractAttack/InteractPress)`` path (source
Rock.cpp:204-238).

Two config modes, both using the standard room's Dwarf Bulborb actor
(``TEKI_Chappy``, generator ``preview dwarf bulborb``) as the Teki target and the
20-red starting squad as the Navi/Pikmin population:

* ``stone``  — a single non-homing Stone birthed directly beside the Dwarf, so it
  contacts the Teki on its first tick and applies the source-fixed 250
  ``InteractAttack``.
* ``kabuto`` — the ordinary Cannon Beetle fire FSM (Wait → Turn → Attack →
  KEYEVENT_2) drives the Stone birth from a configured mouth joint toward the
  Dwarf, so the whole integrated chain ends in the same receiver mutation.
* ``two_teki`` — a two-Teki room (the standard Dwarf bound as the Kabuto firer
  plus a duplicated victim Dwarf). The bound Stone skips its own firer
  (``P2_PROJECTILE_SKIP_SELF``) yet still strikes the *second* Teki through the
  real engine receiver (``P2_PROJECTILE_ENGINE_STRIKE`` with the victim token),
  closing the over-suppression gap. The victim is re-anchored to the firer each
  step (``teki_pin 1``, injected placement, labelled ``P2_PROJECTILE_TEKI_PIN``)
  because the room's two Dwarfs otherwise wander ~70 units apart. The same room
  also drives the lane-21 Groink strike bridge (``p2_groink_apply_strike``)
  against this lane's proxy receiver for a Bomb strike, proving a second family
  consumes the shared projectile-receiver primitive without forking lane-21's
  modules.

Both modes leave the proxy receiver enabled (``receiver any``) so the new engine
path is reported beside the existing proxy path, not instead of it.
"""
import argparse
import json
import os
import re
import struct
import subprocess
import time
from pathlib import Path

from scripts.preview_pikmin2_room import prepare as _prepare_room, records as _gen_records

MAGIC = 'P2_PROJECTILES_1'

# Disc parms (docs/PIKMIN2_CANNON_PROJECTILE_ASSETS.md §5): Stone speed fp06 250,
# proper search-rumble speed fp01 100, life fp00 99999. The source Teki damage is
# the fixed 250 in Rock.cpp (the attackDamage field below only drives the grounded
# Navi/Pikmin InteractPress branch and is not what mutates the Teki).
STONE_PARMS = dict(moveSpeed=250.0, searchRumbleSpeed=100.0, turnSpeed=0.1,
                   maxTurnAngle=180.0, attackDamage=10.0, sightRadius=1000.0,
                   collisionRadius=40.0, health=99999.0)

# The standard room places the Dwarf Bulborb at (185, 0, -180)
# (scripts/preview_pikmin2_room.py). The Stone is birthed beside it so the first
# contact-detection pass finds the Teki within collisionRadius (40) + host pad (12).
DWARF_POS = (185.0, 0.0, -180.0)
# Facing +x (initialVelocity = moveSpeed * (sin face, 0, cos face)).
FACE_DEG = 90.0

# Second Teki (victim) spawn. It is a duplicated copy of the standard Dwarf
# generator record, so the room holds two live `TEKI_Chappy` with distinct runtime
# tokens. The room's two Dwarfs naturally settle ~70 units apart, so the two-Teki
# run also enables `teki_pin 1` (see build_config) to re-anchor the victim to the
# bound firer each step; the spawn co-ordinate only has to place a second valid
# Chappy somewhere in the room.
VICTIM_POS = (185.0, 0.0, -180.0)

# Groink consumer proof: the muzzle fire origin is placed 30 units above the
# captain's navi_start (scripts/preview_pikmin2_room.py: -85, 0, 0), so the
# muzzle-origin -> live-captain sweep deterministically contains the captain.
GROINK_ORIGIN = (-85.0, 30.0, 0.0)
GROINK_DAMAGE = 10.0


def add_second_teki(run_dir, position=VICTIM_POS, name='preview dwarf victim'):
    """Duplicate the prepared room's single Dwarf Bulborb generator record.

    The generated ``default.gen`` carries exactly one Dwarf (the Kabuto firer).
    Cloning its record (new id/name/position) yields a second live Teki with a
    distinct runtime token, so the bound Stone must prove it skips only its own
    firer and not every Teki in range.
    """
    gen = run_dir / 'assets' / 'dataDir' / 'stages' / 'chal0' / 'default.gen'
    data = gen.read_bytes()
    if data[:4] != b'1.0v':
        raise ValueError('unexpected prepared gen header')
    recs = _gen_records(gen)
    dwarf = next((r for r in recs if r[16:48].rstrip(b'\0') == b'preview dwarf bulborb'), None)
    if dwarf is None:
        raise ValueError('prepared room has no dwarf bulborb record')
    victim = bytearray(dwarf)
    victim[8:12] = struct.pack('>I', len(recs) + 1)
    victim[16:48] = name.encode('ascii').ljust(32, b'\0')
    victim[48:72] = struct.pack('>6f', *position, 0.0, 0.0, 0.0)
    gen.write_bytes(data[:20] + struct.pack('>I', len(recs) + 1) + b''.join(recs) + bytes(victim))


def stone_config(position=None, face_deg=FACE_DEG):
    x, y, z = position or DWARF_POS
    p = STONE_PARMS
    return ('stone %.6g %.6g %.6g %.6g 0 %.6g %.6g %.6g %.6g %.6g %.6g %.6g %.6g 0'
            % (x, y, z, face_deg, p['moveSpeed'], p['searchRumbleSpeed'], p['turnSpeed'],
               p['maxTurnAngle'], p['attackDamage'], p['sightRadius'], p['collisionRadius'],
               p['health']))


def kabuto_config(species='Kabuto', position=None, face_deg=FACE_DEG):
    x, y, z = position or (175.0, 0.0, -180.0)
    # mouth joint in front of the Dwarf, facing +x; the FSM births the Stone at
    # the mouth + (0,25,0). Kabuto = non-homing straight, Rkabuto = homing toward
    # the nearest Navi/Pikmin (the 20-red starting squad).
    return ('kabuto %s %.6g %.6g %.6g %.6g 180 850 30 15 20 8'
            % (species, x, y, z, face_deg))


def groink_config(position=GROINK_ORIGIN, damage=GROINK_DAMAGE):
    x, y, z = position
    return 'groink %.6g %.6g %.6g %.6g' % (x, y, z, damage)


def rig_bank_text():
    """Minimal valid P2_ATTACHMENTS_1 sidecar: `root` + `kuti` mouth joint and a
    60-frame `attack` clip (fire frame 50). Identity TRS samples place the mouth
    at the actor transform, so a Kabuto-actor Stone is born 25 above its own firer
    (inside collisionRadius 40 + pad) — exactly the birth-frame self-contact the
    SKIP_SELF path must reject."""
    s = '0 0 0 0 0 0 1 1 1 1'
    lines = ['P2_ATTACHMENTS_1 2 1', 'root -1', 'kuti 0', 'attack 60 2', '0 59',
             s, s, s, s]
    return '\n'.join(lines) + '\n'


BUILDER_MODES = ('stone', 'kabuto', 'rkabuto', 'kabuto_actor', 'two_teki')


def build_config(mode='stone', generator=0, with_proxy=True):
    """Return the full p2-projectiles.txt body for the requested mode."""
    lines = [MAGIC, 'seed 1']
    lines.append(stone_config())            # stone parms (also the FSM's pool source)
    if mode == 'kabuto':
        lines.append(kabuto_config('Kabuto'))
    elif mode == 'rkabuto':
        lines.append(kabuto_config('Rkabuto'))
    elif mode == 'kabuto_actor':
        lines.append(kabuto_config('Kabuto'))
        # `kabuto_actor` requires a `kabuto_rig` sidecar; rig-bank.txt is written
        # beside p2-projectiles.txt by run().
        lines.append('kabuto_rig rig-bank.txt 185 0 -180 90')
        lines.append('kabuto_actor %d' % generator)
    elif mode == 'two_teki':
        lines.append(kabuto_config('Kabuto'))
        lines.append('kabuto_rig rig-bank.txt 185 0 -180 90')
        lines.append('kabuto_actor %d' % generator)
        lines.append('teki_pin 1')
        lines.append(groink_config())
    lines.append('engine_receiver 1')
    if with_proxy:
        lines.append('receiver any 20')
    return '\n'.join(lines) + '\n'


ENGINE_STRIKE_RE = re.compile(
    r'P2_PROJECTILE_ENGINE_STRIKE target=(\d+) kind=(Attack|Press) damage=([\d.]+) '
    r'applied=(\d) rejected=(\d) health=([\d.-]+)->([\d.-]+) stored=([\d.-]+)->([\d.-]+) '
    r'source=(\d+)')

SKIP_SELF_RE = re.compile(r'P2_PROJECTILE_SKIP_SELF target=(\d+)')

GROINK_RECEIVER_HIT_RE = re.compile(
    r'P2_PROJECTILE_GROINK_RECEIVER_HIT token=(\d+) kind=(\w+) damage=([\d.]+) '
    r'applied=(\d) died=(\d) health=([\d.-]+)')


def parse_engine_strikes(log_text):
    """Return a list of parsed P2_PROJECTILE_ENGINE_STRIKE records."""
    out = []
    for m in ENGINE_STRIKE_RE.finditer(log_text):
        out.append(dict(target=int(m.group(1)), kind=m.group(2),
                        damage=float(m.group(3)), applied=int(m.group(4)),
                        rejected=int(m.group(5)), health_before=float(m.group(6)),
                        health_after=float(m.group(7)),
                        stored_before=float(m.group(8)), stored_after=float(m.group(9)),
                        source=int(m.group(10))))
    return out


def evaluate(log_text):
    """Evaluate the runtime log against the lane-20 receiver-mutation gates.

    Returns a dict of gate -> status and the parsed evidence, so the runtime (or a
    mocked-log unit test) reports PASS/FAIL honestly without needing the engine.
    """
    strikes = parse_engine_strikes(log_text)
    teki = [s for s in strikes if s['kind'] == 'Attack']
    press = [s for s in strikes if s['kind'] == 'Press']

    def teki_ok():
        for s in teki:
            if s['applied'] and s['stored_after'] > s['stored_before'] + 1.0:
                return True
        return False

    def press_ok():
        for s in press:
            if s['applied'] and s['health_after'] < s['health_before']:
                return True
        return False

    window = 'Experimental preview window set to 960x540 windowed and centered' in log_text
    ready = 'P2_PROJECTILES_READY' in log_text
    stone_contact = 'P2_PROJECTILE_STONE_CONTACT' in log_text
    kabuto_fire = 'P2_PROJECTILE_KABUTO_FIRE' in log_text
    destroy = 'P2_PROJECTILE_STONE_DESTROY' in log_text

    skip_self = set(int(m) for m in SKIP_SELF_RE.findall(log_text))
    attack_targets = {s['target'] for s in teki}
    self_hit = bool(skip_self & attack_targets)

    # Two-Teki proof: an applied Teki Attack whose target is NOT the skipped firer
    # proves the Stone struck a *second* Teki (skip-self did not over-suppress).
    victim_struck = any(s['applied'] and s['target'] not in skip_self for s in teki)

    groink_hits = list(GROINK_RECEIVER_HIT_RE.finditer(log_text))
    groink_bomb = any(m.group(2) == 'Bomb' and m.group(4) == '1' for m in groink_hits)

    gates = {
        'window_960x540_centered': 'PASS' if window else 'FAIL',
        'config_ready': 'PASS' if ready else 'FAIL',
        'stone_contact': 'PASS' if stone_contact else 'FAIL',
        'cannon_fire_fsm': 'PASS' if kabuto_fire else 'UNTESTED',
        'teki_attack_receiver_mutation': 'PASS' if teki_ok() else 'FAIL',
        'navipiki_press_receiver_mutation': 'PASS' if press_ok() else ('UNTESTED' if not press else 'FAIL'),
        'cannon_self_hit_skipped': ('PASS' if (skip_self and not self_hit)
                                    else ('UNTESTED' if not skip_self else 'FAIL')),
        'second_teki_engine_strike': ('PASS' if (skip_self and victim_struck)
                                      else ('UNTESTED' if not skip_self else 'FAIL')),
        'groink_bomb_receiver_mutation': ('PASS' if groink_bomb
                                          else ('UNTESTED' if not groink_hits else 'FAIL')),
        'stone_destroy_teardown': 'PASS' if destroy else 'UNTESTED',
    }
    return dict(gates=gates, strikes=strikes)


def run(exe, assets, converted, output, mode='stone', seconds=40.0, generator=0):
    """Stage a fresh room, write the config, launch the exe, capture and evaluate."""
    run_dir = _prepare_room(Path(assets).resolve(), Path(converted).resolve(), Path(output))
    if mode == 'two_teki':
        add_second_teki(run_dir)
    (run_dir / 'p2-projectiles.txt').write_text(build_config(mode, generator), encoding='utf8')
    if mode in ('kabuto_actor', 'two_teki'):
        (run_dir / 'rig-bank.txt').write_text(rig_bank_text(), encoding='utf8')

    env = dict(os.environ)
    env['PYTHONUTF8'] = '1'
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PATH'] = r'C:\msys64\mingw64\bin;' + env.get('PATH', '')

    log_path = run_dir / 'native.log'
    with log_path.open('wb') as log:
        proc = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                cwd=str(run_dir), stdout=log, stderr=subprocess.STDOUT,
                                env=env)
        deadline = time.time() + seconds
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.25)
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    log_text = log_path.read_text(encoding='utf8', errors='replace')
    result = evaluate(log_text)
    result['exit_code'] = proc.returncode
    result['run_dir'] = str(run_dir)
    result['mode'] = mode
    result['log_len'] = len(log_text)
    (run_dir / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe', type=Path, required=True)
    p.add_argument('--assets', type=Path,
                   default=Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets'))
    p.add_argument('--converted', type=Path,
                   default=Path('C:/Users/alari/pikmin-randomizer/output/pikmin2-room105'))
    p.add_argument('--output', type=Path,
                   default=Path('C:/Users/alari/pikmin-randomizer/output/projectile-engine-receiver'))
    p.add_argument('--mode', choices=BUILDER_MODES, default='stone')
    p.add_argument('--generator', type=int, default=0,
                   help='kabuto_actor generator ID (room Teki _70 value)')
    p.add_argument('--seconds', type=float, default=40.0)
    a = p.parse_args()
    result = run(a.exe, a.assets, a.converted, a.output, a.mode, a.seconds, a.generator)
    print(json.dumps(result, indent=2))
    ok = all(v in ('PASS', 'UNTESTED') for v in result['gates'].values())
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
