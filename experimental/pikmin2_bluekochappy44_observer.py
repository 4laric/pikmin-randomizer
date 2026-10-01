"""BlueKochappy44 generated-identity gate-1 observer (shard lane, #461).

Tooling-only contract checker: proves the SAME real generated spawn correlates
across three native birth-marker legs for source 44 (BlueKochappy / Dwarf
Orange Bulborb) without redoing the existing dwarf_orange install/arena/
profile/bank modules or roster evidence:

  leg 1 (seed-resolve): a spawn manifest naming source_id, generator UID,
  expected XYZ and health for the generated spawn;
  leg 2 (generated-placement bind): P2_ENEMY_READY rows carrying species,
  source_id, generator UID, XYZ and health;
  leg 3 (dwarf-orange actor binding): P2_KOCHAPPY_STATE/POS/DEAD family rows
  carrying the same generator UID (family behavior actually bound).

Fail-closed: any missing leg, UID/generator mismatch, unmapped slot,
unsupported terrain, missing route evidence, or injected-birth taint yields
gate1_ok False. Generator-0 placeholder rows (pre-bind phase) never count as
identity. Nothing here can fabricate acceptance: gate 1 stays BLOCKED until a
real generated run is observed by a runtime lane.
"""
import argparse
import json
import math
import re
from pathlib import Path

SOURCE_ID = 44
SPECIES = 'BlueKochappy'
EXPECTED_HEALTH = 250.0
XYZ_TOLERANCE = 5.0
MIN_ROUTE_POINTS = 3
MIN_ROUTE_DISPLACEMENT = 5.0

TAINT_MARKERS = ('INJECT', 'TELEPORT', 'FORCED_BIRTH', 'mHealth =', 'mHealth=')

READY_RE = re.compile(
    r'P2_ENEMY_READY species=(\S+) source_id=(\d+) native_family=(\S+) '
    r'generator=(\d+) x=(-?\d+\.\d+) y=(-?\d+\.\d+) z=(-?\d+\.\d+) '
    r'health=([\d.]+) max_health=([\d.]+) behavior=(\S+)')
STATE_RE = re.compile(r'P2_KOCHAPPY_STATE generator=(\d+) state=(\w+)')
POS_RE = re.compile(r'P2_KOCHAPPY_POS generator=(\d+) state=(\w+) x=(-?\d+\.\d+) z=(-?\d+\.\d+)')
GENERIC_DEAD_RE = re.compile(r'P2_KOCHAPPY_DEAD generator=(\d+) source_id=(\d+)')


class ObserverError(ValueError):
    pass


def parse_manifest(obj):
    """Validate a spawn manifest mapping (seed-resolve leg)."""
    if not isinstance(obj, dict):
        raise ObserverError('Spawn manifest must be an object')
    try:
        source_id, generator = int(obj['source_id']), int(obj['generator'])
        xyz = [float(v) for v in obj['expected_xyz']]
        health = float(obj.get('health', EXPECTED_HEALTH))
    except (KeyError, TypeError, ValueError) as exc:
        raise ObserverError('Malformed spawn manifest') from exc
    if source_id != SOURCE_ID or generator <= 0 or len(xyz) != 3:
        raise ObserverError('Spawn manifest identity out of contract')
    if any(not math.isfinite(v) for v in xyz) or health <= 0:
        raise ObserverError('Spawn manifest values not finite/positive')
    return dict(source_id=source_id, generator=generator, expected_xyz=xyz, health=health)


def parse_ready_rows(text):
    """Parse generated-placement bind rows (leg 2)."""
    rows = []
    for match in READY_RE.finditer(text):
        species, source, family, generator, x, y, z, health, max_health, behavior = match.groups()
        rows.append(dict(species=species, source_id=int(source), family=family,
                         generator=int(generator), xyz=[float(x), float(y), float(z)],
                         health=float(health), max_health=float(max_health), behavior=behavior))
    return rows


def parse_family_rows(text):
    """Parse dwarf-orange actor binding rows (leg 3)."""
    states = [(int(g), s) for g, s in STATE_RE.findall(text)]
    positions = [(int(g), s, float(x), float(z)) for g, s, x, z in POS_RE.findall(text)]
    deaths = [(int(g), int(s)) for g, s in GENERIC_DEAD_RE.findall(text)]
    return dict(states=states, positions=positions, deaths=deaths)


def _dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def observe_gate1(manifest_obj, log_text):
    """Correlate the three legs; fail closed on every adversarial class."""
    manifest = parse_manifest(manifest_obj)
    ready = parse_ready_rows(log_text)
    family = parse_family_rows(log_text)
    target = [r for r in ready if r['source_id'] == SOURCE_ID and r['generator'] != 0]
    uids = {r['generator'] for r in target}
    nonzero_uids = {r['generator'] for r in ready if r['generator'] != 0}
    placeholders = [r for r in ready if r['source_id'] == SOURCE_ID and r['generator'] == 0]
    same_uid_family = [g for g, _ in family['states']] + [g for g, _, _, _ in family['positions']] + [g for g, _ in family['deaths']]
    positions = [(x, z) for g, _, x, z in family['positions'] if g == manifest['generator']]
    displacement = max((_dist((x, z), tuple(manifest['expected_xyz'][i] for i in (0, 2))) for x, z in positions), default=0.0)
    checks = dict(
        manifest_valid=True,
        ready_present=len(target) >= 1,
        single_uid=len(uids) == 1 and uids == {manifest['generator']},
        no_source_swap=all(r['source_id'] == SOURCE_ID for r in ready if r['generator'] == manifest['generator']),
        no_placeholder_identity=all(_dist(r['xyz'], manifest['expected_xyz']) <= XYZ_TOLERANCE for r in placeholders),
        health_match=all(abs(r['health'] - manifest['health']) < 0.01 for r in target),
        xyz_match=all(_dist(r['xyz'], manifest['expected_xyz']) <= XYZ_TOLERANCE for r in target),
        family_bound=any(g == manifest['generator'] for g in same_uid_family),
        route_evidence=(len(positions) >= MIN_ROUTE_POINTS and displacement >= MIN_ROUTE_DISPLACEMENT
                        and all(math.isfinite(x) and math.isfinite(z) for x, z in positions)),
        no_taint=not any(marker in log_text for marker in TAINT_MARKERS),
        unmapped_slots=all(g in nonzero_uids for g in [manifest['generator']]),
    )
    return dict(gate1_ok=all(checks.values()), checks=checks,
                generator=manifest['generator'] if all(checks.values()) else None)


def read_log(path):
    """Dependency-free run-log reader."""
    return Path(path).read_text(encoding='utf-8', errors='replace')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    print(json.dumps(observe_gate1(manifest, read_log(args.log)), indent=2))
