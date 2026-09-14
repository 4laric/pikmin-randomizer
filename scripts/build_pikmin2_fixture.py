"""Build an isolated Windows MinGW fixture from a completed CMake/Ninja build.

Never rebuilds production. Ninja freshness is an observation, not historical
certification that the reused objects were built from the current Git commit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


class BuildRejected(ValueError):
    pass


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def snapshot(paths):
    result = {}
    for path in sorted(set(p.resolve() for p in paths), key=str):
        if not path.is_file():
            raise BuildRejected('Missing input: ' + str(path))
        before = path.stat()
        value = sha256(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise BuildRejected('Input changed while hashing: ' + str(path))
        result[str(path)] = dict(sha256=value, size=after.st_size, mtime_ns=after.st_mtime_ns)
    return result


def check_snapshot(expected):
    actual = snapshot(map(Path, expected))
    changed = [path for path in expected if expected[path] != actual[path]]
    if changed:
        raise BuildRejected('Inputs changed during fixture build: ' + ', '.join(changed[:5]))


def windows_args(command):
    """Split the Windows compiler argv grammar without destroying backslashes."""
    args, at = [], 0
    while at < len(command):
        while at < len(command) and command[at] in ' \t':
            at += 1
        if at == len(command):
            break
        value, quoted = [], False
        while at < len(command) and (quoted or command[at] not in ' \t'):
            if command[at] == '\\':
                end = at
                while end < len(command) and command[end] == '\\':
                    end += 1
                number = end - at
                if end < len(command) and command[end] == '"':
                    value.extend('\\' * (number // 2))
                    at = end
                    if number % 2:
                        value.append('"')
                        at += 1
                        continue
                else:
                    value.extend('\\' * number)
                    at = end
                    continue
            if command[at] == '"':
                if quoted and at + 1 < len(command) and command[at + 1] == '"':
                    value.append('"')
                    at += 2
                    continue
                quoted = not quoted
            else:
                if not quoted and command[at] in '&|<>':
                    raise BuildRejected('Unsupported shell operator in compiler command')
                value.append(command[at])
            at += 1
        if quoted:
            raise BuildRejected('Unterminated command quote')
        args.append(''.join(value))
    if not args or any(arg.startswith('@') for arg in args):
        raise BuildRejected('Empty command or unsupported response file')
    return args


def compiler_args(command):
    # Accept only CMake's observed inert cd wrapper. Never execute cmd/shell text.
    wrapper = re.fullmatch(r'(?:"[^"]*[/\\]cmd\.exe"|\S*[/\\]cmd\.exe|cmd\.exe) /C "cd \. && (.*) && cd \."',
                           command, re.IGNORECASE)
    if wrapper:
        command = wrapper.group(1)
    return windows_args(command)


def option_index(args, flag):
    if args.count(flag) != 1 or args.index(flag) + 1 >= len(args):
        raise BuildRejected('Expected exactly one ' + flag)
    return args.index(flag) + 1


def absolute(value, root):
    path = Path(value.replace('\\', '/'))
    return (path if path.is_absolute() else root / path).resolve()


def expand_response(command, build):
    # CMake emits a Ninja response file for the final link once the expanded
    # command crosses its length threshold (seen on the combined lane-13 head).
    # Ninja only keeps the file with `-d keeprsp`, so it must already be on disk.
    def replace(match):
        path = Path(match.group(2))
        if not path.is_absolute():
            path = build / path
        if not path.is_file():
            raise BuildRejected('Missing response file (rerun the target link with `ninja -d keeprsp`): ' + str(path))
        return path.read_text(encoding='utf-8')
    return re.sub(r'@("?)([^\s"]+\.rsp)\1', replace, command)


def select_commands(commands, source, build):
    main = (source / 'pc_port/pc_main.cpp').resolve()
    compiles, links, objects = [], [], set()
    # Archive/custom build steps can contain real shell pipelines. They are not
    # compiler/link invocations and must never be evaluated by this tool.
    parsed = [compiler_args(expand_response(line, build)) for line in commands if ' -c ' in line or ' -o ' in line]
    for args in parsed:
        if '-c' in args:
            obj = absolute(args[option_index(args, '-o')], build)
            objects.add(obj)
            if absolute(args[option_index(args, '-c')], build) == main:
                compiles.append(args)
    if len(compiles) != 1:
        raise BuildRejected('Expected exactly one native pc_main compilation')
    compile_args = compiles[0]
    main_object = absolute(compile_args[option_index(compile_args, '-o')], build)
    for args in parsed:
        if '-c' not in args and '-o' in args:
            matches = [i for i, value in enumerate(args) if not value.startswith('-') and absolute(value, build) == main_object]
            if len(matches) == 1:
                links.append(args)
    if len(links) != 1:
        raise BuildRejected('Expected exactly one link command using pc_main object')
    link_args = links[0]
    option_index(link_args, '-o')
    if absolute(compile_args[0], build) != absolute(link_args[0], build):
        raise BuildRejected('Compile and link compiler differ')
    return compile_args, link_args, main_object, objects


def fixture_compile(args, fixture, output, source):
    if any(a.startswith(('-save-temps', '-fdump', '-dumpdir', '-dumpbase', '-MJ')) for a in args):
        raise BuildRejected('Unsupported compiler side-output option')
    result, at = [], 0
    while at < len(args):
        flag = args[at]
        if flag in ('-MF', '-MT', '-MQ'):
            if at + 1 >= len(args):
                raise BuildRejected('Missing dependency flag operand')
            at += 2
            continue
        if flag not in ('-MD', '-MMD', '-MP'):
            result.append(flag)
        at += 1
    result[option_index(result, '-c')] = str(fixture)
    result[option_index(result, '-o')] = str(output / 'fixture.obj')
    result.extend(['-I' + str(fixture.parent), '-I' + str(source / 'tools'),
                   '-MD', '-MF', str(output / 'fixture.d'), '-MT', 'fixture'])
    return result


def dependency_command(args, output):
    result, at = [], 0
    while at < len(args):
        if args[at] in ('-o', '-MF', '-MT'):
            at += 2
            continue
        if args[at] not in ('-c', '-MD'):
            result.append(args[at])
        at += 1
    return result + ['-M', '-MF', str(output / 'preflight.d'), '-MT', 'fixture']


def make_dependencies(text, build):
    text = text.replace('\\\r\n', '').replace('\\\n', '')
    if not text.startswith('fixture:'):
        raise BuildRejected('Unexpected fixture dependency target')
    # GCC emits Make escapes, not shell quoting. Preserve ordinary Windows
    # backslashes; only consume escapes meaningful in a dependency filename.
    values, value, at = [], [], len('fixture:')
    while at < len(text):
        char = text[at]
        if char == '\\' and at + 1 < len(text) and text[at + 1] in ' \t#:\\':
            value.append(text[at + 1])
            at += 2
            continue
        if char == '$' and at + 1 < len(text) and text[at + 1] == '$':
            value.append('$')
            at += 2
            continue
        if char.isspace():
            if value:
                values.append(''.join(value))
                value = []
        else:
            value.append(char)
        at += 1
    if value:
        values.append(''.join(value))
    if not values:
        raise BuildRejected('Empty fixture dependency list')
    return {absolute(value, build) for value in values}


def ninja_dependencies(text, objects, build):
    found, dependencies, current = set(), set(), None
    for line in text.splitlines():
        match = re.fullmatch(r'(.*): #deps (\d+), deps mtime \d+ \((VALID|STALE)\)', line)
        if match:
            current = absolute(match[1], build)
            if current in objects:
                if match[3] != 'VALID':
                    raise BuildRejected('Stale Ninja dependency record: ' + str(current))
                found.add(current)
        elif line.startswith('    ') and current in objects:
            dependencies.add(line.strip())
        elif line.strip():
            current = None
    if found != objects:
        raise BuildRejected('Missing Ninja compiler dependency records')
    return {absolute(path, build) for path in dependencies}


def run(args, cwd, env=None):
    completed = subprocess.run(args, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=300)
    return completed.returncode, completed.stdout


def require_fresh(ninja, build, record):
    code, text = run([str(ninja), '-n', '-d', 'explain', 'pikmin_pc'], build)
    record.append(dict(returncode=code, output=text))
    if code != 0 or text.strip() != 'ninja: no work to do.':
        raise BuildRejected('Native Ninja target has pending work or freshness could not be established; no production rebuild was run')


def git_state(source):
    values = {}
    for key, args in [('head', ['rev-parse', 'HEAD']), ('status', ['status', '--porcelain=v1', '--untracked-files=normal']),
                      ('tracked_diff', ['diff', '--binary', 'HEAD'])]:
        code, text = run(['git', '-C', str(source)] + args, source)
        if code:
            raise BuildRejected('Cannot read native Git state')
        values[key + ('_sha256' if key == 'tracked_diff' else '')] = (
            hashlib.sha256(text.encode('utf-8')).hexdigest() if key == 'tracked_diff' else text.strip())
    return values


def resolve_libraries(args, compiler, build, env):
    if any(a in ('-static', '-Bstatic', '-m32') or a.startswith(('-B', '--sysroot', '-specs', '-fuse-ld'))
           or any(flag in a for flag in ('-Bstatic', '-Map', '--output', '-Wl,-L', '--library-path')) for a in args):
        raise BuildRejected('Unsupported linker library mode or side-output option')
    search = []
    for index, arg in enumerate(args):
        if arg == '-L':
            search.append(absolute(args[index + 1], build))
        elif arg.startswith('-L'):
            search.append(absolute(arg[2:], build))
    code, text = run([str(compiler), '-print-search-dirs'], build, env)
    lines = [line[len('libraries: ='):] for line in text.splitlines() if line.startswith('libraries: =')]
    if code or len(lines) != 1:
        raise BuildRejected('Cannot identify compiler library search directories')
    search.extend(absolute(value, build) for value in lines[0].split(';') if value)
    libraries = {}
    for arg in args:
        if not arg.startswith('-l'):
            continue
        if arg == '-l':
            raise BuildRejected('Split -l library option is unsupported')
        # GNU PE linker searches each directory before moving to the next one.
        name = arg[2:]
        names = [arg[3:]] if arg.startswith('-l:') else [
            'lib' + name + '.dll.a', name + '.dll.a', 'lib' + name + '.a',
            name + '.lib', 'lib' + name + '.dll', name + '.dll']
        candidates = [directory / name for directory in search for name in names]
        located = next((p.resolve() for p in candidates if p.is_file()), None)
        if located is None:
            raise BuildRejected('Cannot resolve link library: ' + arg)
        libraries[arg] = located
    return libraries


def compiler_helpers(compiler, args, build, env):
    names = ['cc1plus', 'collect2', 'as', 'ld']
    if any(a.startswith('-flto') for a in args):
        names += ['lto-wrapper', 'lto1']
    result = {}
    for name in names:
        code, text = run([str(compiler), '-print-prog-name=' + name], build, env)
        value = text.strip()
        candidate = absolute(value, build)
        if not candidate.is_file():
            located = shutil.which(value, path=env['PATH'])
            candidate = Path(located).resolve() if located else candidate
        if code or not candidate.is_file():
            raise BuildRejected('Cannot identify compiler helper: ' + name)
        result[name] = candidate
    return result


def build_fixture(build, source, fixture, output, expected_head, check_only=False):
    build, source, fixture, output = (p.resolve() for p in (build, source, fixture, output))
    if ',' in str(output):
        raise BuildRejected('Output path cannot contain a comma in linker output options')
    if output.is_relative_to(source) or output.is_relative_to(build):
        raise BuildRejected('Private output must be outside the native source and production build')
    output.mkdir(parents=True, exist_ok=False)
    record = dict(schema=1, status='checking', historical_build_certified=False, source=str(source),
                  build=str(build), fixture=str(fixture), expected_native_head=expected_head,
                  freshness_checks=[], commands=[], limitations=[
                      'Ninja dependency freshness and current hashes do not certify historical build source identity.',
                      'No clean-machine installation, DLL packaging or gameplay acceptance is established.',
                      'Implicit compiler runtime/startup dependencies are not copied into the private link snapshot.',
                      'Concurrent edits are detected by before/after observations; this is not a production build lock.'])
    try:
        if not fixture.is_file() or fixture.suffix != '.cpp':
            raise BuildRejected('Expected an existing C++ fixture source')
        cache = {}
        for line in (build / 'CMakeCache.txt').read_text(encoding='utf-8').splitlines():
            if line and not line.startswith(('#', '//')) and '=' in line:
                key, value = line.split('=', 1)
                cache[key.split(':')[0]] = value
        if cache.get('CMAKE_GENERATOR') != 'Ninja' or absolute(cache['CMAKE_HOME_DIRECTORY'], build) != source:
            raise BuildRejected('CMake generator or configured source directory mismatch')
        compiler, ninja = (absolute(cache[key], build) for key in ('CMAKE_CXX_COMPILER', 'CMAKE_MAKE_PROGRAM'))
        record['configuration_inputs'] = snapshot([build / 'CMakeCache.txt', build / 'build.ninja',
                                                   build / 'CMakeFiles/rules.ninja', compiler, ninja, fixture])
        record['observed_source'] = git_state(source)
        if not re.fullmatch(r'[0-9a-f]{40}', expected_head) or record['observed_source']['head'] != expected_head:
            raise BuildRejected('Native HEAD differs from explicitly expected commit')
        record['build_type'] = cache.get('CMAKE_BUILD_TYPE')
        require_fresh(ninja, build, record['freshness_checks'])
        env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
        code, text = run([str(ninja), '-t', 'commands', 'pikmin_pc'], build)
        if code:
            raise BuildRejected('Cannot obtain Ninja commands')
        (output / 'native-commands.txt').write_text(text, encoding='utf-8')
        compile_args, link_args, main_object, objects = select_commands(text.splitlines(), source, build)
        if absolute(compile_args[0], build) != compiler:
            raise BuildRejected('Ninja compiler differs from CMake cache')
        code, deps = run([str(ninja), '-t', 'deps'], build)
        if code:
            raise BuildRejected('Cannot inspect Ninja dependencies')
        inputs = ninja_dependencies(deps, objects, build) | objects
        code, declared_inputs = run([str(ninja), '-t', 'inputs', 'pikmin_pc'], build)
        if code:
            raise BuildRejected('Cannot inspect Ninja declared inputs')
        for line in declared_inputs.splitlines():
            path = absolute(line.strip('"'), build)
            if not path.is_dir():
                inputs.add(path)
        libraries = resolve_libraries(link_args, compiler, build, env)
        helpers = compiler_helpers(compiler, compile_args + link_args, build, env)
        explicit = {absolute(a, build) for a in link_args if a.lower().endswith(('.a', '.lib', '.obj', '.o')) and not a.startswith('-')}
        inputs |= explicit | set(libraries.values()) | set(helpers.values()) | {fixture, compiler, ninja,
                  build / 'CMakeCache.txt', build / 'build.ninja', build / 'CMakeFiles/rules.ninja',
                  build / '.ninja_log', build / '.ninja_deps', absolute(link_args[option_index(link_args, '-o')], build)}
        record['toolchain'] = {}
        for name, path in [('compiler', compiler), ('ninja', ninja)]:
            code, version = run([str(path), '--version'], build, env)
            if code:
                raise BuildRejected('Cannot query toolchain version')
            record['toolchain'][name] = dict(path=str(path), version=version)
        record['resolved_libraries'] = {name: str(path) for name, path in libraries.items()}
        record['compiler_helpers'] = {name: str(path) for name, path in helpers.items()}
        compile_args = fixture_compile(compile_args, fixture, output, source)
        record['inputs'] = snapshot(inputs)
        if check_only:
            require_fresh(ninja, build, record['freshness_checks'])
            check_snapshot(record['inputs'])
            check_snapshot(record['configuration_inputs'])
            if git_state(source) != record['observed_source']:
                raise BuildRejected('Native Git state changed during check')
            record['status'] = 'checked_not_built'
            return record
        # Discover fixture-specific headers before compilation so edits can be detected.
        preflight = dependency_command(compile_args, output)
        record['commands'].append(preflight)
        code, text = run(preflight, build, env)
        (output / 'preflight.log').write_text(text, encoding='utf-8')
        if code:
            raise BuildRejected('Fixture dependency scan failed; see preflight.log')
        fixture_inputs = make_dependencies((output / 'preflight.d').read_text(encoding='utf-8'), build)
        check_snapshot(record['inputs'])
        record['fixture_inputs'] = snapshot(fixture_inputs)
        private = output / 'link-inputs'
        private.mkdir()
        copies = {}
        for index, original in enumerate(sorted(explicit | set(libraries.values()), key=str)):
            if original == main_object:
                continue
            destination = private / (str(index) + '-' + original.name)
            shutil.copy2(original, destination)
            if sha256(destination) != record['inputs'][str(original)]['sha256']:
                raise BuildRejected('Link input changed while copying')
            copies[original] = destination
        rewritten = []
        for arg in link_args:
            path = absolute(arg, build) if not arg.startswith('-') else None
            if path == main_object:
                rewritten.append(str(output / 'fixture.obj'))
            elif path in copies:
                rewritten.append(str(copies[path]))
            elif arg in libraries:
                rewritten.append(str(copies[libraries[arg]]))
            elif arg.startswith('-Wl,--out-implib,'):
                rewritten.append('-Wl,--out-implib,' + str(output / 'fixture.dll.a'))
            else:
                rewritten.append(arg)
        rewritten[option_index(rewritten, '-o')] = str(output / 'fixture.exe')
        for phase, command in [('compile', compile_args), ('link', rewritten)]:
            record['commands'].append(command)
            code, text = run(command, build, env)
            (output / (phase + '.log')).write_text(text, encoding='utf-8')
            if code:
                raise BuildRejected('Fixture ' + phase + ' failed; see ' + phase + '.log')
        actual_deps = make_dependencies((output / 'fixture.d').read_text(encoding='utf-8'), build)
        if actual_deps != fixture_inputs:
            raise BuildRejected('Fixture dependency set changed during compilation')
        require_fresh(ninja, build, record['freshness_checks'])
        check_snapshot(record['inputs'])
        check_snapshot(record['fixture_inputs'])
        check_snapshot(record['configuration_inputs'])
        if git_state(source) != record['observed_source']:
            raise BuildRejected('Native Git state changed during fixture build')
        record['artifacts'] = snapshot([output / 'fixture.exe', output / 'fixture.obj'])
        record['status'] = 'built'
        return record
    except Exception as error:
        record['status'] = 'rejected'
        record['error'] = str(error)
        raise
    finally:
        (output / 'provenance.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-native-head', required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        result = build_fixture(args.build, args.source, args.fixture, args.output, args.expected_native_head, args.check_only)
        print(json.dumps(dict(status=result['status'], output=str(args.output.resolve()))))
    except (BuildRejected, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + '\n')
