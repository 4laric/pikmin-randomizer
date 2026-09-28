# Tank / Wtank import slice

Child #195, parent #170, integration #186. Codex owns this slice under shared
4laric. Owned files are `experimental/pikmin2_tank_assets.py`,
`tests/test_pikmin2_tank_assets.py` and this document. No shared converter,
native hook, build, source export or player session was changed.

## Source contract

Local source revision: `632af93787b9c95b63f0c13be32b161375ce3a96` in
`native/pikmin2-research`. The generated manifest includes hashes of the actual
source files read, not just a revision label. Disc reader accepts only legally
provided local US GPVE01 revision 0 assets.

`src/plugProjectYamashitaU/enemyInfo.cpp:47–48` registers spawnable Tank (24)
and Wtank (25), both with BDT_Strong drops and no registered child helper.
Tank's concrete fire implementation is `Ftank::Obj`; abstract `Tank::Obj` and
the shared manager are not an extra creature. Wtank shares Tank's model,
animation, animation-manager, collision and stone resources, but has distinct
retail parameters and external texture. `TankMgr.cpp` shares model/anim data.

Source resources:

- `enemy/data/Tank/model.szs` and `anim.szs`.
- `enemy/data/Tank/fire_butadokkuri_main_s3tc.bti`.
- `enemy/data/Wtank/mizu_butadokkuri_main_s3tc.bti`.
- `enemy/parm/enemyParms.szs`: Tank collision, animation manager and stone
  metadata; separate `tank/enemyparm.txt` and `wtank/enemyparm.txt`.

Both `Ftank.cpp::changeMaterial` and `Wtank.cpp::changeMaterial` replace image
slot zero. The importer uses the existing bounded texture-zero replacement,
then weighted draw matrices for each sampled pose. Source
`TankMgr.cpp::createModel` also requests a differed display list for
`mat_dokkuri_main`; dynamic J3D texture-coordinate behavior is not reproduced.

Both variants have retail health 1000, maximum breath range 120 and attack
radius 25. Fire attack damage is 10; water attack damage is **0**. The complete
parameter blocks are retained separately, including repeated keys in different
blocks. No values are silently copied between variants.

There are 16 joints and 8 collision nodes. Root collision radius is 32.5 on
joint 1 (`kosi`, offset -5,0,0); child radii are 10,15,10,5,5,5,5 on joints
14,1,2,4,6,11,13. The emitter is joint 15 (`hoppe`), selected in `Tank.cpp:33`.
`updateEmit` normalizes its world matrix X axis, advances 10 units along that
axis and subtracts 10 from world Y. Sampled model-space matrices are retained;
the recorded model-space analogue must not be blindly transformed with its
already-applied Y offset when integrating a rotated/scaled actor.

## Motions and gameplay boundaries

The seven source motions and their retail durations/events are:

| Clip | Frames | Events / loop interval |
|---|---:|---|
| dead | 90 | None; source end event drives death completion |
| move1 | 55 | Loop 15–44 |
| flick | 95 | Event 2 at 45 |
| attack | 95 | Event 2 at 55 |
| waitact1 | 35 | Loop 0–34 |
| waitact2 | 50 | None |
| type5 | 40 | Loop 10–29; carcass-carry motion |

Source FSM (`Tank.h:25`) has Dead, Wait, Move, MoveTurn, ChaseTurn, Attack and
Flick. `TankState.cpp:844–913` starts the Attack animation with breath disabled;
event 2 enables breath, ongoing updates apply receiver interactions, and
cleanup disables breath and changes effects. Flick event 2 performs the native
knockback. Imported event metadata executes none of these actions.

`Tank.cpp::isAttackable` checks a forward region against live captains/Pikmin,
with vertical and lateral radius limits. `emitCollideRatio` grows the breath
and traces a radius-2.5 sphere against map floor/wall collision; contact limits
range and effect radius. This is not an unoccluded cone or a free projectile.
Stone/earthquake interruptions stop effects/reset growth and resume through
their source lifecycle callbacks. Dead cleanup finishes effects and the shared
death procedure creates the source drop/carcass path; actual rewards, carrying
and cleanup have not been implemented or tested by this importer.

