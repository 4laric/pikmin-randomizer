# MiniHoudai78 correlated natural generated birth — lane muse-groink handoff (l60, #500)

Implementation owner: Codex through shared GitHub account `4laric`. Executing
contributor: Muse Spark 1.3 through OpenCode
(`opencode-go/muse-spark-1.3-contributor`), lane `muse-groink`.
Parent #198; wave #491; existing integration #437/#186. Attempt
`7e167420066a496a9b785da772f3ff45`, ownership generation 2.

Scope: close gate 1 for mobile MiniHoudai78 via an actual legal generated
encounter, including the projectile corridor/helper contract. Observer plus
negative tests; placement/packaging coordination. Pedestal FminiHoudai97 is
out of scope; existing Groink modules are untouched; legacy l21 is
claim-held and read-only (inspected, never edited). Accepted
movement/combat/death/reward/reentry evidence is preserved below as history,
not relabeled as a new combined run.

## Source audit (read-only research rev 632af93787b9c95b63f0c13be32b161375ce3a96)

- MiniHoudai=78: source role, spawnable, use_own_id, day_end_max 4,
  BDT_Normal, no child birth (`docs/PIKMIN2_ENEMY_ROSTER.json`). Mobile
  Gatling Groink; `MiniHoudai::Obj` is inherited by fixed and roaming
  groinks (`docs/PIKMIN2_CANNON_GROINK_AUDIT.md`).
- FminiHoudai=97: distinct source identity sharing the bank; no dedicated
  module yet. Not touched by this lane (pedestal-97 resolve is a
  fail-closed negative in the observer).
- Projectile corridor/helper contract: MiniHoudaiShotGun pool of up to 3
  shells, radius-10 swept sphere, gravity 20, `InteractBomb` to Navi/Pikmin
  and 100 to Teki, reclaimed by `doUpdateCommon`
  (`docs/PIKMIN2_CANNON_GROINK_AUDIT.md`). **No spawnable helper birth
  exists** (`child_name` null): the helper contract is complete by audit —
  there is no helper to birth, so the encounter needs no helper marker.
  Shell volleys are a family-run gate (future MiniHoudai FSM work), not a
  placement constraint (l52). Fixture volley support is preserved history
  (`docs/PIKMIN2_GROINK_BURST.md`: 3-shell emission, 10-damage Bomb
  strikes, once-per-shell dedup; fixture-pinned placement, labeled).

## Dependency consumption (reviewed candidates only, exact order)

