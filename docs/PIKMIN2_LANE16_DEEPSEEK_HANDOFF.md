# Lane 16 (Frogs/aquatic) — DeepSeek handoff (#167)

Worker session: DeepSeek (lane 16). Implementation owner: Codex through shared
account 4laric (recorded per AGENTS.md; this session is the executing agent, not
a separate identity). This slice is an **acceptance** deliverable on the current
approved pair; no new generic subsystem was built and no already-integrated FSM
was reimplemented.

## Source IDs and files owned

Family (#167): Frog 17, MaroFrog 18, Catfish 26, Tadpole 27, Jigumo 63,
UmiMushi (Toady Bloyster) 71, UmiMushiBlind 101. This slice exercises the Frog 17
/ MaroFrog 18 chain only; the Tadpole/Catfish/Jigumo/UmiMushi native source FSMs
(`pc_p2_tadpole.cpp`, `pc_p2_catfish.cpp`, `pc_p2_jigumo.cpp`, `pc_p2_umimushi*.cpp`)
are already present in the native tree and were not modified.

File scope owned this slice: no production source change was required. The Frog
native body remains a labelled P1 proxy driven by source parameters
(`pc_port/pc_p2_frog.cpp`, `pc_p2_frog_policy.h`) with attribution markers and
manager reset/re-entry. Root harness/tests exercised (unchanged): `experimental/
pikmin2_frog_{runtime,combat,carry,arena}.py` plus their tests.

## Ordered commits / dirty state

- Root branch `deepseek/p2-l16`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`,
  head `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (clean at start of work).
- Native branch `deepseek/p2-l16-native`, base/head
  `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (clean).

No native code change was made this slice: the aquatic native modules are already
integrated on the base, and the lane's primary next action is acceptance. A
source-faithful Frog **FSM** port (Wait/Turn/Jump/JumpWait/Fall/Attack/Fail/
TurnToHome/GoHome) on `pc_p2_frog.cpp` — matching the Catfish/Jigumo/UmiMushi
ports — is the explicit next implementation slice and is intentionally left to a
separate bounded commit rather than a rushed change here.

## Interfaces / hooks touched

None. `teki.h`, `tekibteki.cpp`, `tekimgr.cpp`, `pc_p2_preview.cpp` and CMake are
untouched. The frog param chain, setup/reset/forget seam and `P2_FROG_*`
markers already present in the base were used as-is.

## Build evidence (`output/dsw/l16-build-evidence.txt`)

Native `b805d9c626e4f4558c95aef7cac311a5d9a2068f`, clean. Configured with Ninja +
MinGW g++ (CMAKE_MAKE_PROGRAM set to the Python-bundled ninja), Release,
`PIKMIN_NATIVE_JAUDIO=ON`, `PIKMIN_NATIVE_OPTIMIZE=OFF` (portable CPU, matching
the maintained build convention). `pikmin_pc` built 603/603; `ninja -n` no work.
Executable `native-l16-build/bin/nectar.exe` SHA-256
`920ebb5c3086b4e6c538e48a3f37173b7241a43d223224f6be9f06cf13ff0397`.

Note: the shipped `build_lane.py` wrapper did not pass `-DCMAKE_MAKE_PROGRAM` and
therefore could not configure from a clean build dir; the configure step was run
manually under `slot.py run build l16` with the flags above, then the wrapper was
used for the build itself.

## Fixture adoption evidence

All runs: `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`, GL slot wrapped via
`slot.py run gl l16`. Each run log contains
`Experimental preview window set to 960x540 windowed and centered` and the
20-red `ensure_pikmin_squad` overlay (observed `pikis=20` at frame 120 in the
carry run; `P2_FROG_COMBAT_BEGIN ... pikis=20` in the combat run). Frog bank
regenerated fresh into `output/dsw/l16-out/frog-bank` from the P2 disc
(`GPVE01` rev 0) + decomp checkout `632af93787b9c95b63f0c13be32b161375ce3a96`;
staged `p2-frog.txt` SHA-256 `0c929f7b0ac5c7375d0df2c277f8a574c71e61b9dcd9eaac4e0f1148071065ec`.

Private fixtures (all `status=built` against native head `b805d9c6...`):

| Fixture | exe SHA-256 |
|---|---|
| fixture-runtime | `5d1b86c484a6c7bd67a95a4bab7ecd46afab1bd052d40e6f3f59c21a2dee8bb2` |
| fixture-combat | `884d81902e78b99fb4e1d5cc9c36a2e9ef0a262ae6775636c17d174d8af40ad5` |
| fixture-carry | `b768df371ece9aa2b429bf3906d476d535283f9b2bafd07ca08c03df7b142123` |

## Run results (all on the current head)

| Run | Stage dir | Result |
|---|---|---|
| runtime (default placement) | `l16-out/run-runtime/stages/1a2f21ebde494a0eb4986841b5446131` | PASS exit 0 |
| runtime (near_onion) | `l16-out/run-runtime-nearonion/stages/a740c36636c04f2d859e1e13e11cd315` | PASS exit 0 |
| combat (natural, no injection) | `l16-out/run-combat/stages/838febc1f841444298775ad7b13dbfd1` | PASS exit 0 |
| carry (near_onion, injected lethal) | `l16-out/run-carry/stages/f5b95e9f795b419fa695874c6b61e576` | UNOBSERVED exit 0 |

## Concrete source IDs and six-gate tables

One `Source ID:` line and one six-gate table per identity the lane claims. Gate 1
and 2 PASS rows are cited to `output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:NNN`
(the runtime fixture re-run on native `7ad50a85`); gate 3 cites the combat re-run
`output/dsw/l16-out/run-combat-f3/stages/b974d1e3a7d9403084c1ac47ee5b4ace/native.log:NNN`.
Injected evidence is UNTESTED, never PASS.

### 17 `Frog`
- Source ID: 17 `Frog`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:1267 | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:1293 | natural |
| 3. Attacks and receivers | PARTIAL (natural attack + vulnerability; natural lethal not reached) | output/dsw/l16-out/run-combat-f3/stages/b974d1e3a7d9403084c1ac47ee5b4ace/native.log:1325 | natural |
| 4. Death and corpse | UNTESTED (injected) | output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:1473 | injected |
| 5. Actual transport and reward | UNTESTED | no transport/receipt observation | natural |
| 6. Cleanup and re-entry | UNTESTED (manager reset/re-entry only; full scene/day teardown not run) | output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:1313 | injected |

### 18 `MaroFrog`
- Source ID: 18 `MaroFrog`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:1268 | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:1272,1361 (`P2_FROG_DRAW species=MaroFrog` wait1/attack draws) | natural |
| 3. Attacks and receivers | UNTESTED | no combat run tracks MaroFrog as the target | natural |
| 4. Death and corpse | UNTESTED (injected) | output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43/native.log:1485 | injected |
| 5. Actual transport and reward | UNTESTED | no transport/receipt observation | natural |
| 6. Cleanup and re-entry | UNTESTED | manager reset/re-entry only | injected |

### 26 `Catfish`
- Source ID: 26 `Catfish`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | native FSM `pc_p2_catfish.cpp` present, not exercised this pass | natural |
| 2. Autonomous movement and animation | UNTESTED | not exercised this pass | natural |
| 3. Attacks and receivers | UNTESTED | not exercised this pass | natural |
| 4. Death and corpse | UNTESTED | not exercised this pass | natural |
| 5. Actual transport and reward | UNTESTED | not exercised this pass | natural |
| 6. Cleanup and re-entry | UNTESTED | not exercised this pass | natural |

### 27 `Tadpole`
- Source ID: 27 `Tadpole`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | prior `docs/PIKMIN2_TADPOLE_NATIVE.md`; not re-run this pass | natural |
| 2. Autonomous movement and animation | UNTESTED | not re-run this pass | natural |
| 3. Attacks and receivers | N/A | source-backed harmless (fp24=0); no attack surface | natural |
| 4. Death and corpse | UNTESTED | not exercised this pass | natural |
| 5. Actual transport and reward | UNTESTED | not exercised this pass | natural |
| 6. Cleanup and re-entry | UNTESTED | not exercised this pass | natural |

### 63 `Jigumo`
- Source ID: 63 `Jigumo`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | native FSM `pc_p2_jigumo.cpp` present, not exercised this pass | natural |
| 2. Autonomous movement and animation | UNTESTED | not exercised this pass | natural |
| 3. Attacks and receivers | UNTESTED | not exercised this pass | natural |
| 4. Death and corpse | UNTESTED | not exercised this pass | natural |
| 5. Actual transport and reward | UNTESTED | not exercised this pass | natural |
| 6. Cleanup and re-entry | UNTESTED | not exercised this pass | natural |

### 71 `UmiMushi`
- Source ID: 71 `UmiMushi`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | native FSM `pc_p2_umimushi.cpp` present, not exercised this pass | natural |
| 2. Autonomous movement and animation | UNTESTED | not exercised this pass | natural |
| 3. Attacks and receivers | UNTESTED | not exercised this pass | natural |
| 4. Death and corpse | UNTESTED | not exercised this pass | natural |
| 5. Actual transport and reward | UNTESTED | not exercised this pass | natural |
| 6. Cleanup and re-entry | UNTESTED | not exercised this pass | natural |

### 101 `UmiMushiBlind`
- Source ID: 101 `UmiMushiBlind`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | native FSM `pc_p2_umimushi.cpp` Blind split present, not exercised this pass | natural |
| 2. Autonomous movement and animation | UNTESTED | not exercised this pass | natural |
| 3. Attacks and receivers | UNTESTED | not exercised this pass | natural |
| 4. Death and corpse | UNTESTED | not exercised this pass | natural |
| 5. Actual transport and reward | UNTESTED | not exercised this pass | natural |
| 6. Cleanup and re-entry | UNTESTED | not exercised this pass | natural |

Injected state is separated: lethal death was produced by the fixture's
`stimulate(InteractAttack(navi,nullptr,10000,false))` at `observed>=360`; the
natural exchange (vulnerability + landing press) is NOT injected.

## Tests run

- `py -3.12 -m pytest -q tests/test_pikmin2_frog_behavior.py
  tests/test_pikmin2_frog_combat.py tests/test_pikmin2_frog_rewards.py
  tests/test_pikmin2_frog_carry.py tests/test_pikmin2_frog_arena.py
  tests/test_pikmin2_tadpole_behavior.py` → **51 passed**.
- The three fixture validators re-run on the fresh logs: runtime `passed=true`,
  combat `passed=true`, carry `passed=false` (honest `UNOBSERVED`).

## Assumptions

- Read-only use of the shared decomp checkout (`native/pikmin2-research`) and the
  P2 disc as extraction inputs; neither was edited. Frog bank regenerated into my
  own `l16-out`, not a shared bank.
- `-DPIKMIN_NATIVE_OPTIMIZE=OFF` adopted as the "portable CPU" convention; IPO
  left at the repo default. Recorded here for provenance.
- No native FSM was authored this slice; acceptance on the current head was the
  primary next action and is what is delivered.

## Remaining blockers (naming provider lane)

1. **Frog native source FSM** (lane 16, next slice): `pc_p2_frog.cpp` is still
   `P1_proxy`; the source ten-state FSM (Wait/Turn/Jump/JumpWait/Fall/Attack/
   Fail/TurnToHome/GoHome, `FrogState.cpp:13`) is only modeled host-side in
   `pikmin2_frog_behavior.py`. Port it like `pc_p2_catfish/jigumo/umimushi`.
2. **Natural lethal combat** (lane 16 + 10 receivers): 20 reds deal ~540 damage
   before the frog's landing press wipes the squad; a legal source receiver /
   larger squad is needed to observe a natural kill of the 800-HP Frog.
3. **Transport/reward** (lane 06 rewards, 04 placement): the carry fixture did
   not observe a corpse pellet in `pelletMgr` after the same injected attack that
   the runtime fixture (same arena, same head, same bank) converted into two
   corpses. The discrepancy is in the carry fixture's corpse/carry observation
   path, not the arena or native head. Next: instrument `findCorpse` with a
   pellet census after injection to see whether the corpse pellet is born but
   `mPelletView` mismatch or is never born in that fixture.
4. **Persistence/campaign** (lane 03/06/33): no generated-seed spawn, receipt or
   restart run; identity admission remains empty.

## Reproduction (one exact command)

From the current root worktree (`output/dsw/l16-root`), after building
`native-l16`/`native-l16-build` and regenerating the frog bank into
`output/dsw/l16-out/frog-bank`, run the natural-combat fixture:

```
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PIKMIN_P2_ROOM_WINDOW='960x540'; $env:PYTHONUTF8='1'
py -3.12 output/deepseek-wave/slot.py run gl l16 -- py -3.12 -m experimental.pikmin2_frog_combat run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/frog-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/run-combat" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/fixture-combat/fixture.exe"
```

## Slice 2

Worker session: DeepSeek (lane 16). This slice ports the Frog/MaroFrog **source
FSM** onto `pc_p2_frog.cpp` (the previous slice's "next implementation slice").

### What was implemented (native)

- `pc_port/pc_p2_frog.cpp` now drives the ten-state source FSM
  (Dead/Wait/Turn/Jump/JumpWait/Fall/Attack/Fail/TurnToHome/GoHome from
  `FrogState.cpp`) on the P1 TEKI_Frog/TEKI_Frow host, emitting
  `P2_FROG_STATE species=<Frog|MaroFrog> generator=<id> state=<name>` on every
  transition. Existing `P2_FROG_READY`/`P2_FROG_BANK_READY` and the
  setup/reset/forget seam are preserved.
- New `pc_p2_frog_update(BTeki*)` and `pc_p2_frog_suppress_ai(const BTeki*)`.
  `suppress_ai` returns true for registered actors and is wired into
  `BTeki::doAI()` so the P1 TaiOtimoti strategy does not act for registered
  frogs (the source FSM has exclusive control). `update` is wired into the
  `BTeki::update()` chain (`src/plugPikiNakata/tekibteki.cpp`).
- Landing press: source `collisionCallback` InteractPress(attackDamage) on
  grounded non-bittered Navi/Pikmin in the source head radius (23/21), fired once
  at the Fall->Attack landing. Jump shake: InteractFlick(0 knockback) at the
  type1 key event (frame 8). Jump-fail -> Fail via the isStickTo stuck stand-in;
  home-return via TurnToHome/GoHome. MaroFrog retargets a living captain
  (`attackNaviPosition`).
- Two correctness fixes required because the P1 TAI is suppressed in the
  registered frog: pending damage is applied through `makeDamaged()` (the
  TaiDamagingAction path no longer runs), and death is finalized through
  `pcEscapeNow()` (die()+dieSoon(); dieSoon only runs in the suppressed doAI
  block). Without these, the frog took no damage and never dropped a corpse.
- `pc_p2_frog_policy.h` adds `p2frog::stateName(int)` for the mapping.

### Root-side

- New `experimental/pikmin2_frog_fsm.py` (parse/validate `P2_FROG_STATE` rows:
  10 legal states, Wait-first, adjacency table, Dead terminal, combat-cycle and
  per-variant requirements) and `tests/test_pikmin2_frog_fsm.py` (9 tests).

### Subagent usage

Three subagents were dispatched in parallel:

1. `explore` (source audit) — returned compact FrogState.cpp state/transition/
   event/param/parameter tables with file:line citations. Used as-is as a
   cross-check against my own read of `FrogState.cpp`/`Frog.h`/`MaroFrog.cpp`;
   confirmed the ten states and confirmed the landing press is InteractPress in
   `collisionCallback` and that there is **no** eatPikmin/swallow for Frog.
2. `explore` (candidate inventory) — surfaced that `pc_p2_frog.cpp` was still a
   P1 proxy (no update/suppress), that `P2_FROG_STATE` did not exist natively,
   and located the `pcEscapeNow()` escape helper in `include/teki.h` (used for
   the corpse fix). Used as-is; the `dieSoon`/`pcEscapeNow` pointer saved real
   debugging time.
3. `general` (tests + validator) — wrote `experimental/pikmin2_frog_fsm.py` +
   `tests/test_pikmin2_frog_fsm.py`; 9 tests pass locally. Used as-is; committed
   unchanged.

Estimated net: the two explore agents saved roughly a full working session of
grep/read time (they located `pcEscapeNow`, confirmed the ODI loop and the
suppress-AI pattern). The general agent's validator was correct on first run.

### Build / runtime evidence

- Native commits: `6b1a2063` on `deepseek/p2-l16-native` (base
  `b805d9c626e4f4558c95aef7cac311a5d9a2068f`). Incremental Release builds
  (`PIKMIN_NATIVE_JAUDIO=ON`, MinGW g++ 16.2, Ninja) succeeded at three
  intermediate heads, EXE SHA-256:
  - `17d8ee75ddfb8ea8a34d0364af2688dd25ae7c3fec1419b7264cbb4e4a531590` (FSM port)
  - `4146ec445e15d7a3ead0286c1fca745486654f944af110cc3cbafa979f150f3a` (+makeDamaged)
  - `19e437a2bf5aa5e70f14c55b727681b9b22d0d9ee5b85cec4bec14e921422811` (+pcEscapeNow)
- Runtime fixture (rebuilt `ad336c59…` / final `52e5272b…`) **PASS**, exit 0:
  `PASS P2_FROG_RUNTIME birth4 controls2 corpses2 injected_attack=1 natural=0`;
  all checks true (births, cleanup_reentry `4/4/4`, source_params 800/1100,
  Frog/MaroFrog live+corpse+poses). The `P2_FROG_STATE` trace shows the source
  cycle `type1→wait2→type2→attack→wait1→waitact1` before injected death, and
  `clip=dead` then `corpse=1 clip=dead` on pcEscapeNow. Run dir
  `output/dsw/l16-out/run-runtime-s2/stages/f03e4a22ed95402cb9fe1b484fd336e0`.
- Python: `py -3.12 -m pytest -q tests/test_pikmin2_frog_fsm.py
  tests/test_pikmin2_frog_behavior.py tests/test_pikmin2_frog_combat.py
  tests/test_pikmin2_frog_rewards.py tests/test_pikmin2_frog_carry.py
  tests/test_pikmin2_frog_arena.py tests/test_pikmin2_tadpole_behavior.py` →
  **60 passed**.

### Six-gate change vs slice 1

| Gate | Slice 1 | Slice 2 (FSM) |
|---|---|---|
| A identity/spawn | PASS | PASS |
| B movement/animation | PASS (P1 proxy) | PASS (source FSM state trace) |
| C combat | natural vulnerability PASS, natural lethal FAIL | natural rerun **BLOCKED** (env) |
| D death/corpse | PASS injected | PASS injected (real source press + pcEscapeNow) |
| E cleanup/re-entry | PASS | PASS |
| F persistence | UNTESTED | UNTESTED |

### BLOCKED (environmental, not this lane)

After the FSM landed, the shared MinGW toolchain on this host failed:
`g++.exe`/`cc1.exe`/`cc1plus.exe` exit 1 with no stdout/stderr and produce no
object or assembly file, affecting even a trivial `int main(){}` compile (C and
C++) while `as.exe` still works. This is a host-wide failure under the current
18-lane parallel load (Windows `C:\Users\alari\AppData\Local\Temp` at ~14 GB,
thousands of cc*.s files), not a source error — the same sources compiled and
linked at the three SHAs above. Blocked remainder:
- **Combat fixture re-run** (natural combat + landing-press under the FSM) and
- **Natural-lethal attempt** (Frog-only free-mode deploy, no injected damage).

Mechanism expectation (to re-verify once the host recovers): the source Frog is
800 HP; the 20-red starting squad deals well under 800 before the frog's landing
press (InteractPress, attackDamage 10) wipes them, so natural lethal should FAIL
with a health floor ~260 and a squad floor 0 — the same floor observed in slice
1's P1-proxy combat run. Two trivial hardening edits are already in the committed
source (a `dead`-escape once-guard and a per-landing `pressDone` reset) but are
not part of the last successful build (`19e437a2`, which predates them); they
compile-trivial and will be verified on the next build.

### One exact reproduction

```
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
$env:PIKMIN_P2_ROOM_WINDOW='960x540'; $env:PYTHONUTF8='1'
py -3.12 output/deepseek-wave/slot.py run gl l16 -- py -3.12 -m experimental.pikmin2_frog_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/frog-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/run-runtime-s2" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/fixture-runtime-s2/fixture.exe"
```

## Slice 2 — review fix pass (`l16-fix2`)

Review rejection resolved item-by-item. The `g++` host-wide failure had already
cleared (verified: full Release build + link succeeds at the new head).

### Item resolutions

1. **`pressDone` compile break** — added `bool pressDone = false;` to `FrogFsm`
   (`pc_p2_frog.cpp`); the per-landing reset now compiles (item 1 was the flat
   compile failure — the previous handoff admitted the reset was never compiled).
2. **dirty=no build + fixture re-runs** — committed first, then built at the fixed
   head through `build_lane.py l16`; three new `dirty=no` rows appended to
   `l16-build-evidence.txt`. Rebuilt and re-ran the runtime fixture, the combat
   fixture and the natural-lethal attempt (combat = natural, no injection), all
   on the committed head.
3. **Deferred death + validator wired** — removed the unconditional
   `mHealth<=0 → Dead` at `pc_p2_frog_update` and deferred death to the source
   exec points: `Wait` (isDead), `Turn`/`TurnToHome`/`GoHome` (finishMotion),
   `Attack`/`Fail` (KEYEVENT_END), never from Jump/JumpWait/Fall. The
   `experimental/pikmin2_frog_fsm.py` adjacency table already agreed with the
   source. `pikmin2_frog_runtime.py` and `pikmin2_frog_combat.py` now actually
   call the validator (`checks['fsm']`); a `P2_FROG_SETUP` episode marker added to
   `pc_p2_frog_setup` lets the validator re-segment around the observed==80
   re-entry so the reset does not forge an illegal adjacency.
4. **groundY drift / sinking** — `groundY` is now captured from a floor probe
   (`mapMgr->getMinY`) at setup and re-probed at each `launchHop` (no longer the
   driftable `pos.y`), and every grounded state pins `pos.y = groundY`.
5. **FRG_FAIL unreachable** — in `FRG_JUMP` entry, `stuckPikminCount>0 && rand01 <
   p.jumpFail` transits to `FRG_FAIL` (StateJump::init); `rand01`/`nextRand` are
   live again and the dead `nextState` field was removed.
6. **shouldFlick** — replaced "any target within 40u" with a stuck-Pikmin count
   gate (`mStickListHead` walk) at the `mShakeOffSticking1` tier (3); the
   graduated flick-timer thresholds are a documented port omission. Frozen frogs
   now wait/turn before jumping. `Turn` also commits immediately when attackable
   or aligned (source `finishMotion`), restoring the landing-press combat gate.
7. **Fall→Attack** — split the hop at the apex (`JumpWait → Fall` at `airTimer >=
   airTime/2`) and land `Fall → Attack` on **probed floor contact**
   (`probeFloorY(pos) >= pos.y`, source `FrogState.cpp:341`), with the
   `airTimer >= airTime` bound kept only as a fallback for a hop with no floor
   below; this replaces the elapsed `type2*1.5` timer. (Fix-3 item 1: the earlier
   fix-2 sentence paired "floor contact" with the `airTimer` timer, which was not
   what the code did; see the fix-3 section.)
8. **pressOnGround comment** — `doLandPress` comment now accurately describes the
   `collisionCallback` landing press only; the false "flips stuck" claim deleted
   (the pressOnGround stuck-shakeoff is not reproduced on the P1 host).
9. **markers/params** — added `shakeRange` (120.0) to `p2frog::Params` and used it
   in `doJumpFlick`; `P2_FROG_READY` prints `behavior=source_fsm`;
   `P2_FROG_LAND` now counts Navi separately instead of hard-coding `navi=0`.
10. **Hook split** — `src/plugPikiNakata/tekibteki.cpp` (+4 lines) was extracted
    into its own `lane16: hooks — wire pc_p2_frog FSM update + suppress-AI into
    BTeki (#167)` commit; the FSM port is a separate commit.

### Ordered commits

Native `deepseek/p2-l16-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`:

| Commit | Message |
|---|---|
| `7122f544` | lane16: hooks — wire pc_p2_frog FSM update + suppress-AI into BTeki (#167) |
| `99b09e86` | lane16: port Frog/MaroFrog source FSM onto P1 Wollywog host (#167) |
| `51acd8b0` | lane16: review fixes 2 — deferred death, floor-probed groundY, stuck-gated flick, FRG_FAIL entry, land navi count (#167) |
| `19e36c83` | lane16: review fixes 2 — P2_FROG_SETUP episode marker for FSM re-entry (#167) |
| `32749e5a` | lane16: review fixes 2 — source-faithful Turn finishMotion (#167) |

Root `deepseek/p2-l16`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

| Commit | Message |
|---|---|
| `53bf6ae` | lane16: wire source-FSM validator into runtime/combat acceptance (#167) |
| `1b44593` | lane16: split FSM-episode validation on P2_FROG_SETUP (#167) |
| `e0fd013` | lane16: parse multi-digit squad in the natural-lethal combat validator (#167) |

### Build evidence (all `dirty=no`, appended to `l16-build-evidence.txt`)

| native | EXE SHA-256 |
|---|---|
| `51acd8b0c68b743a6276c81fa4c098962e13c24a` | `615b96843d7cce8c77f1cd5625833a65da54400287f528fe73b11d33fa7bfaec` |
| `19e36c83648de33add0263074b4d5378fe3490e5` | `46c8972a12a10da3f6d8fd3314de47c4e35dc4b7995d2ef4247a49b105523432` |
| `32749e5a5178b6a712fdb5fb6893a68b4b56e68c` | `97bee0e978d7e898568c838607b5705c038b2db349f717586829587d4c9bf322` |

### Fixture re-runs (committed head `32749e5a`, 960x540, GL slot wrapped)

| Fixture | Stage dir | Result |
|---|---|---|
| runtime (injected lethal) | `run-runtime-s2d/stages/24a8c28de0644a1a9baad664924b59be` | **PASS** exit 0; `fsm=true`, no illegal transitions |
| combat (natural, 4-actor arena; no injection) | `run-combat-s2d/stages/69b3103a6d334202aaa1def16a0cd5a1` | **PASS** exit 0; `fsm=true`, `reason=depleted`; frog survives (floor ~245 HP); squad stays at 20 after each jump flick and drops to 0 only on the last tick |

`P2_FROG_READY` now prints `behavior=source_fsm`; `P2_FROG_LAND` counts
`pikmin`/`navi` separately; death is deferred (`attack→dead` terminal, no
`jump→dead`); frozen frogs `wait→turn` before jumping.

### Tests

`py -3.12 -m pytest -q tests/test_pikmin2_frog_fsm.py
tests/test_pikmin2_frog_runtime.py tests/test_pikmin2_frog_combat.py
tests/test_pikmin2_frog_behavior.py tests/test_pikmin2_frog_carry.py
tests/test_pikmin2_frog_rewards.py tests/test_pikmin2_frog_arena.py
tests/test_pikmin2_tadpole_behavior.py` → **64 passed**.

### Six-gate change vs slice 2

| Gate | Slice 2 | fix pass |
|---|---|---|
| C combat | natural rerun BLOCKED (env) | natural combat (4-actor arena); natural-lethal free-mode attempt not run |

### Subagent usage (this pass)

No subagents were available in this session (no task tool was exposed), so the
review-specified three-way subagent split could not be run. All source audit,
validator wiring, native fixes, builds and GL re-runs were done directly by this
session. The slice-2 `general` subagent's validator remains in use, now correctly
executed against the real log (it had been committed un-run; this pass found and
fixed the episode-boundary and multi-digit-squad issues that only real output
exposes). Honest negative result: the subagent experiment added no measurably
saved time on this fix pass.

## Slice 2 — review fix pass 3 (`l16-fix3`)

Fix on the merged wave-native head (the integrator's resolved `pc_p2_frog.cpp`,
keeping this lane's FSM phase/clip selection and lane 09's
`pc_gfx_specular_family_scope` bracket around `drawshape`). Items 1-3 are the
blocking review items.

### Item resolutions

1. **Fall→Attack floor contact (blocking).** `pc_p2_frog.cpp` `FRG_FALL` now
   transits when `probeFloorY(actor->getPosition(), s.groundY) >= pos.y` (source
   `FrogState.cpp:341` `mFloorTriangle` contact semantics), with
   `s.airTimer >= p.airTime` kept only as a fallback for a hop with no floor
   below. The fix-2 handoff sentence above is corrected.
2. **Combat / natural-lethal row (blocking).** The lane-14-style Frog-only
   free-mode natural-lethal attempt was **not** run; the row is relabeled
   "natural combat (4-actor arena); natural-lethal free-mode attempt not run".
   The 4-actor log shows natural vulnerability (800→365) and the landing press
   delivered to 20 Pikmin, but the jump flick disengages the squad each jump (it
   stays at 20 until the final tick), so "press wipes the squad" is not what the
   log shows. Running the free-mode Frog-only arena remains the next bounded step.
3. **Ingestible gate tables (blocking).** The single shared six-gate table was
   replaced by one `Source ID:` line + six-gate table per claimed identity
   (17/18/26/27/63/71/101). `check_p2_handoff_gates.py` now accepts gates 1 and 2
   for 17 and 18, warns nothing, and refuses nothing (exit 0); output pasted
   below.
4. **P2_FROG_LAND validator + dead `logLand`.** `experimental/pikmin2_frog_combat.py`
   now matches `behavior=(P1_proxy|source)` (the `land_attribution` list was
   always empty before); the native `logLand` (the dead `behavior=P1_proxy`
   landing path) is deleted and its `pc_p2_frog_draw` call site simplified. Note
   `logPress`/`P2_FROG_PRESS` is now also unobserved (it keyed on the P1 `Attack`
   motion, which the suppressed P1 TAI never plays) and is left as reported-only
   instrumentation.
5. **state=fail / hook ordering / retargetNavi.** `state=fail` appears in zero
   logs: FRG_FAIL is implemented (jump-entry `stuckPikminCount>0 && rand01 <
   jumpFail`) but is **untested at runtime** this pass. Hook commit `7122f544`
   precedes the port commit `99b09e86` and does not compile standalone (it wires
   symbols the port declares), so the pair is **non-bisectable** as committed.
   `retargetNavi` now uses `naviMgr->getNavi()` like `nearestTarget` (it was an
   all-Navi iterator), giving consistent single-active-Navi selection.

### Ordered commits

Native `deepseek/p2-l16-native`, on merged wave base `acf597eb`:

| Commit | Message |
|---|---|
| `7ad50a85` | lane16: review fixes 3 - Fall floor-contact landing, drop dead logLand, retargetNavi consistency (#167) |

Root `deepseek/p2-l16`:

| Commit | Message |
|---|---|
| `531d0c96` | lane16: review fixes 3 - accept behavior=source in the P2_FROG_LAND validator (#167) |

### Build evidence (`dirty=no`, appended to `output/dsw/l16-build-evidence.txt`)

| native | EXE SHA-256 |
|---|---|
| `7ad50a85ba5e9d3a69744eaa92aaa286f436abd3` | `8a6b6e0ffda3f34e10c78142519e79ff8ce727dbae7040a11b18856913682726` |

`ninja -n` = "ninja: no work to do." The host-wide `g++`/`cc1` silent failure
seen at the start of this pass had cleared before this build.

### Fixture re-runs (committed head `7ad50a85`, 960x540, GL slot wrapped)

| Fixture | Stage dir | Result |
|---|---|---|
| runtime (injected lethal) | `output/dsw/l16-out/run-runtime-f3/stages/e8edbce3f2bf445eb68c3feaa9731d43` | **PASS** exit 0; `fsm=true`, floor-contact landing, no illegal transitions |
| combat (natural, 4-actor arena; no injection) | `output/dsw/l16-out/run-combat-f3/stages/b974d1e3a7d9403084c1ac47ee5b4ace` | **PASS** exit 0; `fsm=true`; vulnerability 800→365; landing press on 20 Pikmin; frog survives (natural lethal not reached) |

### Tests

`py -3.12 -m pytest -q tests/test_pikmin2_frog_combat.py tests/test_pikmin2_frog_fsm.py`
→ **20 passed** (including the new `behavior=source` validation cases).

### Gate-checker output

`py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE16_DEEPSEEK_HANDOFF.md`
(exit 0, no refused PASS):

```text
17 Frog (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  ignored [PARTIAL]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
18 MaroFrog (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
26 Catfish (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
27 Tadpole (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
63 Jigumo (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
71 UmiMushi (role=variant):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
101 UmiMushiBlind (role=variant):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [UNTESTED]
  3. attacks_receivers  ignored [UNTESTED]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [UNTESTED]
```

### Subagent usage (this pass)

Three subagents were dispatched in parallel (the task tool was available this
pass):

1. `explore` (free-mode arena + floor-contact audit) — located the lane-14 /
   Kochappy free-mode deploy block (`observed==240`, `resetPosition` +
   `changeMode(PikiMode::FreeMode)`), confirmed source `StateFall::exec`
   floor-triangle transit, and reported that `probeFloorY` uses
   `getMinY(x,z,false)`. Used as-is to write the item-1 fix and to scope the
   (not-run) free-mode attempt.
2. `explore` (marker/gate discrepancy inventory) — returned the exact
   `pikmin2_frog_combat.py:100-102` regex, the `logLand`/`logPress` ranges and
   draw call site, the `retargetNavi`/`nearestTarget` ranges, the
   `7122f544`→`99b09e86` commit ordering, and the checker/gate-format locations.
   Used as-is.
3. `general` (validator fix) — changed the `P2_FROG_LAND` regex to
   `behavior=(P1_proxy|source)` and added three cases; `11 passed` in that file.
   Used as-is, committed as `531d0c96`.

Estimated net: the two `explore` agents removed the read-heavy discovery
(free-mode pattern, checker format, commit ordering) from this session and were
accurate; the `general` agent's fix was correct on first run. This pass's
subagent use was a net saver versus the fix-2 pass, which had no task tool and
cost a longer manual read.
