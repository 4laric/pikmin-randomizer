"""Process identity includes creation time, so a recycled PID is not its owner."""
import ctypes
import os
from pathlib import Path
import socket
import subprocess
import threading
import time


class DeadIdentityCache:
    """An exact dead identity cannot become alive again, even when its PID is reused."""
    def __init__(self, inspect, limit=16384, *, unknown_seconds=0, clock=time.monotonic):
        self.inspect, self.limit = inspect, limit
        self.dead = set()
        self.lock = threading.Lock()
        self.unknown = {}
        self.unknown_seconds, self.clock = unknown_seconds, clock

    def __call__(self, identity):
        key = tuple(identity.get(k) for k in ('host', 'pid', 'started'))
        cacheable = all(key) and set(identity) == {'host', 'pid', 'started'}
        if cacheable:
            with self.lock:
                if key in self.dead:
                    return 'dead'
                if self.unknown.get(key,0) > self.clock():
                    return 'unknown'  # Conservative protection, never permission to recover.
        result = self.inspect(identity)
        if cacheable and result == 'dead':
            with self.lock:
                if len(self.dead) >= self.limit:
                    self.dead.clear()
                self.dead.add(key)
                self.unknown.pop(key,None)
        elif cacheable and result == 'unknown' and self.unknown_seconds:
            with self.lock:
                if len(self.unknown)>=self.limit:self.unknown.clear()
                self.unknown[key]=self.clock()+self.unknown_seconds
        return result


def _windows_reused(identity):
    """CIM may expose creation time even when a recycled service PID denies handles.

    Only a positive mismatch proves the old owner dead; missing observations
    remain unknown. This fallback never authorizes killing the replacement.
    """
    try:
        pid = int(identity['pid'])
        expected = int(identity['started'])
        if pid <= 0 or expected <= 0:
            return False
        command = (f"$p = Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
                   "if ($p.CreationDate) { $p.CreationDate.ToUniversalTime().ToFileTimeUtc() }")
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                                capture_output=True, text=True, timeout=5,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        observed = int(result.stdout.strip()) if result.returncode == 0 else 0
        # CIM timestamps have microsecond precision; FILETIME uses 100 ns.
        return observed > 0 and observed // 10 != expected // 10
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        return False


def identify(pid):
    pid = int(pid)
    if pid <= 0:
        raise ValueError('PID must be positive')
    if os.name == 'nt':
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x101000, False, pid)  # query + synchronize
        if not handle:
            if ctypes.get_last_error() == 87:  # ERROR_INVALID_PARAMETER: no such PID
                raise ProcessLookupError(pid)
            raise PermissionError('Cannot inspect process')
        try:
            status = kernel.WaitForSingleObject(handle, 0)
            if status == 0:
                raise ProcessLookupError(pid)
            if status != 258:  # WAIT_TIMEOUT means still running
                raise PermissionError('Cannot inspect process exit state')
            times = [wintypes.FILETIME() for _ in range(4)]
            if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
                raise PermissionError('Cannot inspect process creation time')
            started = str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)
        finally:
            kernel.CloseHandle(handle)
    else:
        try:
            fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        except FileNotFoundError as error:
            raise ProcessLookupError(pid) from error
        if fields[0] == 'Z':
            raise ProcessLookupError(pid)
        started = fields[19]  # field 22, after pid and parenthesized comm
    return {'host': socket.gethostname(), 'pid': pid, 'started': started}


def boot_time():
    """Wall-clock seconds of this host's last boot, or None where it cannot be measured."""
    if os.name != 'nt':
        return None
    kernel = ctypes.WinDLL('kernel32')
    kernel.GetTickCount64.restype = ctypes.c_ulonglong
    return time.time() - kernel.GetTickCount64() / 1000


def boot_id():
    """This host's boot counter (Windows BootId, bumped by every boot), or None. Unlike boot_time it
    cannot move with a clock correction."""
    if os.name != 'nt':
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters') as key:
            value, kind = winreg.QueryValueEx(key, 'BootId')
        return value if kind == winreg.REG_DWORD and isinstance(value, int) else None
    except OSError:
        return None


def started_before_boot(identity, boot=boot_time, margin=60, recorded_boot=None, current_boot=boot_id):
    """True only for a same-host Windows identity created before the current boot: nothing it
    started can still run. The wall-clock comparison must agree with a boot counter the process
    recorded at start (recorded_boot) that differs from the current one, so neither a clock
    correction nor a missing marker proves anything. Any missing observation is False."""
    try:
        if identity.get('host') != socket.gethostname() or os.name != 'nt':
            return False
        now = current_boot()
        if not (isinstance(recorded_boot, int) and isinstance(now, int) and recorded_boot != now):
            return False
        at = boot()
        started = int(identity['started']) / 1e7 - 11644473600  # FILETIME (100 ns since 1601) to Unix.
        return at is not None and 0 < started < at - margin
    except (AttributeError, KeyError, TypeError, ValueError, OSError):
        return False


def process_rows():
    """[{ProcessId, ParentProcessId, Name}] from one Toolhelp snapshot: cheap (no CIM, no PowerShell)
    but without creation times. None when the snapshot cannot be taken."""
    if os.name != 'nt':
        return None
    from ctypes import wintypes
    class Entry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', ctypes.c_long), ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
    if not snapshot or snapshot == wintypes.HANDLE(-1).value:
        return None
    try:
        entry, rows = Entry(), []
        entry.dwSize = ctypes.sizeof(Entry)
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            rows.append(dict(ProcessId=entry.th32ProcessID, ParentProcessId=entry.th32ParentProcessID, Name=entry.szExeFile))
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        return rows if ctypes.get_last_error() == 18 else None  # ERROR_NO_MORE_FILES: the walk completed.
    finally:
        kernel.CloseHandle(snapshot)


def busy_descendants(rows, pid):
    """Names of pid's descendants other than conhost.exe, or None when rows cannot say (pid absent).
    Without creation times a recycled parent PID counts as a descendant: conservative, never a pass."""
    if not isinstance(rows, list) or pid not in {r.get('ProcessId') for r in rows}:
        return None
    family = {pid}
    while True:
        more = {r['ProcessId'] for r in rows if r.get('ParentProcessId') in family and r.get('ProcessId') != 0}
        if more <= family: break
        family |= more
    return sorted(str(r.get('Name')) for r in rows if r['ProcessId'] in family - {pid}
                  and str(r.get('Name')).lower() != 'conhost.exe')


def probe(identity):
    if identity.get('host') != socket.gethostname():
        return 'unknown'
    try:
        return 'alive' if identify(identity['pid']) == identity else 'dead'
    except ProcessLookupError:
        return 'dead'
    except (OSError, KeyError, ValueError):
        return 'dead' if os.name == 'nt' and _windows_reused(identity) else 'unknown'