Root branch `codex/muse-l60-groink` (base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`):

- `d74ef4f8` — own gen-1 observer/tests/handoff (#500, prior attempt).
- `a3e916b6` — cherry-pick of `bd97334a` (muse-placement #492: candidate
  slots, `MUSE_GENERATED_SLOTS` with 78→328297937, placement observer,
  16 tests, handoff). Parents match base; no file overlap with owned
  scope; applied clean, no conflicts.
- `dc435be` — cherry-pick of `3131b76d` (muse-packaging #493: candidate
  staging, 58 family binding). Clean, no conflicts.
- `0ebc941` — cherry-pick of `f82171d` (packaging handoff doc). Clean.
- (pending commit) gen-2 observer/tests/handoff updates (#500).

Native branch `codex/muse-l60-groink-native` (base
`7b9ecaa668fd55332073446cdbdaf6424b209ea7`):

- `a319ba1` — own gen-1 headless fixture (#500).
- `bc09efc` — cherry-pick of `4765885b` (placement native #492:
  `museBind` + `P2_GENERATED_PLACEMENT` marker + registry queries for
  41/57/58/78; returns false so the family sidecar owns behavior).
  Clean, no conflicts.
- `4820e84` — own gen-2 fixture extension (runtime slot-constant
  assertions: 78→accepted uid, 97 excluded).

No wave wholesale merge; no other files touched. Ancestry checked before
each pick (`merge-base --is-ancestor` false for all four; parents equal
the lane bases).

## Natural generated encounter (product binary, real seed path)

Stager: `output/muse-wave/l60/stage_seedrun.py` (output dir, not worktree
source). Fresh private arena from the current
`scripts/preview_pikmin2_room.overlay()` (20→40-red starting squad, valid
terrain, no immediate extinction), one appended P1 Frog vehicle row
(type 0) at generator 201078 near the squad, `p2-groink-teki.txt` (short
2s/3s carcass profile), `p2-placement-slots.txt` (201078→328297937),
`bootstrap.txt` with the real deterministic layout
(`resolve_layout('muse-groink-78b','Player1',['328297937'],[78])` →
binding 78→328297937, `build_bootstrap` → `ENEMY_P2 1 a019a3ef… 1
328297937 78`; roster revision matches the native header exactly), and
the real packaging path (`stage_candidates` + `verify_staging`,
receipt `ca7fd4ad…`). Booted the private product build
`bin/nectar.exe` with `--experimental-pikmin2-room --randomizer-seed`,
hidden window, dummy audio, `PIKMIN_P2_ROOM_WINDOW=960x540`.

Labeled shaping (harness choices, not native claims): single legal slot
(the reviewed accepted slot; lane05 arena-slot precedent), explicit
cohort [78] (admitted pool stays empty by design; no admission implied),
staged positions, 40-red squad (l21 precedent so area attacks leave
survivors), unattended run (no captain input). The birth path itself —
bootstrap → `GenObjectTeki::birth` → resolve → native bind → probe →
sidecar claim — is 100% native engine behavior.

Primary run `output/msw/l60-seedrun-stage/9e1151af246641c2bf821ff1c74f8d78/native.log`
(sha256 `594d73c9acd291342a2a393040229a3423404997992611d9bbeae7b425c5b383`,
300 s wall, healthy 30 fps, no extinction; corroborating 20-red run
`1b88fab5…/native.log` sha256 `40c90086284b0e22` shows the same four
markers):

- `:14` `[PC Port] Experimental preview window set to 960x540 windowed and centered`
- `:414` `[PC Generator] default: read 45 generators, 45 fully recognised`
- `:592` `P2_SEED_RESOLVE source_id=78 target=328297937 original_type=0 x=-98.9 z=1848.5`
- `:593` `P2_GENERATED_PLACEMENT source_id=78 target=328297937 generator=201078 bound=1`
- `:594` `P2_PLACEMENT_SLOT generator=201078 slot=328297937 actor=0 xyz=0 terrain=none route=0 route_distance=1508.5 x=-98.864 y=30.000 z=1848.469 water_depth=0.00`
- `:729` `P2_GROINK_CARCASS_READY generator=201078 type=0 gauge_delay=2.000 recovery=3.000 max_health=1200.000`
- `:743` `P2_PLACEMENT_PROBE actors=0 evidence_slots=0 source=birth_hook`

Root observers on this log: `correlated_birth(…, 201078)` → all spawn
checks True, `gate1` True; `observe_identity(…, 78)` → resolved/bound
328297937 = accepted uid, `correlated` True, no refusal;
`pedestal_confusion` False.

Honest limits, stated plainly: the `:594` probe line reports
`xyz=0 terrain=none route=0` — slot agreement is the catalog join
(sidecar 201078→328297937), and fresh native terrain/route acceptance
remains lane-04 evidence, not claimed here. No `P2_GROINK_CARCASS_BECOME`
in 300 s with 40 adjacent reds: the unattended product run performs no
captain input and the stock P1 Frog vehicle never engaged (no LAND
markers; lane-16's frog FSM sidecar is out of scope), so the host
survived at full health and the carcass never began. Death/revival
therefore stays preserved l21 evidence under gates 4/6, not a new claim.
No `P2_ENEMY_READY` exists for Groink (no family READY module); identity
rests on the four agreeing seams.

## Build evidence

- Product: private `output/msw/native-l60-build`, native `4820e849`
  clean, `bin/nectar.exe` sha256
  `3909a5c852eb8063e895f5939a744c75aee07530f8900993e7b80119d1d16c81`,
  `ninja -n` → `ninja: no work to do.`
  (`output/muse-wave/l60/build-1789524701783583200.log`).
  Build-dir note: the wrapper's fixed `-DCMAKE_C_COMPILER=g++` bare
  name breaks the maintained fixture builder (`Missing input: <build>/g++`)
  and a bare reconfigure once reset JAUDIO/OPTIMIZE (link failure
  `Jac_NoteDemoSkipped`, per fan-out guide). Repaired inside the private
  build dir only: absolute `.exe` compiler paths, JAUDIO=ON,
  OPTIMIZE=OFF, regenerated + full rebuild through the leased wrapper.
  No source touched.
- Headless contract fixture (`scripts/build_pikmin2_fixture.py` from this
  worktree — the maintained copy predates #437 response-file expansion;
  same leased wrapper, same provenance schema; expected head `4820e849`,
  `provenance.json` status `built`) →
  `output/msw/l60-fixture-05/fixture.exe` sha256 `164f50d6c8ff4e7f…`.
  `output/msw/l60-gen2-run-01/native.log`: SIDECAR/SLOT/RESOLVE +
  `P2_MUSE_GROINK_SLOT_CONSTANTS source=78 slot=328297937 pedestal=0` +
  BIRTH_POLICY + `PASS MUSE_GROINK_CORRELATED` (exit 0; observer
  `muse_contract` all-True). Negatives: slot disagreement exit 1
  (`slot_disagree`), pedestal-97 resolve exit 1 (`resolve_source`).
  Labeled contract evidence, never gameplay.
- Focused regression: `py -3.12 -m pytest
  tests/test_pikmin2_muse_groink.py tests/test_pikmin2_muse_placement.py
  tests/test_pikmin2_muse_packaging.py tests/test_pikmin2_seed_evidence.py -q`
  → 55 passed.
- Fixture adoption: fresh arena via current overlay (45 generators incl.
  40-red squad), observed 960×540 centered startup, live room at 30 fps,
  no immediate extinction. Gameplay is the product room, not a custom
  main, so no replacement-main adoption gap applies.

## Gate table

- Source ID: 78 `MiniHoudai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | output/msw/l60-seedrun-stage/9e1151af246641c2bf821ff1c74f8d78/native.log:592 P2_SEED_RESOLVE source_id=78 target=328297937 and :593 P2_GENERATED_PLACEMENT bound=1 and :594 P2_PLACEMENT_SLOT generator=201078 slot=328297937 and :729 P2_GROINK_CARCASS_READY (observer gate1 True; accepted slot 328297937) | natural (shaped slot/cohort/positions labeled above) |
| 2. Autonomous movement and animation | PASS | output/dsw/l21-out/run-groink-live/native.log:1269,:1305,:1319,:1566 P2_GROINK_MOVE (position + source-FSM state + clip + phase; travel 0 -> 84.377 over 600 ticks) | natural (preserved l21 slice5; not a new run) |
| 3. Attacks and receivers | PASS | output/dsw/l21-out/run-groink-live/native.log:1313 P2_FROG_LAND radius=23.0 pikmin=3 behavior=source and :1314 P2_GROINK_TARGET_HIT health=30.0->20.0 state=22->33 alive=1->1 (and :1455 health=10.0->0.0 alive=1->0) | natural (preserved l21 slice5; not a new run) |
| 4. Death and corpse | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1277 P2_FROG_DEAD and :1279 P2_GROINK_CARCASS_BECOME (natural free-mode squad kill) | natural (preserved l21 slice4; not a new run) |
| 5. Actual transport and reward | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1378 P2_POD_RECEIPT id=corpse:groink:201001 value=2 new=1 pokos=2 seeds=0 | natural (preserved l21 slice4; not a new run) |
| 6. Cleanup and re-entry | PASS | output/dsw/l21-out/run-groink-reentry/native.log:1340 P2_GROINK_TEKI_FORGET bound=1 remaining=0 and :1345 P2_GROINK_TEKI_RESET bound_before=1 bound_after=0 and :1348 P2_GROINK_REENTRY stale_bound=0 rebound=1 | natural (preserved l21 slice6; not a new run) |

Gates 2-6 reuse the exact l21 citations already transcribed into the roster
ledger; this lane ran no new gameplay for them and advances none of them.
No ADMIT write; no allowlist change; deny-by-default tests untouched.

## Remaining work

Natural carcass begin/birth (needs a combat driver: lane-16 frog FSM
sidecar or input automation — out of scope) and natural shell-volley
witnesses (family FSM scope) are open and honestly unclaimed. No new
shared-hook blocker: every seam used (seed bridge, generated-placement
bind, probe birth hook, groink sidecar) already exists in-tree.
