# Breadbug asset prototype and arena hook proposal

Scope #168; common arena contract #186. This extends the completed behavior
audits with local source extraction and converter evidence. It does not replace
`PIKMIN2_SCAVENGER_ENEMY_AUDIT.md` or Claude's delivered Breadbug/beetle audit.
No native registration, actor placement, save or reward behavior is changed.

`experimental.pikmin2_breadbug_assets.py` extracts US GPVE01 revision0 resources
for PanModoki38, OoPanModoki40 and helper PanHouse83. It records source archive
hashes, original model and parameter/animation/collision files, model joints,
ordered clip keyevents, full parameter blocks and collision tree parents,
radii, IDs, offsets and joint indices. Repeated parameter keys in different
blocks stay distinct; duplicate keys within one block are rejected. Nest alias39
is not emitted as an independently spawnable creature.

Local evidence: `output/p2-lifecycle-batch/breadbug-assets-02/breadbugs.json`.
Small Breadbug has14 joints,9 clips and9 converted first-pose MODs. Giant has13
joints and9 clips; all pose conversions fail explicitly with `Unsupported
display-list attribute`. Nest has1 joint, no animation bank, and a converted
static `nest.mod`. Each model has2 source collision nodes. These are first-pose
conversion probes, not animated playback, event execution or visual QA.
The Giant also has special texture-matrix setup in `panModokiMgr.cpp:83`;
shared converter changes need their own review rather than dropping attributes.

Actual proper parameters differ by variant: small ip01=11, fp03 carry speed35,
fp04 receiver damage1000, fp06 press damage200; Giant ip01=1, speed45,
receiver damage1000 and press damage100. Preserve this distinction when using
earlier audit summaries. `PanModoki::canTarget` accepts minimum weight strictly
below its threshold; `OoPanModoki::canTarget` accepts at/above. Carry strength
is `(minimum+maximum)*0.5` (`panModoki.cpp:1314`). Reference tests exercise these
arithmetic/eligibility rules, not the entire PelletCarry contest state machine.

## Smallest native arena increment

Start with one small Breadbug and one P1 control in a private copy of a known P1
map, preserving original collision/routes. Family profile and placements remain
separate per #186. First gates are model/collision binding, source clip playback
and a bounded Walk/Wait loop. Label any P1 locomotion proxy explicitly. Do not
place Giant until its display-list gate is resolved. The nest is owned by its
Breadbug and is never offered as an autonomous randomizer enemy.

Requested future root-owned hooks, before runtime edits:

- Family registration maps one validated generator instance to a typed family
  profile; logs source ID, effective XYZ, model identity and source collision
  joint bindings. No actor ID is allocated by this extractor.
- Per-instance animation adapter supports the nine registered clips and their
  source events. Source FSM has11 states: Dead, Walk, Back, Pulled, Appear, Hide,
  Damage, Wait, Stick, Sucked and CarryEnd (`PanModokiBase.h:29`). Do not disguise
  a generic Bulborb attack loop as this behavior.
- Cargo ownership interface exposes eligible cargo, exclusive capture/release,
  source carry-force arbitration and receiver-arrival notification. Begin with
  one ordinary non-progression pellet and no AP reward; nest storage and treasure
  receipt ownership remain disabled until their exact lifecycle is implemented.
- Nest child lifetime follows parent spawn/death/stage cleanup. Source has up to15
  held treasure slots and recovery on death, so deleting captured treasure or
  duplicating its receipt is not an acceptable temporary substitute.
- Damage adapter distinguishes press, ordinary attacks, receiver damage and
  Giant Purple-only stun behavior. Use actual variant parameters above.
- Death/corpse adapter must preserve source carcass eligibility separately from
  released held cargo, then validate attachment, routing and delivery once.
  The helper nest is non-carcass; the completed source audit documents its
  disabled damage/death/platform events. No corpse behavior was exercised here.

Acceptance remains untested for all native arena gates: autonomous movement,
combat, carry contest, receiver damage, nest storage/release, death/corpse and
stage cleanup. First-pose import success does not mark these complete.

Reproduce locally:

```powershell
py -3.12 -m experimental.pikmin2_breadbug_assets --iso <US-disc> --output <fresh-directory>
py -3.12 -m pytest tests/test_pikmin2_breadbug_assets.py -q
```

Three reference tests pass. Extracted retail assets remain local and are not
committed or exported. No shared native build or player binary changed.
