"""Lane 05 slice 5: the generated seed resolves on the wave native, end to end.

Generates a real ``randomizer.seed.generate`` seed on the REAL lane-04 placement
catalog (restricted to the arena's stage-0 ground slots, cohort acceptance
stamped), stages its content through the REAL runner entry point
(``runner.launch`` -> ``install_layout``) into the preview-generator room, and
boots ``nectar.exe --experimental-pikmin2-room --randomizer-seed <bootstrap>`` so
the wave native resolves the seed's chosen slot natively: lane-04
``P2_PLACEMENT_SLOT`` (reads the staged ``p2-placement-slots.txt`` sidecar), lane-03
``P2_SEED_RESOLVE source_id=<n>`` (``GenObjectTeki::birth``) and the family
``P2_ENEMY_READY`` for the SAME generator, plus the Snow run's ``P2_SNOW_BANK``
with the Pod present.

The admission cohort is injected the same way lane 03/04 seed tests do
(``experimental.pikmin2_seed_bridge.admitted_ids`` is patched for the duration of
``generate`` and ``runner.launch``, because the committed roster denies by
default). The Pod (``p2-pod.txt``/``pod.mod``) is a preview/reward anchor, not
enemy family content: staged here so ``pc_p2_enemy.cpp:161`` does not gate
preview-mode Snow; ownership is lane 13.

    py -3.12 slot.py run gl <lane> -- py -3.12 scripts/run_p2_generated_seed.py stage \
        --assets <P1> --converted <c> --bank <bank> --profile <ref> --snow <cohort-run> \
        --pod <cohort-run> --out <dir> --seed seed-slice5 --cohort 44
    py -3.12 slot.py run gl <lane> -- py -3.12 scripts/run_p2_generated_seed.py run \
        --exe <nectar.exe> --out <dir>
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.probe_p2_cohort_native import (  # noqa: E402
    GENERATOR_FOR_SOURCE, POD_CONFIG, build_content, build_retail,
    write_placement_sidecar)
from experimental.pikmin2_seed_evidence import (  # noqa: E402
    cohort_markers, find_mingw, ready_species, resolve_markers)

ENUM_FOR_SOURCE = {44: 'BlueKochappy', 45: 'YellowKochappy'}
READY_TOKEN = {44: 'BlueKochappy', 45: 'YellowKochappy'}


def placement_document(cohort):
    """The REAL lane-04 catalog restricted to one arena slot, cohort accepted (stamped).

    The arena holds one generator per identity, so the seed is bound to a single
    real catalog slot (the first stage-0 ground slot uid) — the seed's chosen slot.
    The catalog ships deny-by-default, so the slot's ``xyz``/``terrain``/``route``
    evidence is set True and the cohort profiles are given ``accepted_gates=['arena']``.
    This is labelled INJECTED admission shaping for the bridge, not a claim the
    native run accepted the cohort.
    """
    from randomizer import p2_placement_catalog as catalog
    from randomizer.p2_placement import validate_document
    doc = json.loads(json.dumps(catalog.build_document()))
    ground = [slot for slot in doc['slots']
              if slot['stage'] == 0 and slot['terrain'] == 'ground']
    if not ground:
        raise ValueError('no stage-0 ground slot in the placement catalog')
    arena_slot = dict(min(ground, key=lambda slot: slot['uid']))
    arena_slot.setdefault('evidence', {})
    for key in ('xyz', 'terrain', 'route'):
        arena_slot['evidence'][key] = True
    doc['slots'] = [arena_slot]
    cohort_enums = {ENUM_FOR_SOURCE[source_id] for source_id in cohort}
    for profile in doc['profiles']:
        if profile['identity'] in cohort_enums:
            profile['accepted_gates'] = ['arena']
    return validate_document(doc)


def stage(args):
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cohort = tuple(sorted(set(args.cohort) or [44]))
    build_retail(args.assets, args.converted, args.pod, out / 'retail', cohort)
    build_content(args.bank, args.profile, args.snow, out / 'content', cohort)

    import experimental.pikmin2_seed_bridge as bridge
    from randomizer import runner
    from randomizer.seed import generate as _generate

    async def noop(*_a, **_k):
        pass

    saved_admitted = bridge.admitted_ids
    saved_serve = runner.serve
    bridge.admitted_ids = lambda roster: list(cohort)
    runner.serve = noop
    try:
        manifest = _generate(args.seed, p2_enemies=True, p2_placement=placement_document(cohort))
        bindings = manifest['p2_layout']['bindings']
        assert {b['source_id'] for b in bindings} == set(cohort), bindings
        actors = {b['target']: GENERATOR_FOR_SOURCE[b['source_id']] for b in bindings}
        runner.launch(manifest, out / 'session', assets=out / 'retail',
                      p2_content=out / 'content', p2_actors=actors)
    finally:
        bridge.admitted_ids = saved_admitted
        runner.serve = saved_serve

    run_dirs = list((out / 'session' / 'runs').iterdir())
    assert len(run_dirs) == 1, run_dirs
    run_dir = run_dirs[0]

    slots = {}
    for b in bindings:
        slots.setdefault(b['source_id'], []).append(int(b['target']))
    sidecar = [(GENERATOR_FOR_SOURCE[sid], sorted(uids)[0]) for sid, uids in slots.items() if uids]
    write_placement_sidecar(run_dir, sidecar)
    if 45 in cohort:
        (run_dir / POD_CONFIG).write_text((Path(args.pod).resolve() / POD_CONFIG).read_text())
    (run_dir / 'preview.json').write_text(json.dumps(
        dict(room='room_4x4a_4_conc', experimental=True, ap=False, save_resume=False), indent=2))
    (out / 'stage.json').write_text(json.dumps(dict(
        run=str(run_dir), cohort=list(cohort), seed=args.seed,
        bindings=manifest['p2_layout']['bindings'],
        generator_slots=[[int(g), int(s)] for g, s in sidecar],
        command=['nectar.exe', '--experimental-pikmin2-room']), indent=2))
    (out / 'seed-manifest.json').write_text(json.dumps(manifest, indent=2))
    return dict(run=str(run_dir), bindings=manifest['p2_layout']['bindings'],
                cohort=list(cohort), slots={str(k): sorted(v) for k, v in slots.items()})


def boot_native(stage_dir, exe, out, seconds):
    stage_dir = Path(stage_dir).resolve()
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    env['SDL_AUDIODRIVER'] = 'dummy'
    mingw = find_mingw()
    if mingw:
        env['PATH'] = mingw + os.pathsep + env.get('PATH', '')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    kw = dict(cwd=stage_dir, env=env)
    if os.name == 'nt':
        kw['startupinfo'] = startup
    log_path = out / 'native.log'
    timed_out = False
    bootstrap = Path(stage_dir) / 'bootstrap.txt'
    cmd = [str(Path(exe).resolve()), '--experimental-pikmin2-room',
           '--randomizer-seed', str(bootstrap.resolve())]
    with log_path.open('w', encoding='utf-8') as lg:
        proc = subprocess.Popen(cmd, stdout=lg, stderr=subprocess.STDOUT, **kw)
        try:
            proc.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
    return log_path.read_text(encoding='utf-8', errors='replace'), timed_out, proc.returncode


def run(args):
    out = Path(args.out).resolve()
    stage_json = json.loads((out / 'stage.json').read_text(encoding='utf-8'))
    cohort = stage_json['cohort']
    text, timed_out, returncode = boot_native(stage_json['run'], args.exe, out, args.seconds)

    checks = cohort_markers(text)
    # Per-identity bank/READY checks are recomputed from the staged cohort; the
    # fixed bank/ready keys cohort_markers pre-filled are popped rather than
    # duplicated (a source outside the cohort must emit NEITHER its bank NOR its
    # READY line).
    for key in ('dwarf_bank', 'dwarf_ready', 'snow_bank', 'snow_ready'):
        checks.pop(key, None)
    for source_id, token in READY_TOKEN.items():
        bank_line = ('P2_DWARF_ORANGE_BANK poses=' if source_id == 44
                     else 'P2_SNOW_BANK poses=') in text
        ready_line = f'P2_ENEMY_READY species={token}' in text
        if source_id in cohort:
            checks[f'ready_{token}'] = ready_line
            checks[f'bank_{token}'] = bank_line
        else:
            checks[f'no_ready_{token}'] = not ready_line
            checks[f'no_bank_{token}'] = not bank_line
    checks['only_seed_identity'] = set(ready_species(text)) == {READY_TOKEN[s] for s in cohort}
    # Wave-native resolution: lane-03 seed bridge + lane-04 placement reader agree.
    checks.update(resolve_markers(text, cohort, GENERATOR_FOR_SOURCE))

    passed = (timed_out or returncode == 0) and all(checks.values())
    result = dict(passed=passed, timed_out=timed_out, exit_code=returncode,
                  cohort=cohort, checks=checks, observed_species=ready_species(text),
                  bindings=stage_json['bindings'], generator_slots=stage_json['generator_slots'])
    (out / 'evidence.json').write_text(json.dumps(result, indent=2))
    for keep in (Path(stage_json['run']) / 'p2-binding-receipt.json', out / 'stage.json'):
        if keep.is_file() and not (out / keep.name).exists():
            shutil.copyfile(keep, out / keep.name)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    s = sub.add_parser('stage')
    for name in ('assets', 'converted', 'bank', 'profile', 'snow', 'pod', 'out'):
        s.add_argument('--' + name, type=Path, required=True)
    s.add_argument('--seed', type=str, default='seed-slice4')
    s.add_argument('--cohort', type=int, action='append', default=[])
    r = sub.add_parser('run')
    for name in ('exe', 'out'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--seconds', type=float, default=45)
    a = parser.parse_args()
    if a.command == 'stage':
        print(json.dumps(stage(a), indent=2))
    else:
        print(json.dumps(run(a), indent=2))


if __name__ == '__main__':
    main()
