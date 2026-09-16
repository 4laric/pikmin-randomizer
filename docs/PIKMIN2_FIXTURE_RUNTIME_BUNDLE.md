# Private fixture DLL bundle (#135)

`scripts/bundle_pikmin2_fixture.py` collects an existing Windows fixture executable
and its transitive non-system PE imports into a new private directory. Every copied
file has an origin, SHA-256, and import list in `runtime-provenance.json`.
This tool does not build native code, stage game assets, or certify gameplay.

DLL lookup uses only explicitly supplied directories (repeat `--dll-root` if
needed), with case-insensitive names. Missing or ambiguous matches fail, even if
ambiguous candidates have identical bytes. System32 imports and Windows API-set
contracts remain system dependencies and are not copied. A supplied DLL that
shadows a system dependency is rejected. Cycles are handled without recursion.
Existing output is never reused. Input hashes are checked during inspection and
again before copying; a failed copy can leave an incomplete directory without a
manifest, which must not be treated as a valid bundle.

## Recorded validation: 2026-09-12

Root base: `7ac96bd`. Used the fixed previous fixture at native observed HEAD
`606c0c1763073aa9576c08455b42fa548f59b4f7`, executable SHA-256
`3ab25db6b06ce489b9eff87c304b1f358fde48f228cb15f388a2a4d93a1e3e7b`.
No native rebuild or shared source changes occurred.

Run from the private worktree with an existing `output` parent:

```powershell
py -3.12 -m scripts.bundle_pikmin2_fixture --executable C:/Users/alari/pikmin-randomizer/output/p2-fixture-builds/output/native-room-606c0c17/fixture.exe --dll-root C:/msys64/mingw64/bin --system-directory C:/Windows/System32 --objdump C:/msys64/mingw64/bin/objdump.exe --output output/runtime
py -3.12 -m unittest tests.test_pikmin2_fixture_bundle
```

Result: five files bundled (executable plus `libgcc_s_seh-1.dll`,
`libstdc++-6.dll`, `libwinpthread-1.dll`, and `SDL2.dll`). Seven tests passed:
transitive cycles/system exclusion, missing dependencies, ambiguity, no overwrite,
system shadowing, unsafe import names, and inputs changing during inspection.

Startup smoke command, executed via Python 3.12:

```python
import ctypes, os, subprocess
from pathlib import Path
root = Path('output/runtime').resolve()
ctypes.windll.kernel32.SetErrorMode(0x8003)
env = {'SystemRoot': os.environ['SystemRoot'], 'WINDIR': os.environ['WINDIR'],
       'PATH': str(Path(os.environ['SystemRoot']) / 'System32'),
       'TEMP': str(root), 'TMP': str(root)}
result = subprocess.run([str(root / 'fixture.exe')], cwd=root, env=env,
                        capture_output=True, timeout=15)
assert result.returncode == 1
assert b'requires --experimental-pikmin2-room' in result.stdout
```

Observed exit 1, stdout `FAIL p2 room: requires --experimental-pikmin2-room`,
empty stderr. This is the expected application-level argument guard, proving that
the loader now reaches application code. The unbundled negative control previously
exited `0xc0000135` before application output. Deliberately omitting the room flag
stops before window initialization, asset loading, and gameplay.

## Limits

This is a same-host loader smoke, not a clean Windows VM install test. It resolves
ordinary PE imports, not arbitrary runtime `LoadLibrary` calls or graphics drivers.
System dependencies depend on the explicitly selected system directory and OS;
use the target machine's compatible toolchain DLLs. The helper assumes trusted
local inputs and does not claim protection from concurrent hostile filesystem
changes. Runtime hashes describe the copied binaries, not historical build inputs.
All binaries, manifests, and smoke logs remain ignored local output. The helper is
for private fixtures; redistribution and production launcher packaging are separate.
