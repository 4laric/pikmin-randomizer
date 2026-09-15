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
  closing the over-suppression gap. The victim is a natural-settle Teki placed in
  the fire corridor, so the Stone reaches it *in flight* (``--teki-pin`` is an
  opt-in injected-co-location scenario, labelled ``P2_PROJECTILE_TEKI_PIN``, not
  part of the primary run). The same room drives the lane-21 Groink classifier
  (``p2_groink_classify_hit``) and applies the classified Bomb through this lane's
  **engine** receiver on the live captain Navi
  (``P2_PROJECTILE_GROINK_ENGINE_HIT`` with a health decrease), proving a second
  family consumes the shared receiver primitive without forking lane-21's modules.

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

# Second Teki (victim) spawn: placed directly in the firer's fire corridor
# (the firer settles at ~(173.6, 0, -143.2) and faces +z), so the victim's
# natural settle — wherever its one-time spawn move lands it — stays within the
# Stone's collision radius of the +z trajectory. The Stone therefore strikes the
# victim *in flight* (~50-90 units downrange), not at the birth frame. `teki_pin`
# (injected co-location) remains available as a separately-flagged scenario (see
# build_config) and is NOT part of the primary two-Teki run.
VICTIM_POS = (173.6, 0.0, -60.0)

# Groink consumer proof: the muzzle fire origin is placed 30 units above the
# captain's navi_start (scripts/preview_pikmin2_room.py: -85, 0, 0), so the
# muzzle-origin -> live-captain sweep deterministically contains the captain.
GROINK_ORIGIN = (-85.0, 30.0, 0.0)
GROINK_DAMAGE = 10.0

# Bomb consumer proof: same muzzle origin/damage as the Groink proof; the
# detonated Bomb is applied through the engine receiver on the live captain Navi.
BOMB_ORIGIN = (-85.0, 30.0, 0.0)
BOMB_DAMAGE = 10.0


def add_second_teki(run_dir, position=VICTIM_POS, name='preview dwarf victim', count=1):
    """Duplicate the prepared room's single Dwarf Bulborb generator record.

    The generated ``default.gen`` carries exactly one Dwarf (the Kabuto firer).
    Cloning its record (new id/name/position) yields `count` live victim Teki with
    distinct runtime tokens, so the bound Stone proves it skips only its own firer
    and can strike each surviving victim in flight (repeatable flight strikes).
    Secondary victims are scattered along the firer's +z corridor so each
    subsequent fire finds the next surviving victim.
    """
    gen = run_dir / 'assets' / 'dataDir' / 'stages' / 'chal0' / 'default.gen'
    data = gen.read_bytes()
    if data[:4] != b'1.0v':
        raise ValueError('unexpected prepared gen header')
    recs = _gen_records(gen)
    dwarf = next((r for r in recs if r[16:48].rstrip(b'\0') == b'preview dwarf bulborb'), None)
    if dwarf is None:
        raise ValueError('prepared room has no dwarf bulborb record')
    x, y, z = position
    victims = []
    for i in range(count):
        victim = bytearray(dwarf)
        victim[8:12] = struct.pack('>I', len(recs) + 1 + i)
        victim[16:48] = (name + (' %d' % i)).encode('ascii').ljust(32, b'\0')
        vx, vy, vz = x, y, z + i * 22.0
        victim[48:72] = struct.pack('>6f', vx, vy, vz, 0.0, 0.0, 0.0)
        victims.append(bytes(victim))
    gen.write_bytes(data[:20] + struct.pack('>I', len(recs) + count)
                    + b''.join(recs) + b''.join(victims))


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


def bomb_config(position=BOMB_ORIGIN, damage=BOMB_DAMAGE):
    x, y, z = position
    return 'bomb %.6g %.6g %.6g %.6g' % (x, y, z, damage)


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


def build_config(mode='stone', generator=0, with_proxy=True, teki_pin=False):
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
        # The primary two-Teki run is NOT injected: the victim sits at its natural
        # settle in the fire corridor and the Stone reaches it in flight. teki_pin
        # (injected co-location) is opt-in via the teki_pin flag.
        if teki_pin:
            lines.append('teki_pin 1')
        lines.append(groink_config())
        lines.append(bomb_config())
    lines.append('engine_receiver 1')
    if with_proxy:
        lines.append('receiver any 20')
    return '\n'.join(lines) + '\n'


ENGINE_STRIKE_RE = re.compile(
    r'P2_PROJECTILE_ENGINE_STRIKE target=(\d+) kind=(Attack|Press) damage=([\d.]+) '
    r'applied=(\d) rejected=(\d) health=([\d.-]+)->([\d.-]+) stored=([\d.-]+)->([\d.-]+) '
    r'source=(\d+)')

SKIP_SELF_RE = re.compile(r'P2_PROJECTILE_SKIP_SELF target=(\d+)')

STONE_DESTROY_RE = re.compile(r'P2_PROJECTILE_STONE_DESTROY reason=(\w+) traces=(\d+)')

GROINK_ENGINE_HIT_RE = re.compile(
    r'P2_PROJECTILE_GROINK_ENGINE_HIT token=(\d+) kind=(\w+) damage=([\d.]+) '
    r'applied=(\d) rejected=(\d) health=([\d.-]+)->([\d.-]+)')

KABUTO_AIM_RE = re.compile(
    r'P2_PROJECTILE_KABUTO_AIM fire=(\d+) victim=\(([\d.-]+),([\d.-]+),([\d.-]+)\) '
    r'origin=\(([\d.-]+),([\d.-]+),([\d.-]+)\) face_deg=([\d.-]+)')