Fire calls `InteractFire`, water calls `InteractBubble` (variant source files).
`src/plugProjectKandoU/interactPiki.cpp:445,503` exempts Red/Bulbmin from fire
panic and Blue/Bulbmin from water panic, subject to current-state invincibility
and panic-transition guards. **Zero water damage does not mean no interaction.**
It still causes water panic for susceptible Pikmin. The reference tests preserve
that distinction. Captain fire checks Forged Courage, versus and invincibility;
bubble uses its own active-world/versus/invincibility guards and no fire-upgrade
exemption (`interactNavi.cpp:166,189`). Do not recolor a fire receiver as water.

## Actual conversion and reproducibility

Final independent runs:
`output/p2-lifecycle-batch/tank-assets-05` and `tank-assets-06`.
All 126 files match byte-for-byte, including every raw asset, normalized
converter report, MOD and manifest. Evidence:
`output/p2-lifecycle-batch/tank-reproducibility.json`.
Manifest SHA256:
`f5db9a1d73a09b8ed233b548d806a3484a647a40e73fec6c74ac5161222c87b7`.

Each variant converted all seven clips: 27 poses each, 54 total, using three
base samples plus every event/loop boundary. MOD bytes total 1,219,968; all
output files total 1,465,188 bytes. Actual extraction/conversion times were
0.339 and 0.333 seconds on this machine (not a native frame-time benchmark).
Each model has 247 vertices, 490 triangles, one shape and one texture. Converter
reports no discarded attributes for these assets. Source TEV remains an
approximation: vertex color times identifiable UV0 diffuse texture; source
blend, alpha compare, depth state and hierarchy order are retained.

The first two runs found only absolute destination names in converter JSON
reports; the new family writer now records relative names. Those earlier runs
are retained as diagnostic evidence, not labeled fully reproducible.

Limits: 32 MiB source resource, 16 MiB per MOD, 256 MiB total pose budget,
128 joints, 2–8 base samples, duration 2–10000 and at most 32 ordered events.
Seven tests pass, covering frame/event/loop validation, finite emitter basis,
receiver distinction, output-independent reports, invalid sampling, overwrite
refusal and separate/finite parameter blocks. Generated manifests use exact LF
bytes. Source mismatch is visible through source/resource/model/texture hashes;
a future installer must enforce these hashes before native installation.

```powershell
py -3.12 -m experimental.pikmin2_tank_assets --iso <local-disc> --source native/pikmin2-research --output <fresh-directory>
py -3.12 -m pytest tests/test_pikmin2_tank_assets.py -q
```

## Next bounded runtime contract

There is no converter blocker in this slice. Begin a private original-P1 arena
with one explicitly opted-in P1 `TEKI_Tank` (15, Fiery Blowhog) plus an ordinary
control. Keep P1 AI/collision/fire/corpse/rewards authoritative while validating
the Tank live model and native-motion mapping. P2 carrying/death motions need
their own lifecycle tests. Root owns setup/CMake/registration hooks.

Wtank can share the visual bank machinery, but must remain display-only or
clearly labeled fire-behavior proxy until a separate typed Bubble receiver,
color immunity, captain guard, attack-event and map-clipped breath implementation
is tested. A source water visual must not imply safe Blue or vulnerable Red
gameplay until that boundary is implemented. No actor IDs or native hooks are
allocated by the importer.

| Gate | Result |
|---|---|
| Source contract and local conversion | PASS at this bounded level |
| Deterministic extraction / budgets | PASS |
| Native display and exact placement | UNTESTED |
| Autonomous movement / attacks / receivers | UNTESTED |
| Death, corpse delivery and rewards | UNTESTED |
| Cleanup, re-entry and mixed-scene performance | UNTESTED |

Child #195 can close after source integration/review. Parent #170 stays open
for runtime behavior and full-family parity. No retail assets are committed.
