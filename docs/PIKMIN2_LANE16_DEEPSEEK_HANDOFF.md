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

## Six arena gates (Frog 17 / MaroFrog 18)

| Gate | Result | Evidence / label |
|---|---|---|
| A Identity + spawn | PASS | `P2_FROG_BIRTH id=201001/2 type=0/33 registered=1`, source health 800/1100 via `P2_FROG_READY`; controls keep P1 values |
| B Autonomous movement + animation | PASS | per-state drawn poses (wait1/waitact1/type1/type2/attack/dead) incl. both live and corpse poses |
| C Combat / receivers | PASS (natural vulnerability + attack) / **natural lethal FAIL** | `P2_FROG_COMBAT`: frog health 800→260 under NODAMAGE natural Pikmin attacks; squad 20→0 from frog landing press (reason=depleted); frog never died — 20 reds insufficient vs source 800 HP |
| D Death / corpse / transport | corpse **PASS (injected, labelled)**; natural death UNTESTED; transport/reward **FAIL** | runtime (default + near_onion) both observed two live `PelletView` corpses after injected `InteractAttack(10000)`; `natural_deaths=[]` in every run. Carry fixture stayed `UNOBSERVED corpses=0` — see blockers |
| E Cleanup / re-entry | PASS | `P2_FROG_CLEANUP registered_before=4 cleared=4 reentry=4` (manager reset then rebuild; controls stay unregistered) |
| F Persistence | UNTESTED | no generated-session / process-restart reward ledger run |

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
