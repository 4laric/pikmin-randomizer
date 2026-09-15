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
