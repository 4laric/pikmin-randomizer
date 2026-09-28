# Catfish26 natural-kill prerequisite packet (#800)

Lane `catfish26-natural-kill-prereq-discovery` (enemies-5 cycle 34 recovery for
the blocked observer `shard-enemies-5-catfish26-observer` #783). Read-only
pin-discovery/diagnosis: no engine, build, launch, runtime or gameplay claim.
All six gates are UNTESTED. No ADMIT.

## Defect (from the #783 handoff, sha ffdea6d7, read-only)

Catfish (Water Dumple, source ID 26, generator 374001) binds, runs its native
KochappyBase FSM and naturally engages the staged squad, but the squad never
kills it, so no natural death edge (gates 4/6) is reachable. Two candidate
prerequisites were recorded: a White-Pikmin stage, or a Pikmin-stickable
Catfish body.

## Source trace (file:line)

| Anchor | Finding |
|---|---|
| `pc_p2_catfish.cpp:374-393` (`swallowEvent`) | Applies the source proper fp02=300 poison: `actor->mHealth -= result.poisonDamage`, preserving the normal InteractKill death/corpse. |
| `pc_p2_catfish.cpp:379` | The poison is gated by `pc_p2_is_white(p)`: only a swallowed White Pikmin poisons the eater. |
| `pc_p2_catfish.cpp:12-20,221-243` | P2 two-slot mouth is not representable on the P1 host; the port body is not Pikmin-stickable (throws land, no latch), so red attack damage is not sustained. |
| `pc_p2_white.cpp:47` | `pc_p2_is_white` requires `pc_p2_whites_enabled()`. |
| `pc_p2_white.cpp:59-77` (`pc_p2_white_setup`) | Requires `p2-white.txt` (line 62) and the `white_*` room models (lines 70,76); absent sidecar disables White and returns. |
| `native/CMakeLists.txt:176-177` | `pc_p2_white.cpp` + `pc_p2_white_poison.cpp` are already compiled in the maintained wave. |
| `experimental/pikmin2_aquatic_assets.py:32` | Aquatic `SPECIES` = Catfish/Tadpole/Jigumo/UmiMushi; White is not present. |
| `experimental/pikmin2_aquatic_install.py:201` | The aquatic install refuses out-of-manifest species; it never stages `p2-white.txt` or `white_*`. |

Verified this turn: neither `p2-white.txt` nor any `white_wait/walk/attack1/happa`
model exists anywhere in-repo. The catfish module (`pc_p2_catfish.cpp`) exists
only in the family private native trees, not the maintained `native/` checkout.

## Producer decision

**`catfish26-stickable-receiver-native`** (Pikmin-stickable Catfish receiver
registration, family-native engine change) is the exact in-repo producer.

- Rationale: the White-Pikmin path is source-faithful and its poison is already
  implemented, but it is **not executable**: it needs the retail `white_*` room
  models, which are a **user-owned asset** (and the species is owned by the open
  backlogs #131/#395). Authoring `p2-white.txt` alone is insufficient.
- The receiver path needs no retail assets: register the bound Catfish as a
  Pikmin-attack receiver so latched red throws deliver sustained
  `InteractAttack` damage to `mHealth` while preserving the KochappyBase FSM.

### Contract

- Producer lane: `catfish26-stickable-receiver-native` (family-native).
- Callsites: `native/pc_port/pc_p2_catfish.cpp` (bind/receiver registration),
  `native/pc_port/pc_p2_catfish.h` (declaration).
- Build membership: `native/CMakeLists.txt` (add/confirm the catfish module).
- First executable slice: register the receiver and prove latched red throws
  reduce `mHealth` to death; observe `P2_CATFISH_DEAD` + corpse.
- Blocked-on (White path only): `user_asset:retail white_* room models`
  (`p2-white.txt` is authorable).

## Remapped downstream consumer command (#783)

`shard-enemies-5-catfish26-observer` (#783): re-run the guarded observer2
fixture over the batch-2 aquatic arena with red throws (`p2_muse_catfish_fixture.cpp`;
native pin `719160dc`) and read `P2_CATFISH_DEAD` / `P2_CATFISH_CORPSE_READY`,
then the re-entry pass. Expected: one natural kill edge so gates 4 and 6 can be
observed. All other gates remain UNTESTED.

## Captain safety (#632)

N/A: diagnosis only; no runtime run executed, launched or proposed. Any future
runtime consumer in this family must adopt the orimaDead/NaviDead/HP<=1 guard
(`scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) with
CAPTAIN_DOWN/BLOCKED semantics and record adoption hashes.
