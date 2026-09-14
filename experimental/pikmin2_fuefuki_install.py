"""Opt-in Antenna Beetle (Fuefuki) lane profile installation into a private run.

Issue #245, arena/integration contract #186. Installs the lane-owned
squad-control/FSM/binding seam contract tokens as exact-byte configs into an
already private run directory. Every conflict or changed source is refused
BEFORE any mutation. The FUEFUKIANIM motion bank (item (f) of the lane's
binding slice) stays with the engine lane's converter/material work (#128):
this profile declares the seam contract only and ships no assets. Native
actor registration wiring rides on the lane's pc_p2_fuefuki_binding.h seam;
no shared/native edits here.
"""
import argparse
import hashlib
import json
from pathlib import Path

PROFILE_TXT = 'p2-fuefuki-profile.txt'
INSTALL_JSON = 'fuefuki-install.json'

ENEMY_ID = 41
STATE_COUNT = 9
ANIM_COUNT = 10
SEAM_VERSION = 'P2_FUEFUKI_SEAM_1'

# Lane seam tokens: the five lane-owned bindings implemented in
# native/pc_port/pc_p2_fuefuki_binding.h plus the #128-owned motion bank.
SEAM_BINDINGS = ('enumerate', 'follow', 'ping', 'reclaim', 'kill', 'probe')
EXTERNAL_DEPS = ('motion_bank:#128',)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def profile_text():
    """Canonical LF profile: audited squad-control seam contract tokens."""
    rows = [SEAM_VERSION]
    rows.append(f'enemy fuefuki {ENEMY_ID} states {STATE_COUNT} anims {ANIM_COUNT}')
    rows.append('cadence fixed_hz 30 cast_seconds 3.0 ring_grow_seconds 1.0 '
                'escape_speed 1500 walk_cap_seconds 5.0 squad_window_ticks 5')
    rows.append('cadence_parms fp11 min_whistle fp12 no_squad fp13 with_squad '
                'fp01 ground_time fp03 airborne fp21 struggle fp22 jump fp31 landing_chance')
    for name in SEAM_BINDINGS:
        rows.append(f'binding {name} lane_owned')
    rows.append('ownership single_controller exclusive_table epoch_invalidated')
    rows.append('reclaim panic_only single_write captain_switch_not_routed '
                'party_combine_not_routed')
    rows.append('release death_panic_before_callbacks suspend_success_emote')
    rows.append('carcass carry_anim')
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
