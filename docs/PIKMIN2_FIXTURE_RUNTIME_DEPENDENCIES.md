# Private fixture runtime dependency audit (#135)

On 2026-09-12, the previously built private room fixture failed Windows loader
startup when copied alone into a fresh directory with a System32-only PATH.
Exit status was `3221225781` (`0xc0000135`, DLL not found), with empty stdout/stderr.
The successful compile/link evidence therefore does not establish standalone launch.
This is a private fixture packaging gap, not evidence about a distributed launcher.

Audited executable:
`output/p2-fixture-builds/output/native-room-606c0c17/fixture.exe`, SHA-256
`3ab25db6b06ce489b9eff87c304b1f358fde48f228cb15f388a2a4d93a1e3e7b`.
Its provenance records native HEAD `606c0c1763073aa9576c08455b42fa548f59b4f7`;
this audit used root base `a4c58834864410a30fa416fef0123ef93b6b3d41`.
No rebuild or shared-source changes were performed.

## Static import evidence

`C:/msys64/mingw64/bin/objdump.exe -p <binary>` was run on the executable
and recursively on each non-system dependency found in that toolchain directory.

| Non-system DLL | Non-system imports |
| --- | --- |
| `libgcc_s_seh-1.dll` | `libwinpthread-1.dll` |
| `libwinpthread-1.dll` | None |
| `libstdc++-6.dll` | `libgcc_s_seh-1.dll`, `libwinpthread-1.dll` |
| `SDL2.dll` | None |

All four are direct imports of the executable and were available in
`C:/msys64/mingw64/bin`, but not beside the audited executable. Its other direct
imports are `msvcrt.dll`, `KERNEL32.dll`, `OPENGL32.dll`, `USER32.dll`, and
`WS2_32.dll`. The four toolchain DLLs' remaining imports resolved to this host's
System32. This checks ordinary PE imports; it does not inventory dynamically
loaded graphics drivers or prove compatibility on another Windows installation.

## Isolated negative launch reproduction

Run this Python from the root of a private worktree. The destination must be fresh.
The source below is the existing fixture, not the production game. Windows error
dialogs are suppressed for the child; a timeout bounds unexpected execution.

```python
import ctypes, os, shutil, subprocess
from pathlib import Path
root = Path('output/clean-launch').resolve()
root.mkdir(parents=True)
source = Path('C:/Users/alari/pikmin-randomizer/output/p2-fixture-builds/output/native-room-606c0c17/fixture.exe')
exe = root / 'fixture.exe'
shutil.copy2(source, exe)
ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
env = {'SystemRoot': os.environ['SystemRoot'], 'WINDIR': os.environ['WINDIR'],
       'PATH': str(Path(os.environ['SystemRoot']) / 'System32'),
       'TEMP': str(root), 'TMP': str(root)}
result = subprocess.run([str(exe)], cwd=root, env=env,
                        capture_output=True, timeout=15)
print(hex(result.returncode & 0xffffffff), result.stdout, result.stderr)
```

Observed output: `0xc0000135 b'' b''`. The copied executable's hash matched the
original. Reports and executable copies remain in ignored private `output/`.

## Follow-up boundary

A fixture runtime packager should collect these four toolchain DLLs alongside the
executable, record their hashes and origins, and then verify loader startup in an
isolated environment. No DLLs were copied or packaging behavior changed in this
audit. A positive launch would still require the appropriate private asset/session
inputs and separate runtime QA; it would not certify gameplay. Kimi's gameplay
lane and the shared Snow rebuild were left untouched.
