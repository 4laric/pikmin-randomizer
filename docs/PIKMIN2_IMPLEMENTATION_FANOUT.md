# P2 implementation fan-out and mandatory fixture baseline

Agent entrypoint, 2026-09-13. Documentation tracking: #404. Coordination and
shared-semantics review: #186. Implementation owner: Codex through shared GitHub
account `4laric`; assignment alone does not identify a lane or activate work.

Execution update, 2026-09-15: use [the workflow operating contract](PIKMIN2_WORKFLOW.md)
for durable lane records, watchdog actions, resource leases, handoff validation
and integration metrics. Its current policy supersedes historical reservations.

Read this before claiming or resuming a P2 implementation slice. Follow
[AGENTS.md](../AGENTS.md), [the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md),
[blockers](PIKMIN2_FULL_IMPL_BLOCKERS.md), and
[family status](PIKMIN2_FAMILY_STATUS.md). This guide defines dispatch and fixture
requirements; it does not reassign existing owners or authorize duplicate work.

## Mandatory first action: adopt the current test fixture

### Verify local source availability before declaring assets missing

On this host, consult the canonical workspace's
`output/workflow/asset-inputs.json` before reporting missing legal/source assets.
The inventory records the local P2 disc, all 2,768 disc members with offsets and
sizes, hash-verified Forest/Yakushima cave data and Demon model/animation bytes,
and the existing P1 runtime asset directory. Recheck the actual paths and relevant
bytes using `experimental.pikmin2_assets.disc_files`; stale inventory metadata is
not proof of absence or availability. The disc is currently at
`C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`; runtime assets are at
`C:/Users/alari/AppData/Roaming/PikminRandomizer/game-data/assets`.

Distinguish missing raw source bytes from unfinished extraction, decompression,
conversion, geometry decoding, staging, source integration and runtime support.
Those engineering gaps need concrete owned work, not a request for the user to
provide assets already present. Record exact missing members, searched roots and
failed reads before claiming an external asset dependency. Use private output for
derived data and preserve the source disc and shared asset installation. Raw
asset presence never establishes runtime readiness or clears gameplay gates.

Every new AND already-running lane must refresh its fixture baseline before its
next runtime acceptance run. Old generated arenas and old executables do not
acquire these changes automatically. Report adoption in the lane's child issue.

| Component | Required behavior | Known introducing revision |
|---|---|---|
| Root `scripts/preview_pikmin2_room.py` | `overlay()` calls `ensure_pikmin_squad()` for the supported `dataDir/stages/chal0/default.gen` override, adding 20 red Pikmin when no Pikmin record exists | Root `a51b301` |
| Native `pc_port/pc_main.cpp` | Experimental-room startup defaults to a 960×540 window and calls `pc_window_center()` after loading persisted settings | Native `1d5a242b`; root source export `541bfba` |

These are minimum capability markers, not a request to reset to old commits.
Use the newest integration-approved source containing both changes and all
current lane dependencies. Record exact root/native commits and dirty state.
Check your own worktree, not just the maintained checkout. Preserve ongoing work
when merging/rebasing; equivalent cherry-picked changes require source evidence
because ancestry alone will not identify them.

1. Refresh the root overlay script and the lane's native source. Inspect inherited
   scripts for original absolute paths before executing them.
2. Regenerate the arena into a NEW private `output/` directory with the current
   family arena runner using the current `preview_pikmin2_room.overlay()`.
   Existing Pikmin generators are preserved; the helper does not top up an
   existing squad. Unsupported/custom stage formats or runners bypassing this
   overlay need an explicit equivalent starting squad and their own evidence.
3. Confirm the generated stage has live starting Pikmin in valid positions.
   The default added squad is 20 reds. This prevents immediate zero-Pikmin
   extinction at startup; it does not disable extinction during gameplay.
   Check terrain/placement for the lane's arena and document any override.
4. Build the lane's current native source in its private build directory. Set
   `$env:PIKMIN_P2_ROOM_WINDOW='960x540'` for the standard acceptance launch and
   use the experimental-room entrypoint. Do not inherit `off` or `0`, fullscreen
   settings, or a stale executable. Other dimensions are for explicitly recorded
   observation needs, not the standard default.
5. Observe a 960×540 centred window, a live squad, and entry into active gameplay
   without the immediate extinction screen. Standard startup logs should include
   `Experimental preview window set to 960x540 windowed and centered`.
   Capture the log and window/squad evidence in the private run directory.

