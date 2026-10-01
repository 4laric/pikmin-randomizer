# Pikmin 2 BigTreasure (Titan Dweevil) weapon ownership and teardown contract — issue #246

Implementation owner: Codex using shared account 4laric. Parent: #175;
integration contract: #186; roadmap tier 8: #197. Follows the source audit in
[PIKMIN2_BIGTREASURE_AUDIT.md](PIKMIN2_BIGTREASURE_AUDIT.md) and applies the
\#169 Groink standalone-policy pattern
([PIKMIN2_GROINK_PROTOTYPE.md](PIKMIN2_GROINK_PROTOTYPE.md)). This is an
isolated policy milestone: no native actor, hook, placement, converter or
gameplay claim. Source semantics reference US GPVE01 rev 0 at research
revision `632af93787b9c95b63f0c13be32b161375ce3a96`. The model/motion
converter handoff (including the four weapon models) remains gated on #128
and is deferred.

## Module

The lane-owned independent files are `pc_port/pc_p2_bigtreasure.h/.cpp` and
`tools/p2_bigtreasure_test.cpp` in the native repository. They add no shared
hooks and no converter/build changes; root serializes shared
hooks/converter/build/export per the issue. All randomness enters as explicit
host-supplied values (`randWeightFloat` inputs), fixtures are deterministic,
and ticks are the 30 Hz source rate — never wall clock. A future host
integration supplies the terrain/sphere-trace adapter for elec/water
ballistics (same host-terrain-adapter shape as the Groink shell trace) and
owns actors, damage receivers, sound and effects.

## Ownership contract

- The four weapons (`elec`/`fire`/`gas`/`water`) and Louie (`loozy`) are
  dependent captured pellet actors. The boss is the sole owner
  (`mTreasures[4]`, `mLouie`; `BigTreasure.cpp:703-742`); only the owner
  drives capture updates, damage, knock-off and release. No shared writes.
- Knock-off: weapon HP 6000 → 0 releases the pellet with `endCapture` and an
  upward pop of 100; from there generic cargo (pellet carry) rules apply
  (`BigTreasure.cpp:788-818`). Louie is never dropped by damage; death
  releases it at pop 150 (`BigTreasure.cpp:912-920`).
- Body exposure: weapon coll parts are neutralized on knock-off and
  `tam1`/`tam2` become damageable only when all four weapons are gone
  (`setupBigTreasureCollision`, `BigTreasure.cpp:670-697`). Pikmin-source
  damage with a collision part is the only route; Land quarters damage;
  bitter cuts weapon damage to 0.1× (`BigTreasure.cpp:248-275,864-887`).
- Phase transitions are per weapon at HP 3000: pinch smoke fires on the
  downward crossing (starting ≥ 3000, result < 3000) and the damaged attack
  parameter set applies at health ≤ 3000 (strict `>` in `isNormalAttack`,
  `BigTreasure.cpp:1200-1203`). Global escalation is the remaining-weapon
  count (BGM steps, body exposure).
- Next-weapon pick is health-weighted: weight 12000 − HP per live weapon,
  bands in elec/fire/gas/water order (`BigTreasure.cpp:984-1035`).
- Attack pacing: threshold 4 + 2 × liveWeapons seconds, 3× accrual with an
  unstuck outsider nearby, attack allowed only with a live target inside the
  225-unit XZ box (`BigTreasure.cpp:356-403`).
- Pooled attack nodes: 8 fire / 200 gas / 16 water / 17 elec
  (`BigTreasureAttack.cpp:1043-1097`). Emission fails softly at exhaustion.
  Elec invariant: 1 invisible anchor + maxDischarge ≤ 17, preserved by
  `setElecMaxDischarge` (`BigTreasureAttack.cpp:2712-2782`).
- Weapon-loss guards (ItemWait/PreAttack/Attack/PutItem): losing every weapon
  exits to DropItem; losing the chosen weapon mid-charge/attack re-enters
  PreAttack and re-picks (`BigTreasureState.cpp:375-377,497-505,573-581,642-650`).

## Lane teardown policy for the three source gaps

1. **Weapons still captured at death** (never released in source): on defeat
   the owner releases every captured weapon with the standard knock-off pop
   (endCapture + (0,100,0)), then Louie at its source pop of 150. No captured
   pellet may outlive its owner; this keeps the multi-actor lifetime bounded
   as the import pipeline requires.
2. **In-flight water bubbles survive `finishWaterAttack()`** (empty in
   source): preserved verbatim for normal state exits — bubbles keep flying
   and hitting until ground impact. On defeat the lane force-recycles
   in-flight bubbles with no hit events, because the attacker is dying and
   damage attribution would be invalid.
3. **`hipdropCallBack` returns the negation of `damageCallBack`**
   (`BigTreasure.cpp:281-284`): preserved exactly (`== P2BTDMG_Ignored`),
   including the "sure." oddity, so host hip-drop reporting matches source.

## Fixtures and evidence

Fixtures in `tools/p2_bigtreasure_test.cpp` cover: per-weapon phase
transition at 3000 (including the exact-3000 boundary), knock-off and
zero-weapon body exposure, Pikmin-only/coll-part/Land/bitter damage routing,
health-weighted pick band boundaries, attack pacing thresholds and 3×
accrual, weapon-removed-mid-attack FSM guards, defeat with weapons remaining,
pool exhaustion per element, the elec 17-node invariant, water persistence
across `finishAttack` plus defeat teardown, and the full multi-actor lifetime
(five captured pellets + pooled nodes).

Build and run (local MinGW, matching the Groink lane's command shape; binary
kept in the untracked local `output/` directory):

```powershell
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_test.cpp pc_port/pc_p2_bigtreasure.cpp -o <private-output>/p2_bigtreasure_test.exe
```

Result: compiles warning-clean under `-Wall -Wextra -Werror`; all 11 fixture
groups pass (`p2_bigtreasure_test: all fixtures passed`, exit 0). Two fixture
corrections were needed against source semantics: exactly-3000 weapon health
already selects the damaged parameter set (strict `>`) while pinch smoke
fires when dipping *below* 3000 from ≥ 3000, and the pacing threshold is a
strict `>` comparison.

## Deferred and open items

- Model/motion/parameter converter handoff for boss + four weapon models:
  gated on #128, deferred per the issue slice.
- Projectile ballistics (fire sweep, gas arms, water arc, elec bounce/chain)
  need the host terrain/trace adapter and per-element runtime acceptance;
  this milestone covers ownership, pools and lifetimes only.
- Pellet configs (carry weights) and `mPelletDropCode` finale treasure are
  disc data (audit open questions Q1/Q5); native save/persistence behavior
  (Q4) remains unverified.
- Arena staging under #186 (fixed placement first, mixed levels later per
  the boss staged-phases gate) and native compile against the frozen host
  remain future slices; root owns any shared boss/weapon hook requests.
