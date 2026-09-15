# Pikmin 2 lane 21 (Groink) DeepSeek handoff — fix1

Lane 21 — Gatling Groink (`MiniHoudai` 78 / `FminiHoudai` 97). Tracking #198;
candidate reuse #204–#210. Executing agent: opencode (deepseek-v4-pro), 2026-09-14.
Implementation owner: Codex through shared account `4laric`.

## Supersession of the rejected slice

The first slice reimplemented the parked Codex carcass candidate under the same
file names with an incompatible free-function/POD API (a terminal `revived` flag,
health clamping, collapsed gauge-manager guard) and was rejected. The native
branch was reset to base and the parked Codex work resumed by cherry-pick; the
Python twin / tests / docs were rewritten to mirror the parked API.

## Slice delivered

Death/corpse recovery for #78/#97: resume the parked carcass regeneration +
replacement-object revival policy (`pc_p2_groink_carcass`) and the host
registration guard (`pc_p2_groink_lifetime`), and add a typed birth descriptor
(`P2GroinkCarcassBirth`) plus a Python twin and tests. The integrated
shell-strike bridge is untouched.

## Source IDs and files owned

- #78 MiniHoudai, #97 FminiHoudai.
- Native (`deepseek/p2-l21-native`): `pc_port/pc_p2_groink_carcass.{h,cpp}`,
  `pc_port/pc_p2_groink_lifetime.h`, `tools/p2_groink_carcass_test.cpp`,
  `tools/p2_groink_lifetime_test.cpp`, `tools/P2_GROINK_CARCASS.md`,
  `tools/P2_GROINK_LIFETIME.md`, CMake test wiring.
- Root (`deepseek/p2-l21`): `experimental/pikmin2_groink_carcass.py`,
  `tests/test_pikmin2_groink_carcass.py`, `docs/PIKMIN2_GROINK_CARCASS.md`,
  `docs/PIKMIN2_LANE21_DEEPSEEK_HANDOFF.md`.

## Ordered commits and dirty state

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

Native (`deepseek/p2-l21-native`):
1. `45697128` — cherry-pick of parked `codex/p2-groink-carcass` @ `8324a5a0`
   (feat: model Groink carcass recovery and revival request ordering).
2. `016a3b77` — cherry-pick of parked `codex/p2-groink-lifetime` @ `14d9391d`
   (feat: guard Groink registrations across revival and reuse).
