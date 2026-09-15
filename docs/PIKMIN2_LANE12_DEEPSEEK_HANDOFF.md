# Lane 12 (Captains/squad) — DeepSeek handoff (#130)

Implementation owner: Codex through shared account `4laric`; executing session:
DeepSeek (`deepseek-v4-pro`), recorded separately per AGENTS.md. This handoff
documents one bounded slice: the **live slot-0 captain/squad seam** and
**survivor-gated game over**, consumed by the Greater Jellyfloat (lane 29)
captor-family path and demonstrated against the real Navi/NaviMgr in a private
GL runtime. This revision addresses review fixes (full stage-finish guard, bind
attribution, test portability, evidence logs).

## Source IDs / owned files

This is a shared/provider lane (captain/squad semantics), not a family lane, so
the "identity" is the captain slot 0 (Olimar) Navi object, not an enemy ID. The
real consumer is the **Greater Jellyfloat (OniKurage, P2 id 72)** captain-capture
path (`pc_port/pc_p2_kurage_arena.cpp`, lane 29), whose doc records "lane 12's
live Navi/NaviMgr host adapter is still the provider gate for captain
health/switch/knockout fidelity" (`docs/PIKMIN2_JELLYFLOAT_EXPANSION_NATIVE.md`).

Files owned/edited (native worktree `output/dsw/native-l12`):

- `pc_port/pc_p2_captain.h` / `pc_port/pc_p2_captain.cpp` — added the live
  query seam `captain_handle(int)`, `captive_count()`, `navi_dead(int)`.
- `src/plugPikiKando/gameCoreSection.cpp` — `#include "pc_p2_captain.h"`;
  `pc_p2_captain::setup_from_navi_mgr()` after Navi creation in the
  `GameCoreSection::GameCoreSection(...)` **constructor** (live auto-bind);
  `pc_p2_captain::teardown()` in `exitStage()` before `naviMgr = nullptr`
  (symmetry with the lifetime seam).
- `src/plugPikiKando/naviState.cpp` — `NaviDeadState::init` now calls
  `naviMgr->informOrimaDead(navi)` (null-guarded) and **guards the whole
  stage-finish block** (`GameStat::orimaDead`, `RESFLAG_OlimarDown`,
  `MOVIECMD_StageFinish`, camera deactivation, `releasePikis`, `startPause`) on
  `getAliveOrima() == nullptr`, returning early on the survivor-switch path.
- `tools/p2_captain_runtime.cpp` — lane-12 private real-GL runtime fixture
  (replacement-main), drives the live adapter through the four boundary
  semantics plus a labelled injected knockout scenario.

Root worktree files:

- `tests/test_pikmin2_captain_live.py` — source-presence gate only: asserts the
  live-seam markers are present in the resolved native tree
  (`PIKMIN_NATIVE_ROOT` env → `native/` → `engine/`); no duplicate engine-double
  tests, no hardcoded lane paths.

## Ordered commits

Native worktree (branch `deepseek/p2-l12-native`, base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`):

1. `0d0627ce` — "lane12: live slot-0 captain/squad seam + survivor-gated game
   over (#130)" (pc_p2_captain, gameCoreSection, naviState, fixture).
2. `dfdf39cc` — "lane12: fix runtime cleanup gate to test captive reload
   restoration (#130)" (fixture only).
3. `a90ceab3` — "lane12: review fixes - guard full stage-finish on survivor set,
   null-check naviMgr, correct bind attribution to constructor (#130)" (naviState,
   fixture).

Root worktree (branch `deepseek/p2-l12`, base
`ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):

1. `dfa349a` — "lane12: add live captain/squad seam pytest gates (#130)".
2. `(this handoff)` — "lane12: review fixes - portable test + handoff updates (#130)".

