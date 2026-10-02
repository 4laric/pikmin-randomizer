"""Stage and supervise ordinary native title UI initialization of a new blank card."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from blank_card_preflight import MARKER, completion, digest, inventory, preflight_new, require
from preview_pikmin2_room import overlay
from fixture_platform import runtime_dependencies, is_windows
import run_pikmin2_fixture as guarded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--canonical-root', required=True, type=Path)
    parser.add_argument('--session-root', required=True, type=Path)
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--exe', required=True, type=Path)
    parser.add_argument('--runtime-dir', type=Path)
    parser.add_argument('--timeout', type=int, choices=[60], default=60)
    parser.add_argument('--development-launch', action='store_true', help='Use the explicit private development launcher')
    args = parser.parse_args()
    canonical = args.canonical_root.resolve(strict=True)
    require(canonical == ROOT.resolve(), 'Runner must use its own pinned root checkout')
    session, card = preflight_new(args.canonical_root, args.session_root)
    exe = args.exe.resolve(strict=True)
    assets = args.assets.resolve(strict=True)
    runtime_dir = runtime_dependencies(exe, args.runtime_dir)[0] if is_windows() else None
    # Native title/UI must not inherit a campaign/BBFT shortcut or somebody else's settings/card.
    removed = []
    for key in list(os.environ):
        if key.upper().startswith(('PIKMIN_', 'P2_', 'COOP_', 'NECTAR_', 'BBFT_')):
            removed.append(key)
            del os.environ[key]
    session.mkdir(parents=True)
    run = session / 'blank-card-run'
    run.mkdir()
    config = run / 'private-config'
    config.mkdir()
    os.environ.update(NECTAR_SAVE_DIR=str(card), PIKMIN_SETTINGS_PATH=str(config / 'settings.json'),
                      XDG_CONFIG_HOME=str(config), XDG_DATA_HOME=str(config), APPDATA=str(config), LOCALAPPDATA=str(config),
                      SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS='1', PIKMIN_P2_ROOM_WINDOW='960x540', PIKMIN_SHADER_CACHE='0')
    overlay(assets, run / 'assets', {})
    argv = [str(exe), '--blank-card-root', str(card)]
    inputs = dict(session_absent_at_preflight=True, card_root=str(card), argv=argv,
                  native_ui=True, randomizer_enabled=False, saved_bytes_injected=False,
                  timeout_seconds=60, removed_environment_names=sorted(removed),
                  effective_private_environment={key: os.environ[key] for key in
                      ('NECTAR_SAVE_DIR', 'PIKMIN_SETTINGS_PATH', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'APPDATA', 'LOCALAPPDATA', 'PIKMIN_SHADER_CACHE')})
    (run / 'blank-card-inputs.json').write_text(json.dumps(inputs, indent=2) + '\n', encoding='utf-8')
    result = guarded.launch(exe, run, argv[1:], [MARKER], 60, toolchain=runtime_dir,
                            canonical_root=canonical, session_root=session, development_launch=args.development_launch)
    # launch returns only after its owned child/group cleanup. No retry in this session.
    require(result.get('launched', True), 'Blank-card launch refused; preserve failed session')
    log = (run / 'native.log').read_text(errors='replace')
    completion(result, log)
    actual = inventory(canonical, session)
    evidence = {name: digest(run / name) for name in
                ('native.log', 'run-result.json', 'run-inputs.json', 'blank-card-inputs.json')}
    receipt = dict(schema='native-blank-card-v1', accepted=True, session=str(session), run=str(run),
                   card_root=str(card), exe=str(exe), exe_sha256=digest(exe), evidence=evidence,
                   inventory=actual, campaign_generations=0, native_ui=True,
                   gameplay_accepted=False, save_time_fit_proven=False)
    # Exclusive creation prevents relabeling an earlier attempt.
    with (session / 'blank-card-verified.json').open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
