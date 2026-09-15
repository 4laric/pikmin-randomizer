# OniKurage (Greater Spotted Jellyfloat, EnemyID 72) shared-base slice

Bounded native implementation of OniKurage as a Greater variant of the already
integrated Lesser Jellyfloat/Kurage bridge. Worktree
`output/native-species-onikurage`, branch `opencode/p2-species-onikurage`.

Source revision `632af93787b9c95b63f0c13be32b161375ce3a96`
(`src/plugProjectNishimuraU/OniKurage.cpp`, `OniKurageState.cpp`,
`include/Game/Entities/OniKurage.h`).

## What was added

- `pc_port/pc_p2_onikurage_fsm.h` - thin composition of the shared
  `p2kurage::Fsm` pinned to `Variant::Greater`, so the OniKurage state set
  (Kurage's eleven states plus `Drop`) is exercised without forking the machine.
- `pc_port/pc_p2_onikurage_mouth.h/.cpp` - dependency-free model of the two
  captain `MouthSlots` (OniKurage.cpp:251) plus `suckNavi` admission,
  `updateCollPartOffset`, `isFinishNaviSuck`, `isNaviSucked`,
  `flickStickNavi` (explicit Flick + Bomb release) and `escapeCheckNavi`
  (including the bittered `mHealth = 0` escalation).
- `pc_port/pc_p2_onikurage_teki_policy.h` / `pc_p2_onikurage_teki.h/.cpp` -
  private opt-in sidecar binding (`p2-onikurage-teki.txt`) mirroring
  `pc_p2_kurage_teki`, owning the shared Pikmin receiver and the two mouth slots.
- `tools/p2_onikurage_fsm_test.cpp`, `tools/test_p2_onikurage_mouth.cpp`,
  `tools/test_p2_onikurage_teki_policy.cpp` - standalone fixtures.
- `tools/run_onikurage_automatic_binding.py` - fixture runner.
- Hooks in `pc_p2_kurage_flight_policy.h`, `pc_p2_kurage_fsm.h`,
  `CMakeLists.txt`, `gameCoreSection.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
  `tools/p2_kurage_runtime.cpp`.

## Shared-base design (Kurage unchanged)

`pc_p2_kurage_flight_policy.h` gains a `Variant { Lesser, Greater }` selector.
The legacy `movePitchOffset(timer, dt)` / `attackPitchOffset(frame)` / ... entry
points still return the Kurage numbers; new `Variant`-taking overloads supply the
OniKurage keyframes (move amplitude 20 vs 50, attack/flick/takeoff/fall offsets
from OniKurage.cpp:301-421). `dropShouldFinish()` and `naviSearchAdmit()` encode
the OniKurage-only rules.

`pc_p2_kurage_fsm.h` appends `State::Drop` and adds a `Variant` constructor
argument defaulting to `Variant::Lesser`. The Greater branches are guarded, so
the default path is byte-identical: the existing `p2_kurage_fsm_test` still
reports `PASS checks=35` and `p2_kurage_flight_policy_test` still reports
`PASS checks=35`.

## OniKurage behaviour ported

- `Drop` (OniKurageState.cpp:470): entered from `Attack` END when a captain is
  held (`isNaviSucked`), after the health-death check; reuses the `Fall` motion,
  clearing `EB_Untargetable`; finish when ground distance < 25, vertical velocity
  > 0, or timer > 3 s; END chooses `Dead` or `Land`.
- Greater `Attack` finishing uses `(health <= 0 || isFinishNaviSuck()) &&
  (isNaviSucked || timer > suckTime || fallTimer > shakeTime)`.
- Greater `Ground` enters `GroundFlick` when a captain is held (or Pikmin stuck).
- Two captain mouth slots; `flickStickNavi` produces `InteractFlick`
  (`FLICK_BACKWARD_ANGLE`) + `InteractBomb` along the normalized horizontal
  separation * 50.
- Pikmin suction reuses `pc_p2_kurage_receiver` unchanged: OniKurage's Pikmin
  loop (OniKurage.cpp:562) is Kurage's loop on the `suck` coll part.

## Port adaptations (bounded host)

- The PC host has no P2 `MouthSlots`/`MouthCollPart`, no animated `Proom` joint
  and no `InteractSuikomi_Test`/`InteractSarai`/`InteractFlick`/`InteractBomb`
  stimulus. `pc_p2_onikurage_mouth` therefore models the slots and returns the
  source decisions for the adapter to apply to a `Navi`; slot identity is an
  opaque integer target, not a `Navi*`.
- `advanceDefaultOffset` replaces the animated world-matrix read with the
  source's own `interpolate`/`approach` math.
- No OniKurage-specific converted MOD exists; the bounded host reuses the Kurage
  wait/attack shapes as the established visual stand-in.
- The runtime fixture binds a generated Frog actor (generator 201001) as the
  bounded OniKurage stand-in; the sidecar magic `P2_ONIKURAGE_TEKI_1` selects the
  Greater path. A fixture must write only one of the Kurage/OniKurage sidecars,
  because both bindings would otherwise share the generated actor and double-tick
  the shared receiver.
- Captain attachment/release is not exercised live (no host Navi is captured):
  `flickStickNavi`/`escapeCheckNavi` are covered by the standalone mouth fixture.

## Build evidence

- Private build dir `output/native-species-onikurage-build`; Ninja, MinGW
  g++ 16.2.0, Release, JAudio ON, `PIKMIN_NATIVE_OPTIMIZE=OFF`.
- `[536/536] Linking CXX executable bin\nectar.exe`.
- Freshness: `cmake --build ... --target pikmin_pc -- -n` -> `ninja: no work to do.`
- `nectar.exe` SHA-256
  `EBA9558F3AF1F4404CEC2B22CC391BE3803D663EB35931028D45B6638E8B4013`.
- `SDL2.dll` + `libwinpthread-1.dll` copied into the build `bin/`.

## Standalone tests

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_onikurage_fsm_test.cpp -o p2_onikurage_fsm_test.exe
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/test_p2_onikurage_mouth.cpp pc_port/pc_p2_onikurage_mouth.cpp -o test_p2_onikurage_mouth.exe
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/test_p2_onikurage_teki_policy.cpp -o test_p2_onikurage_teki_policy.exe
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_kurage_fsm_test.cpp -o p2_kurage_fsm_test.exe
```

- `p2_onikurage_fsm_test PASS checks=22`
- `p2_onikurage_mouth_test PASS checks=27`
- `pc_p2_onikurage_teki_policy_test` (CTest) PASS
- `p2_kurage_fsm_test PASS checks=35` (shared base unchanged)
- `p2_kurage_flight_policy_test PASS checks=35` (shared base unchanged)
- CTest `-R "onikurage|kurage"` -> 3/3 passed.

## Runtime acceptance

Fixture built with `scripts/build_pikmin2_fixture.py` against the private build
(`output/onikurage-auto-fixture-01`, status `built`, fixture SHA-256
`7d3a9c4c6874cb51b024f373b8eb917b07dbb9139809848927edeb9118434506`), driven by
`tools/run_onikurage_automatic_binding.py` with inputs from
`output/kurage-auto-runtime-07`:

- `P2_KURAGE_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1`
- `[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`
- `P2_ONIKURAGE_TEKI_READY generator=201001 type=0 variant=Greater mouth_slots=2 binding=private_adapter`
- `P2_ONIKURAGE_AUTO_BIND_PASS generator=201001 type=0 variant=Greater mouth_slots=2 source=GameCoreSection::finalSetup sidecar=p2-onikurage-teki.txt direct_bind_calls=0`
- `returncode: 0` (`output/onikurage-auto-runtime-01/automatic-binding.json`,
  log SHA-256 `7d3f38ddf4ea53f819c0a2ac7815d90ef2020851b546b2b7ed01069fb4cf7c47`).

## Gate table

| Gate | Result | Evidence |
|---|---|---|
| Identity + binding | PASS | `P2_ONIKURAGE_TEKI_READY` / `P2_ONIKURAGE_AUTO_BIND_PASS` at `GameCoreSection::finalSetup` |
| Window + squad | PASS | 960x540 centered=1; `red=20` starting squad |
| FSM / Drop | PASS (unit + bound) | 22 FSM assertions incl. Drop entry/finish/END and Greater pitch; shared Kurage 35+35 unchanged |
| Pikmin suction | implemented + reused | shared `pc_p2_kurage_receiver`; captured on the bound actor |
| Captain capture/release | implemented + policy-tested | 27 mouth assertions (2 slots, rest pose, Flick+Bomb, bitter escape); no live Navi run |
| Death | PASS (unit) | `Drop`/`Attack`/`Ground`/`Fall` health routing in FSM test |
| Cleanup | PASS | `pc_p2_onikurage_teki_reset/forget` wired into `tekimgr` teardown + `gameCoreSection` reset |

## Blockers / open

- Live captain capture/release against real `Navi` objects (no host `Navi` mouth
  geometry / stimulus). `flickStickNavi` and `escapeCheckNavi` are unit-tested.
- OniKurage-specific converted MOD / material fidelity is untested; the Kurage
  asset is reused as the visual stand-in.
- Full Drop falling motion under the FSM host clock beyond the bound actor is not
  run; only the policy/FSM transitions are asserted.
