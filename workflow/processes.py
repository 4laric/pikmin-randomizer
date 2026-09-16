"""Process identity includes creation time, so a recycled PID is not its owner."""
import ctypes
import os
from pathlib import Path
import socket


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


def probe(identity):
    if identity.get('host') != socket.gethostname():
        return 'unknown'
    try:
        return 'alive' if identify(identity['pid']) == identity else 'dead'
    except ProcessLookupError:
        return 'dead'
    except (OSError, KeyError, ValueError):
        return 'unknown'
