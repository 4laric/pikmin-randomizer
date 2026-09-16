# Guarded manual one-trip QA handoff (#135)

`scripts/prepare_pikmin2_manual_qa.py` prepares fixed executable/DLL copies and a
source-bound command for the existing manual entrance → cave → entrance profile.
It does not automate F6, play the cave, or modify the native build. Preparation
requires a new directory; the identity change in #185 requires a new session.

## Prepare and launch

Create a local JSON config with `surface_exe`, `cave_exe`, and an `assets` object.
The assets object requires `assets`, `source_import`, `pocket`, `treasure`, `pod1`,
`pod2`, `purple`, and `imported`. Optional keys are `transitions`, `snow`, `roster`,
and `transition_assets`. Values are existing local paths; use absolute paths for
an unambiguous handoff. No native executable is built by this helper. If a new
fixture is needed, the integration owner must first use the isolated fixture
builder and hand off its provenance separately.

```powershell
py -3.12 -m scripts.prepare_pikmin2_manual_qa prepare --config output/config.json --output output/manual-qa-01 --objdump C:/msys64/mingw64/bin/objdump.exe --dll-root C:/msys64/mingw64/bin --system-directory C:/Windows/System32
py -3.12 -m scripts.prepare_pikmin2_manual_qa check output/manual-qa-01/qa-launch.json
py -3.12 -m scripts.prepare_pikmin2_manual_qa launch output/manual-qa-01/qa-launch.json
```

Run from the preparing checkout. `check` is read-only. `launch` repeats the guards
and runs the recorded command with that checkout as its working directory. The
manifest contains the complete argv array, exact input paths, all asset file
hashes, Python executable identity, Python source file hashes, and runtime file
manifests. Each runtime directory also records copied binary origins and hashes.
Source, asset, runtime, command, or interpreter changes are refused before launch.
An existing session is refused and preserved: this helper is for a fresh QA trip,
not a resume frontend. The underlying one-trip launcher remains responsible for
boundary saves and recovery; retain its recorded command and original inputs.

Hashes detect accidental drift, not hostile manifest rewriting. Python source
hashes cover `.py` files under `scripts`, `experimental`, and `randomizer`, not
every interpreter package or OS dependency. This is not a portable standalone
installer: runtime DLLs are copied, but the Python checkout and asset directories
remain external dependencies and must stay at their recorded paths. Moving the
package or changing those inputs requires preparation into a new output directory.
Windows Store Python records the launch alias and the package executable hash.

## Recorded handoff, 2026-09-12

Base: `d48eaac` (advanced from the initially reserved `75fbc45` at lead request).
Private checkout: `C:/Users/alari/pikmin-randomizer/output/p2-manual-qa-bundle`.
Prepared manifest: `output/manual-qa-01/qa-launch.json`; the `session` directory
does not yet exist. The two copied executable identities are:

| Role | Origin | SHA-256 |
| --- | --- | --- |
| Historical manual entrance | `output/p2-lifecycle-batch/manual-entrance/manual.exe` | `7bfcf482f81ea18d68835e97a2268f51d3b4281d8cfcbdae6e684b49ceaa60f8` |
| Latest production cave | `native/build-randomizer/bin/nectar.exe` | `43b55203a770dfb26565bdfdf773ba7980a9d68c81a63e4822c81d6e249b535c` |

Origins are relative to `C:/Users/alari/pikmin-randomizer`. The lead identified
the cave executable as its completed native `156cbefa` production build; this
worker verified binary hashes during inspection/copy, not historical compilation.
The historical manual executable is intentionally not presented as the latest
native build. Both private runtime folders contain their resolved DLL closure.

The local config used Kimi's recorded input paths from
`output/qa/2026-09-12-run1/provenance.json`, `asset_args`, with the executable
origins above. Thus the inputs are reproducible without committing disc assets.
The new launcher source includes the #185 identity fix; no historical session
or historical content identity was reused.

Validation: 14 tests passed across the new guard tests and existing DLL bundler
tests. The real prepare and check commands passed. The real one-trip `play()`
staging path also passed in a separate `output/staging-check` directory with its
process callback replaced by a recorder returning 0: exactly one intended surface
launch was recorded, and zero native processes were started. This validates the
argument profile and staging, not native startup or gameplay. The actual handoff
session remains fresh. Evidence is local `output/staging-evidence.json`.

Physical F6 at the entrance, normal cave gameplay, floor transitions, geyser
return, and gameplay acceptance remain with Kimi/the user. The existing bounded
prototype warning still applies, including its fence, boundary-only saves, and
maximum 20 returned survivors. No assets, binaries, manifests, or saves are shipped
in this source commit.
