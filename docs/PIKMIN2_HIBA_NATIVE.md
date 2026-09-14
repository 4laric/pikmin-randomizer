# Lane 22 fixed-hazard native slice

Issue [#170](https://github.com/4laric/pikmin-randomizer/issues/170), child
#447. Root behavior model: `experimental/pikmin2_elemental_behavior.py`
(branch `opencode/p2-lane22-elemental`). This slice adds the three fixed
elemental hazards after the dweevil capture/drop sidecar
([dweevil slice](PIKMIN2_DWEEVIL_NATIVE.md)).

## 1. Scope

Delivered:

- `native/pc_port/pc_p2_hiba_policy.h` — engine-free mirror of the
  fixed-hazard section of the Python model: per-hazard state IDs, disc vs
  header timings, Wait -> Attack activation, Hiba/GasHiba emission gates, the
  ElecHiba Wait -> Sign -> Attack -> Wait chain, two-node separation,
  team-head damage routing, bridge/gate link owner, versus attribute modes,
  panic subtypes, receiver colour immunity, and a strict
  `P2_HIBA_NATIVE_1` sidecar reader.
- `native/pc_port/pc_p2_hiba.{h,cpp}` — sidecar-gated runtime for Hiba (20),
  GasHiba (21) and ElecHiba (22) on a bounded 30 Hz clock; inert when
  `p2-hiba-native.txt` is absent, fail-closed when malformed.
- Additive registration: `PC_PORT_SOURCES` in `native/CMakeLists.txt`,
  `pc_p2_hiba_setup()` in `pc_p2_preview_setup()`, `pc_p2_hiba_reset()` in the
  three `TekiMgr` reset paths, `pc_p2_hiba_update()` in `GameCoreSection::update`.
- `tests/pikmin2_hiba_policy.cpp` — strict standalone policy test
  (`-Wall -Wextra -Werror`).
- `tests/test_pikmin2_hiba_native.py` — protocol, synthetic-gate, Python-model
  consistency and native compile/run checks.
- `experimental/pikmin2_hiba_runtime.py` — root harness mirroring the dweevil
  harness (`build`/`run`/`play`).

## 2. Source anchors

Decompilation revision `632af93787b9c95b63f0c13be32b161375ce3a96`
(`native/pikmin2-research`, read-only), audit
`docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md`:

| Behavior | Anchor |
|---|---|
| Hiba Dead/Wait/Attack, emission | `HibaState.cpp:14-20,127-159` |
| GasHiba attack-start gate and finish condition | `GasHibaState.cpp:129-169` |
| GasHiba bridge/gate living link | `GasHiba.cpp:193-296,204-272` |
| ElecHiba Dead/Wait/Sign/Attack chain | `ElecHibaState.cpp:13-20,93-131,145-198,204-268` |
| ElecHiba +/- separation nodes | `ElecHibaMgr.cpp:110-131` |
| ElecHiba team-head damage / invulnerability | `ElecHiba.cpp:139-157,752-776` |
| Versus attribute discharge mode | `ElecHiba.cpp:264-329,307-324` |
| Receiver colour immunity | `src/plugProjectKandoU/interactPiki.cpp:334,445,503,531` |

Retail disc proper blocks used by the driver: Hiba wait 3.0 / active 2.5,
GasHiba wait 0.0 / active 3.0 / attack-start 0.6, ElecHiba wait 1.5 /
warning 1.5 / active 2.5 (`docs/PIKMIN2_DWEEVIL_ASSETS.md` lines 153-166).
Header build-time defaults are kept distinct and asserted in the policy test.

## 3. Sidecar contract

Absent `p2-hiba-native.txt` means inert. A present but malformed file fails
closed (`P2_HIBA invalid profile` + `abort()`). The grammar mirrors the C++
reader and the Python `protocol()` serializer:

```text
P2_HIBA_NATIVE_1
<hazardCount>                                                                 # 1..8
<generatorId> <hazardId> <x> <y> <z> <yaw> <health> <waitOverride> <separation> <link>
                                                                              x hazardCount
```

`hazardId` is 20/21/22; `waitOverride < 0` uses the disc wait; `separation`
must be 0 unless ElecHiba; `link` (0 none, 1 bridge, 2 gate, 3 bridge+gate)
must be 0 unless GasHiba. `waitOverride` gives the fixture a short activation
without changing the store defaults.

## 4. Receiver application

The element is applied through receivers this P1 port actually owns. Hiba's
fire uses the engine `InteractFire` path (`interactBattle.cpp:191-205`,
`TAIhibaA.cpp:30-32`): `piki->stimulate(InteractFire(owner, damage))`; Red is
rejected by the receiver and the run logs `P2_HIBA_PASS`. This is the same
generic receiver P1 uses; no generic damage/physics or lane-20 blast primitive
was changed.

This P1 base has **no** `InteractGas`/`InteractDenki` class (they exist only in
the P2 decompilation), so a vulnerable target for GasHiba/ElecHiba is logged
`P2_HIBA_APPLY_BLOCKED ... reason=no_engine_interaction` after the policy
receiver decision. That blocked apply is explicitly labeled; the activate and
emit gates for all three hazards still execute.

Markers emitted:

- `P2_HIBA_READY | ACTIVATE | SIGN | DEACTIVATE | EMIT | DEAD | LINKED | NODES`
- `P2_HIBA_HIT ... applied=1` (vulnerable, engine receiver applied)
- `P2_HIBA_PASS ... immune=1 applied=0` (colour-immune pass)
- `P2_HIBA_APPLY_BLOCKED ... applied=0` (vulnerable, no engine receiver)
- `P2_HIBA_CLEANUP kill_all=1`

## 5. Fixture baseline and gates

`experimental/pikmin2_hiba_runtime.py run` stages the original P1 practice
course into the existing `chal0` experimental slot via the squad overlay
(5 red / 5 blue), sets `p2-cargo-free.txt`, and launches the private
replacement-main fixture with `PIKMIN_P2_ROOM_WINDOW=960x540` (#404 baseline:
`P2_HIBA_BASELINE red=5 blue=5`, `Experimental preview window set to 960x540
windowed and centered`). The hazards are placed on the live-Pikmin centroid at
`ready==30` (labeled) so the receivers are deterministic. One bounded scenario
(`P2_HIBA_SCENARIO hiba_gas_elec`) proves all four gates:

| Gate | Evidence | Status |
|---|---|---|
| activate | `P2_HIBA_ACTIVATE` for Hiba, GasHiba, ElecHiba | **PASS** |
| emit | `P2_HIBA_EMIT` for InteractFire/Gas/Denki | **PASS** |
| vulnerable-hit | `P2_HIBA_HIT ... colour=Blue ... applied=1` (Hiba/fire) | **PASS** |
| immune-pass | `P2_HIBA_PASS ... colour=Red ... immune=1` (Hiba/fire) | **PASS** |

Gas and denki *engine application* is BLOCKED (no interaction class); their
policy receiver decision is emitted. The fixture self-terminates on gate
satisfaction or on a bounded behavior-tick timeout with
`P2_HIBA_BLOCKED <gate> reason=timeout`. This worker only built the fixture;
the coordinator owns the serialized GL run.

## 6. Remaining work / BLOCKED

- **GasHiba/ElecHiba engine receivers**: no `InteractGas`/`InteractDenki` in
  this P1 base; their vulnerable apply is BLOCKED pending a receiver audit /
  implementation. Do not copy Pikmin colour rules into captain or enemy
  receivers.
- **GasHiba bridge/gate living gate**: the policy owner is implemented and the
  runtime honors a configured `link` as a non-living state until cleared, but
  the fixture stages `link=0`; `setInitLivingThing` link transitions are not
  reproduced (RECONSTRUCTED in the policy).
- **ElecHiba versus counter/mode persistence** across area reloads is
  RECONSTRUCTED in the policy and not exercised.
- **Visuals/effects/collision**: no Hiba/GasHiba/ElecHiba model, particle
  cylinder, wire team actor, culling or LOD; the hazards are position/FSM
  simulations.
- **Death/corpse and re-entry cleanup**, and the hazard `stop` timing, remain
  open.
- No runtime/gameplay acceptance is claimed by this worker; only build, policy
  test and fixture-build evidence.
