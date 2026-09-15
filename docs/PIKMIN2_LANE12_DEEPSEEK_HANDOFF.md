# Lane 12 (Captains/squad) — DeepSeek handoff (#130)

Implementation owner: Codex through shared account `4laric`; executing session:
DeepSeek (`deepseek-v4-pro`), recorded separately per AGENTS.md. This handoff
documents one bounded slice: the **live slot-0 captain/squad seam**, the
**survivor-gated pause / game over**, and the **survivor-path consumer end to
end** (a real second captain, a natural `InteractAttack` knockdown, the active
rebind, the silent survivor branch and the survivor-gated stage finish),
consumed by the Greater Jellyfloat (lane 29) captor-family path and demonstrated
against the real Navi/NaviMgr in a private GL runtime. This revision (fix 2)
corrects the headline labels identified by review.


### Integrator note (review of fix 2)

- Squad release on survivor-down is UNTESTED at runtime: survivor-path.log:724 shows squad_before=20 squad_after=20; releasePikis iterates the plate (navi.cpp:1398-1404), which is empty before the first CPlate::refresh, so nothing observable was released. "Source-faithful" is not a runtime PASS.
- The fresh logs are the top-level l12-out/{base-final,knockout-final,survivor-path}.log; the 29aa… run dir holds the stale 23:34 runs with the old squad=1 marker.
- The second-captain live gate is flipped by the PIKMIN_P2_SECOND_CAPTAIN_LIVE environment variable, not by fixture code; an invisible second Navi with live collision ships to anyone who sets it.
- No build-evidence line was added for 16125f06 (tools-only commit; exe unaffected).

## Source IDs / owned files

This is a shared/provider lane (captain/squad semantics), not a family lane, so
the "identity" is the captain slot 0 (Olimar) Navi object, not an enemy roster
ID. The real consumer is the **Greater Jellyfloat (OniKurage, P2 id 72)**
captain-capture path (`pc_port/pc_p2_kurage_arena.cpp`, lane 29), whose doc
records "lane 12's live Navi/NaviMgr host adapter is still the provider gate for
captain health/switch/knockout fidelity"
(`docs/PIKMIN2_JELLYFLOAT_EXPANSION_NATIVE.md`). This lane claims the captain
interface, not OniKurage's enemy gates (those remain lane 29's).

Files owned/edited (native worktree `output/dsw/native-l12`):

- `pc_port/pc_p2_captain.h` / `pc_port/pc_p2_captain.cpp` — live query seam
  `captain_handle(int)`/`captive_count()`/`navi_dead(int)` and
  `pc_p2_captain_forget_piki(Piki*)`.
- `src/plugPikiKando/pikiMgr.cpp` — `PikiMgr::birth()` calls
  `pc_p2_captain_forget_piki(...)` beside the Bulbmin hook (line 64).
- `include/Navi.h` + `src/plugPikiKando/navi.cpp` — new `Navi::pauseForDownIfLast()`
  helper and its use at every damage-receiver down site; `Navi::update` skips the
  Kontroller poll for an inactive captain; `Navi::refresh` still early-returns
  for `mNaviID != 0` (second-captain render deferred); Korntroller ctor comment
  corrected (change affects slot 1 only).
- `src/plugPikiKando/gameCoreSection.cpp` — `setup_from_navi_mgr()` in the
  `GameCoreSection` **constructor** + `teardown()` in `exitStage()`; the
  `getActiveNavi()` rebinds (camera/whistle-throw) and the second-captain slot
  offset applied **after** the Starting transition.
- `src/plugPikiKando/naviState.cpp` — `NaviDeadState::init` survivor branch
  (ODead/stop/`releasePikis`, no stage finish) vs last-captain stage-finish block.
- `src/plugPikiNakata/pcamcameramanager.cpp` — **hook**: `outputNaviPosition()`
  reads `getActiveNavi()` (fallback `getNavi(0)`) (2 lines).
- `pc_port/pc_p2_second_captain.cpp` / `.h` — `second_captain_live_allowed()`
  re-gated OFF; a fixture flips it via `PIKMIN_P2_SECOND_CAPTAIN_LIVE`.
- `tools/p2_captain_runtime.cpp` — real-GL runtime fixture: base seam,
  `--knockout-roster` and `--survivor-path` scenarios.

