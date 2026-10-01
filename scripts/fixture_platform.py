"""Platform primitives for private fixtures; broker admission is a separate gate."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys

WINDOWS_DLLS = ('libstdc++-6.dll', 'libgcc_s_seh-1.dll', 'libwinpthread-1.dll')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def is_windows():
    return sys.platform == 'win32'


def windows_dependencies(exe, runtime_directory=None, *, include_sdl=True):
    directory = Path(runtime_directory).resolve(strict=True) if runtime_directory is not None else Path('C:/msys64/mingw64/bin')
    names = WINDOWS_DLLS + (('SDL2.dll',) if runtime_directory is not None and include_sdl else ())
    hashes = {name: digest(directory / name) for name in names}
    for name, sha in hashes.items():
        local = Path(exe).resolve().parent / name
        if local.exists() and digest(local) != sha:
            raise ValueError(f'Conflicting executable-local runtime DLL: {local}')
    return directory, hashes


def check_loader_environment(env):
    forbidden = sorted(k for k in env if k.startswith('LD_') or k in ('GLIBC_TUNABLES', 'GCONV_PATH', 'LOCPATH'))
    if forbidden:
        raise ValueError('Loader environment overrides forbidden: ' + ', '.join(forbidden))


def elf_interpreter(exe):
    """Read PT_INTERP directly; reject non-ELF, malformed or static inputs."""
    with Path(exe).open('rb') as stream:
        header = stream.read(64)
        if len(header) < 64 or header[:4] != b'\x7fELF' or header[4] not in (1, 2) or header[5] not in (1, 2):
            raise ValueError('Expected an ELF executable')
        order = '<' if header[5] == 1 else '>'
        if struct.unpack_from(order + 'H', header, 16)[0] not in (2, 3):
            raise ValueError('ELF is not an executable or PIE')
        wide = header[4] == 2
        offset = struct.unpack_from(order + ('Q' if wide else 'I'), header, 32 if wide else 28)[0]
        size, count = struct.unpack_from(order + 'HH', header, 54 if wide else 42)
        if size < (56 if wide else 32) or count > 4096:
            raise ValueError('Invalid ELF program header table')
        interpreter = None
        for index in range(count):
            stream.seek(offset + index * size)
            entry = stream.read(size)
            if len(entry) != size:
                raise ValueError('Truncated ELF program headers')
            if struct.unpack_from(order + 'I', entry)[0] != 3:
                continue
            position = struct.unpack_from(order + ('Q' if wide else 'I'), entry, 8 if wide else 4)[0]
            length = struct.unpack_from(order + ('Q' if wide else 'I'), entry, 32 if wide else 16)[0]
            if interpreter is not None or not 2 <= length <= 4096:
                raise ValueError('Invalid ELF interpreter')
            stream.seek(position)
            raw = stream.read(length)
            if len(raw) != length or raw[-1:] != b'\0' or b'\0' in raw[:-1]:
                raise ValueError('Invalid ELF interpreter path')
            interpreter = Path(os.fsdecode(raw[:-1]))
        if interpreter is None or not interpreter.is_absolute():
            raise ValueError('A dynamic ELF with an absolute interpreter is required')
        return interpreter


def linux_dependencies(exe, env=None, cwd=None):
    env = dict(os.environ if env is None else env)
    check_loader_environment(env)
    exe = Path(exe).resolve(strict=True)
    if not exe.is_file() or not os.access(exe, os.X_OK):
        raise ValueError('ELF must be an executable regular file')
    loader = elf_interpreter(exe)
    resolved_loader = loader.resolve(strict=True)
    # ldd uses the host's supported loader. Reject custom interpreters instead
    # of claiming that tracing one loader describes another loader's execution.
    host_loader = elf_interpreter(Path('/usr/bin/python3').resolve(strict=True)).resolve(strict=True)
    if resolved_loader != host_loader:
        raise ValueError('ELF interpreter differs from the supported host loader')
    directory = Path(cwd or Path.cwd()).resolve(strict=True)
    probe_env = dict(env, LC_ALL='C', LANG='C', PATH='/usr/bin:/bin')
    result = subprocess.run(['/usr/bin/ldd', str(exe)], cwd=directory, env=probe_env, capture_output=True, text=True, timeout=10)
    if result.returncode or 'not found' in result.stdout or 'not found' in result.stderr:
        raise ValueError('Unresolved ELF dependencies: ' + (result.stdout + result.stderr).strip())
    libraries = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or re.fullmatch(r'linux-(?:vdso|gate)\S* \(0x[0-9a-fA-F]+\)', line):
            continue
        match = re.fullmatch(r'(?:(\S+) => )?(.+?) \(0x[0-9a-fA-F]+\)', line)
        if not match:
            raise ValueError('Unrecognized ldd dependency: ' + line)
        name, path = match.groups()
        resolved = (directory / path).resolve(strict=True)
        if not resolved.is_file():
            raise ValueError('ELF dependency is not a regular file: ' + str(resolved))
        name = name or path
        record = {'path': path, 'resolved_path': str(resolved), 'sha256': digest(resolved)}
        if name in libraries and libraries[name] != record:
            raise ValueError('Ambiguous ELF dependency: ' + name)
        libraries[name] = record
    if not libraries:
        raise ValueError('No resolved ELF dependencies')
    if not any(item['resolved_path'] == str(resolved_loader) for item in libraries.values()):
        raise ValueError('ldd did not report the ELF interpreter')
    return {'platform': 'linux', 'executable': {'path': str(exe), 'sha256': digest(exe)},
            'loader': {'path': str(loader), 'resolved_path': str(resolved_loader), 'sha256': digest(resolved_loader)},
            'libraries': libraries, 'ldd_stdout': result.stdout, 'runtime_directory': None, 'cwd': str(directory),
            'scope': 'ELF link-time dependency closure; dynamically loaded plugins/drivers are not enumerated'}


def runtime_evidence(exe, runtime_directory=None, env=None, *, include_sdl=True, cwd=None):
    if is_windows():
        directory, hashes = windows_dependencies(exe, runtime_directory, include_sdl=include_sdl)
        return {'platform': 'windows', 'runtime_directory': str(directory), 'dlls': hashes,
                'executable': {'path': str(Path(exe).resolve()), 'sha256': digest(exe)}}
    if runtime_directory is not None:
        raise ValueError('Linux runtime libraries are resolved from ELF, not a DLL directory')
    return linux_dependencies(exe, env, cwd)


def runtime_dependencies(exe, runtime_directory=None):
    """Compatibility tuple for captain runners; Linux keys are resolved paths."""
    evidence = runtime_evidence(exe, runtime_directory)
    if evidence['platform'] == 'windows':
        return Path(evidence['runtime_directory']), evidence['dlls']
    hashes = {v['resolved_path']: v['sha256'] for v in evidence['libraries'].values()}
    hashes[evidence['loader']['resolved_path']] = evidence['loader']['sha256']
    return None, hashes


def fresh_destination(source, destination):
    source = Path(source).resolve(strict=True)
    destination = Path(destination)
    if os.path.lexists(destination):
        raise ValueError('Destination must be fresh: ' + str(destination))
    resolved = destination.resolve()
    if source == resolved or source in resolved.parents or resolved in source.parents:
        raise ValueError('Source and destination must not overlap')
    return source, resolved


def copy_private_tree(source, destination, overrides=None):
    """Materialize independent files, following readable links but rejecting cycles."""
    source, destination = fresh_destination(source, destination)
    overrides = {} if overrides is None else dict(overrides)
    for key in overrides:
        path = PurePosixPath(key)
        if not key or path.is_absolute() or '..' in path.parts or '\\' in key or str(path) != key:
            raise ValueError('Override must be a normalized relative path: ' + key)
        if any(str(parent) in overrides for parent in path.parents if str(parent) != '.'):
            raise ValueError('Override file conflicts with descendant: ' + key)
    def copy(src, dst, changes, ancestors):
        real = src.resolve(strict=True) if src.exists() or src.is_symlink() else None
        if real is not None:
            if real in ancestors or real == destination or destination in real.parents:
                raise ValueError('Asset link cycle or destination alias: ' + str(src))
            if not real.is_dir():
                raise ValueError('Expected asset directory: ' + str(src))
        dst.mkdir(parents=True, exist_ok=False)
        ancestry = ancestors | ({real} if real is not None else set())
        names = ({p.name for p in real.iterdir()} if real is not None else set()) | {k.split('/')[0] for k in changes}
        for name in sorted(names):
            entry, target = src / name, dst / name
            if name in changes:
                target.write_bytes(changes[name])
                continue
            children = {k[len(name)+1:]: v for k, v in changes.items() if k.startswith(name + '/')}
            if children or entry.is_dir():
                copy(entry, target, children, ancestry)
            else:
                resolved = entry.resolve(strict=True)
                if not resolved.is_file():
                    raise ValueError('Asset is not a regular file: ' + str(entry))
                shutil.copyfile(resolved, target)  # No hardlinks or shared writable targets.
    copy(source, destination, overrides, set())


def owned_process_options():
    return {} if is_windows() else {'start_new_session': True}


def terminate_owned_process(proc):
    """On POSIX retire the owned group even if its leader already exited."""
    if is_windows():
        if proc.poll() is None:
            proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if proc.poll() is None:
        proc.wait(timeout=10)


def linux_admission(exe, canonical_root, session_root, run_directory):
    """Consult the fixed controller proof, never a caller-selected authorization."""
    helper = Path('/srv/game-ci/production/fixture_admission_proof.py')
    python = Path('/usr/bin/python3')
    def trusted_file(path, allow_symlink=False):
        resolved = path.resolve(strict=True)
        if not allow_symlink and resolved != path:
            raise ValueError('Controller proof path may not be redirected')
        for entry in {*path.parents, *resolved.parents, path, resolved}:
            info = entry.stat()
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError('Controller proof paths must be root-owned and not group/other writable')
        if not stat.S_ISREG(resolved.stat().st_mode):
            raise ValueError('Controller proof must be a regular file')
    trusted_file(helper)
    trusted_file(python, allow_symlink=True)
    root, session, exe, run = (Path(p).resolve(strict=True) for p in (canonical_root, session_root, exe, run_directory))
    if not session.is_relative_to(root / 'output') or not run.is_relative_to(session):
        raise ValueError('Linux run/session must remain inside the pinned root output')
    env = dict(os.environ)
    check_loader_environment(env)
    result = subprocess.run([str(python), '-I', str(helper), '--root', str(root), '--session', str(session), '--exe', str(exe)],
                            env=env, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError('Fixed controller fixture admission denied')
    try:
        proof = json.loads(result.stdout)
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid controller admission response') from error
    fields = {'schema', 'admitted', 'unit', 'cgroup', 'pins', 'job', 'root', 'session', 'exe',
              'exe_sha256', 'target', 'source', 'guard_sha256', 'controller_sha256', 'proof_helper_sha256', 'catalog_sha256'}
    pin_fields = {'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'FIXTURE_SUITE', 'FIXTURE_REQUEST_ID',
                  'FIXTURE_SOURCE_SHA256', 'PIKMIN_SHA', 'NATIVE_SHA'}
    if not isinstance(proof, dict) or set(proof) != fields or proof['schema'] != 1 or proof['admitted'] is not True:
        raise ValueError('Controller admission schema mismatch')
    if not isinstance(proof['pins'], dict) or set(proof['pins']) != pin_fields:
        raise ValueError('Controller admission pins mismatch')
    if any(proof[k] != str(v) for k, v in (('root', root), ('session', session), ('exe', exe))):
        raise ValueError('Controller admission path mismatch')
    for key in ('exe_sha256', 'guard_sha256', 'controller_sha256', 'proof_helper_sha256', 'catalog_sha256'):
        if not isinstance(proof[key], str) or not re.fullmatch('[0-9a-f]{64}', proof[key]):
            raise ValueError('Controller admission hash mismatch')
    for key, value in proof['pins'].items():
        if not isinstance(value, str) or not value:
            raise ValueError('Invalid controller source pin')
        if key in ('PIKMIN_SHA', 'NATIVE_SHA') and not re.fullmatch('[0-9a-f]{40}', value):
            raise ValueError('Invalid controller commit pin')
        if key == 'FIXTURE_SOURCE_SHA256' and not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError('Invalid controller source hash')
    if proof['exe_sha256'] != digest(exe) or proof['proof_helper_sha256'] != digest(helper):
        raise ValueError('Controller proof executable/helper hash mismatch')
    for key in ('unit', 'cgroup', 'job', 'target', 'source'):
        if not isinstance(proof[key], str) or not proof[key]:
            raise ValueError('Controller admission context missing')
    # Exact cgroup/unit, immutable source and fixed target checks belong to the
    # root-owned controller. Return only the contracted fields, never its environment.
    return proof
