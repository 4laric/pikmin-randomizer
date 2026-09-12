# White Pikmin capability audit (#131 / #155)

Source audit, 2026-09-12. Root base `26c1919e8513d7838ab54a27d390c1570ded6d34`.
Read-only projectPiki/pikmin2 decomp revision
`632af93787b9c95b63f0c13be32b161375ce3a96`, locally under
`native/pikmin2-research`. References below are relative to that source root unless
explicitly called port references. This is implementation groundwork, not native
White support or a completed White Flower Garden playthrough.

## Source behavior contracts

### Species and movement

`include/Game/Piki.h:41` defines Blue=0, Red=1, Yellow=2, Purple=3, White=4,
Bulbmin=5. The stored-species range includes White; the Onion range stops at Yellow.
Do not implement White as a recolored Red with Red storage semantics.

`src/plugProjectKandoU/piki.cpp:715` (`Piki::getSpeed`) first returns the dope
speed when doped. Otherwise it selects maturity-dependent base speed, interpolates
with walk speed using the caller's multiplier, then applies White's run multiplier.
`include/Game/PikiParms.h:103` initializes that multiplier to 2.0. This is a
constructor default, not a measured retail value or a promise that every movement
path is twice as fast. White-specific attack, throw, and carry parameters are
selected at `piki.cpp:880`, `:904`, and `:915` respectively. Defaults are declared
in `PikiParms.h:23`, `:106`, and `include/Game/NaviParms.h:33`.

The carry value participates in `pelletMgr.cpp:4065` and `:4096` via accumulated
`mCarryPower`; it is not sufficient evidence to advertise White as counting for
1.5 Pikmin on a minimum-carrier requirement. Retail parameter extraction and the
full carry-speed/weight calculation remain separate validation work.

### Poison gas immunity and vent interaction

`src/plugProjectKandoU/interactPiki.cpp:531` (`InteractGas::actPiki`) respects gas
invincibility and state invincibility first. If panic transition is permitted,
non-White/non-Bulbmin Pikmin enter `PIKISTATE_Panic` with `PIKIPANIC_Gas` and record
the attacker identity. White and Bulbmin do not take that transition; the interaction
returns false. This is an interaction/state gate, not a large health pool.

`src/plugProjectNishimuraU/GasHiba.cpp:181` constructs `InteractGas` for the hazard.
Its damage callback at `:108` checks a non-captain attacker and vertical bounds;
it does **not** require the attacker to be White. Preserve the distinction between
surviving gas and being allowed to damage the emitter. Pikmin task selection also
has story/discovery-dependent gas-gate checks in `pikiAI.cpp:683`; inspect those
when implementing gate work rather than applying a universal White-only rule.

### Poisoning a predator

`src/plugProjectYamashitaU/enemyAction.cpp:1148` (`EnemyFunc::swallowPikmin`)
iterates attached creatures, requires a Pikmin attached to the mouth and any caller
condition to pass, then sends `InteractKill`. Only successful kill stimulation of
a White invokes `eatWhitePikminCallBack(piki, poisonDamage)`. Mere touching, latching
onto an enemy, or taking an unrelated death path is not this trigger.

`enemyBase.cpp:3293` adds the supplied damage on every callback. The
`EB_EatingWhitePikmin` flag gates the initial damage animation timer, poison
effects, and sound; it does not suppress subsequent damage calls. The shared
swallow path also gates the `g2B_white_poison` discovery movie/flag at
`enemyAction.cpp:1162`. Damage is caller-supplied, not a global constant:
`src/plugProjectNishimuraU/SnakeCrowState.cpp:663` passes the Snagret's proper
`mPoisonDamage` parameter. Enemy-specific overrides and other ingestion paths must
be checked per family before declaring all predators supported.

### Buried treasure: finding, digging, and release

`src/plugProjectKandoU/pikiAI.cpp:202` selects a live `ItemTreasure` for
`ACT_BreakRock` when it is visible, or when the searching Pikmin is White, subject
to work-distance and buried-treasure search-range checks. The direct action path
at `:712` rejects non-White requests for invisible treasure; `:722` allows White's
formation-check path to start the work action. A second search branch at `:526`
also admits White or visible treasure. Detection is local AI eligibility, not
proof of a map-wide treasure reveal or Treasure Gauge behavior.

`src/plugProjectKandoU/itemTreasure.cpp:405` defines visible as a remaining-depth
ratio **at most 0.85** (with a pellet present). Its collision filter at `:414`
allows White to interact before visibility while ignoring other creatures.
Thus other species can become eligible after partial excavation; a permanent
White-only dig lock would be incorrect.

`ItemTreasure::NormalState::onDamage` at `:65` consumes work damage, advances stage
life and remaining depth, and releases the pellet when remaining depth reaches
zero. The fully buried, first-time story branch records `DEMO_Whites_Digging` and
plays `x14_white_dig`. `Item::doAI` at `:223` updates work bounds and the pellet's
burial transform as depth changes. `Item::releasePellet` at `:115` is the handoff
to the actual collectible. A hidden model plus immediate cargo spawn would omit
the work state, visibility transition, collision behavior, and discovery lifecycle.
Treasure work parameters load from `user/Abe/item/treasureParms.txt` (`:446`).

### Obtaining White Pikmin

