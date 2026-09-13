# P2 implementation fan-out and mandatory fixture baseline

Agent entrypoint, 2026-09-13. Documentation tracking: #404. Coordination and
shared-semantics review: #186. Implementation owner: Codex through shared GitHub
account `4laric`; assignment alone does not identify a lane or activate work.

Read this before claiming or resuming a P2 implementation slice. Follow
[AGENTS.md](../AGENTS.md), [the import pipeline](PIKMIN2_ENEMY_IMPORT_PIPELINE.md),
[blockers](PIKMIN2_FULL_IMPL_BLOCKERS.md), and
[family issue coordination](https://github.com/4laric/pikmin-randomizer/issues/186). This guide defines dispatch and fixture
requirements; it does not reassign existing owners or authorize duplicate work.

## Mandatory first action: adopt the current test fixture

Every new AND already-running lane must refresh its fixture baseline before its
next runtime acceptance run. Old generated arenas and old executables do not
acquire these changes automatically. Report adoption in the lane's child issue.

| Component | Required behavior | Known introducing revision |
|---|---|---|
| Root `scripts/preview_pikmin2_room.py` | `overlay()` calls `ensure_pikmin_squad()` for the supported `dataDir/stages/chal0/default.gen` override, adding 20 red Pikmin when no Pikmin record exists | Root `a51b301` |
| Native `pc_port/pc_main.cpp` | Experimental-room startup defaults to a 960×540 window and calls `pc_window_center()` after loading persisted settings | Native `1d5a242b`; root source export `541bfba` |

These are minimum capability markers, not a request to reset to old commits.
Both markers must be verified: #419 imports the overlay, while the historical
window candidate is not automatically present in every maintained engine export.
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

Before dispatch, reconcile contradictory status against pinned evidence. At this
writing, the blocker doc's blanket cleanup statement differs from batch-1 evidence
in family status, and King WarCry is listed both open and passed. Scope only the
remaining unproven behavior; do not repeat completed work based on a stale summary.

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
against one build directory. Coordinate real-GL/input fixture slots through the
integration lead; private builds do not remove runtime contention.

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
after integration and runs `scripts/export_native_source.py`. Never push native
origin. Keep assets, builds, logs, saves and runtime state local under `output/`;
do not modify the parallel original BBFT or decomp/research checkouts or relink AP.
