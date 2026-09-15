"""Lane-local (#242) real-GL runner for the dedicated captor spawn identity.

Stages two fresh private arenas from the converted room bank:

* a **dedicated** arena whose single enemy generator is post-processed to carry
  ``TEKI_P2Demon`` (type 35) via ``p2_demon_identity_arena.py``, and
* a **legacy** arena left exactly as the stock room stager writes it
  (``TEKI_Chappy`` type 3).

The known-good Demon pose/event/mod assets and the freshly built fixture are
overlaid, then the fixture modes run with ``PIKMIN_P2_ROOM_WINDOW=960x540``. The
dedicated arena proves the ordinary opt-in path selects the dedicated identity
``dedicated=1`` with no explicit generator/type; the legacy arena keeps the
placeholder and all existing regression modes reproducible.
"""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p2_demon_identity_arena as identity  # noqa: E402

ROOT = Path(r'C:\Users\alari\pikmin-randomizer')

DEDICATED_MODES = [
    ('ordinary_dedicated', 'ordinary_dedicated', {}),
]
LEGACY_MODES = [
    ('ordinary_legacy', 'ordinary_legacy', {}),
    ('ordinary', 'ordinary', {}),
    ('natural', 'natural', {}),
    ('natural_idle', 'natural_idle', {}),
    ('drop', 'drop', {}),
    ('livecapture', 'livecapture', {}),
    ('teardown', 'teardown', {}),
]


def load_preview(root):
    spec = importlib.util.spec_from_file_location('preview', root / 'scripts/preview_pikmin2_room.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stage_arena(preview, assets, converted, outdir, ref, fixture, dedicated):
    outdir.mkdir(parents=True, exist_ok=True)
    session = preview.prepare(assets.resolve(), converted.resolve(), outdir.resolve())
    for path in ref.glob('demon*.txt'):
        shutil.copy2(path, session / path.name)
    src_course = ref / 'assets/dataDir/courses/pikmin2room'
    dst_course = session / 'assets/dataDir/courses/pikmin2room'
    for name in ('demon0.mod', 'demon17.mod'):
        shutil.copy2(src_course / name, dst_course / name)
    for pattern in ('attack1_*.mod', 'waitact*.mod'):
        for path in src_course.glob(pattern):
            shutil.copy2(path, dst_course / path.name)
    if dedicated:
        gen, old_type, new_type = identity.patch_session(session)
        print('ARENA dedicated session=%s gen=%s old_type=%d new_type=%d' % (session, gen, old_type, new_type), flush=True)
    else:
        print('ARENA legacy session=%s gen=unpatched' % session, flush=True)
    shutil.copy2(fixture, session / 'fixture.exe')
    return session


def run_modes(session, modes):
    results = {}
    env_base = dict(os.environ)
    env_base['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env_base['SDL_AUDIODRIVER'] = 'dummy'
    env_base['PATH'] = r'C:\msys64\mingw64\bin' + os.pathsep + env_base.get('PATH', '')
    exe = session / 'fixture.exe'
    for label, mode, extra in modes:
        env = dict(env_base)
        for key in ('PIKMIN_DEMON_ORDINARY', 'PIKMIN_DEMON_ORDINARY_GENERATOR',
                    'PIKMIN_DEMON_ORDINARY_TYPE', 'PIKMIN_DEMON_ORDINARY_LEGACY_PLACEHOLDER'):
            env.pop(key, None)
        env['DEMON_HOST_MODE'] = mode
        env.update(extra)
        try:
            run = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=session, env=env,
                                 capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
            rc, out, err = run.returncode, run.stdout, run.stderr
        except subprocess.TimeoutExpired as exc:
            rc = 124
            out = exc.stdout.decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
            err = exc.stderr.decode('utf-8', 'replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
        (session / (label + '.out')).write_text(out, encoding='utf-8')
        (session / (label + '.err')).write_text(err, encoding='utf-8')
        passed = rc == 0 and 'PASS DEMON_HOST' in out and 'FAIL DEMON_HOST' not in out
        failed = 'FAIL DEMON_HOST' in out
        marker = next((line.strip() for line in out.splitlines()
                       if 'PASS DEMON_HOST' in line or 'FAIL DEMON_HOST' in line), '')
        identity_line = next((line.strip() for line in out.splitlines()
                              if 'DEMON_ORDINARY_IDENTITY' in line), '')
        bind_line = next((line.strip() for line in out.splitlines()
                          if 'DEMON_ORDINARY_BIND' in line), '')
        window = next((line.strip() for line in out.splitlines()
                       if 'P2_DEMON_HOST_WINDOW' in line), '')
        results[label] = dict(rc=rc, passed=passed, failed=failed, marker=marker,
                              identity=identity_line, bind=bind_line, window=window)
        print('RESULT %-24s rc=%s passed=%s failed=%s %s' % (label, rc, passed, failed, marker), flush=True)
        print('       %s' % window, flush=True)
        print('       %s' % identity_line, flush=True)
        print('       %s' % bind_line, flush=True)
    return results


def print_summary(results):
    print('SUMMARY', flush=True)
    for label, result in results.items():
        print('  %-24s rc=%-4s pass=%-5s %s' % (label, result['rc'], result['passed'], result['marker']), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=Path(r'C:\Users\alari\pikmin-local\game\assets'))
    parser.add_argument('--converted', type=Path, default=ROOT / 'output/pikmin2-room105')
    parser.add_argument('--ref', type=Path,
                        default=ROOT / 'output/demon-adopt-run-02/b2c84a2164a04445950f4719d9574f48')
    parser.add_argument('--root', type=Path, required=True, help='Reviewed randomizer root containing the current room stager')
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()

    preview = load_preview(args.root.resolve())
    dedicated = stage_arena(preview, args.assets, args.converted, args.outdir / 'dedicated',
                            args.ref, args.fixture, dedicated=True)
    legacy = stage_arena(preview, args.assets, args.converted, args.outdir / 'legacy',
                         args.ref, args.fixture, dedicated=False)

    results = {}
    results.update(run_modes(dedicated, DEDICATED_MODES))
    results.update(run_modes(legacy, LEGACY_MODES))
    print_summary(results)

    dedicated_ok = (results.get('ordinary_dedicated', {}).get('passed')
                    and 'dedicated=1' in results.get('ordinary_dedicated', {}).get('identity', ''))
    legacy_ok = ('legacy=1' in results.get('ordinary_legacy', {}).get('identity', ''))
    print('DEDICATED_RUN dedicated=1 pass=%s' % bool(dedicated_ok), flush=True)
    print('LEGACY_RUN legacy=1 pass=%s' % bool(legacy_ok), flush=True)
    if not (dedicated_ok and legacy_ok and all(r['passed'] for r in results.values())):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
