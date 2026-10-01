"""Build the preview no-cargo room-bolt reconciliation fixture against a private build (#679).

Thin wrapper over scripts/build_pikmin2_fixture.py: links
native/tools/p2_preview_nocargo_reconciliation_fixture.cpp against the private
pikmin_pc graph without editing shared build files, then runs the
engine-independent guard self-test and negative test.

Never rebuilds production. Private output must stay outside the native source
and the production build directory.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import build_pikmin2_fixture as base


FIXTURE_REL = Path('tools/p2_preview_nocargo_reconciliation_fixture.cpp')


def _ninja_rsp_map(build):
    """Map Ninja RSP_FILE paths to their link-edge content.

    The private build's link commands reference `@CMakeFiles/*.rsp`, and
    Ninja only materializes those files while running the edge. The content
    (`rspfile_content = $in $LINK_PATH $LINK_LIBRARIES`) is fully declared
    in build.ninja: the edge's explicit inputs plus its LINK_PATH /
    LINK_LIBRARIES bindings, in that order.
    """
    mapping = {}
    inputs, bindings = None, {}

    def flush():
        rsp = bindings.get('RSP_FILE')
        if rsp and inputs is not None:
            content = list(inputs)
            content.extend(bindings.get('LINK_PATH', '').split())
            content.extend(bindings.get('LINK_LIBRARIES', '').split())
            mapping[rsp.replace('\\', '/')] = content

    for raw in (Path(build) / 'build.ninja').read_text(encoding='utf-8').splitlines():
        if raw.startswith('build '):
            flush()
            left, _, right = raw[len('build '):].partition(':')
            tokens = right.split()
            ins = tokens[1:] if tokens else []
            cut = next((i for i, tok in enumerate(ins) if tok in ('|', '||')), len(ins))
            inputs, bindings = ins[:cut], {}
        elif raw[:1] not in (' ', '\t'):
            flush()
            inputs, bindings = None, {}
        elif inputs is not None:
            line = raw.strip()
            if re.fullmatch(r'[A-Z_]+ = .*', line):
                key, _, value = line.partition(' = ')
                bindings[key] = value.strip()
    flush()
    return mapping


def _expand_response_line(line, build, rsp_map):
    """Splice @response file content into a Ninja command line.

    Compatibility shim: this lane's base helper predates response-file
    support, and the private pikmin_pc link command exceeds the Windows
    argv limit (CMake emits `@<file>.rsp`). Prefer the on-disk file when
    present; otherwise fall back to the build.ninja edge declaration,
    mirroring the vendored-guard pattern (#632).
    """
    def replace(match):
        path = match.group(1) or match.group(2)
        resolved = base.absolute(path, build)
        if resolved.is_file():
            return resolved.read_text(encoding='utf-8', errors='replace').strip()
        key = path.replace('\\', '/')
        if key in rsp_map:
            return ' '.join(rsp_map[key])
        raise base.BuildRejected('Missing Ninja response file: ' + path)
    return re.sub(r'@"([^"]+)"|@([^\s"@]+\.rsp)', replace, line)


def _install_response_shim(output):
    """Teach the base helper to consume Ninja response files (no shared edits)."""
    orig_select = base.select_commands
    orig_run = base.run

    def select_commands(commands, source, build):
        # Expand only genuine compiler/link invocations; archive/custom
        # pipelines must pass through exactly as the base helper expects.
        rsp_map = None
        expanded = []
        for line in commands:
            if (' -c ' in line or ' -o ' in line) and '@' in line and '.rsp' in line:
                if rsp_map is None:
                    rsp_map = _ninja_rsp_map(build)
                line = _expand_response_line(line, build, rsp_map)
                if '@' in line and '.rsp' in line:
                    raise base.BuildRejected('Ninja response command is missing or unexpanded')
            expanded.append(line)
        return orig_select(expanded, source, build)

    def run(command, cwd, env=None):
        length = sum(len(str(arg)) + 1 for arg in command)
        if length <= 7000:
            return orig_run(command, cwd, env)
        # Spill long argv to a response file (GCC treats backslash as escape).
        response = (Path(output).resolve() / 'link.rsp')
        lines = ['"' + str(arg).replace('\\', '\\\\').replace('"', '\\"')
                 + '"' for arg in command[1:]]
        response.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return orig_run([command[0], '@' + str(response)], cwd, env)

    base.select_commands = select_commands
    base.run = run


def fixture_env(build):
    env = dict(os.environ)
    path = env.get('Path', env.get('PATH', ''))
    extra = os.pathsep.join((r'C:\msys64\mingw64\bin', str(Path(build) / 'bin')))
    env['Path'] = extra + os.pathsep + path if path else extra
    return env


def run_guard_checks(exe, build):
    exe = Path(exe)
    env = fixture_env(build)
    selftest = subprocess.run([str(exe), '--guard-self-test'], capture_output=True,
                              text=True, timeout=60, env=env)
    if selftest.returncode != 0 or 'P2_NOCARGO_RECONCILIATION_SELFTEST_PASS' not in selftest.stdout:
        raise SystemExit('guard self-test failed:\n' + selftest.stdout + selftest.stderr)
    negative = subprocess.run([str(exe), '--guard-negative-test'], capture_output=True,
                              text=True, timeout=60, env=env)
    if negative.returncode != 86 or 'P2_FIXTURE_CAPTAIN_DOWN' not in negative.stdout:
        raise SystemExit('guard negative test failed:\n' + negative.stdout + negative.stderr)
    if 'PASS' in negative.stdout.split('P2_FIXTURE_CAPTAIN_DOWN', 1)[0]:
        raise SystemExit('guard negative test emitted PASS before interruption')
    return {'selftest': selftest.stdout.strip().splitlines()[-1],
            'negative_exit': negative.returncode}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-native-head', required=True)
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--skip-guard-checks', action='store_true')
    args = parser.parse_args()
    fixture = (args.source / FIXTURE_REL)
    _install_response_shim(args.output)
    result = base.build_fixture(args.build, args.source, fixture, args.output,
                                args.expected_native_head, args.check_only)
    checks = {}
    if result.get('status') == 'built' and not args.check_only and not args.skip_guard_checks:
        checks = run_guard_checks(Path(args.output).resolve() / 'fixture.exe', args.build)
    print(json.dumps(dict(status=result['status'],
                          output=str(args.output.resolve()), **checks)))


if __name__ == '__main__':
    main()
