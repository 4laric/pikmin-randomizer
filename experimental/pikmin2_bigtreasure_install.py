"""Opt-in BigTreasure (Titan Dweevil) lane profile installation into a private run.

Issue #246, arena/integration contract #186. Installs the lane-owned host
seam contract tokens as exact-byte configs into an already private run
directory. Every conflict or changed source is refused BEFORE any mutation.
Model/motion conversion stays with the engine lane's converter/material
work (#128): this profile declares the seam contract only and ships no
assets. Registration wiring rides on the lane's native seam
(pc_p2_bigtreasure_host.h); no shared/native edits here.
"""
import argparse
import hashlib
import json
from pathlib import Path

PROFILE_TXT = 'p2-bigtreasure-profile.txt'
INSTALL_JSON = 'bigtreasure-install.json'

ENEMY_ID = 73
STATE_COUNT = 12
CAPTURED_PELLETS = 5  # elec/fire/gas/water weapon pellets + Louie
SEAM_VERSION = 'P2_BIGTREASURE_SEAM_1'

# Lane seam tokens: the lane-owned bindings implemented in
# native/pc_port/pc_p2_bigtreasure_host.h and pc_p2_bigtreasure_map_trace.h.
SEAM_BINDINGS = ('map_trace', 'ground_query', 'host_profile', 'tick_entry',
                 'defeat_teardown', 'probe')
EXTERNAL_DEPS = ('models_motions:#128', 'pellet_configs:disc_data',
                 'mpellet_drop_code:disc_data')

# Disc-verified pellet configurations (#128 extraction,
# docs/PIKMIN2_ENGINE_DISC_PARMS.md): carry min/max, poko value, treasure
# dictionary ID, collision radius/height. loozy money 10 is verbatim.
# mPelletDropCode is null in story mode: the finale treasure is the loozy
# pellet itself (releaseItemLoozy, dead.bca KEYEVENT_100 frame 320).
PELLET_CONFIGS = {
    'elec':  {'carry_min': 30, 'carry_max': 40, 'pokos': 1000, 'dictionary': 197, 'radius': 35, 'height': 50},
    'fire':  {'carry_min': 30, 'carry_max': 40, 'pokos': 1000, 'dictionary': 198, 'radius': 35, 'height': 52},
    'gas':   {'carry_min': 30, 'carry_max': 40, 'pokos': 1000, 'dictionary': 199, 'radius': 37, 'height': 20},
    'water': {'carry_min': 30, 'carry_max': 40, 'pokos': 1000, 'dictionary': 200, 'radius': 35, 'height': 51},
    'loozy': {'carry_min': 1,  'carry_max': 5,  'pokos': 10,   'dictionary': 201, 'radius': 12, 'height': 10},
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def profile_text():
    """Canonical LF profile: audited BigTreasure host seam contract tokens."""
    rows = [SEAM_VERSION]
    rows.append(f'enemy bigtreasure {ENEMY_ID} states {STATE_COUNT} '
                f'captured_pellets {CAPTURED_PELLETS}')
    rows.append('placement fixed_first staged_phases_gate no_locomotion '
                'no_spawn_table_registration')
    rows.append('pools fire 8 gas 200 water 16 elec 17 elec_invariant '
                'anchor_plus_discharge_le_17')
    rows.append('pacing base_seconds 4 per_live_weapon_seconds 2 pinch_hp 3000 '
                'weapon_hp 6000 body_damage_zero_weapons_only')
    rows.append('teardown pools_first water_bubbles_force_recycled '
                'weapon_pop_y_100 louie_pop_y_150')
    for name in ('elec', 'fire', 'gas', 'water', 'loozy'):
        cfg = PELLET_CONFIGS[name]
        rows.append(f'pellet {name} carry {cfg["carry_min"]} {cfg["carry_max"]} '
                    f'pokos {cfg["pokos"]} dict {cfg["dictionary"]} '
                    f'radius {cfg["radius"]} height {cfg["height"]}')
    rows.append('finale mpellet_drop_code_null_story loozy_pellet_via_releaseItemLoozy '
                'dead_bca_keyevent_100_frame_320')
    for name in SEAM_BINDINGS:
        rows.append(f'binding {name} lane_owned')
    for dep in EXTERNAL_DEPS:
        rows.append(f'external {dep}')
    return '\n'.join(rows) + '\n'


def install(run_dir):
    run = Path(run_dir)
    if not run.is_dir():
        raise SystemExit(f'private run directory missing: {run}')
    data = profile_text().encode('utf-8')
    digest = sha(data)
    target = run / PROFILE_TXT
    receipt = run / INSTALL_JSON
    # Refuse any conflict BEFORE mutation.
    if target.exists() and sha(target.read_bytes()) != digest:
        raise SystemExit(f'refusing to overwrite changed profile: {target}')
    if receipt.exists():
        prior = json.loads(receipt.read_text(encoding='utf-8'))
        if prior.get('profile_sha256') != digest:
            raise SystemExit(f'refusing to overwrite changed install receipt: {receipt}')
        return {'status': 'already-installed', 'profile_sha256': digest}
    target.write_bytes(data)
    payload = {'status': 'installed', 'seam': SEAM_VERSION, 'enemy_id': ENEMY_ID,
               'profile_sha256': digest, 'bindings': list(SEAM_BINDINGS),
               'pellet_configs': PELLET_CONFIGS,
               'external_dependencies': list(EXTERNAL_DEPS)}
    receipt.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True,
                        help='existing private run directory to install into')
    args = parser.parse_args()
    payload = install(args.run_dir)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
