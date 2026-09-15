# Lane 12 (Captains/squad) — DeepSeek handoff (#130)

Implementation owner: Codex through shared account `4laric`; executing session:
DeepSeek (`deepseek-v4-pro`), recorded separately per AGENTS.md. This handoff
documents one bounded slice: the **live slot-0 captain/squad seam** and
**survivor-gated game over**, consumed by the Greater Jellyfloat (lane 29)
captor-family path and demonstrated against the real Navi/NaviMgr in a private
GL runtime.

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
  `pc_p2_captain::setup_from_navi_mgr()` after Navi creation in
  `GameCoreSection::finalSetup` (live auto-bind); `pc_p2_captain::teardown()`
  in `exitStage()` before `naviMgr = nullptr` (symmetry with the lifetime seam).
- `src/plugPikiKando/naviState.cpp` — `NaviDeadState::init` now calls
  `naviMgr->informOrimaDead(navi)` and gates `GameStat::orimaDead` on
  `naviMgr->getAliveOrima() == nullptr` (survivor-gated game over).
- `tools/p2_captain_runtime.cpp` — new lane-12 private real-GL runtime fixture
  (replacement-main), drives the live adapter through the four boundary
  semantics plus a labelled injected knockout scenario.

Root worktree files:

- `tests/test_pikmin2_captain_live.py` — new pytest: compiles the engine-double
  policy/adapter contract binaries with `-Werror` and asserts the live seam
  markers are present in the full native worktree sources.

## Ordered commits

Native worktree (branch `deepseek/p2-l12-native`, base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`):

1. `0d0627ce` — "lane12: live slot-0 captain/squad seam + survivor-gated game
   over (#130)" (pc_p2_captain, gameCoreSection, naviState, fixture).
2. `dfdf39cc` — "lane12: fix runtime cleanup gate to test captive reload
   restoration (#130)" (fixture only).

Root worktree (branch `deepseek/p2-l12`, base
`ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):

1. `dfa349a` — "lane12: add live captain/squad seam pytest gates (#130)".

