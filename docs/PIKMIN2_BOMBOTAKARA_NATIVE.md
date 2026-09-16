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

## 3. Shared blast status — wired on the maintained line (#447, approved-base rebase)

The shared Bomb/BlastSarai primitive now exists on the maintained line
(`pc_port/pc_p2_bombsarai_blast.{h,cpp}`, projectiles/BombSarai lane #169). The
rebased BombOtakara module consumes it instead of emitting a blocked marker:

- each detonation builds a `P2BombSaraiBlastEvent`
  (`center = payload xyz`, retail Bomb parms `radius 90` fp22, `halfHeight 50`
  fp02, `tekiDamage 500` fp01, `naviPikiDamage 10` fp24 — the pinned values from
  the lane-20 tests),
- enumerates live Pikmin and the captain, calls `p2_bombsarai_route_blast`, and
  applies the source Bomb's `InteractBomb` to each routed hit,
- a carrierless BombOtakara blast is attributed to the bomb itself, so a
  stateless module-local `Creature` positioned at the blast center is the
  `InteractBomb` owner (the receiver dereferences `mOwner->mSRT.t`,
  `interactBattle.cpp:63`).

No duplicate blast is implemented; generic damage/physics is otherwise
untouched.

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
  total_detonations=1`, followed by `P2_BOMBOTAKARA_BLAST ... shared_primitive=1`
  (routed hits applied through `InteractBomb`);
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
| shared-blast | `P2_BOMBOTAKARA_BLAST ... shared_primitive=1` x2, `pikmin_hits>=1` | **PASS** |

The fixture self-terminates on gate satisfaction or a bounded behavior-tick
timeout with `P2_BOMBOTAKARA_BLOCKED gates reason=timeout`. This worker only
built the fixture; the coordinator owns the serialized GL run.

## 7. Remaining work / BLOCKED

- **Shared blast application** — **wired** on the maintained line via
  `pc_p2_bombsarai_blast.h` (projectiles lane #169); the detached Bomb enemy
  binding and a real payload `EnemyID_Bomb` actor (for a non-synthetic
  `InteractBomb` owner) remain open.
- **Real Bomb enemy binding** — the payload is a sidecar stub; binding a real
  `EnemyID_Bomb` teki/creature and its `mCarrier` linkage is open.
- **Visuals/effects/collision** — no BombOtakara or Bomb model, fuse effect or
  explosion visuals.
- **Earthquake / bittered runtime paths** — the policy decision covers them and
  the test asserts them, but the fixture only exercises contact and death.
- **Death/corpse and re-entry cleanup** beyond the fixture `kill_all` marker.
- No natural gameplay acceptance is claimed; the bounded injected GL run below
  passed, but real Bomb binding and the shared blast remain open.

## 8. Runtime evidence (bounded, labeled injections)

GL run `output/p2-lane22-bombotakara-run-02/bombotakara/a80087ca19844aab96f14e77cdc3fc43`
(fixture `output/p2-lane22-bombotakara-fixture-02/build/fixture.exe` SHA-256
`d589ebd263495b8322f6022d5b6e3858bf5214cbb2baa9f9b83aeb74e87aca54`), validator
all-true (`completion`, `baseline`, `window`, `carry`, `arm`,
`detonate_contact`, `detonate_death`, `exactly_two_detonations`,
`suppressed_contact`, `suppressed_death`, `exactly_two_suppressed`,
`blast_blocked`, `cleanup`, `no_timeout`, `no_rewards`):

```text
P2_BOMBOTAKARA_ARM generator=30 payload=40 arm_seconds=1.50 source=stimulateBomb
P2_BOMBOTAKARA_DETONATE generator=30 payload=40 trigger=contact detonated=1 exactly_once=1 total_detonations=1
P2_BOMBOTAKARA_BLAST_BLOCKED generator=30 payload=40 reason=no_shared_blast
P2_BOMBOTAKARA_DETONATE generator=31 payload=41 trigger=death detonated=1 exactly_once=1 total_detonations=1
P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=31 payload=41 trigger=death detonated=0 already_detonated=1
PASS P2_BOMBOTAKARA_RUNTIME gates_ready
```

The bomb stub, placements and contact/death triggers are labeled injections;
the shared blast application remains BLOCKED (no shared interface at this
base). No natural gameplay acceptance is claimed.

## 9. Approved-base rebase: shared blast wired (maintained line)

Rebased onto the current maintained native (`codex/p2-main-review-native` head
`c223f442`), which now carries the shared BombSarai blast:

- Native `opencode/p2-lane22-blast` @ `0d29450363da77ebb9d36119c75d8badbe029509`
  (base `c223f442`; never pushed). Module files `pc_p2_bombotakara.{h,cpp}` and
  `pc_p2_bombotakara_policy.h` plus additive hooks; private build
  `output/p2-lane22-blast-build`, 548/548 link, `ninja -n pikmin_pc` no work.
- Fixture `output/p2-lane22-root/output/p2-lane22-blast-fixture-01/build/fixture.exe`,
  provenance status `built`, expected native head `0d294503`.
- GL run `output/p2-lane22-root/output/p2-lane22-blast-runtime-02/bombotakara/d17ab182d2b6464f854b1a7d1cc413af`
  PASS:

```text
P2_BOMBOTAKARA_DETONATE generator=30 ... trigger=contact detonated=1 exactly_once=1 total_detonations=1
P2_BOMBOTAKARA_BLAST generator=30 ... radius=90.0 receivers=11 hits=10 pikmin_hits=10 teki_damage=500.0 navi_piki_damage=10.0 shared_primitive=1
P2_BOMBOTAKARA_BLAST generator=31 ... radius=90.0 receivers=11 hits=10 pikmin_hits=10 teki_damage=500.0 navi_piki_damage=10.0 shared_primitive=1
PASS P2_BOMBOTAKARA_RUNTIME gates_ready
```

The two blasts route through the shared primitive and apply `InteractBomb` to 10
live Pikmin each (observed engine damage, not a predicted log). The blast owner
is a labeled module-local bomb-position `Creature` because the module has no
payload `EnemyID_Bomb` actor yet. The response-file fixture-builder fix
(`scripts/build_pikmin2_fixture.py`) is shared with the lane-23 handoff.
