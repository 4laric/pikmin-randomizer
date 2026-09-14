# Lane 22 BombOtakara payload native slice

Issue [#170](https://github.com/4laric/pikmin-randomizer/issues/170), child
#447. Root behavior model: `experimental/pikmin2_elemental_behavior.py`
(branch `opencode/p2-lane22-elemental`). This slice adds the BombOtakara (93)
payload after the [dweevil capture/drop](PIKMIN2_DWEEVIL_NATIVE.md) and
[fixed-hazard](PIKMIN2_HIBA_NATIVE.md) slices.

## 1. Scope

Delivered:

- `native/pc_port/pc_p2_bombotakara_policy.h` — engine-free mirror of the
  BombOtakara section of the Python model: shared OtakaraBase Bomb-carry state
  IDs, the `stimulateBomb` 1.5 s force delay, the payload decision
  (`kill_carrier`/`force_bomb`/`damage_payload`/`chase_payload`), exactly-once
  detonation, trigger names, and a strict `P2_BOMBOTAKARA_NATIVE_1` sidecar
  reader.
- `native/pc_port/pc_p2_bombotakara.{h,cpp}` — sidecar-gated runtime: the
  carrier is born holding a sidecar-staged Bomb stub (labeled), arms through
  the 1.5 s force delay, and detonates exactly once on contact/press or death.
  Inert without `p2-bombotakara-native.txt`; malformed fails closed.
- Additive registration: `PC_PORT_SOURCES`, `pc_p2_bombotakara_setup()` in
  `pc_p2_preview_setup()`, `pc_p2_bombotakara_reset()` in the three `TekiMgr`
  reset paths, `pc_p2_bombotakara_update()` in `GameCoreSection::update`.
- `tests/pikmin2_bombotakara_policy.cpp` — strict standalone policy test
  (`-Wall -Wextra -Werror`).
- `tests/test_pikmin2_bombotakara_native.py` — protocol, synthetic-gate,
  Python-model consistency and native compile/run checks.
- `experimental/pikmin2_bombotakara_runtime.py` — root harness
  (`build`/`run`/`play`).

## 2. Source anchors

Decompilation revision `632af93787b9c95b63f0c13be32b161375ce3a96`
(`native/pikmin2-research`, read-only), audit
`docs/PIKMIN2_ELEMENTAL_ENEMY_AUDIT.md`:

| Behavior | Anchor |
|---|---|
| Shared Bomb-carry states 11..13 | `OtakaraBase.h:22-39`, `OtakaraBaseState.cpp:14-34,744-907` |
| `initBombOtakara` payload capture on `otakara`, `mCarrier` | `OtakaraBase.cpp:649-677` |
| Birth-drop payload reinit | `OtakaraBase.cpp:321-327` |
| Carrier killed when payload pointer disappears | `OtakaraBaseState.cpp:761-763,816-819,880-882` |
| `stimulateBomb` -> `forceBomb` after 1.5 s | `OtakaraBase.cpp:699-707` |
| Delegated damage / earthquake | `BombOtakara.cpp:42-87` |
| Shared blast ownership (projectiles lane #169) | audit lines 20,30,36 |

Payload ID 36 (`EnemyID_Bomb`) is the separate child, not a duplicate
spawnable (`docs/PIKMIN2_DWEEVIL_ASSETS.md` section 1).

## 3. Shared blast status — BLOCKED

At this base there is **no** `pc_port/pc_p2_bombsarai_bomb.*`,
`pc_p2_bombsarai_blast.*` or `pc_p2_projectiles*` module, and no Bomb teki: the
P1 engine only has the Pikmin-thrown bomb-rock item (`include/BombItem.h`) and
the King actor's labeled actor-local bomb stub. There is therefore no shared
blast/explosion interface to consume. Per the lane instruction the runtime does
**not** implement a duplicate blast: each detonation emits

```text
P2_BOMBOTAKARA_BLAST_BLOCKED generator=<id> payload=<id> reason=no_shared_blast
```

and the actual area-blast application stays **BLOCKED** pending the projectiles
lane contract. Generic damage/physics is untouched.

## 4. Sidecar contract

Absent `p2-bombotakara-native.txt` means inert. A present but malformed file
fails closed (`P2_BOMBOTAKARA invalid profile` + `abort()`). Grammar (mirrored
by the C++ test and Python `protocol()`):

```text
P2_BOMBOTAKARA_NATIVE_1
<unitCount>                                                       # 1..4
<generatorId> <x> <y> <z> <yaw> <health> <payloadId> <bx> <by> <bz>   x unitCount
```

`generatorId`/`payloadId` are unique across the profile. The optional fixture
injection file `p2-bombotakara-inject.txt` is a sequence of
`P2_BOMBOTAKARA_INJECT_1 <tick> <generatorId> <contact|press|death|earthquake|payload_lost>`
lines and is never present in a normal run.

## 5. Exactly-once evidence design

Each unit starts `carrying=true` (the payload is captured on the `otakara`
joint at birth) and logs `P2_BOMBOTAKARA_CARRY`. The `stimulateBomb` delay
accrues at 30 Hz and at 1.5 s logs `P2_BOMBOTAKARA_ARM`. A trigger calls
`detonate(payloadPresent, alreadyDetonated)`:

- first trigger -> `P2_BOMBOTAKARA_DETONATE ... detonated=1 exactly_once=1
  total_detonations=1`, followed by `P2_BOMBOTAKARA_BLAST_BLOCKED
  reason=no_shared_blast`;
- any later trigger -> `P2_BOMBOTAKARA_DETONATE_SUPPRESSED ... detonated=0
  already_detonated=1`.

A `payload_lost` injection instead logs `P2_BOMBOTAKARA_PAYLOAD_LOST` +
`P2_BOMBOTAKARA_KILL_CARRIER` (payload decision `kill_carrier`).

## 6. Fixture baseline and gates

`experimental/pikmin2_bombotakara_runtime.py run` stages the original P1
practice course into the existing `chal0` experimental slot via the squad
overlay (5 red / 5 blue), sets `p2-cargo-free.txt`, and launches the private
replacement-main fixture with `PIKMIN_P2_ROOM_WINDOW=960x540` (#404 baseline).
Two carriers are placed on the live-Pikmin centroid at `ready==30` (labeled).
Carrier 30 is triggered by contact (ticks 75, 105), carrier 31 by death
(ticks 90, 120). One bounded scenario
(`P2_BOMBOTAKARA_SCENARIO carry_arm_detonate`) proves:

| Gate | Evidence | Status |
|---|---|---|
| carry | `P2_BOMBOTAKARA_CARRY` x2 | **PASS** |
| arm | `P2_BOMBOTAKARA_ARM arm_seconds=1.50` x2 | **PASS** |
| detonate | `P2_BOMBOTAKARA_DETONATE` contact x1 + death x1, `detonated=1 exactly_once=1` | **PASS** |
| exactly-once | `P2_BOMBOTAKARA_DETONATE_SUPPRESSED already_detonated=1` x2 | **PASS** |
| shared-blast | `P2_BOMBOTAKARA_BLAST_BLOCKED reason=no_shared_blast` x2 | **BLOCKED** |

The fixture self-terminates on gate satisfaction or a bounded behavior-tick
timeout with `P2_BOMBOTAKARA_BLOCKED gates reason=timeout`. This worker only
built the fixture; the coordinator owns the serialized GL run.

## 7. Remaining work / BLOCKED

- **Shared blast application** — BLOCKED; wire to the projectiles-lane (#169)
  bomb/blast primitive when it lands. Do not fork it here.
- **Real Bomb enemy binding** — the payload is a sidecar stub; binding a real
  `EnemyID_Bomb` teki/creature and its `mCarrier` linkage is open.
- **Visuals/effects/collision** — no BombOtakara or Bomb model, fuse effect or
  explosion visuals.
- **Earthquake / bittered runtime paths** — the policy decision covers them and
  the test asserts them, but the fixture only exercises contact and death.
- **Death/corpse and re-entry cleanup** beyond the fixture `kill_all` marker.
- No runtime/gameplay acceptance is claimed by this worker; only build, policy
  test and fixture-build evidence.