Dirty state: both worktrees clean after the commits above (nothing committed
under other lanes' `output/`, no assets/exe/build dirs committed).

## Interfaces / hooks touched and why

- `pc_p2_captain::setup_from_navi_mgr()` was already implemented but had **no
  live caller** besides the lane-11 Bulbmin preview, so the adapter never bound
  during ordinary play. The `finalSetup` hook binds it against the live
  `naviMgr`/`pikiMgr` every scene; `exitStage` unbinds it. Single-captain play is
  unchanged (the adapter binds slot 0 and the zero-control guard refuses
  only-captain capture).
- `NaviDeadState::init` previously set the global `GameStat::orimaDead = true`
  unconditionally on first death and never notified the roster, so the lane-12
  second-captain primitives (`informOrimaDead`/`getAliveOrima`/`isNaviDead`)
  were never exercised by the real death path. Now death marks the roster and
  game over is signalled only when no alive captain remains — source-faithful to
  P2 `singleGS_MainGame.cpp:914-928` (`mDeadNavis != 2`). With one captain the
  observable behaviour is byte-identical (the sole captain going down still ends
  the run).
- `captain_handle`/`captive_count`/`navi_dead` give a captor family a
  target-identity and captivity query without taking an engine dependency.

No family FSMs were edited; the Greater Jellyfloat's own `P2CaptainPolicy`
composition (`pc_p2_kurage_arena.cpp:633`) is unchanged and remains lane 29's.

## Build evidence

`output/dsw/l12-build-evidence.txt`:

```
2026-09-14T20:00:04 lane=l12 target=pikmin_pc native=0d0627ce27de25e73e3f23548d6050136a4d6b7b dirty=no
build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l12-build
exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l12-build\bin\nectar.exe
sha256=78e309eb67dcb8615e84a00db98057df0d24007561dbe64fce106030d4fff16e
ninja_n="ninja: no work to do." seconds=144
```

Fixture `p2-captain-fixture-01` (provenance `status=built`, expected native head
`dfdf39cc226b0f6b28bac50165d293fb1c0a03b1`), `fixture.exe` SHA-256
`ef73531cb12da3c3a8ee3871971cba58d42ccce50f2be1f7d68f7dbe10cad1ff`.

## Fixture adoption evidence

Fresh arena staged into
`output/dsw/l12-out/29aa57121d014e72ad96464855620d1d` using
`scripts/preview_pikmin2_room.py` (current overlay). Converted room inputs read
from `output/dsw/l04-out/converted/` (read-only; `pikmin2-room105` is no longer
present on this host). Observed 960×540 centred window and a live 20-red squad:

```
P2_CAPTAIN_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
P2_CAPTAIN_SQUAD live=20
```

## Six-gate table

| Gate | Result | Evidence | Natural vs injected |
|---|---|---|---|
| 1. Exact identity | PASS | `P2_CAPTAIN_TARGET_IDENTITY slot=0 handle_matches=1 health=100.0` (captain slot 0 = live `naviMgr->getNavi(0)`) | natural (live scene auto-bind) |
| 2. Claim/release | PASS | `P2_CAPTAIN_CLAIM_REFUSED guard=zero_control`; `P2_CAPTAIN_ACTOR_CAPTURED`/`RELEASED` on a live Piki | claim/release of a **live Piki** natural; only-captain capture refusal natural (source zero-control guard) |
| 3. Interrupted capture | PASS | `P2_CAPTAIN_INTERRUPT_DROP released=1 state=free_reclaimable` (captor death frees held, never deletes) | natural |
| 4. Cleanup / re-entry | PASS | `P2_CAPTAIN_CLEANUP_RELOAD conserved=1 captive_count=0` (reload restores captive to previous owner) | natural |
| 5. Survival semantics (knockout + survivor-gated game over) | PASS | `P2_CAPTAIN_KNOCKOUT_SYNC dead=1 alive_orima=none orima_dead=1` | **injected** death (`mHealth=0` + `Navi::finishDamage`), not natural combat; game over still raised with zero survivors |
| 6. Real second-captain runtime | BLOCKED | `second_captain_live_allowed()` is still `false` | N/A on this port |

`PASS P2_CAPTAIN_RUNTIME` (both the default boundary-semantics scenario and
`--knockout-roster`) emitted; fixture exit code 0.

## Tests run and results

```
export PATH="/c/msys64/mingw64/bin:$PATH"
py -3.12 -m pytest tests/test_pikmin2_captain_live.py \
    tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_captain_squad_split.py -q
```

- `test_pikmin2_captain_live.py`: **4 passed** (adapter + policy engine-double
  compile/run, live-seam source markers, idempotency check).
- `test_pikmin2_captain_adapter.py` + `test_pikmin2_captain_squad_split.py`:
  **passed** with the MinGW bin dir on PATH. Without it they fail on this shared
  host (g++ cannot load its own DLLs in the pytest subprocess); the new file
  works around this by prepending the compiler dir to PATH.
- `test_pikmin2_lanes_1012_policies.py`: 1 unrelated failure
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
- Second-captain live spawning stays gated off; the survivor-gated game-over
  change is single-captain-safe and is only *observably different* once a second
  captain exists.

## Remaining blockers

- Real second-captain controls, per-captain camera, HUD and the live second
  spawn remain gated (`second_captain_live_allowed()` false); unblocking them is
  lane 12's own follow-up, not a provider dependency.
- The Greater Jellyfloat still composes `P2CaptainPolicy` directly (a bounded
  adapter) rather than `pc_p2_captain::capture_captain`; wiring it to the live
  captain-capture now available here is **lane 29**'s family-adapter work
  (provider of the consumer-facing live seam = this lane, done).
- Natural (non-injected) combat-driven captain knockout is not proven here; the
  roster/survivor hook is exercised via an injected death only.

## Subagent usage

- `explore` "source audit": used as-is — pinned P1-port NAVISTATE_Dead/orimaDead
  anchors and confirmed the roster primitives were (unused) primitives only; the
  P2 decomp (OniKurage suckNavi/escapeCheckNavi, `mDeadNavis != 2`) is at
  `output/dsw/native/pikmin2-research`, not in my worktree. Large time save.
- `explore` "candidate inventory": used as-is — confirmed no live runtime ever
  called `setup_from_navi_mgr()` (only lane-11 Bulbmin) and that the contract
  already existed inbox. Prevented reimplementing the adapter. Large time save.
- `general` "tests/harness scaffolding": wrote `tests/test_pikmin2_captain_live.py`;
  used as-is after I verified its markers matched my final API (initial run was
  correctly 1-fail because my native seam did not yet exist). Saved ~15 min of
  mechanical pytest-writing; net positive.

Estimated net time: roughly 30–45 minutes saved across the three agents.

## Reproduction

```bash
export PATH="/c/msys64/mingw64/bin:$PATH"; export PIKMIN_P2_ROOM_WINDOW=960x540; export PYTHONUTF8=1
C:/Users/alari/pikmin-randomizer/output/dsw/p2-captain-fixture-01/fixture.exe --experimental-pikmin2-room
# or, with the injected knockout scenario:
C:/Users/alari/pikmin-randomizer/output/dsw/p2-captain-fixture-01/fixture.exe --experimental-pikmin2-room --knockout-roster
```

Run with cwd =
`C:/Users/alari/pikmin-randomizer/output/dsw/l12-out/29aa57121d014e72ad96464855620d1d`.
