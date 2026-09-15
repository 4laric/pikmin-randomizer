# Pikmin 2 lane 21 (Groink) DeepSeek handoff

Lane 21 — Gatling Groink (`MiniHoudai` 78 / `FminiHoudai` 97). Tracking #198;
candidate reuse #204–#210. Executing agent: opencode (deepseek-v4-pro), 2026-09-14.
Implementation owner: Codex through shared account `4laric`.

## Slice chosen

One source enemy ID (#78 MiniHoudai, plus its fixed pedestal variant #97) and the
missing end-to-end slice **death/corpse recovery**: source-faithful carcass
gauge-delay -> regeneration -> replacement-object revival, mirroring
`MiniHoudai::Obj::doBecomeCarcass` / `doUpdateCarcass`
(`src/plugProjectNishimuraU/MiniHoudai.cpp:282-325`). The already-integrated
shell-strike bridge (`pc_p2_groink_hit` / `pc_p2_groink_strike`) is preserved and
not reimplemented.

## Source IDs and files owned

- #78 MiniHoudai (roaming Gatling Groink), #97 FminiHoudai (fixed pedestal).
- Native (`deepseek/p2-l21-native`): `pc_port/pc_p2_groink_carcass.{h,cpp}`,
  `tools/p2_groink_carcass_test.cpp`, CMake registration.
- Root (`deepseek/p2-l21`): `experimental/pikmin2_groink_carcass.py`,
  `tests/test_pikmin2_groink_carcass.py`, `docs/PIKMIN2_GROINK_CARCASS.md`.

## Ordered commits and dirty state

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both branches clean at handoff.

Native (`deepseek/p2-l21-native`):
1. `88373a12` — lane21: source Groink carcass regeneration and replacement-object revival (#198)

Root (`deepseek/p2-l21`):
1. `895124b` — lane21: source Groink carcass revival policy twin, tests and doc (#198)

## Interfaces and hooks touched

New engine-free policy only; no shared-framework edits. `pc_p2_groink_carcass`
depends solely on the existing `pc_p2_groink.h` (P2GroinkVec3). No shared files
(`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
`gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) were modified. The host
contract: a future actor calls `p2_groink_carcass_become` on death, then
`p2_groink_carcass_step(parms, dt)` each update; on `Revive` it performs the
replacement `generalEnemyMgr->birth` with the returned `P2GroinkCarcassBirth` and
transits the old object to `MINIHOUDAI_Rebirth`.

## Build evidence (output/dsw/l21-build-evidence.txt)

```
2026-09-14T19:30:47 lane=l21 target=pikmin_pc native=88373a124ead6ca354cb24b84ad4ed21bfaf1be4 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l21-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l21-build\bin\nectar.exe sha256=b85d69a8f3d0054d5ccef81ca31a29206a1f69acaac1c3e39285a154bd086504 ninja_n="ninja: no work to do." seconds=160
```

Configure: Ninja + MinGW g++ 16.2.0, `-DCMAKE_BUILD_TYPE=Release
-DPIKMIN_NATIVE_JAUDIO=ON -DPIKMIN_NATIVE_OPTIMIZE=OFF`, `CMAKE_MAKE_PROGRAM`
set to the Python-bundled `ninja.exe`
(`…/Python312/Scripts/ninja.exe`), compilers on `C:\msys64\mingw64\bin` PATH
(MSYS `/c/msys64/mingw64/bin` form). `pikmin_pc` links clean (604/604).

## Fixture adoption evidence

No real-GL runtime fixture was run for this slice — the deliverable is an
actor-independent policy proven by compiled CTest + Python unit tests. The
current starting-Pikmin overlay / 960×540 centred-window adoption is therefore
**deferred** to the next runtime acceptance run (the policy runs on the existing
integrated Groink strike fixture's host, which already adopts the current
override, not a regenerated family room).

## Six-gate table (natural vs injected)

| Gate | Verdict | Evidence |
|---|---|---|
| 1. Exact identity and spawn | source-backed N/A | No new actor registration here; policy feeds the existing MiniHoudai/FminiHoudai identity. |
| 2. Autonomous movement/animation | UNTESTED | Out of slice (locomotion remains on the shared actor hook). |
| 3. Attacks and receivers | unchanged / BLOCKED natural | Strike bridge integrated; in-flight natural moving hits remain fixture-pinned (see GROINK_STRIKE). |
| 4. Death and corpse | source-backed policy + unit-proven; BLOCKED natural | `doBecomeCarcass`/`doUpdateCarcass` mirrored; natural carcass needs the live actor `onKill` path. |
| 5. Actual transport/reward | source-backed N/A | No reward changes; carcass pellet transport is lane 06. |
| 6. Cleanup and re-entry | BLOCKED | Replacement birth + `MINIHOUDAI_Rebirth` transition outstanding. |

No injected health/state is claimed as gameplay PASS; the whole gate table is
honest and none of the natural gates were promoted.

## Tests run and results

- Native CTest: `p2_groink_carcass_test` PASS; all nine `p2_groink*` CTests PASS
  (strike, test, attack, clock, events, target, volley, hit, carcass).
- Root Python: `tests/test_pikmin2_groink_carcass.py` 10 passed; combined
  `test_pikmin2_groink_arena.py` + `test_pikmin2_groink_assets.py` +
  `test_pikmin2_groink_carcass.py` = 14 passed.

## Assumptions

- Params default to source values: `maxHealth` 1200 (roaming) / 700 (fixed),
  `healthGaugeTimer` 30s (fp11), `respawnRate` 10s (fp12); the module accepts
  host-supplied overrides.
- The engine's `lifeGaugeMgr` presence guard is collapsed to a semantic
  `GaugeActive`/`GaugeInactive` event; the host applies it only when it owns a
  gauge.
- A single overshooting step crosses the gauge but does not also regenerate
  (source's if / else-if only runs one branch per update).
- Revive is terminal for the carcass (the object transits to Rebirth and stops
  running the carcass update).

## Remaining blockers (provider lane)

- Real MiniHoudai actor registration / locomotion / pursuit: shared
  `teki.h`/`tekimgr.cpp`/`gameCoreSection.cpp` hook (lane 01 integration).
- Carcass pellet drop (EnemyBase::onKill) and replacement `generalEnemyMgr->birth`
  wiring: lane 06/07 lifetime + reward semantics.
- Natural in-flight moving hit / animated muzzle still open as before (lane 20
  primitives + #128 angle-aware bake).

## Reproduction

```
cd /c/Users/alari/pikmin-randomizer/output/deepseek-wave && PATH="/c/msys64/mingw64/bin:$PATH" py -3.12 slot.py run build l21 -- ctest --test-dir C:/Users/alari/pikmin-randomizer/output/dsw/native-l21-build -R p2_groink --output-on-failure
```