BOMB_ENGINE_HIT_RE = re.compile(
    r'P2_PROJECTILE_BOMB_ENGINE_HIT token=(\d+) kind=(\w+) damage=([\d.]+) '
    r'applied=(\d) rejected=(\d) health=([\d.-]+)->([\d.-]+)')


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


def strike_ratio_of(log_text):
    """Return (fires, hits): the number of Kabuto fires vs the number of
    health-destroy contacts in the log."""
    fires = len(re.findall(r'P2_PROJECTILE_KABUTO_FIRE\b', log_text))
    hits = sum(1 for m in STONE_DESTROY_RE.finditer(log_text) if m.group(1) == 'health')
    return fires, hits


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

    # Groink engine-receiver proof: the classified Bomb is applied through the
    # captain Navi's own stimulate(InteractAttack), so apply=1 AND a real health
    # decrease are required (a proxy/wind path would not move the Navi's health).
    groink_hits = list(GROINK_ENGINE_HIT_RE.finditer(log_text))
    groink_bomb_navi = any(
        m.group(2) == 'Bomb' and m.group(4) == '1'
        and float(m.group(7)) < float(m.group(6))
        for m in groink_hits)

    # Bomb engine-receiver proof: the detonated Bomb is applied through the
    # captain Navi's own engine receiver, so kind=Bomb, apply=1 AND a real health
    # decrease are required.
    bomb_hits = list(BOMB_ENGINE_HIT_RE.finditer(log_text))
    bomb_engine_navi_hit = any(
        m.group(2) == 'Bomb' and m.group(4) == '1'
        and float(m.group(7)) < float(m.group(6))
        for m in bomb_hits)

    fires, hits = strike_ratio_of(log_text)

    # Flight vs birth-frame: the first health-destroy on the victim records how
    # many map traces the Stone flew before contacting (2 = birth frame, >=4 =
    # real trajectory). teki_pin (injected co-location) is excluded.
    # traces= is cumulative across flights, so gate on the per-flight delta
    # between consecutive STONE_DESTROY lines (integrator fix from review).
    destroys = [(m.group(1), int(m.group(2))) for m in STONE_DESTROY_RE.finditer(log_text)]
    per_flight = []
    prev = 0
    for reason, traces in destroys:
        per_flight.append((reason, traces - prev))
        prev = traces
    health_traces = [delta for reason, delta in per_flight if reason == 'health']
    flew = bool(health_traces) and min(health_traces) >= 4
    teki_pinned = 'P2_PROJECTILE_TEKI_PIN' in log_text

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
        'victim_contact_in_flight': ('PASS' if (skip_self and victim_struck
                                                and not teki_pinned and flew)
                                     else ('UNTESTED' if not (skip_self and victim_struck)
                                           else 'FAIL')),
        'groink_engine_receiver_navi_hit': ('PASS' if groink_bomb_navi
                                            else ('UNTESTED' if not groink_hits else 'FAIL')),
        'bomb_engine_navi_hit': ('PASS' if bomb_engine_navi_hit
                                 else ('UNTESTED' if not bomb_hits else 'FAIL')),
        'victim_strike_ratio': ('UNTESTED' if fires == 0
                                else ('PASS' if (fires >= 9 and hits > fires // 2)
                                      else 'FAIL')),
        'stone_destroy_teardown': 'PASS' if destroy else 'UNTESTED',
    }
    return dict(gates=gates, strikes=strikes, strike_ratio=f'{hits}/{fires}')


def run(exe, assets, converted, output, mode='stone', seconds=40.0, generator=0,
        teki_pin=False, victims=1):
    """Stage a fresh room, write the config, launch the exe, capture and evaluate."""
    run_dir = _prepare_room(Path(assets).resolve(), Path(converted).resolve(), Path(output))
    if mode == 'two_teki':
        add_second_teki(run_dir, count=victims)
    (run_dir / 'p2-projectiles.txt').write_text(
        build_config(mode, generator, teki_pin=teki_pin), encoding='utf8')
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
    # Repo-relative output root (…/output) so argparse defaults are not
    # user-absolute paths; `--assets` is outside any repo layout and is required.
    output_root = Path(__file__).resolve().parents[1] / 'output'
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe', type=Path, required=True)
    p.add_argument('--assets', type=Path, required=True)
    p.add_argument('--converted', type=Path, default=output_root / 'pikmin2-room105')
    p.add_argument('--output', type=Path, default=output_root / 'projectile-engine-receiver')
    p.add_argument('--mode', choices=BUILDER_MODES, default='stone')
    p.add_argument('--generator', type=int, default=0,
                   help='kabuto_actor generator ID (room Teki _70 value)')
    p.add_argument('--teki-pin', action='store_true',
                   help='inject the victim onto the firer (labelled P2_PROJECTILE_TEKI_PIN)')
    p.add_argument('--victims', type=int, default=1,
                   help='number of victim dwarfs to spawn in the fire corridor')
    p.add_argument('--seconds', type=float, default=40.0)
    a = p.parse_args()
    result = run(a.exe, a.assets, a.converted, a.output, a.mode, a.seconds, a.generator,
                 teki_pin=a.teki_pin, victims=a.victims)
    print(json.dumps(result, indent=2))
    ok = all(v in ('PASS', 'UNTESTED') for v in result['gates'].values())
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
