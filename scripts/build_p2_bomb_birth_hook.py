"""Private leased build/run helper for the Bomb birth-hook fixture (#677)."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(args, cwd, env=None):
    completed = subprocess.run(
        args, cwd=str(cwd), env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding='utf-8',
        errors='replace', timeout=600)
    return completed.returncode, completed.stdout


def build_fixture(native, output, compiler='g++'):
    """Compile the guarded hook fixture standalone (engine-free)."""
    native, output = Path(native), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    exe = output / 'p2_bomb_mgr_birth_hook_fixture.exe'
    # The provider detonate path routes through the real bombsarai blast
    # TU (same as the #616 standalone test); linked read-only, not owned.
    cmd = [compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
           '-I' + str(native / 'pc_port'),
           '-DP2_BOMB_MGR_BIRTH_NO_HOST',
           str(native / 'tools/p2_bomb_mgr_birth_hook_fixture.cpp'),
           str(native / 'pc_port/pc_p2_bombsarai_blast.cpp'),
           '-o', str(exe)]
    code, text = run(cmd, native)
    (output / 'compile.log').write_text(text, encoding='utf-8')
    if code:
        raise SystemExit('Fixture compile failed; see compile.log')
    code, text = run([str(exe)], native)
    (output / 'fixture.log').write_text(text, encoding='utf-8')
    if code or 'ALL_FIXTURE_PASS' not in text:
        raise SystemExit('Fixture run failed; see fixture.log')
    return {'executable': str(exe), 'executable_sha256': sha256(exe)}


def guard_hash():
    """Hash the canonical captain-guard header (read-only reference)."""
    candidates = [
        Path('C:/Users/alari/pikmin-randomizer/output/workflow/autofill/'
             'planning-shards/enemies-5/prepared/dangomushi94-observer/'
             'scripts/p2_fixture_captain_guard.h'),
    ]
    for path in candidates:
        if path.is_file():
            return {'guard': str(path), 'guard_sha256': sha256(path)}
    return {'guard': None, 'guard_sha256': None}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler', default='g++')
    args = parser.parse_args(argv)
    record = build_fixture(args.native, args.output, args.compiler)
    record.update(guard_hash())
    record['native_head'] = subprocess.run(
        ['git', '-C', str(args.native), 'rev-parse', 'HEAD'],
        capture_output=True, text=True).stdout.strip()
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