**Custom C++ fixtures need special attention:** the fixture builder replaces the
production main object. A fixture with its own startup is not guaranteed to run
`pc_main.cpp` window setup. Its owner must verify equivalent window sizing and
centring in that entrypoint and record observed evidence. An environment variable
alone cannot add the behavior to an old or custom executable.

**Guarded cave boots must use wall-clock supervision (#671).** Run the canonical
`scripts/run_pikmin2_cave_fixture.py --exe <private-exe> --source-run <old-run>
--run-dir <new-private-run> --timeout 60` instead of launching an unbounded raw
fixture or relying on its frame counter. The runner preserves input files,
creates a separate overlay with readable files and valid directory junctions,
streams `native.log`, kills its own child on timeout, and writes `run-result.json`.
Keep `run-inputs.json` with the executable and input hashes. Never construct a
directory junction to an ordinary file: this made `consFont.bti` unreadable and
crashed real startup in `Font::setTexture` despite green guard self-tests.

The historical Yakushima arena also disagreed with its 20-survivor checkpoint.
Regenerate the lane arena using the current squad baseline before acceptance;
do not weaken the checkpoint count check. `--baseline-assets <legal-P1-assets>`
explicitly regenerates the standard 20-Pikmin arena for a **boot smoke test only**.
It replaces lane placement and cannot establish cave geometry, collision or
gameplay acceptance. The same bounded runner with
`P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN=1` must produce raw exit 86 and
`P2_FIXTURE_CAPTAIN_DOWN` with no boot PASS. Window creation and engine-independent
guard tests alone do not establish a working boot.

**Other native fixtures also require a bounded runtime launch (#701/#702).**
Use `py -3.12 scripts/run_pikmin2_fixture.py --exe <private-exe> --run-dir
<fresh-staged-private-arena> --arg=--experimental-pikmin2-room --pass-marker
"<fixture-specific PASS marker>" --timeout 60` from the canonical checkout.
Use the fixture's actual arguments (for example `--arg=--experimental-challenge-level
--arg=1`). The runner validates readable boot assets/runtime DLLs, preserves cwd,
records hashes and kills only its own fixture child on timeout. Stage the correct
arena before launching; an empty directory is not a runtime input package.
Do not use a build supervisor for runtime: `leased_run.py` sets cwd to the source
worktree, discarding the selected arena. Runtime needs no build lease. A window
stuck in `System::Initialise`/`pumpAudio` is not gameplay progress; preserve its
failure logs and correct inputs before a fresh attempt.

If a window is already stuck at extinction, retire that run, regenerate its arena
and relaunch the updated executable. Do not use an extinction-screen screenshot
as gameplay evidence or alter production extinction semantics to bypass it.
Keep independent QA bundles immutable; create a new version and hand it off.

Required adoption comment (fill every field; do not claim PASS from source alone):

```text
Fixture baseline adoption
Child issue / lane / implementation owner:
Root commit + dirty state / overlay source:
Native commit + dirty state / worktree / private build directory:
Squad change present / window change present (ancestry or source evidence):
Fresh arena command / run directory / asset and config hashes:
Executable SHA-256 / fixture provenance status if applicable:
Window setting / observed size and centring evidence:
Live starting Pikmin / active gameplay / no immediate extinction evidence:
PASS, FAIL, or BLOCKED; remaining work:
```

The coordinator maintains an adoption checklist for ALL active lanes in #186.
An existing lane's next handoff is incomplete without this record. A document
link or commit acknowledgement is not runtime adoption evidence.

## Dispatch by shared blockers and bounded species

One owner per family or explicitly separated FSM/resource group. Keep variants
sharing a base module together. Claim an assigned child issue before edits with
exact identities, target evidence level, owned files, dependencies, requested
shared hooks, and observable acceptance criteria. Check existing owners first.

| Lane | First bounded deliverable | Ownership boundary |
|---|---|---|
| Converter / animation (#128) | Reproduce Pelplant conversion failure, fix one bounded capability, list the actual clips/species unlocked | Shared semantics reviewed through #186; separate fidelity polish from conversion correctness |
| Receivers (#170) | Explain FireOtakara's accepted-but-zero-damage attack; prove valid damage, immunity and death paths | Dweevil owner implements family behavior; generic routing changes receive focused review |
| Lifecycle / acceptance (#397) | Non-invincible fixture observes death, forget/reset and re-entry with no stale references or duplicate rewards | Own reusable fixture infrastructure; family owners implement their actor cleanup |
| Species behavior | One species with available assets: source FSM, animation-driven attack, receivers, death and delivery or source-backed N/A | Expand its shared base/variants after the first complete gameplay slice |
| Projectiles (#169) | One birth → motion/homing → collision → damage → destruction path, including interruption and teardown | Coordinate consumers in Cannon, BombSarai and Man-at-Legs; preserve Groink ownership and any parked status |
| Existing mechanics completion | One outstanding runtime gate in an existing P2-mechanics lane | Existing Bulblax, captor and scavenger owners continue; do not duplicate their modules |

At limited capacity, prioritize receivers, lifecycle, one species implementation,
and converter work. Integration remains a separate maintained-build/export role.
This table is a proposed work split, not an assertion that all lanes are staffed.
Jellyfloat install/arena can be a bounded additional slice when an owner is free;
bosses need explicit helper/receiver lifetime contracts before gameplay integration.

## Sequence and acceptance

First milestone: two species executing source behavior and passing applicable
arena gates together, with proven receiver and lifecycle paths. Build a reference
species while removing concrete receiver/lifecycle failures. Extract shared
services from demonstrated needs; do not make a universal AI framework a prerequisite.

Then expand by independent FSM/resource groups. Each implementation maps source
states, motion timing and events, including loop boundaries and interruptions.
Record event ownership, immunities, helper/attachment lifetimes and exactly-once
drops/rewards. Event metadata or sampled poses alone do not execute source behavior.

Each handoff reports the six arena gates as PASS / FAIL / BLOCKED / UNTESTED /
source-backed N/A, with evidence paths:

1. Exact identity and spawn.
2. Autonomous movement and animation.
3. Attacks and receivers.
4. Death and corpse.
5. Actual transport and reward.
6. Cleanup and re-entry.

Label injected state/health separately from natural combat. Manager recreation
does not prove full scene teardown or campaign resume. A starting squad does not
fix invincible proxies. Begin mixed-scene correctness, frame-time and memory
measurements with the first two implemented species; establish explicit budgets
with integration before scaling density. Family complete still requires every
parent identity and all applicable gates, including mixed-scene performance.

Before dispatch, reconcile status against pinned evidence and register the actual
lane in the local workflow registry. The old blocker document is historical;
King WarCry is passed. Scope only remaining unproven behavior and do not dispatch
duplicate cleanup/FSM work from stale blanket summaries.

## Private builds and reviewable handoffs

Use a lane-owned native worktree and build directory under ignored `output/`.
Do not edit/build the shared native checkout for exploratory lane work. Example
from the repository root, after creating the lane worktree:

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake -S output/native-<lane> -B output/native-<lane>-build -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++
cmake --build output/native-<lane>-build --target pikmin_pc -j 6
cmake --build output/native-<lane>-build --target pikmin_pc -- -n
```

Replace placeholders. Record pinned commit, private build directory, executable
SHA-256 and the no-work dry-run result for each attempt. Never run two heavy jobs
against one build directory. Use resource leases for private builds and the
aggregate heavy-build budget. Shared runtime fixtures require the shared-runtime
lease; private runtime launches are exempt from that reservation.

For replacement-main fixtures, use [the provenance builder](PIKMIN2_FIXTURE_BUILDS.md)
against that completed PRIVATE build:

```powershell
py -3.12 scripts/build_pikmin2_fixture.py --source output/native-<lane> --build output/native-<lane>-build --fixture <fixture.cpp> --expected-native-head <full-native-commit> --output output/<lane>-fixture-<attempt>
```

Run only an attempt whose `provenance.json` status is `built`. Freshness rejection
requires resolving inputs and rebuilding; a produced executable alone is insufficient.
The builder does not launch, stage assets, or supply the starting squad/window policy.

Cap each worker at one active implementation slice and one ready handoff. Each
handoff includes parent/child issue, owner, exact base and ordered commits, owned
files, requested shared hooks, source mapping, tests, build provenance, fixture
adoption record, gate evidence and remaining work. Isolate shared-semantics edits
into focused commits. Update the issue with progress and integrated commits.

Family owners can implement narrow additive registration hooks. Saves/rewards,
captain state, generic damage/physics, actor lifetime, converter defaults and ID
conflicts require #186 review. Only integration builds `native/build-randomizer`
after integration and runs `scripts/export_native_source.py`. Native origin pushes
follow [AGENTS.md](../AGENTS.md#git-push-policy); main/default and p2-integration
branches remain protected. Keep assets, builds, logs, saves and runtime state local under `output/`;
do not modify the parallel original BBFT or decomp/research checkouts or relink AP.

## Mandatory captain safety (#632; active lanes included)

Before the next runtime run, add the fixture-only canonical helper
`scripts/p2_fixture_captain_guard.h` (absolute include or hash-recorded local copy),
or an equivalent tested guard. It never changes health or production behavior.
Once the captain has initialized, call the guard immediately after the engine
idle step and BEFORE movie/pause/UI early returns, readiness gates, observation
counters, or PASS markers. Check all three independent signals:

```cpp
Navi* n = naviMgr ? naviMgr->getNavi() : nullptr;
if (n) {
    p2_fixture_require_captain(GameStat::orimaDead,
        n->getCurrState() && n->getCurrState()->getID() == NAVISTATE_Dead,
        n->mHealth, observed);
}
// Only now process pause/movie/UI and increment observed ticks.
```

Include the pinned engine's GameStat/Navi/NaviState declarations. This helper
prints P2_FIXTURE_CAPTAIN_DOWN and exits 86 (BLOCKED), including nonfinite HP.
Do not skip death checks just because a movie or pause is active. An initialized
captain disappearing unexpectedly likewise blocks observation, rather than
counting ticks. A timeout alone does not explain whether gameplay advanced.

Park the captain outside the tested enemy's actual attack reach for enemy death,
transport and re-entry tests where captain hits are irrelevant. Do not move him
away when captain targeting/damage is the test. Do not introduce blanket health
refills, revive/clear death flags, disable extinction, or change production rules.
Protection is permitted only as explicitly labelled fixture instrumentation for
isolated observations; record its mechanism and exclude it from captain-damage,
survival and unmodified-combat acceptance. Separate unprotected runs prove those.

Record child issue, fixture/guard hashes, placement/protection policy, rebuilt
executable hash, a negative captain-down guard test, and fresh runtime log. Existing
runs are not retroactively protected. Interrupted logs are diagnostic evidence;
mark unfinished gates BLOCKED/UNTESTED. Preserve earlier PASS evidence using its
separate original successful run. Handoff validation rejects captain-down log
references supporting PASS gates or PASS slice criteria. It does not infer safety
from absence of a marker in an old, uninstrumented fixture. Reviewers must verify
adoption before accepting fresh runtime claims. Death-specific tests may cite the
interruption as a labelled negative test, not as general gameplay completion.

For affected active lanes, the controller sets a captain-safety adoption requirement
and writes `captain-safety-required.md` in their runtime output plus an integrator
review notice. A runtime handoff must add:

```json
"captain_safety": {"policy": "unprotected", "evidence": ["guard_source", "guard_negative_test", "fresh_runtime_log"]}
```

inside `fixture_adoption`, with keys resolving to hashed handoff evidence. The
reviewer checks the source call order and each evidence role; merely supplying
keys does not prove adoption. Use `protected_observation` only for the isolated,
labelled case described above. Its attack/receiver PASS is rejected. Existing
already-submitted handoffs are not rewritten; apply the requirement before the
next run. Subsequent controller dispatches repeat the instructions explicitly.

## Preparation packets are not source implementation

A missing native hook, build registration or engine entry point needs a job that reserves the actual native files in a private native worktree, implements them, compiles/tests them and submits native commits for the existing integrator to review and merge. A job owning only documentation and a Python patch generator is preparation, even if its title says "landing" or "integration candidate". Integrating that packet does not integrate its proposed native patch and must not clear the consumer's source dependency.

The single-writer restriction protects the maintained checkout and final merge/export. It does not prohibit issue-backed, exclusively owned private native implementation. Serialize overlapping file claims; do not evade them by producing repeated packets. Record the actual executable producer lane with `workflow.blocked_followup` so verified source integration can wake its consumer. The #668 Mar registration job is an example: it owns native CMake/preview/Mar/receipt code and compiled tests, while #665 is only a preparation input.
