"""Cooperative, cross-worktree Windows GL leases and bounded process-tree runs."""
import argparse
import contextlib
import ctypes
from ctypes import wintypes
import hashlib
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import time


def shared_output():
    common = subprocess.check_output(
        ['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], text=True
    ).strip()
    return Path(common).parent / 'output'


@contextlib.contextmanager
def leases(directory, names):
    directory.mkdir(parents=True, exist_ok=True)
    opened = []
    try:
        for name in sorted(names):
            stream = (directory / (name + '.lock')).open('a+b')
            stream.seek(0, 2)
            if stream.tell() == 0:
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                stream.close()
                raise RuntimeError(f'Busy lease: {name}; retry after owner finishes') from None
            opened.append(stream)
        yield
    finally:
        for stream in reversed(opened):
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            stream.close()


def checked_spec(path, lane, output):
    spec = json.loads(path.read_text(encoding='utf-8-sig'))
    exe = Path(spec['executable']).resolve(strict=True)
    cwd = Path(spec['cwd']).resolve(strict=True)
    if not cwd.is_relative_to(output.resolve()) or cwd == output.resolve():
        raise ValueError('cwd must be a private directory under shared output')
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    if digest != spec['sha256'].lower():
        raise ValueError('Executable hash differs from reviewed descriptor')
    if not isinstance(spec.get('args', []), list) or not all(isinstance(x, str) for x in spec.get('args', [])):
        raise ValueError('args must be a list of strings, never shell text')
    if not 0 < spec.get('timeout_seconds', 0) <= 1800:
        raise ValueError('timeout_seconds must be 1..1800')
    if lane == 'B':
        review = spec.get('no_input_review', {})
        for field in ('no_desktop_input', 'no_focus_changes', 'no_shared_writes', 'autonomous_exit'):
            if review.get(field) is not True:
                raise ValueError(f'GL-B requires reviewed {field}=true')
        if not review.get('source_commit') or not review.get('reviewer'):
            raise ValueError('GL-B requires source_commit and reviewer')
    return spec, exe, cwd


class Job:
    """Keep descendants contained; closing the runner also closes its job handle."""
    def __init__(self):
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        # JOBOBJECT_EXTENDED_LIMIT_INFORMATION, Windows x64 layout.
        if ctypes.sizeof(ctypes.c_void_p) != 8:
            raise RuntimeError('Requires 64-bit Python')
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ctypes.create_string_buffer(144)
        ctypes.c_uint32.from_buffer(limits, 16).value = 0x2000  # KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, limits, len(limits)):
            self.close()
            raise ctypes.WinError(ctypes.get_last_error())

    def assign(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            process.kill()
            process.wait()
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.api.TerminateJobObject(self.handle, 124)
            self.api.CloseHandle(self.handle)
            self.handle = None


def run(spec_path, lane):
    output = shared_output()
    spec, exe, cwd = checked_spec(spec_path, lane, output)
    names = ['A', 'B'] if lane == 'exclusive' else [lane]
    names += ['cwd-' + hashlib.sha256(str(cwd).casefold().encode()).hexdigest()]
    lease_dir = output / 'gl-lanes'
    with leases(lease_dir, names):
        run_dir = lease_dir / ('run-' + str(time.time_ns()))
        run_dir.mkdir()
        result = dict(lane=lane, runner_pid=os.getpid(), spec=spec, status='starting',
                      started=time.time(), logs=str(run_dir))
        record = run_dir / 'result.json'
        record.write_text(json.dumps(result, indent=2))
        job = Job()
        process = None
        try:
            env = os.environ.copy()
            env.update(spec.get('env', {}))
            env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
            if lane == 'B':
                env.update(SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS='0', SDL_AUDIODRIVER='dummy')
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0 if lane == 'B' else 4  # hidden / no activate
            with (run_dir / 'stdout.log').open('wb') as stdout, (run_dir / 'stderr.log').open('wb') as stderr:
                # Start suspended so no descendants can escape before job assignment.
                process = subprocess.Popen([str(exe), *spec.get('args', [])], cwd=cwd,
                    env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                    startupinfo=startup, creationflags=0x00000004 | subprocess.CREATE_NO_WINDOW)
                job.assign(process)
                nt = ctypes.WinDLL('ntdll')
                nt.NtResumeProcess.argtypes = [wintypes.HANDLE]
                nt.NtResumeProcess.restype = ctypes.c_long
                if nt.NtResumeProcess(int(process._handle)) != 0:
                    raise RuntimeError('Unable to resume contained process')
                result.update(status='running', child_pid=process.pid)
                record.write_text(json.dumps(result, indent=2))
                try:
                    result['exit_code'] = process.wait(timeout=spec['timeout_seconds'])
                    result['status'] = 'passed' if result['exit_code'] == 0 else 'failed'
                except subprocess.TimeoutExpired:
                    result.update(status='timeout', exit_code=124)
        except BaseException as error:
            result.update(status='error', error=str(error), exit_code=1)
            raise
        finally:
            job.close()
            if process is not None:
                process.wait()
            result['finished'] = time.time()
            record.write_text(json.dumps(result, indent=2))
            print(json.dumps({key: result[key] for key in ('lane', 'status', 'logs', 'exit_code')}), flush=True)
        return result['exit_code']


def status():
    directory = shared_output() / 'gl-lanes'
    result = {}
    for lane in ('A', 'B'):
        try:
            with leases(directory, [lane]):
                result[lane] = 'free'
        except RuntimeError:
            result[lane] = 'busy'
    print(json.dumps(dict(lanes=result, shared_directory=str(directory),
                         note='Cooperative leases only; check for legacy unleased runs too.')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--lane', choices=['A', 'B', 'exclusive'])
    parser.add_argument('--spec', type=Path)
    args = parser.parse_args()
    if args.status:
        status()
        raise SystemExit(0)
    if not args.lane or not args.spec:
        parser.error('--lane and --spec are required for a run')
    raise SystemExit(run(args.spec, args.lane))