3. `5f5cf5fe` — lane21: resume parked carcass candidate - birth descriptor and CMake test wiring (#198).

Root (`deepseek/p2-l21`):
1. `895124b` — lane21: source Groink carcass revival policy twin, tests and doc (#198) [superseded API; kept in history].
2. `cd0c59f` — lane21: DeepSeek handoff for carcass revival slice (#198) [superseded].
3. `795b208` — lane21: resume parked carcass API in the Python twin, tests and doc (#198).
4. `5b27c79` — lane21: fix1 handoff for resumed parked carcass candidate (#198).

## Interfaces and hooks touched

Kept parked: `class P2GroinkCarcass { become(config); reset(); step(delta,
pelletAlive, gaugeManager, activeTick) }` returning ordered `KillPellet` /
`RequestBirth` commands (host reports birth outcome; no terminal flag), and
`class P2GroinkLifetime` (generation-qualified handles, single pending revival
ticket, fail-closed serials). Added `P2GroinkCarcassBirth { position; faceDir;
existenceLength; inPiklopedia; }` as the host payload for `RequestBirth`. No
shared files modified; no product `PC_PORT_SOURCES` wiring (parked scope "no
shared hooks/build/export"); only two additive CMake test targets were added.

## Build evidence (output/dsw/l21-build-evidence.txt + output/dsw/l21-out/)

```
2026-09-14T20:52:01 lane=l21 target=pikmin_pc native=5f5cf5fe72f40a47c06cd6b33c9672ebed97774a dirty=no build_dir=...\native-l21-build exe=...\bin\nectar.exe sha256=9dd6f5d3fd6d53962bf83b0fc4ab8b7e5cfae1ee16f4d31ae0c5c4a07d167840 ninja_n="ninja: no work to do." seconds=74
2026-09-14T20:39:42 lane=l21 target=p2_groink_lifetime_test native=5f5cf5fe... exe=...\p2_groink_lifetime_test.exe sha256=d62bb72c... ninja_n="ninja: no work to do."
```
CTest (10/10 `p2_groink*` PASS) logged to `output/dsw/l21-out/ctest-groink-all.log`;
carcass+lifetime subset in `output/dsw/l21-out/ctest-carcass-lifetime.log`.

## Fixture adoption evidence

No real-GL runtime fixture run this slice (actor-independent policy). The
current starting-Pikmin overlay / centred 960×540 window adoption is deferred
to the next runtime acceptance run.

## Six-gate table (natural vs injected)

| Gate | Verdict |
|---|---|
| 1. Identity and spawn | source-backed N/A (policy attaches to existing #78/#97 identity) |
| 2. Movement and animation | UNTESTED (locomotion + Rebirth anim on shared actor hook) |
| 3. Attacks and receivers | unchanged (strike bridge; in-flight moving hits remain fixture-pinned) |
| 4. Death and corpse | source-backed policy + unit-proven; BLOCKED naturally (needs live `onKill` path) |
| 5. Transport and reward | source-backed N/A (lane 06 owns drops/cargo) |
| 6. Cleanup and re-entry | BLOCKED (guard exists; `generalEnemyMgr->birth` + Rebirth transit pending) |

No injected state promoted to a gameplay PASS.

## Tests run and results

- Native CTest: all ten `p2_groink*` PASS (incl. `p2_groink_carcass_test`,
  `p2_groink_lifetime_test`).
- Root Python: `tests/test_pikmin2_groink_carcass.py` 15 passed;
  `test_pikmin2_groink_arena.py` + `test_pikmin2_groink_assets.py` + carcass = 17 passed.

## Assumptions

- Kept parked adapters unchanged (config fields finite/nonnegative ≤1e6,
  `recoverySeconds>0`, step delta in [0,0.25]).
- `P2GroinkCarcassBirth` carries exactly the four `EnemyBirthArg` fields the
  source populates (position, face-dir, existence length, Piklopedia flag);
  `mTypeID` stays host/manager-owned.
- Python twin uses snake_case field names (idiomatic) for the same three config
  fields; command ordering and no-clamp semantics are identical to native.

## Next-wave order note

The ledger's next-wave order ("natural targeting/burst and shell effects",
then "source revival/carcass recovery") was skipped: this slice advances the
carcass/revival policy (a later item) because the earlier items need the live
MiniHoudai actor over the shared `teki.h`/`tekimgr.cpp`/`gameCoreSection.cpp`
hook. Natural targeting/burst/shell effects remain the next slice.

## Remaining blockers (provider lane)

- Real MiniHoudai actor registration / locomotion / pursuit and natural
  in-flight moving hit / animated muzzle: shared `teki.h`/`tekimgr.cpp`/
  `gameCoreSection.cpp` hook (lane 01 integration; lane 20 primitives, #128 bake).
- Carcass pellet drop (`EnemyBase::onKill`) and `generalEnemyMgr->birth` +
  `init` + Rebirth transit wiring: lane 06/07 lifetime + reward semantics.

## Subagent usage

Three parallel subagents were used (per the brief):
1. `explore` — source audit of `doBecomeCarcass`/`doUpdateCarcass`, parameter
   defaults, `EnemyBirthArg` fields, Rebirth state events, and the
   pellet-kill → owner-release chain. Result used as-is (materially confirmed
   no-clamp, no-retry, life-gauge guard; cited in the doc and handoff).
2. `explore` — full Groink inventory across both trees (modules, parked
   branches, markers, CMake wiring). Used as-is; confirmed `pc_p2_groink_lifetime`
   was parked-only and un-wired, and named the `P2_GROINK_*` marker set.
3. `general` — wrote the Python twin (`experimental/pikmin2_groink_carcass.py`)
   and `tests/test_pikmin2_groink_carcass.py` to mirror the parked API (15 tests
   pass). Used essentially as-is; I reviewed the no-clamp/no-retry/gauge-guard
   coverage and only integrated it without further edits.

Net: the delegation saved the read-heavy source/inventory work and the Python
port; my own context stayed on the native cherry-pick/build/ctest/handoff.

## Reproduction

```
cd /c/Users/alari/pikmin-randomizer/output/deepseek-wave && PATH="/c/msys64/mingw64/bin:$PATH" py -3.12 build_lane.py l21 --target p2_groink_carcass_test && PATH="/c/msys64/mingw64/bin:$PATH" ctest --test-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l21-build -R p2_groink --output-on-failure
```

## Slice 2

Bind the parked `P2GroinkCarcass` model to a live generated Groink actor so the
death/corpse gate moves off a policy-only unit test onto a real actor update.

### What it adds

Native `pc_port/pc_p2_groink_teki.{h,cpp}` + `pc_p2_groink_teki_policy.h`: a
family sidecar (exact `pc_p2_kurage_teki` / `pc_p2_mamuta` shape) that reads
`p2-groink-teki.txt` (`P2_GROINK_TEKI_1`), binds the generated Teki at that
generator/type in `GameCoreSection::finalSetup`, and drives
`P2GroinkCarcass::step(dt, pelletAlive, gaugeManager)` from the actor's own
`BTeki::update` each frame with `dt = gsys->getFrameTime()`. Host commands act on
the real objects — `KillPellet` kills the actor's own corpse pellet
(`t->mPellet->kill(false)`), `ActivateGauge`/`DeactivateGauge` toggle
`TEKIOPT_LifeGaugeVisible`, `RequestBirth` emits the
`P2_GROINK_CARCASS_BIRTH` descriptor (position/face-dir from the dead actor) and
marks the old object terminal (→ `MINIHOUDAI_Rebirth`). All seams log ordered
`P2_GROINK_CARCASS_READY/BECOME/GAUGE_ACTIVE/GAUGE_INACTIVE/KILL_PELLET/BIRTH`.

The carcass `become()` fires on the alive→dead transition so the regrowth
timeline is read from the actor's real death and pellet presence, never injected.

### Source IDs and files owned

- #78 MiniHoudai, #97 FminiHoudai (unchanged identity).
- Native (`deepseek/p2-l21-native`): `pc_port/pc_p2_groink_teki.{h,cpp}`,
  `pc_port/pc_p2_groink_teki_policy.h`, `tools/p2_groink_teki_test.cpp`, CMake
  (main-build + test wiring); shared hooks `src/plugPikiKando/gameCoreSection.cpp`,
  `src/plugPikiNakata/tekibteki.cpp`, `pc_port/pc_p2_teki_lifetime.cpp`.
- Root (`deepseek/p2-l21`): `experimental/pikmin2_groink_carcass_teki.py`,
  `tests/test_pikmin2_groink_carcass_teki.py`, this handoff.

### Ordered commits and dirty state

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

Native (`deepseek/p2-l21-native`), after the fix1 commits:
1. `b3f784e9` — lane21: bind Groink carcass policy to a live generated actor sidecar (#198).
2. `e22e075d` — lane21: wire Groink carcass sidecar into shared teki lifecycle hooks (#198).

Root (`deepseek/p2-l21`):
1. `c711545` — lane21: root validator guarding the Groink carcass-birth marker (#198).

### Interfaces and hooks touched

Shared hook commit `e22e075d` adds three additive seams, each mirroring an
existing family sidecar call: `pc_p2_groink_teki_setup()` in
`GameCoreSection::finalSetup`, `pc_p2_groink_teki_tick(this)` in `BTeki::update`,
and `pc_p2_groink_teki_forget/reset` in the centralized
`pc_p2_teki_lifetime.cpp` registration set (`pc_p2_forget_teki` /
`pc_p2_reset_all_teki`). No draw override and no `teki.h` change. No product
wiring beyond adding `pc_p2_groink_carcass.cpp` + `pc_p2_groink_teki.cpp` to the
main source list (they were previously test- or module-only).

### Build evidence (output/dsw/l21-build-evidence.txt)

```
2026-09-14T21:24:15 lane=l21 target=pikmin_pc native=e22e075d04d86889a14fbfa2cfccbd15dab3652d dirty=no build_dir=...\native-l21-build exe=...\bin\nectar.exe sha256=bd18573d5296f15432d0ba94c37a1408311e95de594051e54766639ae03b79ea ninja_n="ninja: no work to do." seconds=0
2026-09-14T21:20:11 lane=l21 target=p2_groink_teki_test native=5f5cf5fe... dirty=yes exe=...\p2_groink_teki_test.exe sha256=3cc854e16549cb344b539acb3b2086bb7130261746f94a3f5b7e9265b53a6178
```

### Fixture adoption evidence

No real-GL natural run this slice: there is no generated Groink spawn fixture yet
(the existing `P2_GROINK_ARENA` consumer is a stationary `no_ai=1 no_damage=1`
model with no pellet/gauge, and the sidecar needs a live MiniHoudai host actor
over the shared actor hook). The centred 960×540 window / live starting-Pikmin
adoption is unchanged from before and deferred to the slice that lands the actor.

### Six-gate table (natural vs injected)

| Gate | Verdict |
|---|---|
| 1. Identity and spawn | source-backed N/A (sidecar attaches to the existing #78/#97 identity) |
| 2. Movement and animation | UNTESTED (locomotion on shared actor hook) |
| 3. Attacks and receivers | unchanged (strike bridge) |
| 4. Death and corpse | sidecar-bound + unit-proven; BLOCKED naturally (no live Groink spawn, pellet-drop/onKill) |
| 5. Transport and reward | source-backed N/A (lane 06) |
| 6. Cleanup and re-entry | BLOCKED (`generalEnemyMgr->birth` + Rebirth transit on lane 06/07) |

No injected state promoted to a gameplay PASS.

### Tests run and results

- Native CTest: all eleven `p2_groink*` PASS, including the new
  `p2_groink_teki_test` (reader + config handoff) — log in
  `output/dsw/l21-out/ctest-groink-slice2.log`.
- Root Python: `tests/test_pikmin2_groink_carcass_teki.py` 5 passed (pure
  validator + real-source check via `PIKMIN_NATIVE_ROOT`).

### Assumptions

- `pelletAlive` maps to the actor's own corpse pellet (`PelletView::mPellet`
  alive); `gaugeManager` is always true (the P1 engine life-gauge manager is
  unconditional for a bound Teki).
- Regenerated health stays inside `P2GroinkCarcass` and is surfaced through
  `pc_p2_groink_teki_health()` rather than being written back to `t->mHealth`
  (writing a dead P1 host's `mHealth` up would resurrect the proxy actor and
  fight its corpse FSM); the real health-gauge regrowth is a lane 06/07 concern.
- `RequestBirth` logs position/face-dir from the dead actor and leaves
  `existenceLength=-1`/`inPiklopedia=false` because `EnemyBirthArg` duration and
  the Piklopedia flag are owned by the lane 06/07 manager-birth path.

### Remaining blockers (provider lane)

- Live MiniHoudai actor registration + generated-node spawn in a room (lane 01
  shared actor hook / lane 03 generator / lane 05 install) — without it there is
  no naturally dying Groink to drive the sidecar.
- Pellet drop (`EnemyBase::onKill`) and `generalEnemyMgr->birth` + Rebirth
  transit (lane 06/07) for the real KillPellet/RequestBirth end state.

### Subagent usage

Not delegated: this session had no `task` subagent tool, so the read-heavy source
audit, existing-candidate inventory and test scaffolding were done inline by the
agent itself rather than three parallel subagents. Net effect: the intended
parallelization was not exercised; the slice still completed with the native
implementation, build, CTest and root-validator evidence done directly. Honest
negative result for the required three-subagent experiment.

### Reproduction

```
cd /c/Users/alari/pikmin-randomizer/output/deepseek-wave && PATH="/c/msys64/mingw64/bin:$PATH" py -3.12 build_lane.py l21 --target p2_groink_teki_test && PATH="/c/msys64/mingw64/bin:$PATH" ctest --test-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l21-build -R p2_groink --output-on-failure
```
