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
4. `<head>` — lane21: fix1 handoff (this document).

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
