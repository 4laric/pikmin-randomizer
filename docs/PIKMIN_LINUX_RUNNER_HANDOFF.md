# Pikmin private Linux runner handoff

2026-10-01. Tracking: [#1112](https://github.com/4laric/pikmin-randomizer/issues/1112).
Implementation owner: Codex through shared GitHub account `4laric`.

The coordination lead reports an existing Ubuntu 26.04.1 x86-64 host with 8 vCPUs,
16 GiB RAM and about 287 GiB free. These are reported host observations, not an
independent benchmark. The Bloodborne chat owns baseline installation, accounts,
configuration and upload. This handoff performed only local read-only inventory
and source/CI review: no provisioning, transfer, build or runtime.

The earlier 8-vCPU/32-GiB/240-GB proposal was an unmeasured estimate and is
superseded by the actual host report. Start with one admitted heavy job, initially
four compiler workers. Concurrent Bloodborne/Pikmin builds require measured
aggregate memory headroom. Linux compilation and package smoke have evidence;
Linux gameplay, saving and software rendering remain unvalidated.

## Source baseline and acceptance boundary

- Root documentation base: `9cae7fd5a20e0f0cac470ef4d340563ca6a12bf8`.
- Accepted native main supplied by integration:
  `77b4c8922cb7740ca2ea182429b4196f1be46b8b`.
- Integration subsequently completed root export
  [PR #1113](https://github.com/4laric/pikmin-randomizer/pull/1113), merged as
  `89da5c3e574b6ab3fd125d820b27876bea159075`, with clean native production
  `54743e12003888891d4dc3de249214cb18627fa6` and 4,017 byte-exact exported files.
  Prefer that root delivery for source setup. Its local Release/no-work and
  bounded captain checks are Windows evidence. Native main `77b4c892` includes
  a later White fixture not yet included in that export: record which native
  source the Linux job actually compiles. Do not silently substitute a dirty checkout.
- Co-op native PR #103 is a separate line with Linux repairs underway; it is not
  the initial P2-main baseline.

Native source is in
[Open Nectar](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port).
On this Windows machine native `origin` points to a local research checkout;
the GitHub remote is `fork`. Use the GitHub repository explicitly on Linux.
Record full root/native revisions, submodules, dirty state and guard-header hash
for every job. Export acceptance and Windows gameplay acceptance do not transfer
to a new Linux executable.

## Actual private inputs

All measurements below were made locally on 2026-10-01. Bytes are logical file
sizes unless labelled otherwise. Keep game data private and outside Git/artifacts
published by CI.

| Input | Authoritative local path | Bytes | Fingerprint / use |
| --- | --- | ---: | --- |
| P2 original | `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso` | 995,557,376 | SHA-256 `5388b54a9c2d156c94bcfa80acd53b513288dc17e88c97a1edfb57ad25db661a`; GPVE01 revision 0 |
| P1 source RVZ | `C:/Users/alari/Downloads/Pikmin (USA) (Rev 1) (1)/Pikmin (USA) (Rev 1).rvz` | 555,216,756 | SHA-256 `eaa3ffd15c8138c964237b06f628461de1e7ddf01f483da6e457debbc14a6598`; optional original for reproducibility |
| P1 prepared ZIP | `C:/Users/alari/AppData/Roaming/PikminRandomizer/game-data/assets.zip` | 559,375,195 | SHA-256 `8f21264e5df9671008bc2d1a11dff446b72a2d567b1624f96b9c796ab0e3e215` |
| P1 installed tree | Same `game-data/assets` directory | 661,389,111 | 3,497 files; every member matches the prepared ZIP |
| Selected P2 cache | `C:/Users/alari/pikmin-randomizer/output/p2-content-cache` | 130,365,357 | 6,159 files across ten named families; completeness and Linux consumer compatibility not established |

The P2 disc's FST was read using `experimental.pikmin2_assets.disc_files`: 2,768
members, 990,126,724 member bytes. The staged `assets/disc` ISO is byte-identical
but occupies a separate local file: send only one copy. The P1 source ZIP contains
the same RVZ and is redundant when that RVZ is retained. No uncompressed P1 ISO
was found in bounded known locations; the existing RVZ and prepared assets are
available inputs.

The older `C:/Users/alari/bbft/dist/cohesion/pikmin/assets` is a different snapshot:
3,589 files / 665,035,819 bytes. There are 3,495 equal shared paths, a differing
`stage1/default.gen`, one installed-only path and 93 older-only paths. Do not
substitute it for the installed snapshot.

`output/workflow/asset-inputs.json` and the historical
`output/pikmin2-runtime/pikmin2-source-test.iso` are currently absent. The old
1,000,762,688-byte ISO claim is stale, not evidence that current sources are
missing. This audit preserved the canonical inventory location and wrote fresh
private evidence instead.

P1 ZIP + one P2 ISO + selected uncompressed P2 cache total **1,685,297,928 bytes**
(1.57 GiB). Expanded P1 + P2 ISO + cache total **1,787,311,844 bytes** (1.66 GiB).
Retaining both ZIP and expansion adds the ZIP size; retaining the optional RVZ
adds 555,216,756 bytes. These are input sizes, not a complete runner disk budget.
NTFS allocation for the P1 installed tree is 666,603,648 bytes and selected P2
cache 145,910,688 bytes; Linux allocation will differ. No directory junctions
were traversed in measured trees; file identity accounting avoids double-counting
hard links. Identical independent copies still consume separate local space.

## Linux build coverage and first job

The pinned native `.github/workflows/linux.yml` uses Ubuntu 22.04 with `cmake`,
`pkg-config`, `binutils`, `libsdl2-dev` and `libgl1-mesa-dev`, then invokes
`packaging/linux/package-standalone.sh --clean`. The host's newer Ubuntu/toolchain
needs its own result. Record compiler, linker, CMake, Ninja and Python versions;
the root workflow tooling currently uses Python 3.12 locally.

The package script builds NTSC and PAL in Release with
`PIKMIN_NATIVE_OPTIMIZE=OFF`, `PIKMIN_ENABLE_IPO=ON`, and
`PIKMIN_NATIVE_JAUDIO=ON`. A successful prior
[Linux CI run](https://github.com/4laric/Open-Nectar---Pikmin-Native-PC-Port/actions/runs/36864637049)
at `d703218cae578376338fd292aed8477949a661b4` used GNU 11.4, passed 239/239
CTests in 0.89 seconds and spent 719 seconds in the combined package step.
Its 18,466,352-byte compressed artifact is a distribution size, not build storage
or peak RAM. Independent follow-up confirmed exact-main Windows run
`36866194132` passed, while Linux run `36866194148` was still running and its
clean-distro job had not started. Producer
`cbb86fe65411cbfb92f3f5033a85d13c5d91643e` has green Windows `36863875425` and
Linux `36863875702` / `36863770750`. Preserve the distinction and recheck exact
main before the first host job.

Before configuring, provide `P2_CHALLENGE_GUARD_INCLUDE_DIR` explicitly, pointing
to the pinned root `scripts` directory containing the challenge guard header.
Use a private native checkout and private build directory. The initial compile
should cap parallelism at `-j4`; an admitted full build precedes CTest, and
`ninja -C <build> -n` records the no-work result after completion. Build the
registered captain/Purple runtime fixture targets explicitly: they are
`EXCLUDE_FROM_ALL` and Linux packaging does not currently build them. Windows CI
does explicitly build/package these fixtures. A compile-only runtime object
target is not a successful gameplay run.

The root base above contains `scripts/p2_fixture_captain_guard.h`, Git blob
`47b99b7bfd43310c35a7815d46d4f8591b21f573`; PR #1113 is not required for that
header or direct compilation. After the setup owner provisions dependencies and
grants one heavy-job lease, these commands describe the initial job. Variables
must refer to pinned private checkouts, an exclusively owned build directory and
its evidence directory. Capture cgroup memory peaks separately and stop on failure.
Commands have not been executed on Linux by this audit.

```bash
set -euo pipefail
test -f "$ROOT/scripts/p2_fixture_captain_guard.h"
mkdir -p "$EVIDENCE"
cmake -S "$NATIVE" -B "$BUILD" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ \
  -DPIKMIN_NATIVE_OPTIMIZE=OFF -DPIKMIN_ENABLE_IPO=ON -DPIKMIN_NATIVE_JAUDIO=ON \
  -DP2_CHALLENGE_GUARD_INCLUDE_DIR="$ROOT/scripts" \
  2>&1 | tee "$EVIDENCE/configure.log"
/usr/bin/time -v -o "$EVIDENCE/build-time.txt" \
  cmake --build "$BUILD" --target pikmin_pc -j4 \
  2>&1 | tee "$EVIDENCE/build.log"
cmake --build "$BUILD" -j4 2>&1 | tee "$EVIDENCE/offline-build.log"
ctest --test-dir "$BUILD" --output-on-failure --timeout 300 \
  2>&1 | tee "$EVIDENCE/ctest.log"
cmake --build "$BUILD" --target \
  pikmin_ci_fixture_captain_switch pikmin_ci_fixture_purple_combat \
  pikmin_ci_fixture_captain_reentry pikmin_ci_fixture_captain_campaign_resume \
  -j4 2>&1 | tee "$EVIDENCE/fixture-build.log"
cmake --build "$BUILD" --target pikmin_pc \
  pikmin_ci_fixture_captain_switch pikmin_ci_fixture_purple_combat \
  pikmin_ci_fixture_captain_reentry pikmin_ci_fixture_captain_campaign_resume \
  -- -n 2>&1 | tee "$EVIDENCE/no-work.log"
sha256sum "$BUILD/bin/nectar" "$BUILD"/fixtures/pikmin_ci_fixture_* \
  > "$EVIDENCE/executable-hashes.txt"
du -sb "$BUILD" > "$EVIDENCE/build-size.txt"
```

The configured challenge guard also enables `p2_challenge_mode_fixture` and
`p2_challenge_boot_fixture`; standalone native CI without root scripts skips
these. Do not require an invariant 239-test count when enabling additional tests.

Do not invoke the packaging script unrestricted on the shared host: it uses
`nproc`. Its `--build-dir` isolates the primary build/stage only; PAL build and
package output remain fixed within the source checkout, and `--clean` removes
them. A packaging job needs a wholly private checkout and exclusive ownership of
primary, PAL and output paths, plus an enforced CPU budget or reviewed parallelism
override.

The clean Debian 12 smoke installs GL runtime dependencies and exercises
`nectar-launcher --help` and loader dependency resolution. It proves neither
window creation nor input, save/resume, imported assets or rendering correctness.

## Private data layout and job boundaries

Suggested host layout, to be implemented by the setup owner:

```text
private/originals/<game>/<sha256>/       immutable original ISO/RVZ
private/prepared/<manifest-sha256>/     immutable P1 snapshot / versioned P2 cache
jobs/<job-id>/source/                   pinned private checkout
jobs/<job-id>/build/                    exclusive build directory
jobs/<job-id>/runtime/                  writable overlay, settings, saves, cards
jobs/<job-id>/evidence/                 receipts, hashes, bounded logs
workflow/                              host-local registry and admission state
```

Verify remote whole-file hashes and tree manifests before accepting a transfer.
Extract P1 once to a new versioned root and verify every relative file. Derive
caches under keys containing input hashes, converter commit and options; publish
only after validation. Never write runtime settings, generated stages or saves
through hard links into immutable inputs. Writable files require copies or
copy-on-write overlays; read-only links require platform/stager validation.
Every isolated job gets a fresh seed/session path and private cwd. Save/resume
attempts use fresh run directories while retaining that job's fingerprint-bound
session and card. Do not import shared Windows saves or relink Archipelago.

## Admission, measurements and bounded acceptance

Use one enforceable per-host heavy-work budget shared by Bloodborne and Pikmin.
Do not copy Windows live PIDs/leases or network-share SQLite. Retain exclusive
directory ownership and exact PID/start-time identities. Existing workflow
process identity and memory readers have Linux support; provider recovery and
terminal cleanup still contain PowerShell/CIM seams. Review those paths before
enabling automatic Linux dispatch/recovery.

The local Windows controller's 2–4 heavy-job policy is not an entitlement on this
16-GiB host. Begin at one heavy job with four compile workers, no overlapping
Bloodborne build. Measure clean and incremental builds separately with
`/usr/bin/time -v`, plus cgroup `memory.peak`/`memory.events`: maximum individual
process RSS alone does not measure simultaneous compiler memory. Record host free
RAM, swap/OOM events, CPU time, elapsed time, and separate source/build/cache/stage
disk peaks. No Linux build peak or build-tree footprint was established here.
The Windows 32-GB-class whole-host memory snapshot is not a build benchmark.

Measure Bloodborne independently before testing overlap. Admission limits must
leave OS/service headroom and account for both measured peaks. Cgroups, timeout,
PID limits and owned process-group cleanup are proposed controls, not an already
deployed shared scheduler. Stop admission on OOM or unresolved resource pressure.

Future gameplay acceptance needs these ports first:

- `build_pikmin2_fixture.py` assumes MinGW response/import-library semantics;
  use registered Linux CMake targets and fresh ELF/link provenance.
- `run_pikmin2_fixture.py` assumes MinGW DLL hashes and Windows PATH; add
  platform-specific dependency evidence.
- `run_pikmin2_cave_fixture.py` uses `_winapi.CreateJunction`; validate Linux
  staging, file links, font paths and case-sensitive asset lookup.
- Manual PowerShell launchers need Linux equivalents with private saves,
  scoped environment and cleanup restricted to the owned process group.

After those ports, regenerate arenas with the current starting-Pikmin overlay,
20-red baseline where applicable, and 960×540 centred startup as required by
[the fixture contract](PIKMIN2_IMPLEMENTATION_FANOUT.md). Use bounded 60-second
fixture attempts with actual renderer/version recorded and negative captain-down
checks. Xvfb/Mesa llvmpipe/software GL are candidates requiring validation.
Switch/move/camera, ordinary save, restart and repeated resume remain separate
acceptance gates. Do not increase timeouts silently to turn failures into passes.

## Storage, retention and handoff evidence

Bloodborne's chat reports about 29.24 GiB of originals; this audit did not
independently measure those files. Combine that with the measured Pikmin inputs,
then add retained archives, actual source/build/package peaks and active job
copies. The reported 287-GiB free capacity is not a validated concurrency budget.

Proposed initial retention: immutable originals are never automatic cleanup
targets; retain versioned prepared caches while referenced. Keep successful job
logs/receipts seven days, failed jobs fourteen days, and pinned acceptance receipts
until explicitly superseded. Use an initial 20-GiB disposable job/evidence cap and
stop admission below 20% free disk, both provisional operating choices for the
setup owner. Remove only completed, unleased, unpinned job directories. Hash and
retain small receipts before pruning bulky failed arenas; do not archive game
assets inside logs or public build artifacts.

Private Windows evidence is under `output/linux-runner-1112/` (not committed):

- `assets/findings-01.json`, SHA-256
  `2d6bc5caa5bd62e29f9873f1831ef11a7acc0ed8a494d1c5b681beb85ea4bfc9`;
  contains full source fingerprints, per-tree manifest hashes and duplicate accounting.
- `assets/inventory-01.json`, SHA-256
  `c452d2fb739f461e290a94c9e88b0b84e6d906873893c6a7f3ad00a8b5879476`.
- `linux/update-host-and-commands.md` supersedes the audit's earlier host status
  and records exact-main versus producer CI plus the guard-header pin.
- `linux/audit.md`, pinned workflow/package snapshots, `source-blobs.json`, CI
  excerpts and `hashes.json` distinguish observed CI evidence from proposals.

Next owner action: accept the selected input manifest and source pins, integrate
this handoff with Bloodborne's setup, then run one instrumented Linux compile and
offline test job. Linux runtime porting needs its own issue, acceptance criteria
and resource admission. This documentation does not authorize concurrent setup
or imply that any remote test has already run.
