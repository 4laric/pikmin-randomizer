# Packaging a Windows release

`scripts/package_release.py` turns a production native build plus this repository into
`output/pikrando-<version>-windows-x64.zip`, with `SHA256SUMS.txt` beside it and
`release-manifest.json` (commits, exe hash, file list) inside it.

## Build the package

1. Build the production executable without test hooks (`native/build-randomizer/bin/nectar.exe`).
   The script refuses an exe that contains `PIKMIN_RANDOMIZER_TEST_SCRIPT`.
2. Run, from the repository root:

   ```
   python scripts/package_release.py --version 0.28.0-playtest.1 ^
       --python-embed C:\Downloads\python-3.12.10-embed-amd64.zip ^
       --tk-source C:\Python312 ^
       --seed path\to\seed.json
   ```

   `--exe` and `--dlls` default to the build directory (`SDL2.dll`, `libwinpthread-1.dll` next to the exe).
   `--seed` is optional and lands in `seeds/seed.json`, which `Play.cmd` uses when no seed is dragged onto it.

3. The script fails if the package would contain `*.pdb`, `*session.json`, `native.log`, `__pycache__`,
   or a text file mentioning `C:\Users\`. Fix the source, do not edit the zip.

### Bundled Python runtime

Download the **Windows embeddable package (64-bit)** for Python 3.12 from
<https://www.python.org/downloads/windows/> and pass the zip as `--python-embed`. The script extracts it to
`runtime/`, edits `python312._pth` to add `..` (the package root, so `randomizer` imports) and `import site`,
and vendors the pure-Python `websockets` wheel into `runtime/Lib/site-packages` via `pip download`.

The embeddable package has no tkinter. Point `--tk-source` at a full CPython 3.12 install of the same
minor version (a python.org installer directory such as `C:\Python312` or
`%LOCALAPPDATA%\Programs\Python\Python312`); the script copies `Lib/tkinter`, `DLLs/_tkinter.pyd`,
`tcl86t.dll`, `tk86t.dll`, `zlib1.dll` if present, and the `tcl/` directory. Without `--tk-source` the package
still runs the game, but the overlay HUD and F8 tracker are unavailable to players using the bundled runtime;
the script prints a warning. The Microsoft Store Python is not a usable `--tk-source` because its files live
in a protected app package; use a python.org installer.

Without `--python-embed` the package relies on a system Python 3.12+ (`py -3.12`, then `python`), which
must have `websockets` installed for AP mode.

## Player installation

1. Extract the zip anywhere (paths with spaces are fine). Do not put anything else inside the folder.
2. Copy the seed (`seed.json`) into `seeds\`, or drag it onto `Play.cmd`.
3. Run `Play.cmd`. On first launch it asks for the extracted game assets folder (the one containing
   `dataDir\stages`) and remembers it. For AP seeds it asks for the server `host:port` and whether the
   room has a password; the password is passed only to the runner process and never saved.
4. `Play.cmd --reset-assets` forgets the asset folder; `--server host:port` and `--assets dir` skip prompts.

## Where things live

| What | Path |
| --- | --- |
| Settings (assets folder, last server) | `%APPDATA%\PikminRandomizer\config.json` |
| Sessions, one per seed | `%APPDATA%\PikminRandomizer\sessions\<16 hex of seed fingerprint>\` |
| Game logs | `<session>\runs\<token>\native.log` |
| Legacy sessions | a `session` folder next to the seed file is used if it already exists |

Nothing is written inside the extracted package folder, so it can be replaced by a newer version
without losing sessions.

## Bundling a python.org runtime

Install Python 3.12 from python.org (keep "tcl/tk and IDLE" selected), then pass its folder:

```bash
python scripts/package_release.py --version <version> --python-install "C:\Users\<you>\AppData\Local\Programs\Python\Python312"
```

The packager copies python.exe/pythonw.exe, the interpreter DLLs, `DLLs`, `Lib` (without site-packages, tests, IDLE), `tcl`, vendors `websockets`, writes a `._pth` that pins the search path to the copy, and self-checks `import tkinter, websockets` with the bundled interpreter. `--python-embed` remains available for the embeddable zip. `bin/nectar-launcher.exe` (the engine's installer, built from the `pikmin_launcher` CMake target) is packaged automatically when it sits next to `nectar.exe`; it is what lets `Play.cmd` extract game data from a disc image.

## What the package must carry

`nectar.exe` and `nectar-launcher.exe` are MinGW builds and import `libgcc_s_seh-1.dll` and `libstdc++-6.dll` as well as `SDL2.dll` and `libwinpthread-1.dll`. The packager copies all four from beside the exe, falling back to the MinGW `bin` folder (override with the `MINGW_BIN` environment variable) for the GCC runtime, and the audit refuses a package whose executables reference a non-system DLL that is not in `bin/`. This was found by launching the package with a bare `PATH`; every earlier local test had the toolchain on `PATH` and hid it.

The python.org install manager (Python 3.14) places installs under `AppData/Local/Python/pythoncore-3.14-64` and ships Tcl 9 inside the DLLs with no `tcl` folder; `--python-install` accepts that layout. Play.cmd quotes the bundled interpreter path so the package works from folders with spaces.