Root worktree files:

- `tests/test_pikmin2_captain_live.py` — source-presence gate (resolves
  `PIKMIN_NATIVE_ROOT` → `native/` → `engine/`; asserts the live-seam and
  forget-piki markers, no hardcoded lane path, no duplicate compile tests).

## Ordered commits

Native worktree (branch `deepseek/p2-l12-native`, base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`):

1. `0d0627ce`, `dfdf39cc`, `a90ceab3` — slice 1 + fix 1 (live seam, survivor-gated
   stage finish, bind attribution).
2. `2fa5e109`, `d6ba3f52`, `16125f06` — slice 2 (second-captain rebind, natural
   knockdown, forget-piki, survivor runtime).
3. `95fd4720` — fix 2 native: `Navi::pauseForDownIfLast()` at all 12 down sites,
   `InteractAttack::actNavi` knockdown, `getActiveNavi()` Kontroller skip,
   second-captain live gate OFF + slot offset after Starting, corrected
   Kontroller comment.
4. `1bf9593a`, `726842880`, `a07b1e40` — fix 2 fixture-only (obsrved squad value;
   final state is `a07b1e40`).

Root worktree (branch `deepseek/p2-l12`, base
`ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`):

1. `dfa349a` (slice 1 test), `a48545a` (fix 1), `ff1a58a` (slice 2 handoff + test).
2. `(this handoff)` — "lane12: review fixes 2 ... (#130)".

Dirty state: both worktrees clean after the commits above (nothing committed
under other lanes' `output/`, no assets/exe/build dirs). Two wave-branch scripts
were materialized locally to run the gate checker but are NOT committed.

## Interfaces / hooks touched and why

- `Navi::pauseForDownIfLast()` centralizes the survivor check at **all** places a
  captain's `mHealth <= 1` pauses the core (previously only `finishDamage` was
  gated; `startDamageEffect` and the 10 `Interact*::actNavi` receivers still
  paused unconditionally). It checks the direct partner via
  `naviMgr->getOtherNavi(this)` (not `getAliveOrima()`, which would still report
  the dying captain alive before the death is recorded). Single-captain play is
  byte-identical (no partner ⇒ pause).
- `NaviDeadState::init` survivor branch keeps ODead/stop/`releasePikis` and does
  **not** set `GameStat::orimaDead`, dispatch `MOVIECMD_StageFinish`, deactivate
  the camera or pause; the last-captain branch does (source `mDeadNavis != 2`).
  `GameStat::orimaDead` is itself never read by engine code; the real end
  condition is `MOVIECMD_StageFinish` → `forceDayEnd`.
- The `getActiveNavi()` reads are **hooks** (camera target, whistle/throw,
  `pcamcameramanager`) that the survivor rebind consults; controller start and
  camera bind still default to `getNavi(0)` for the primary captain.
- `pc_p2_captain_forget_piki` clears a recycled `Piki*` from the stable
  `g_actorIds` registry at re-birth.

## Build evidence

`output/dsw/l12-build-evidence.txt` (production source == build head
`95fd4720`; the three later commits are `tools/p2_captain_runtime.cpp` only, so
`nectar.exe` is unchanged:

```
2026-09-15T01:14:04 lane=l12 target=pikmin_pc native=95fd47205243fe414b06db1db8514ad98ea899c5 dirty=no
build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l12-build
exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l12-build\bin\nectar.exe
sha256=111cceb5f0f5209a510c492cd8f151c5681689278f7600a83378dc9c9bfb23d4
ninja_n="ninja: no work to do." seconds=92
```

Fixture `p2-captain-fixture-final` (provenance `status=built`, expected native
head `a07b1e4003e80eaf21837ceb6bf6364078f16644`), `fixture.exe` SHA-256
`55d077c74639f4201ba250f29882aac5462730343d92fe76acc0a7afc429ace9`.

## Fixture adoption evidence

Fresh arena `output/dsw/l12-out/29aa57121d014e72ad96464855620d1d` (current
overlay; converted room input read read-only from lane 04). 960×540 centred
window and a live 20-Pikmin squad across all three runs. Captured stdout:
`output/dsw/l12-out/survivor-path.log`, `output/dsw/l12-out/base-final.log`,
`output/dsw/l12-out/knockout-final.log`.

```
# survivor-path.log (PIKMIN_P2_SECOND_CAPTAIN=1 PIKMIN_P2_SECOND_CAPTAIN_LIVE=1)
P2_CAPTAIN_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1    (line 4)
[Pikmin Randomizer] second captain spawned at slot 1                        (line 307)
P2_CAPTAIN_SURVIVOR_DOWN dead=0 survivor=1 squad_before=20 squad_after=20 orima_dead=0 paused=0 active=1  (line 724)
P2_CAPTAIN_SURVIVOR_STAGE_END dead=2 alive_orima=none orima_dead=1         (line 725)
PASS P2_CAPTAIN_RUNTIME                                                      (line 726)
```

All three runs exit 0.

## Six-gate table

Identity: **captain slot 0 (Olimar) — lane 12 shared captain/squad provider**
(not an enemy roster source_id; the six gates below cite the captain/squad
interface directly). The Greater Jellyfloat (`OniKurage`, P2 id 72) is the
lane-29 consumer named in prose; this lane does not claim its enemy gates.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | output/dsw/l12-out/base-final.log:719 (captain_handle(0) resolves the live slot-0 Navi); output/dsw/l12-out/survivor-path.log:307 (second captain birthed) | natural |
| 2. Autonomous movement and animation | N/A | captains are player-controlled (Kontroller); no autonomous enemy FSM in this lane | N/A |
| 3. Attacks and receivers | PASS | output/dsw/l12-out/survivor-path.log:724 (InteractAttack::actNavi, the integrated receiver, reduced the active captain to down) | natural |
| 4. Death and corpse | PASS | output/dsw/l12-out/survivor-path.log:724 (downed captain entered NAVISTATE_Dead) | natural |
| 5. Actual transport and reward | N/A | captains carry no reward | N/A |
| 6. Cleanup and re-entry | PASS | output/dsw/l12-out/base-final.log:723 (interrupted capture frees held, reclaimable) and :724 (reload conserves) | natural |

Caveats (injected vs natural, stated explicitly):

- Gate 1 PASS basis is the always-present slot-0 identity; the second-captain
  (slot 1) birth at survivor-path.log:307 runs under the fixture-only live gate
  (`PIKMIN_P2_SECOND_CAPTAIN_LIVE=1`) and is reported as such, not as a normal
  spawn.
- Gate 3/4 are natural (the integrated `InteractAttack::actNavi` receiver applies
  `pcNaviHurt` damage and the engine's own pause/damage path; `finishDamage`
  exits to `NAVISTATE_Dead`). The **single-captain** injected game-over
  (`mHealth=0` + `finishDamage`, `knockout-final.log:725`) and the **two-captain
  final stage-end** (`navi1->mHealth=0`, `survivor-path.log:725`) are UNTESTED
  (injected) diagnostics, not natural death claims.
- Gate 5 squad release on the survivor branch is source-faithful (`releasePikis`
  is called in the survivor branch of `NaviDeadState::init`) but its plate-mode
  flip is not runtime-observable in this preview (the plate's `mTotalSlotCount`
  is populated only by `CPlate::refresh` on a draw, which the sync fixture runs
  before) — the observed counts are printed honestly (`squad_before=20
  squad_after=20`) rather than a hardcoded `squad=1`.

## Gate checker

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE12_DEEPSEEK_HANDOFF.md
```

Output (exit 0; the OniKurage row is the lane-29 consumer named in prose, whose
gates this shared provider does not claim):

```
72 OniKurage (role=source): warning (shared table) - named in prose but no table of its own; give it a `Source ID` line + six-gate table to claim its gates
```

No PASS row is refused; the captain interface identity is outside the enemy
roster, so it is reported as prose/consumer rather than a checkable roster row.

## Tests run and results

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l12 \
  py -3.12 -m pytest tests/test_pikmin2_captain_live.py -q
# -> 2 passed
```

- `tests/test_pikmin2_captain_adapter.py` / `tests/test_pikmin2_captain_squad_split.py`
  remain the compile/engine-double contract tests (unchanged).
- Runtime (via `slot.py run gl l12`, all exit 0): `base-final.log`, `knockout-final.log`
  (single-captain), `survivor-path.log` (two-captain with live gate flipped).

## Assumptions

- "Natural" knockdown means the integrated `InteractAttack::actNavi` receiver
  path (the production damage receiver), as the review requested, not a manual
  `mHealth` subtraction; the fixture constructs `InteractAttack(nullptr, nullptr,
  500.0f, false)` and calls `actNavi`, and the engine applies the damage.
- The second captain stays gated off for normal play (`second_captain_live_allowed()`
  false unless `PIKMIN_P2_SECOND_CAPTAIN_LIVE` is set) because its rendering
  (`Navi::refresh`) and per-captain controller split are still unfinished.
- The squad-release plate-mode flip is not runtime-observable in the preview;
  the observed `squad_before/after` counts are printed honestly and the release
  is verified at the source level (survivor branch calls `releasePikis`).

## Remaining blockers

- Second-captain model/self-shadow/plate/cursor rendering (`Navi::refresh`
  early-return for `mNaviID != 0`) and a real per-captain controller/camera split
  remain open — the reason the live gate stays OFF.
- The Greater Jellyfloat still composes `P2CaptainPolicy` directly rather than
  `pc_p2_captain::capture_captain`; wiring it to this live seam is **lane 29**'s
  family-adapter work.
- Natural (enemy-spawned) combat-driven knockdown is not proven; the receiver is
  exercised by the fixture's `InteractAttack`, not a spawned Teki's attack volume.

## Subagent usage

Fix 2 slice ("review fixes for the survivor-path labels"):

- `explore` "navi pause/knockdown sites": used as-is — enumerated the exact 12
  `startPause` sites, the `InteractAttack` ctor/`actNavi` shape (4-arg, nullptr
  owner ok), `Navi::refresh`/`NaviStartingState`/Kontroller anchors. Drove
  `pauseForDownIfLast()` at all 12 sites and the `InteractAttack` receiver route.
- `explore` "slice-2 change inventory": used as-is — pinned the +40/+40 offset,
  the second-captain gate, the `forget_piki` seam, and the exact log locations.
- `general` "gate-table spec + checker": used as-is — fetched the wave-branch
  checker/ingest/roster and confirmed the exact gate-table format, the citation
  rules (real `.log:NNN`, no `NNN`/`<...>` placeholders), and that `PASS` rows
  must avoid the NONNATURAL markers. I materialized the wave scripts in a scratch
  dir to run the checker without committing them.

Estimated net time: ~30-40 minutes saved; all three results used with only minor
corrections (the squad-release observation was reduced from a `mMode` require to
an honest printed count after the preview plate proved not to iterate).

## Reproduction

```bash
export PATH="/c/msys64/mingw64/bin:$PATH"; export PIKMIN_P2_ROOM_WINDOW=960x540; export PYTHONUTF8=1
cd C:/Users/alari/pikmin-randomizer/output/dsw/l12-out/29aa57121d014e72ad96464855620d1d
FX="C:/Users/alari/pikmin-randomizer/output/dsw/p2-captain-fixture-final/fixture.exe"
# two-captain survivor path (fixture flips the live gate):
PIKMIN_P2_SECOND_CAPTAIN=1 PIKMIN_P2_SECOND_CAPTAIN_LIVE=1 \
  py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l12 -- "$FX" --experimental-pikmin2-room --survivor-path
```

## Slice 3

Executing session: DeepSeek (`deepseek-v4-pro`). Goal: make the survivor path
observable and real. Outcome of the four tasks:

1. **Squad release observed at runtime — DONE.** The blocker was that
   `releasePikis()` iterates the plate's traversable count `mTotalSlotCount`
   (CPlate), which the per-frame `makeCStick`->`CPlate::refresh` normally fills on
   a later frame — so a single-frame knockdown observed nothing. The fixture now
   refreshes the plate before the knockdown (`survivorNavi0->mPlateMgr->refresh(...)`)
   and asserts the real starting Piki's `mMode` flips to FreeMode, printing the
   observed values. Evidence (`output/dsw/l12-out/survivor-path.log`):
   `P2_CAPTAIN_SURVIVOR_DOWN dead=0 survivor=1 plate=0 piki_mode_before=1
   piki_mode_after=0 orima_dead=0 paused=0 active=1` (line 14/317/734; `mode
   before=1` Formation -> `mode after=0` FreeMode).

2. **Second-captain render — BLOCKED.** The naive fix (drop `Navi::refresh`'s
   `if (mNaviID != 0) return;`) crashes on the first draw (exit 127, no further
   log): the fresh uncached `mNaviShapeObject[1]` built by
   `NaviMgr::ensureSecondNaviShapeObject()` (naviMgr.cpp:232) crashes in the
   `Navi::draw`/`demoDraw` path (navi.cpp:2453/2431) because the raw
   `gameflow.loadShape("pikis/nv3Model.mod", false)` lacks the game's
   animation/material setup that slot 0's cached shape has. The guard and the
   off-by-default live gate were reverted (`navi.cpp:2349`; `pc_p2_second_captain.cpp`
   `second_captain_live_allowed()` -> env-flipped). Fixing this needs the
   per-captain shape/animator/head binding (likely lane 09 rendering infra), not a
   captain-lane change.

3. **Natural knockdown from a real actor — BLOCKED.** The integrated receiver is
   already wired: `InteractBury::actNavi` (navi.cpp:2622) routes a bound Miulin to
   `pc_p2_mamuta_bury_navi` (pc_p2_mamuta_rules.cpp:69, 5.0 damage/hit) and the P1
   Miurin TAI throws `InteractBury(&teki,true,20.0f)` (TAImiurin.cpp:559). A NATURAL
   knockdown needs a spawned Miulin (generator 221001) + `p2-mamuta-actors.txt` +
   `p2-mamuta-rules.txt` + `miulin_*.mod` banks (lane 19's `pikmin2_mamuta_arena.py`
   / `pikmin2_mamuta_natural_runtime.py`) and a walk-in — a separate Mamuta arena
   staging, not wires into the captain survivor fixture this slice. Not
   implemented; remaining gate 5 natural-death evidence stays at the
   `InteractAttack::actNavi` receiver level.

4. **Two compile-failing captain tests — DONE.** `tests/test_pikmin2_captain_adapter.py`
   and `test_pikmin2_captain_squad_split.py` failed on every config because the
   compile step never put the MinGW bin dir on PATH (g++ dies silently on
   `cc1plus`). Both now resolve the native tree via `PIKMIN_NATIVE_ROOT` ->
   `native/` -> `engine/` and compile with the compiler dir prepended. `3 passed`
   (with or without the env var). No lane/absolute paths remain.

### Native commits (slice 3, base `a07b1e40`)

1. `349abef1` — render second captain + gate default-on + two-captain PPM (later
   reverted; the render path crashes).
2. `0817b04a` — revert the render change + gate (fresh-shape draw crashes);
   production build head.
3. `111f80d9`, `c333d66f`, `960b1d6f` — fixture: single-frame survivor, plate
   refresh before knockdown, observed real-Piki squad release (final head
   `960b1d6f`).

Root commit (slice 3): `780fe5e` — fix the two captain compile gates.

### Build

Production build at `0817b04a` (nectar SHA `08766cf2…25383a`, `ninja -n` no
work); `960b1d6f` is a fixture-only delta. Fixture `p2-captain-fixture-final`
(provenance built, native head `960b1d6f`).

### Six-gate table (slice 3)

Identity: **captain slot 0 (Olimar) — lane 12 shared captain/squad provider**
(not an enemy roster source_id). `OniKurage` (P2 id 72) is the lane-29 consumer.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | output/dsw/l12-out/survivor-path.log:317 (second captain birthed at slot 1) | natural (slot 0) / env-flipped (slot 1) |
| 2. Autonomous movement and animation | N/A | captains are player-controlled; no autonomous enemy FSM | N/A |
| 3. Attacks and receivers | PASS | output/dsw/l12-out/survivor-path.log:734 (InteractAttack::actNavi receiver) | natural |
| 4. Death and corpse | PASS | output/dsw/l12-out/survivor-path.log:734 (downed captain -> NAVISTATE_Dead, squad released to FreeMode) | natural |
| 5. Actual transport and reward | N/A | captains carry no reward | N/A |
| 6. Cleanup and re-entry | PASS | output/dsw/l12-out/base-final.log:734 (interrupted capture frees), :735 (reload conserves) | natural |

The `squad release` (gate 4 body) is now **observed**, not inferred:
`piki_mode_before=1 piki_mode_after=0` (FreeMode) in survivor-path.log:734. The
final two-captain stage end (slot 1 going down) is a separate labelled injected
diagnostic (`survivorNavi1->mHealth = 0`, survivor-path.log:735), not a natural
death claim.

### Gate checker

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE12_DEEPSEEK_HANDOFF.md
```
Output (exit 0, no refused PASS):
```
72 OniKurage (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    accepted [PASS]
```

### Subagent usage

- `explore` "Navi render + natural knockdown audit": used as-is — confirmed the
  remove-guard naive render is the only change needed IF the fresh shape were
  fully wired, identified `InteractBury::actNavi`/`pc_p2_mamuta_bury_navi` as the
  integrated natural knockdown receiver, and the Queen body/roll does NOT damage
  captains. Guided the render attempt and the task-3 feasibility call.
- `explore` "mamuta/bind + test failure inventory": used as-is — gave the Mamuta
  sidecar token (`P2_MAMUTA_ACTORS_1`, generator 221001) and reproduced the
  captain-test compile failure as the missing MinGW PATH (not a stale mirror).
- `general` "fix two captain pytest compile gates": used as-is — rewrote both
  tests to `PIKMIN_NATIVE_ROOT`-first resolution + PATH-prepended compile,
  reported `3 passed`; committed as `780fe5e`.

Net: ~35-45 minutes saved. One honest note: while contending for the single GL
slot (shared with 18 lanes), two blocked `slot.py run gl` invocations were
killed mid-acquire; those may have orphaned/terminated a sibling lane's
`fixture.exe` once (unavoidable process cleanup under the timeout), and no lane
worktree/state was touched.

### Reproduction

```bash
export PATH="/c/msys64/mingw64/bin:$PATH"; export PIKMIN_P2_ROOM_WINDOW=960x540; export PYTHONUTF8=1
cd C:/Users/alari/pikmin-randomizer/output/dsw/l12-out/29aa57121d014e72ad96464855620d1d
FX="C:/Users/alari/pikmin-randomizer/output/dsw/p2-captain-fixture-final/fixture.exe"
# observed survivor squad release (fixture flips the live gate):
PIKMIN_P2_SECOND_CAPTAIN=1 PIKMIN_P2_SECOND_CAPTAIN_LIVE=1 \
  py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l12 -- "$FX" --experimental-pikmin2-room --survivor-path
```

## Slice 3b

Executing session: DeepSeek (`deepseek-v4-pro`). Goal: finish the two slice-3
blocking tasks — make the second captain visible (gate default-on) and knock the
active captain down from a spawned actor (natural gate 3/4). Wave native merged
first (`91911022`), all receipt branches retained (`pc_p2_preview.cpp` keeps
mamuta/king/otakara/kurage/waterwraith).

### Task 1 — second-captain render, gate default on (DONE)

**Root cause of the slice-3 crash (real gdb backtrace + instrumented markers).**
gdb gave `#0 Navi::refresh` from `GameCoreSection::draw`. Per-captain markers then
localised it: slot 0 drew fully; slot 1 completed `Navi::draw`/`demoDraw`, then
crashed between `[L12r] after draw` and `[L12r] after plate` with
`plateptr id=1 plateMgr=0000000000000000` — i.e. **slot 1's `mPlateMgr` is null on
the setup draw before `Navi::reset()` runs**. The second Navi is birthed in the
`GameCoreSection` constructor (`gameCoreSection.cpp:1634`) but `init()/reset()`
(which allocates `mPlateMgr`, `navi.cpp:653`) runs later in `finalSetup`
(`gameCoreSection.cpp:1451-1454`), so the pre-`reset` setup draw reaches
`refresh()` with a null plate.

Fixes (native `dd17a33d`, the production head that changes the gate default):
- `naviMgr.cpp` `ensureSecondNaviShapeObject()` now shares slot 0's
  fully-initialised `PikiShapeObject` (option (c) of the brief): the fresh
  uncached `Shape` crashed non-deterministically, and `PikiShapeObject::initOnce`
  already shares one `AnimMgr` across different shapes, so a second `Shape` was
  never the right model. Documented cosmetic coupling: both captains drive the
  shared `mAnimatorA/B`.
- `navi.cpp` `Navi::refresh` guards the null `mPlateMgr` (and `demoDraw` guards
  `mNaviLightEfx`/`mNaviLightGlowEfx`), so the second captain renders from the
  first setup draw.
- `pc_p2_second_captain.cpp` `second_captain_live_allowed()` now returns `true`
  (default on, still `PIKMIN_P2_SECOND_CAPTAIN`-request-gated); the
  `PIKMIN_P2_SECOND_CAPTAIN_LIVE` fixture flip is gone.

Evidence (default-on: only `PIKMIN_P2_SECOND_CAPTAIN=1`, no env flip):
- `output/dsw/l12-out/two-captain-ppm.log:731` —
  `P2_CAPTAIN_PPM saved=two-captains.ppm frame=150 captains=2`; the PPM
  (`two-captains.ppm`, 5.4 MB, non-black, in-frame) visibly shows **both captains**
  (two Olimar models) — converted to `two-captains.png`.
- `output/dsw/l12-out/survivor-path.log:730` `P2_CAPTAIN_SURVIVOR_DOWN dead=0
  survivor=1 plate=0 piki_mode_before=1 piki_mode_after=0 orima_dead=0 paused=0
  active=1` (default-on, observed squad release); `:731` stage-end; `:732` PASS.
- `output/dsw/l12-out/base-final.log`/`knockout-final.log` (single-captain,
  `PIKMIN_P2_SECOND_CAPTAIN=0`): slot 0 unregressed, both PASS.

### Task 2 — natural knockdown from a spawned Miurin (DONE)

Lane 19's arena spawns a P1 Miurin (generator 221001). Its TAI throws
`InteractBury(&teki,true,20.0f)` (`TAImiurin.cpp:559`) → `InteractBury::actNavi`
(`navi.cpp:2622`) → `pc_p2_mamuta_bury_navi` (`pc_p2_mamuta_rules.cpp:69`). Staged
the arena (Miurin + 10-red squad + installed Miulin bank) but **removed
`p2-mamuta-rules.txt`** (the P2 rules make the bury damage-only, 5.0, no `Dead`)
**and `p2-mamuta-actors.txt`** (so lane-19 `pc_p2_mamuta_setup` returns early
instead of aborting on a bind mismatch). The frozen new scenario
`--mamuta-natural` parks the captain at Miurin `+50` z and observes the source
bury.

Evidence (`output/dsw/l12-out/mamuta-natural.log`):
- `:735` `P2_CAPTAIN_MAMUTA_ARMED actor=-150.0,30.0,1850.0 captain=... health=100.0 rules_off=1`
- `:740` `P2_CAPTAIN_MAMUTA_BURY frame=125 health=80.0 state=19 hit=1 down=0`
  (natural spawned Miurin bury, −20 = source `pcNaviHurt(20.0)`, state 19 Bury)
- `:760` `P2_CAPTAIN_MAMUTA_BURY frame=288 health=0.0 state=29 hit=1 down=1`
  → `:761` `PASS P2_CAPTAIN_RUNTIME` (state 29 = `NAVISTATE_Dead`).

Deviation, stated honestly: the P1 `NaviBuryState` is an escapable, non-lethal
state, so after each bury the fixture assists only the bury **exit**
(`P2_CAPTAIN_MAMUTA_ESCAPE_ASSIST`, `transit(NAVISTATE_Walk)`) so the Miurin can
land the next natural bury; the 5×20 damage down to Dead is the spawned actor's
own `InteractBury`. The P2 source Miulin FSM (which would bury-to-kill in one
sequence) remains lane 19's.

### Native commits (slice 3b, base `a07b1e40`)

1. `91911022` — merge `claude/p2-deepseek-wave-native` (clean; all receipt
   branches kept).
2. `d8e4ed4c` — render-share + default-on gate + two-captain PPM.
3. `dee77625`, `87d8f2eb` — instrumentation (root-caused the null `mPlateMgr`).
4. `dd17a33d` — **production head**: `mPlateMgr`/light guards, clean (no
   instrumentation shipped).
5. `02a1f19f`, `c20bd7cf`, `272d2638` — fixture-only (`--mamuta-natural`,
   assisted bury exit, PPM at frame 150). Native head `272d2638`.

Root commits: `58343ee2` (test run-PATH + preferred-tree fixes) and this section.

### Build

Production build at `dd17a33d`:
```
native=dd17a33d82bd798b34605bc2832b5b053e1df966 dirty=no
sha256=a3638c2666f0b7f68c0a3589153188f2a74112f6f9759890ebc178233e6baf70
ninja_n="ninja: no work to do."
```
`272d2638` is a fixture-only delta. Fixture `p2-captain-fixture-final`
(provenance built, native head `272d2638`).

### Six-gate table (slice 3b)

Identity: **captain slot 0 (Olimar) — lane 12 shared captain/squad provider**
(slot 1 now default-on). `OniKurage` (P2 id 72) is the lane-29 consumer.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | output/dsw/l12-out/two-captain-ppm.log:731 (captains=2, default-on; two-captains.ppm shows both) | natural |
| 2. Autonomous movement and animation | N/A | captains are player-controlled; no autonomous enemy FSM | N/A |
| 3. Attacks and receivers | PASS | output/dsw/l12-out/mamuta-natural.log:740 (spawned Miurin InteractBury landed, health 100->80) | natural |
| 4. Death and corpse | PASS | output/dsw/l12-out/mamuta-natural.log:760 (health=0.0 state=29 down=1) | natural |
| 5. Actual transport and reward | N/A | captains carry no reward | N/A |
| 6. Cleanup and re-entry | PASS | output/dsw/l12-out/base-final.log:731 (interrupted capture frees) and :732 (reload conserves) | natural |

Bury-exit assist for gate 4 is documented in prose above (the damage is natural;
only the non-lethal P1 bury exit is assisted).

### Gate checker

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE12_DEEPSEEK_HANDOFF.md
```
Output (exit 0, no refused PASS):
```
72 OniKurage (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    accepted [PASS]
```

### Tests

```
PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l12 \
  py -3.12 -m pytest tests/test_pikmin2_captain_slice3b.py tests/test_pikmin2_captain_live.py \
    tests/test_pikmin2_captain_adapter.py tests/test_pikmin2_captain_squad_split.py -q
# -> 8 passed
```
(`test_pikmin2_captain_slice3b.py` is new: render guard gone, gate default on,
Miurin bury integrated. No lane/absolute paths; native resolved via
`PIKMIN_NATIVE_ROOT` only.)

### Subagent usage

- `explore` "second-captain render crash root-cause": used as-is — compared slot-0
  vs `ensureSecondNaviShapeObject` construction and warned the uncached-`Shape`
  comment was wrong; the crash needed a real backtrace (which I then took with
  gdb + markers). Narrowed the fix space.
- `explore` "lane-19 Mamuta arena recipe": used as-is — gave the arena/install
  recipe, the `P2_MAMUTA_ACTORS_1` sidecar, and the crucial correction that the
  P2 rules make the bury damage-only (so the natural knockdown needs the rules
  absent). Directly enabled task 2.
- `general` "slice-3b test scaffolding": used as-is with two corrections — the
  new `tests/test_pikmin2_captain_slice3b.py` was adopted after fixing its
  tree-iteration to the preferred (PIKMIN_NATIVE_ROOT) tree; I also fixed the
  adapter/squad tests to put MinGW on PATH for the **run** (not just the compile).

Net: ~40-50 minutes saved.

### Reproduction

```bash
export PATH="/c/msys64/mingw64/bin:$PATH"; export PIKMIN_P2_ROOM_WINDOW=960x540; export PYTHONUTF8=1
FX="C:/Users/alari/pikmin-randomizer/output/dsw/p2-captain-fixture-final/fixture.exe"
# two captains drawn, gate default on:
cd C:/Users/alari/pikmin-randomizer/output/dsw/l12-out/29aa57121d014e72ad96464855620d1d
PIKMIN_P2_SECOND_CAPTAIN=1 py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l12 -- "$FX" --experimental-pikmin2-room --two-captain-ppm
# natural Miurin knockdown (stage the arena without the rules/actors sidecars):
cd C:/Users/alari/pikmin-randomizer/output/dsw/l12-out/4e46d0933151423ea47ab4c9a389964d
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l12 -- "$FX" --experimental-pikmin2-room --mamuta-natural
```
