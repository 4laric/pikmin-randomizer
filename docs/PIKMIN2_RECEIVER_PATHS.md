# P2 attack, immunity and death receiver paths (receivers lane, #408)

Receivers lane of [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md),
parent [#170](https://github.com/4laric/pikmin-randomizer/issues/170), child
[#408](https://github.com/4laric/pikmin-randomizer/issues/408). This document
resolves the recorded batch-3 result "FireOtakara host accepts the injected
`InteractAttack` but takes no damage" and records the runtime proof of the
damage, immunity and death paths on this port.

Base: root `1feade3` (integration-approved engine export; contains the
starting-squad overlay `a51b301` and native export `541bfba`) plus the batch-3
north runtime commits (`47af621`, `10d6f73`, `c396caa`). Native
`opencode/p2-batches134-native` @ `356e9c08ad5c681be0d00232cd31d0409fee50ea`
(contains window change `1d5a242b` and the `_ACTORS_1` parse fix). No source
behavior, family FSM or shared semantics were changed.

## 1. Attack resolution is queue-then-apply

An `InteractAttack` does **not** reduce health synchronously. The chain is:

| Step | Anchor |
|---|---|
| `BTeki::stimulate` requires `InteractAttack::actCommon` (visible) | `src/plugPikiNakata/tekibteki.cpp:757`; `src/plugPikiKando/interactBattle.cpp:360` |
| `InteractAttack::actTeki` → `teki->interact(Attack)` | `src/plugPikiNakata/tekiinteraction.cpp:31` |
| `BTeki::interact` → strategy `interact` | `src/plugPikiNakata/tekibteki.cpp:1777` |
| `TekiStrategy::interact` → `interactDefault` | `src/plugPikiNakata/tekistrategy.cpp:72` |
| `BTeki::interactDefault`: invincible early-return, else `mStoredDamage += attack->mDamage`, return true | `src/plugPikiNakata/tekibteki.cpp:1786-1802` |
| `BTeki::makeDamaged`: `mHealth -= mStoredDamage; mStoredDamage = 0` | `src/plugPikiNakata/tekibteki.cpp:788-796` |

`mStoredDamage` is explicitly "damage waiting to be applied on next makeDamaged
call" (`include/teki.h:510`). `makeDamaged` is only called from TAI reaction
actions, e.g. `TaiSimultaneousDamageAction::act`
(`src/plugPikiNakata/taireactionactions.cpp:142-151`),
`TaiCounterattackSimultaneousDamageAction::act` (`:156-170`) and
`TaiDamagingAction` (`:175-191`). Those actions exist only in some states of the
actor's strategy (`TaiChappyStrategy` state table,
`src/plugPikiNakata/taichappy.cpp:327-595`).

Consequences:

- `stimulate(...) == true` ("accepted") only means the damage was queued.
- Health moves only when the current TAI state runs a reaction action. A host
  whose AI stays in a state without one keeps `mStoredDamage` accumulating and
  `mHealth` unchanged.
- Death follows from `makeDamaged` driving `mHealth <= 0` into the dead/dying
  states (`TaiDeadAction` / `TaiDyingAction` / `TaiDyeAction`,
  `taireactionactions.cpp:24-101`).

## 2. The FireOtakara result

The batch-3 fixture injected `InteractAttack(n, nullptr, 100000, false)` on a
`TEKI_Chappy` **placement vehicle**, not a source `OtakaraBase` actor;
`pc_p2_batch2` is visual-only (`P2_BATCH2_BIND ... native_fsm=unimplemented`).
The recorded outcome therefore reflects P1 Chappy AI state at injection time,
not a P2 dweevil receiver or immunity:

- `output/p2-batch3-runtime/runs10/dweevil-a1..a3`: `accepted=1`, `health=130`
  for 160 injected frames — the proxy stayed in a no-reaction state.
- `output/p2-batch3-runtime/runs7/dweevil`: the same FireOtakara reached
  `health=0.0` at `observed=202`.
- Receivers diagnostic on the corrected base (#408): `accepted=1`, health
  `130 -> 0` in 1-2 frames when the state ran a reaction action (below).

State-level diagnostic (`P2_RECV_ATTACK`, receivers fixture):

```text
P2_RECV_ATTACK id=349001 accepted=1 health=130.0 stored=100000.0 state=6 motion=2 invincible=0 observed=200
P2_RECV_ATTACK id=349001 accepted=1 health=0.0   stored=100000.0 state=10 motion=2 invincible=0 observed=201
P2_RECV_ATTACK id=349001 accepted=1 health=0.0   stored=200000.0 state=0  motion=2 invincible=0 observed=202
```

The queued damage is applied on the frame the Chappy TAI enters a reaction
state (here 6 -> 10); accumulated `stored` proves the earlier queueing.

## 3. Runtime proof

Private receivers fixture (`experimental/pikmin2_receivers_runtime.py`, built
against the private native build). Executable SHA-256
`d414b6e99d8459a78130c4403a748501913707d213e4764a5897811b661f03ee`; the in-module
`validate()` gate reports `passed=true` on all six receiver checks.

| Path | Evidence | Result |
|---|---|---|
| live starting squad | `P2_RECV_SQUAD alive=20 reds=20` | PASS (20 reds, valid) |
| valid damage | `accepted=1`, `stored` rises, `health 130 -> 0` | PASS |
| invincibility gate (immunity) | `P2_RECV_IMMUNITY id=349006 pre_invincible=0 accepted=0 health_before=130.0 health_after=130.0` | PASS: with `TEKI_OPTION_INVINCIBLE` set, `interactDefault` rejects the attack and no damage is applied |
| elemental immunity | `P2_RECV_ELEMENT red_fire=0 blue_fire=1 blue_bubble=0 red_bubble=1` | PASS: Red rejects `InteractFire`, Blue rejects `InteractBubble`; the opposite colour accepts |
| death path | health 0 enters `state=0` / `motion=Dead`; `P2_BATCH2_LIFECYCLE` reports dead family actors and the surviving control | PASS |

Evidence roots (private, assets not committed):

- `output/tracks/p2-receivers/runs-recv/stages/83f5c1ce483d4a9181cb05540f9d43ad/`
- `output/tracks/p2-receivers/runs-recv2/stages/0eacad0cc4284733bc1a9f0999d9a090/`
- `output/tracks/p2-receivers/runs-recv3/stages/1e3254618bd4405f9b97bfa1a71d6568/`
- `output/tracks/p2-receivers/runs-recv4/stages/fcd1d954cb61407caec2bf8a325cffd3/` (gated `passed=true`)
- `output/tracks/p2-receivers/runs-recv5/stages/3a75b9a365fb4db58dbdcc61dee18d20/` (gated `passed=true`, incl. elemental immunity)

## 4. Immunity boundary and remaining receivers

- **Runtime-proven here:** the generic invincibility gate in `interactDefault`
  (`tekibteki.cpp:1791-1793`) rejects attacks; `InteractAttack::actCommon`
  additionally gates on `isVisible()`. The port's elemental Pikmin receivers
  also execute: `InteractFire::actPiki` (`interactBattle.cpp:192-206`) rejects
  fire-immune colours and `InteractBubble::actPiki` (`:168-187`) rejects Blue,
  with the opposite colour accepting in the probe. The Navi analogues gate on
  the navi-state `invincible()` (`navi.cpp:2773-2811`).
- **Source-anchored, not yet ported (P2 Gas/Denki and enemy-side):** P2
  elemental immunities live on the Pikmin receiver side in the decompilation
  (`src/plugProjectKandoU/interactPiki.cpp`: `InteractDenki` 334,
  `InteractFire` 445, `InteractBubble` 503, `InteractGas` 531 excludes White
  and checks `gasInvicible`). The port's P1 `InteractAttack::actPiki`
  (`interactBattle.cpp:371-406`) is the analogue actually exercised. See
  [PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md](PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md).
- **Blocked, family-lane:** dweevil elemental discharge receivers, treasure
  damage/forced-drop and BombOtakara payload ownership are not implemented
  (`experimental/pikmin2_batch2_families.py`, dweevil `blocked` map). Source
  `interactCreature` stimuli (Fire/Bubble/Gas/Denki) and reward/drop behavior
  remain owned by the dweevil implementation lane.

No generic routing change was required; this slice adds no shared-semantics
edits and needs no new actor IDs.

## 5. Gates and limitations

| Gate | Result |
|---|---|
| exact spawn | PASS (batch-3 fixture, `349001..349005` at recorded XYZ) |
| autonomous movement/animation | PASS (P1 Chappy proxy) |
| attacks/receivers | damage + invincibility gate PASS; source elemental receivers BLOCKED |
| death/corpse | death PASS; corpse pellet nondeterministic on proxy hosts |
| transport/reward | source-backed BLOCKED (dweevil family lane) |
| cleanup/re-entry | UNTESTED |

Limitations: the subject is the P1 Chappy placement vehicle, not source
`OtakaraBase` behavior; the invincibility probe is an explicit injected
intervention; and the elemental receiver boundary is source evidence only.

## 6. Capability-matrix routing (lanes 10/11 follow-up)

The Pikmin fire/bubble receivers now reject an immune species through the
lane-11 capability matrix (`native/pc_port/pc_p2_species_policy.h`) instead of a
raw P1 colour test, so the same generic routing also covers P2 Bulbmin:

- `InteractFire::actPiki` -> `p2_species_immune(pc_p2_species(piki), P2HazardFire)`
- `InteractBubble::actPiki` -> `p2_species_immune(pc_p2_species(piki), P2HazardWater)`

For Blue/Red/Yellow this is behavior-preserving (matrix gives the same single
immunity). It additionally makes Bulbmin fire- and bubble-immune, matching
`interactPiki.cpp`. The change is in
`src/plugPikiKando/interactBattle.cpp`; private build `[3/3] Linking CXX
executable bin\nectar.exe` (exit 0), `nectar.exe` SHA-256
`2AED74FDB0FAD324D268E10D0D517217B1892CAD5F6473BC879AE2413ED803FE`. It is a
build gate; the new immunity is not yet exercised in a rendered run because no
Bulbmin actor spawns.

## 7. Electric and gas receivers (#170/#408, lane 10)

The port gained the two missing P2 Pikmin hazard receivers, each matching the
source constructor signature and delegating immunity to the same lane-11
matrix:

- `InteractDenki : public Interaction` (`include/Interactions.h`),
  `InteractDenki(Creature*, f32 force, Vector3f* direction)`;
  `actPiki` -> `p2_species_immune(pc_p2_species(piki), P2HazardElectric)`
  (rejects Yellow/Bulbmin). Source `InteractDenki::actPiki`
  (`native/pikmin2-research/src/plugProjectKandoU/interactPiki.cpp:334,347`)
  derives from source `InteractWind`; this port's `InteractWind` has a different
  constructor, so the receiver derives from `Interaction` and carries
  `mDamage`/`mDirection`. A `actNavi` analogue mirrors `InteractFire::actNavi`
  (source `interactNavi.cpp:85`).
- `InteractGas : public Interaction` (`include/Interactions.h`),
  `InteractGas(Creature*, f32 damage)`; `actPiki` ->
  `p2_species_immune(pc_p2_species(piki), P2HazardGas)` (rejects White/Bulbmin).
  Source `InteractGas::actPiki` (`interactPiki.cpp:531,543`).

Implementations: `src/plugPikiKando/interactBattle.cpp` (`actPiki`) and
`src/plugPikiKando/navi.cpp` (`InteractDenki::actNavi`). Additive only; the
existing fire/bubble interactions are unchanged.

**Missing-state blocker at this point (since resolved, see §9).** At the time of
§7 the port had no P2 electric or gas state, so non-immune Piki took the closest
existing P1 path and the exact P2 target was logged via `P2_RECV_DENKI` /
`P2_RECV_GAS`:

| Source target | Port status at §7 | Used instead then |
|---|---|---|
| `PIKISTATE_DenkiDying` (`interactPiki.cpp:348-349`) | absent from `include/PikiState.h` enum | `PIKISTATE_Dying` |
| `PIKISTATE_Panic` + `PIKIPANIC_Gas` (`interactPiki.cpp:542,550-552`) | absent; no generic panic state | `PIKISTATE_Fired` (panic run) |
| `Piki::gasInvicible()` / `mGasInvincible` (`include/Game/Piki.h:198,282`) | absent from `include/Piki.h` | no gas-invincibility gate |

§9 added all three. The rest of §7 still describes the receiver routing and LTO
retention, which §9 preserves.

This is a Pikmin-side receiver gate, not a natural hazard encounter: no
`GasHiba`/`ElecHiba`/gas/denki dweevil emitter spawns yet. The receivers are
exercised directly from native state by the receivers fixture (§8). Because no
emitter references the new receivers yet, LTO would dead-strip them (and their
`P2_RECV_*` logs) from the link; the three definitions are marked
`__attribute__((used))` to keep them compiled into `nectar.exe` until an emitter
references them. `nm -C nectar.exe` then shows `T InteractDenki::actPiki`,
`T InteractGas::actPiki`, `T InteractDenki::actNavi` with real addresses, and
both `P2_RECV_DENKI`/`P2_RECV_GAS` literals are present in the image.

Private build: `[520/520] Linking CXX executable bin\nectar.exe` (exit 0),
`nectar.exe` SHA-256
`6C8DFB43812F1E899547D4BFB0F77EF090C66D4051BFB5D7C4C6717537AF3163`;
`ninja -n pikmin_pc` -> `ninja: no work to do.`. Standalone matrix test
`tools/test_p2_elemental_receivers.cpp` -> `PASS P2_ELEMENTAL_RECEIVERS`
(SHA-256 `E535BC0A661D00FF56A73FFD7EE8C244DBB0CC983C7FBECF78D3020CF3508F3F`).

## 8. Electric and gas Pikmin receivers runtime-proven (lane 10 follow-up)

The §7 receivers are now executed from native state without inventing a
`PIKISTATE_Denki`/`Panic`/`gasInvicible` (none exist on this port). The receivers
fixture picks live squad Piki, assigns identity through the native adapter
(`pc_p2_set_species`, which sets the `mP2*` flags), and injects the two new
interactions directly:

- `pick->stimulate(InteractDenki(n, 10.0f, &dir))`
- `pick->stimulate(InteractGas(n, 10.0f))`

Real run (`output/tracks/p2-receivers-sub2/runs-recv/stages/bc3940c92ffa4d05bb237c4388751538`):

```text
P2_RECV_ELEMENT_EXT yellow_species=2 white_species=4 bulbmin_species=5 red_species=1 bulbmin=1 yellow_denki=0 white_gas=0 bulbmin_denki=0 bulbmin_gas=0 red_denki=1 red_gas=1
```

| Field | Meaning | Result |
|---|---|---|
| `yellow_denki=0` | Yellow (2) `InteractDenki::actPiki` rejects -> immune | PASS |
| `white_gas=0` | White (4) `InteractGas::actPiki` rejects -> immune | PASS |
| `bulbmin_denki=0`, `bulbmin_gas=0` | Bulbmin (5) is immune to both | PASS |
| `red_denki=1`, `red_gas=1` | opposite species Red (1) is affected by both | PASS |

The existing fire/bubble `P2_RECV_ELEMENT` check is retained in the same run.
The in-module `validate()` gate now requires `elemental_immunity_ext` (and the
conditional `bulbmin_immunity`) alongside the six original checks; `readings()`
parses the new line. `tests/test_pikmin2_receivers_runtime.py` covers the new
required checks (11 passed).

Evidence:

- Fixture provenance: `scripts/build_pikmin2_fixture.py` against native
  `4f7485d5d5fcfff28fa0f30b63fc2bfe30f48d00` and private build
  `output/native-sub2-elements-build`; `baseline/provenance.json` status `built`.
- Fixture `fixture.exe` SHA-256
  `B74EAEB71D28BE0084C41CBE5D87E121B735ADD23B32ED0BE5D5533890994CFB`.
- Private production build: `[522/522] Linking CXX executable bin\nectar.exe`
  (exit 0), `nectar.exe` SHA-256
  `10C1DC71CDD1482591F9D82F915556F986CB0087CCC2954CBA5439E62DAE5735`;
  `ninja -n pikmin_pc` -> `ninja: no work to do.`.
- Runtime: `exit_code=0`, `PASS P2_RECEIVERS_RUNTIME`, in-module `validate()`
  `passed=true` with `elemental_immunity_ext=true`, `bulbmin_immunity=true`,
  `bulbmin_present=true`. Window/GL:
  `[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)`,
  `Experimental preview window set to 960x540 windowed and centered`.

**Remaining blocker at §8 (state part since resolved, see §9):** no
`ElecHiba`/`GasHiba`/`ElecOtakara`/`GasOtakara` emitter exists to drive the
receiver naturally, so §8 exercised the receivers by direct native injection.
The enemy-side emitters and dweevil discharge/FSM remain family-lane BLOCKED.
This section proves the Pikmin-side immunity gate only.

## 9. P2 electric/gas Pikmin reaction states (lane 10, #170/#408)

§7/§8 left the non-immune receiver path substituting the closest P1 state. This
slice adds the missing P2 states additively and routes the non-immune paths into
them; existing states are unchanged.

| Source | Port (native `2a4521da`) | Behaviour |
|---|---|---|
| `PikiDenkiDyingState` (`include/Game/PikiState.h:236`) | `PikiDenkiDyingState` / `PIKISTATE_DenkiDying` (`PikiState.h`, `pikiState.cpp`) | freezes velocities, plays `PIKIANIM_Dead`, waits 0.3s, then `PIKISTATE_Dead` (the port's kill pipeline; no electric effect/anim exists) |
| `PikiPanicState` + `PIKIPANIC_Gas` (`include/Game/PikiState.h:717`) | `PikiPanicState` / `PIKISTATE_Panic` (`pikiState.cpp`) | gas flavour: panic-run movement (`PIKIANIM_Moeru`), poison timer, then `PIKISTATE_Dying`; raises the gas gate |
| `Piki::gasInvicible()` (`piki.cpp:832`) | `Piki::gasInvicible()` / `setGasInvincible()` / `mGasInvincible` (`Piki.h`) | narrow gate; set while in gas panic, cleared on cleanup |

Both states are registered in `PikiStateMachine::init` (`registerState(new
PikiDenkiDyingState())`, `registerState(new PikiPanicState())`) so transit can
reach them. The receivers consult the new header-only
`pc_port/pc_p2_hazard_reaction.h` (`p2_hazard_reaction`), which keeps the lane-11
`p2_species_immune` matrix and the gas gate in one testable place:

- `InteractDenki::actPiki` -> non-immune, not already dying/dead -> `PIKISTATE_DenkiDying`
- `InteractGas::actPiki` -> not gas-invincible, non-immune -> `PIKISTATE_Panic`

The `P2_RECV_DENKI` / `P2_RECV_GAS` `__attribute__((used))` retention is kept.

Build evidence (private):

```text
cmake --build output/native-sub3-states-build --target pikmin_pc -j 3
# [523/523] Linking CXX executable bin\nectar.exe   (exit 0)
ninja -C output/native-sub3-states-build -n pikmin_pc -> ninja: no work to do.
nectar.exe SHA-256 936E6B5B289B2F3D0F2A7ADFBDB2AD2AADD9AA4BF5D58C7AC6BDD0252572E490
```

`nm -C nectar.exe` shows `T PikiDenkiDyingState::{init,exec,cleanup}`,
`T PikiPanicState::{init,exec,cleanup}`, `T InteractDenki::actPiki`,
`T InteractGas::actPiki`; `strings` retains both `P2_RECV_*` logs and
`DENKI_DYING`. Standalone test `tools/test_p2_hazard_reaction.cpp` ->
`PASS P2_HAZARD_REACTION`. Root anchors: `tests/test_pikmin2_lanes_1012_policies.py`
(`test_p2_hazard_reaction.cpp` gate, plus `test_pikmin_reaction_states_declared_and_registered`,
`test_denki_gas_receivers_route_to_p2_states`, `test_piki_exposes_gas_invincible_gate`)
-> suite 24 passed.

**Still missing (not claimed):** no electricity/gas emitter exists, so no live
encounter was run; these states were exercised only through the reaction table,
the compile/link of `nectar.exe`, and source anchors. `clearDeadlyPikmins`
(`gameCoreSection.cpp:459`) and the death-link exclusion list (`:2120`) do not
yet include `PIKISTATE_DenkiDying`; it is short-lived and self-terminates into
`PIKISTATE_Dead`, but an emitter-backed slice should add it. The panic state is
the gas flavour only; a `StateArg` channel for other panic types is still absent.


