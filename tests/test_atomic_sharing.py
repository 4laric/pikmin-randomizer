import ctypes
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from randomizer.session import atomic_write


@unittest.skipUnless(os.name == 'nt', 'Windows file-sharing behavior')
class AtomicSharingTests(unittest.TestCase):
    def test_native_style_reader_releases_before_replace(self):
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
                                      ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.txt'
            path.write_text('old', encoding='utf-8')
            handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
            timer = threading.Timer(0.1, kernel.CloseHandle, args=[handle])
            timer.start()
            try:
                atomic_write(path, 'new\n')
                self.assertEqual(path.read_bytes(), b'new\n')
                self.assertFalse(path.with_suffix('.txt.tmp').exists())
            finally:
                timer.join()

    def test_persistent_denial_keeps_live_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.txt'
            path.write_text('old', encoding='utf-8')
            error = PermissionError('denied'); error.winerror = 5
            with patch('randomizer.session.os.replace', side_effect=error), patch('randomizer.session.time.monotonic', side_effect=[0, 2]):
                with self.assertRaises(PermissionError):
                    atomic_write(path, 'new')
            self.assertEqual(path.read_text(encoding='utf-8'), 'old')

    def test_unrelated_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('randomizer.session.os.replace', side_effect=OSError('disk failure')) as replace:
                with self.assertRaises(OSError):
                    atomic_write(Path(folder) / 'state.txt', 'new')
                replace.assert_called_once()
