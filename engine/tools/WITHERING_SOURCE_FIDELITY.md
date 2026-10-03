# Source 55 authored states and vector reactions (#1260)

This continuation depends on the original provider from PR156, including its
no-carcass correction. It owns all thirteen Hanachirashi states in the original
source path; AP family behavior stays in the prior module. It uses literal source
parameters and animation keys, not Mar AI. Wind uses the authored hana3 emitter,
20-degree three-dimensional cone and separate captain/Pikmin direction formulas.
Pikmin and captains have additive native receiver IDs 37 and 38; existing IDs do
not move. The receiver implements retail Blow/Flick and KokeDamage phases, with
nonlethal wind, immediate flower stripping, Purple immunity to blow and actual
whistle recovery. Flicking uses retail vector/randomization and 10% leaf chance;
the Pikmin InteractFlick source does not apply its supplied damage argument.

The original actor binds nine literal enemycoll nodes using the complete BMD
hierarchy and every authored frame. It preserves duplicate `none` identifiers,
stick codes, radii and offsets. Native collision matrices use the renderer's view
basis so the engine's CollPart::getMatrix yields world orientation. Binding is
restored before pool recycling; allocated trees are reused per pool actor.

Run the owned legal producer with an extracted flying asset directory:

```
py -3.12 tools/build_hanachirashi_joint_bank.py --root <randomizer-root> --assets <private-flying-assets> --output <private-runtime>/p2-hanachirashi-joints.txt
```

The startup owner must stage this private bank next to p2-flying-bank.txt. Its
header pins source55, eleven clips and nine nodes. The complete 697-frame bank is
required before native allocation; incomplete/mismatched banks fail preflight.
The producer input and output contain legal material and must remain ignored.

## Direct gameplay script

Use the current 20-Pikmin starting overlay and a centered 960x540 native window.
At ordinary game speed, approach the authored original source55 with a captain
and bud/flower squad. Enter the attack cone both early and late; observe full
vector blow and immediate leaf conversion without wind HP damage. Whistle in
flight and while downed, then confirm formation recovery. Test one Purple in the
cone: leaf conversion, no blow, and no Purple-only Laugh.

Throw four ordinary Pikmin onto actual stickable nodes; repeat with one Purple.
Observe Fall (flight first .75s), Land, Ground, GroundFlick and TakeOff (flight
begins at source key30). Throw one to three ordinary Pikmin and wait more than
one second: observe FlyFlick at damage key15. Move beyond home territory and
observe ChaseInside, then return. Defeat via normal attacks and observe exactly
one ordinary item drop at dead END, with no borrowed Mar carcass. Save at normal
day boundary, resume, and verify source respawn and no duplicated actor/items.

## Evidence and open gates

Portable checks cover source thresholds, clocks, 3D cone/formulas and complete
legal joint-bank parsing, including actual-bank mutations. All changed native
translation units pass their existing compile-command syntax checks. A linked
runner build and actual physical gameplay remain required. Animated joint data
has independent asset-producer validation; this does not prove stick/contact
behavior in gameplay.

Repugnant Appendage immunity requires the captain upgrade owner's API. Source55
item geometry is registered before provider preflight against held-treasure
commit 9a2aaba90. It uses real root+500 for all drops and zero velocity only
for held treasure; common number-pellet velocity RNG is unchanged. The callback
implements the ordinary state; the retail Bittered fallback awaits the stone API. Retail wind
and landing effects, shadow offsets/radius, dynamic reaction save serialization,
and gameplay/save-resume qualification remain open. These are not PASS claims.

The held-treasure dependency is composed in merge 6ef1c473f. Dense legal draw
bank SHA189b8cdc2a06f0721a75993b060a0c70807529ac046075c1bc7977ed1344ccce
contains 462 frames across eleven clips and has independent native decoder
validation. Startup must stage it privately with the complete joint bank.
Prior runner pin 3ca6fe3dd production and both focused tests passed; its ELF SHA
is 72ae1e046f17cf59c13523b51b87cf7810bccd1a0f642d486b70c5b0013e05ff.
This receipt does not qualify the later geometry/dependency composition or gameplay.
