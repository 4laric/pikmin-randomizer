# Lane 22 fixed-hazard native slice

> Integration disposition: opt-in native diagnostic module integrated with corrections; see [Hiba sweep](PIKMIN2_HIBA_INTEGRATION_437.md) for current validation and open gates. Worker runtime evidence below remains pinned to its recorded executable.

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
<generatorId> <hazardId> <x> <y> <z> <yaw> <health> <waitOverride> <separation> <link> <warningOverride>
                                                                              x hazardCount
```

`hazardId` is 20/21/22; `waitOverride < 0` uses the disc wait; `warningOverride
< 0` uses the disc ElecHiba warning; `separation` must be 0 unless ElecHiba;
`link` (0 none, 1 bridge, 2 gate, 3 bridge+gate) must be 0 unless GasHiba;
`warningOverride >= 0` applies only to ElecHiba. `waitOverride` gives the fixture
a short activation without changing the store defaults; `warningOverride` lets
the fixture make ElecHiba attack promptly (before the gas-cluster panic-run).

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
- No natural gameplay acceptance is claimed; the bounded injected GL run below
  passed, but visuals/effects/collision and cleanup remain open.

## 7. Runtime evidence (bounded, labeled injections)

GL run `output/p2-lane22-hiba-run-02/hiba/96648387b6c64688afd207bbc078e49d`
(fixture `output/p2-lane22-hiba-fixture-02/build/fixture.exe` SHA-256
`b0656881ecfc88adffb90b16d8d55a25946ade852d0d418f82d9df0353e9a98f`), validator
all-true (`completion`, `baseline`, `window`, `activate_hiba/gas/elec`,
`emit_hiba/gas/elec`, `vulnerable_hit`, `immune_pass`, `gas_blocked`,
`cleanup`, `cleanup_dead`, `no_timeout`):

```text
P2_HIBA_ACTIVATE generator=20 hazard=Hiba from=wait to=attack
P2_HIBA_EMIT generator=20 hazard=Hiba stimulus=InteractFire
P2_HIBA_HIT generator=20 hazard=Hiba stimulus=InteractFire colour=Blue immune=0 applied=1 damage=1.0
P2_HIBA_PASS generator=20 hazard=Hiba stimulus=InteractFire colour=Red immune=1 applied=0
P2_HIBA_APPLY_BLOCKED generator=21 hazard=GasHiba stimulus=InteractGas colour=Red immune=0 applied=0 reason=no_engine_interaction
PASS P2_HIBA_RUNTIME gates_ready
```

Hazard placement on the live-Pikmin centroid is a labeled injection; the
GasHiba/ElecHiba engine apply remains BLOCKED (no interaction class at this
base). The redirect says to distinguish predicted log gates from observed
runtime passes: the Hiba fire receiver is an observed engine receiver pass; the
Gas/Denki policy decisions are predicted/blocked, not applied. No natural
gameplay acceptance is claimed.

## 8. Rebased delta on the approved native baseline (f14c6851)

Per `PIKMIN2_PREWAVE_REVIEW_437.md` §2, the exact native Hiba delta now sits on
the approved native baseline `f14c6851473ac1161be56c8b98f4f905232f3635` (which
already carries the current Jellyfloat receiver work), so the integrated root
harness can actually run its actor:

- Branch `opencode/p2-lane22-hiba-f14c` @
  `f139d2645ce10243feb8084a2df3c53c29dcb255` (base `f14c6851`; never pushed).
- Files: `pc_port/pc_p2_hiba.{h,cpp}`, `pc_port/pc_p2_hiba_policy.h`,
  `pc_port/pc_p2_dweevil_policy.h` (shared pure policy header; the dweevil
  runtime cpp is **not** included), plus additive registration in
  `CMakeLists.txt`, `pc_port/pc_p2_preview.cpp`,
  `src/plugPikiKando/gameCoreSection.cpp` and
  `src/plugPikiNakata/tekimgr.cpp` (3 teardown paths).
- Private build `output/p2-lane22-hiba-f14c-build`, Ninja Release, JAudio ON;
  full 545/545 link, `ninja -n pikmin_pc` no work.
- Fixture `output/p2-lane22-root/output/p2-lane22-hiba-f14c-fixture-01/build/fixture.exe`
  SHA-256 `8155eacc31caa09636fd6bd5fb729af5c57e1066ddd3dfa27097609037c74142`,
  `provenance.json` status `built`, expected native head `f139d264`.
- GL run `output/p2-lane22-root/output/p2-lane22-hiba-f14c-runtime-01/hiba/d01036c96d2149629f99b737689018e7`,
  validator all-true (`completion`, `baseline`, `window`, `scenario`, `ready`,
  `activate_hiba/gas/elec`, `emit_hiba/gas/elec`, `vulnerable_hit`,
  `immune_pass`, `gas_blocked`, `cleanup`, `cleanup_dead`, `no_timeout`).

This clears the integration blocker for the Hiba fixture. The remaining lane-22
gaps (dweevil engine actor binding, BombOtakara shared blast, visuals/effects)
are unchanged.