`src/plugProjectNishimuraU/Pom.cpp:257` maps `EnemyID_WhitePom` to White.
`Pom::Obj::shotPikmin` at `:279` consumes mouth-attached inputs using
`CKILL_DontCountAsDeath`, updates birth accounting, and creates color-specific
sprouts with `ItemPikihead::InitArg`. Same-color and Queen Candypop accounting have
special branches. This is conversion plus sprouts/plucking, not a free population
increment. Conversion limits and persistence need a dedicated Pom-state/retail
parameter pass; no numeric White yield is asserted by this audit.

## White Flower Garden dependency map

The existing root `docs/PIKMIN2_CONTENT_INVENTORY.json:477` maps `forest_2` to
five floors. This table reports its main-roster inventory, not a new disc decode;
counts, caps/ambush entries, placement, burial depths and exits remain unaudited.

| Floor | Unit pool | Capability-relevant inventory |
| --- | --- | --- |
| 1 | `2_ABE_nor1_cen2_metal.txt` | UjiA/UjiB; `fire_helmet` treasure |
| 2 | `1_ABE_ari_metal.txt` | Tank; `chocoichigo_l`, `diamond_red` |
| 3 | `1_units_white_metal.txt` | WhitePom, Qurione, DaiodoGreen, plants; `gum_tape` |
| 4 | `3_ABE_sak1_sak2_hit1_tsuchi.txt` | GasHiba; `g_futa_kajiwara`, `kinoko_doku` |
| 5 | `1_units_snake_tsuchi.txt` | `SnakeCrow_radar_b`, Egg, plants |

Floor 3 is the main-roster White-conversion dependency; floor 4 requires poison
hazards; floor 5 requires Snagret behavior and its encoded cargo dependency.
An empty standalone treasure list on floor 5 does not imply no boss reward.
The inventory alone does not identify which treasure is fully buried; derive that
from the actual placement/pellet parameters before writing a floor-specific test.

## Required port interfaces and implementation order

Concrete current blockers (port paths, outside the decomp):

- `experimental/pikmin2_campaign.py:14` accepts only blue/red/yellow/purple;
  `:97` serializes tuple indices and `:117` rejects other transfer colors. Its
  `:126` conversion policy grants only the existing floor-2 Purple increase.
- `native/pc_port/pc_p2_cave.cpp:57` accepts colors 0–3; `:62` restores Purple
  through the existing Red-backed Purple adapter. This protocol cannot carry White
  yet. Coordinate both reader/writer and durable-ledger policy changes with #132.
- Existing model extraction, source inventories and unrelated white UI colors
  are not evidence of a White actor implementation.

Proposed sequence, requiring coordinated implementation scope:

1. Add explicit White runtime identity, model/animation registration, parameter
   loading, and consistent boundary serialization. Preserve old session rejection
   rules; do not silently reinterpret existing numeric identities.
2. Add WhitePom conversion and sprout/pluck accounting; define legitimate population
   changes by source floor content rather than copying the Purple floor-2 exception.
3. Route GasHiba through gas immunity/panic and emitter work interfaces. Preserve
   non-White gas rescue/death behavior and attacker accounting.
4. Add buried-item ownership, depth/work state, AI/collision eligibility, and single
   pellet release. Coordinate catalog, hauling receipts and discovery flags with
   #140/#132; do not edit their interfaces independently.
5. Add successful-swallow White damage callbacks in the chosen predator family,
   using its own parameters and lifecycle. Coordinate Snagret with #174.
6. Prove White survivors, conversion accounting, receipts and eventual ship storage
   across cave boundaries. Only then test the complete five-floor natural route.

## Bounded acceptance cases for the implementation

These are proposed tests, **not executed tests**:

| Case | Required observation |
| --- | --- |
| Gas species matrix | Same valid gas hit: White/Bulbmin avoid gas panic; eligible Red enters it; generic invincibility remains respected. |
| Vent work | Gas survival and emitter damage eligibility tested independently, including vertical bounds and captain rejection. |
| Successful ingestion | Mouth-attached White killed by swallow damages predator once per successful kill; non-White, failed kill and non-mouth attachment do not. |
| Multiple Whites | Damage accumulates for each accepted callback while initial poison feedback is gated; no frame-by-frame duplicate ingestion. |
| Buried eligibility | At depth ratios 1.0 and >0.85, White can select/interact, non-White cannot; at 0.85 and below, visibility permits other species. |
| Dig lifecycle | Work reduces depth, bounds/visual burial update, and exactly one real pellet is released at completion; repeated callbacks cannot duplicate cargo. |
| Movement | Match source formula at leaf/bud/flower and several input multipliers; test doped early return separately; load retail parameters before numeric sign-off. |
| Conversion | Valid WhitePom input becomes sprout then plucked White; no death inflation or unexplained population gain; exhausted/failed birth paths preserve accounting. |
| Boundary replay | White identity/maturity survives descent/return/reload; duplicate boundary replay does not duplicate White Pikmin or receipts; legacy unsupported data fails safely. |
| Natural cave gate | Real conversion, gas work, digging/hauling and Snagret reward followed by exit/restart, with source-derived expected survivors and receipts. |

No native build, extracted asset changes or gameplay runs were performed. Validation
for this document was direct source inspection at the pinned revision, comparison
with current protocol guards, and inventory cross-checking. Retail parameter values,
full floor generation, poison effect rendering, save/storage implementation and
natural-play acceptance remain open.