Dirty state: both worktrees clean after the commits above (nothing committed
under other lanes' `output/`, no assets/exe/build dirs committed).

## Interfaces / hooks touched and why

- `pc_p2_captain::setup_from_navi_mgr()` was already implemented but had **no
  live caller** besides the lane-11 Bulbmin preview, so the adapter never bound
  during ordinary play. The `GameCoreSection` **constructor** (not `finalSetup`)
  binds it against the live `naviMgr`/`pikiMgr` after Navi creation; `exitStage`
  unbinds it. Single-captain play is unchanged (the adapter binds slot 0 and the
  zero-control guard refuses only-captain capture).
- `NaviDeadState::init` previously set the global `GameStat::orimaDead = true`
  unconditionally on first death and continued unconditionally into
  `MOVIECMD_StageFinish`/`RESFLAG_OlimarDown`/camera/`releasePikis`/`startPause`,
  and never notified the roster. Note `GameStat::orimaDead` is in fact **never
  read by engine code** (its only writer is naviState; definition/reset at
  `gameStat.cpp:22,59`); the real end-condition is `MOVIECMD_StageFinish` →
  `forceDayEnd` (newPikiGame.cpp:2861-2867) plus `ENDCAUSE_NaviDown` from
  `NaviDeadState::procAnimMsg` (naviState.cpp:3256). So the whole stage-finish
  block is now gated: death marks the roster (`informOrimaDead`, which also
  re-points the roster active index at a survivor) and returns early when
  `getAliveOrima()` is non-null, ending the stage only when every present captain
  is down — source-faithful to P2 `singleGS_MainGame.cpp:914-928`
  (`mDeadNavis != 2`). With one captain the observable behaviour is
  byte-identical (the sole captain going down still ends the run).
- `captain_handle`/`captive_count`/`navi_dead` give a captor family a
  target-identity and captivity query without taking an engine dependency.

No family FSMs were edited; the Greater Jellyfloat's own `P2CaptainPolicy`
composition (`pc_p2_kurage_arena.cpp:633`) is unchanged and remains lane 29's.

## Build evidence

`output/dsw/l12-build-evidence.txt` (single clean head; production source ==
build head, no fixture-only delta):

```
2026-09-14T20:46:00 lane=l12 target=pikmin_pc native=a90ceab388e80bc34ccaa8c7faa74d3226cd5366 dirty=no
build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l12-build
exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l12-build\bin\nectar.exe
sha256=aead294217c8a1e2bad160ce16f84f6ecf95674a6a5ef37e8e5a0a504d532264
ninja_n="ninja: no work to do." seconds=90
```

Fixture `p2-captain-fixture-01` (provenance `status=built`, expected native head
`a90ceab388e80bc34ccaa8c7faa74d3226cd5366`), `fixture.exe` SHA-256
`21222c35e5117557cacf293264b73ef9f0c0c3299d9ee612f77ee6df280c5ddd`.

## Fixture adoption evidence

Fresh arena staged into
`output/dsw/l12-out/29aa57121d014e72ad96464855620d1d` using
`scripts/preview_pikmin2_room.py` (current overlay). Converted room inputs read
from `output/dsw/l04-out/converted/` (read-only; `pikmin2-room105` is no longer
present on this host). Observed 960×540 centred window and a live 20-red squad.

Both fixture runs are saved as `output/dsw/l12-out/captain-runtime.log` and
`output/dsw/l12-out/captain-knockout.log` (stdout captured through
`slot.py run gl l12`). Markers from those logs:

```
P2_CAPTAIN_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
P2_CAPTAIN_SQUAD live=20
```

## Six-gate table

| Gate | Result | Evidence (from l12-out/*.log) | Natural vs injected |
|---|---|---|---|
| 1. Exact identity | PASS | `P2_CAPTAIN_TARGET_IDENTITY slot=0 handle_matches=1 health=100.0` (captain slot 0 = live `naviMgr->getNavi(0)`) | natural (live scene auto-bind) |
| 2. Claim/release | PASS | `P2_CAPTAIN_CLAIM_REFUSED guard=zero_control`; `P2_CAPTAIN_ACTOR_CAPTURED`/`RELEASED` on a live Piki | claim/release of a **live Piki** natural; only-captain capture refusal natural (source zero-control guard) |
| 3. Interrupted capture | PASS | `P2_CAPTAIN_INTERRUPT_DROP released=1 state=free_reclaimable` (captor death frees held, never deletes) | natural |
| 4. Cleanup / re-entry | PASS | `P2_CAPTAIN_CLEANUP_RELOAD conserved=1 captive_count=0` (reload restores captive to previous owner) | natural |
| 5. Survival semantics (knockout + survivor-gated stage finish) | PASS | `P2_CAPTAIN_KNOCKOUT_SYNC dead=1 alive_orima=none orima_dead=1` | **injected** death (`mHealth=0` + `Navi::finishDamage`), not natural combat; game over still raised with zero survivors |
| 6. Real second-captain runtime | BLOCKED | `second_captain_live_allowed()` is still `false`; controller/camera/hud bind `getNavi(0)`/`getNavi()`, not `getActiveNavi()` | N/A on this port |

`PASS P2_CAPTAIN_RUNTIME` emitted in both logs; both fixture exits are 0.

## Tests run and results

The lane test is now a pure source-presence gate (no duplicate engine-double
compile tests, no hardcoded paths):

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l12 \
  py -3.12 -m pytest tests/test_pikmin2_captain_live.py -q
# -> 2 passed
```

- Without `PIKMIN_NATIVE_ROOT` it resolves `native/` (absent here) then the
  stale exported `engine/` mirror, and correctly FAILS on the new markers that
  lane 01 has not yet re-exported — an honest gate, not a leaked-path pass.
- `tests/test_pikmin2_captain_adapter.py` / `tests/test_pikmin2_captain_squad_split.py`
  remain the compile/engine-double contract tests (unchanged this lane).
- `test_pikmin2_lanes_1012_policies.py` has 1 unrelated failure
  (`P2HazardElectric` marker missing from the exported `engine/` mirror) —
  lane-10/11 source, not this lane.

## Assumptions

- The lane is a shared provider: the "one real consumer" is the Greater
  Jellyfloat captain-capture path (lane 29), and the piece delivered here is the
  live `Navi`/`NaviMgr` adapter that path requires, demonstrated by a
  lane-12-owned runtime fixture driving the exact `pc_p2_captain` functions a
  captor family calls. A fixture is a bounded consumer, not a gameplay pass; the
  family adapter edit remains lane 29's.
- `pikmin2-room105` was absent on this host; the identical converted `room.mod`/
  `room.ini`/`treasure.mod` inputs were read read-only from lane 04's private
  converted output (regenerated into my own `l12-out`).
- Second-captain live spawning stays gated off; the survivor-gated stage-finish
  change is single-captain-safe and its survivor path is only *observably
  different* (and currently only re-points the roster, not the controller/camera)
  once a second captain exists.

## Remaining blockers

- Real second-captain controls, per-captain camera, HUD and the live second
  spawn remain gated (`second_captain_live_allowed()` false). On survival, the
  roster active index moves to the survivor, but controller start
  (`gameCoreSection.cpp:1319` `getNavi(0)`) and camera bind
  (`pcamcameramanager.cpp:163`, `gameCoreSection.cpp:1256`) still read
  `getNavi()/getNavi(0)`, not `getActiveNavi()`; re-routing those is the next
  lane-12 slice.
- The Greater Jellyfloat still composes `P2CaptainPolicy` directly (a bounded
  adapter) rather than `pc_p2_captain::capture_captain`; wiring it to the live
  captain-capture now available here is **lane 29**'s family-adapter work
  (provider of the consumer-facing live seam = this lane, done).
- Natural (non-injected) combat-driven captain knockout is not proven here; the
  roster/survivor hook is exercised via an injected death only.

### Follow-up note (pre-existing, next lane-12 slice)

`pc_port/pc_p2_captain.cpp:24-38` keys `g_actorIds` on the live `Piki*` and only
clears the map in `teardown()`, so a freed-then-reused `Piki*` within one scene
can inherit a stale actor id (same lifetime rule the source captor FSMs follow).
Propose a `pc_p2_captain_forget_piki(Piki*)` hook beside the existing
`pc_p2_bulbmin_forget(...)` call at `src/plugPikiKando/pikiMgr.cpp:61` (inside
`PikiMgr::birth()`), so a recycled slot's id is forgotten on re-birth.

## Subagent usage

Fix/l12 slice:

- `explore` "survivor stage-finish audit": used as-is — established that
  `GameStat::orimaDead` is never read by engine code (the real end-condition is
  `MOVIECMD_StageFinish`/`ENDCAUSE_NaviDown`), that P2 ends the stage only at
  `mDeadNavis == 2`, and that `informOrimaDead` already flips the roster active
  index (so no extra `setActiveNavi` is needed). Drove the full-block guard.
- `explore` "forget-piki + mislabel inventory": used as-is — located the
  `pc_p2_bulbmin_forget` model at `pikiMgr.cpp:61`, confirmed no captain forget
  seam exists, and enumerated the four `finalSetup` mislabels (2 in the fixture,
  2 in the handoff). Efficiently caught every place to correct.
- `general` "pytest portability": wrote the rewritten
  `tests/test_pikmin2_captain_live.py`; adopted after verifying it contains no
  absolute paths, resolves `PIKMIN_NATIVE_ROOT` → `native/` → `engine/`, dropped
  the duplicate tests, and that run 2 (`PIKMIN_NATIVE_ROOT` set) = 2 passed.

Estimated net time: ~25–35 minutes saved across the three agents; all three
results used with only trivial verification edits.

## Reproduction

```bash
export PATH="/c/msys64/mingw64/bin:$PATH"; export PIKMIN_P2_ROOM_WINDOW=960x540; export PYTHONUTF8=1
cd C:/Users/alari/pikmin-randomizer/output/dsw/l12-out/29aa57121d014e72ad96464855620d1d
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l12 -- \
  C:/Users/alari/pikmin-randomizer/output/dsw/p2-captain-fixture-01/fixture.exe --experimental-pikmin2-room
# injected knockout scenario:
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l12 -- \
  C:/Users/alari/pikmin-randomizer/output/dsw/p2-captain-fixture-01/fixture.exe --experimental-pikmin2-room --knockout-roster
```
