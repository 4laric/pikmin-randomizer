# Hole of Beasts collision attribute0 (#129)

The two blocked cent rooms use P2 surface attribute0. This batch adds only0 to
the existing audited attribute set; the bit translation is unchanged. Other
unaudited low-nibble values still reject. No geometry, routes or shared native
code changes are made.

## Source comparison

P2 `src/sysCommonU/mapCode.cpp` decodes surface as `byte &15`, slip as
`byte >>4 &3`, and bald as `byte >>6 &1`. Surface0 is a numeric source surface
value, not the P1 hole or water enum. `Navi::onKeyEvent` uses the surface for
footstep selection and separately checks `inWater()`. `HoudaiShotGun.cpp` likewise
checks a water box first, then distinguishes a dry impact effect for attribute6.
Neither caller assigns dangerous behavior to attribute0.

P1 `include/MapCode.h` defines solid0, water5 and hole6; `mapCode.cpp` reads those
from bits29 onward. It separately reads slip bits27–28 and inverted bald bit25.
`creature.cpp` selects weak/strong sliding from the slip field, not surface0.
The converter therefore maps this additional audited dry surface to P1 solid
while preserving the existing slip/bald encoding. Exact P2 footstep sounds and
physical friction tuning remain outside this approximation; identical slip bits
are not a claim that both engines' complete slope dynamics are identical.

## Asset audit

Both local source `waterbox.txt` files declare zero volumes:

| Unit | Triangles | Attribute0 triangles | Routes | Spawn ground probes |
| --- | --- | --- | --- | --- |
| room_cent2_4_tsuchi |233|4|9|32|
| room_cent3_4_tsuchi |229|29|9|27|

All source spawn centers have collision ground, and both directed route graphs
are connected for every audited destination. The extracted source geometry and
route links are preserved; no offsets, route reversal or carry relocation are
introduced. These are static unit-local checks, not native carrying acceptance.

All14Hole of Beasts unit candidates now convert with the existing explicit
material-approximation option. The other12collision-bearing model files remain
byte-identical to their prior imports. The boss room still requires material
approximation independently of this collision change.

Seventeen focused map-code/collision/selected-unit/assembly tests pass. New tests
cover all slip/bald combinations of attribute0, unchanged mappings for every
previously accepted byte, and rejection of every other unaudited attribute.
Local evidence: `output/p2-mapcode0-batch/audit.json` and `import/units.json`.
No native build or hauling test was performed for this batch.
