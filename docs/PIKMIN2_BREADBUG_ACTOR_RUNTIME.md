# Original P1 Breadbug proxy arena runtime

Scope #168/#186. New `pikmin2_breadbug_arena` stages the original Impact Site
practice map, collision/routes and base generator into a private chal0 slot.
It adds one native Collec (type 8) proxy 186081 at (-150,30,1850) and one ordinary Collec
control 186082 at (150,30,1550). These are engineering arena placements, not P2
source placements. Generator offset is zero, birth count/radius is made
explicit with the existing deterministic-birth helper, and every original
course file is byte-verified unchanged. No shared seed/assets are overwritten.

`pikmin2_breadbug_actor_fixture.cpp` uses ordinary native AI updates. It does
not reposition the enemy or write enemy velocity/state/health. It positions
only the fixture captain near the initial actor for camera framing, disables
further tutorial demo flags and provides a zero-input controller. Movement
acceptance requires over 15 units horizontal displacement and at least 15 frames
of native horizontal velocity. Mere gravity settling is not enough.

The driver verifies exact production readiness identity/type/full birth XYZ,
live visual delegation and movement evidence. The fixture keeps the control
alive, resets the family mapping and verifies that drawing now declines both
the proxy and ordinary control. This tests registration reset, not a full
stage unload/reload or natural death/corpse route. Source P2 FSM, cargo stealing,
receiver damage and rewards remain outside this proxy test.

Captures cover initial actor, later movement and post-reset visuals. A capture
must be inspected before reporting framing/appearance success. Native process
success alone does not establish source model fidelity. The binary and frozen
build inputs must be identified in the result/provenance; do not use current
production filenames as historical evidence.

Two driver tests cover fullXYZ, real movement threshold, missing draw and
multiple-ready rejection. Local staging passed at
`output/p2-lifecycle-batch/breadbug-arena-prepare-01`.

The private runtime also replaces the frozen current-source newPikiGame object
with the reusable instrument_tutorial helper from the Kochappy arena fixture.
It pulses A through the actual tutorial Controller; the ordinary tutorial
window update closes text 13 (extinction, from the zero-Pikmin fixture setup).
No overlay flag is force-cleared. Movement sampling starts only after the
normal pause and overlay gates clear. This is injected test input, not manual QA.

## Actual runtime result

The private arena passed with native base
`d7ff676bf8990a442002e1c3d7050f17a93b01a3` and the recorded existing dirty
`creatureCollision.cpp`/`goalItem.cpp` changes (tracked diff SHA256
`7c5baccf4deb14218bb8690dc795a9a6a0c629e3bf2d2f3b9eec501a6bb957ad`).
This is not evidence from a pristine commit. The private build made no shared
native changes.

Result: `output/p2-lifecycle-batch/breadbug-actor-native-01/result.json`.
Run: `9e02bb3ff3b04cf7ad00d4db04781ce4` under that directory.
The exact opted-in actor was type 8, generator 186081, full birth position
(-150,30,1850). It moved 480.690552 horizontal units with native horizontal
velocity in 300 observed frames. The ordinary control stayed alive. Production
draw delegation logged success, and after reset both actors declined the
family visual delegate. Tutorial 13 closed through normal Controller input.

Fixture: `output/p2-lifecycle-batch/breadbug-actor-runtime-link-02/fixture.exe`.
SHA256: `3ab9be485f629df411d70d151b8e2f22e4b06bc5de24e47f14d0421ec04693d3`.
The `commands.json` there records the private tutorial object and relink.
Its base `breadbug-actor-runtime-link-01/provenance.json` records copied build
inputs, freshness checks and source state. The private original and instrumented
tutorial source hashes are retained in the relink record. Implicit compiler
runtime/startup dependencies are not included in the copied input set.

The inspected initial PNG visibly shows the imported live model in the arena.
By the moved/reset captures the actor had wandered outside the camera edge;
those images do not establish visible reset appearance. Reset mapping behavior
is verified by the actual native API assertions. P1 corpse fallback is unchanged
by this implementation, but natural death, corpse delivery, cargo stealing,
stage reload and full P2 behavior remain untested.

Validation: 13 Python tests and 4 subtests passed across the actor runtime,
actor installer, visual installer and asset extractor suites. Private fixture
compilation/link and the actual native process exited successfully.

## Maintained-line reset/re-entry + injected death cleanup (lane 18, 2026-09-14)

Extends the small PanModoki (`TEKI_Collec`) proxy fixture with the two gates
left `UNTESTED` above. No native change; `pc_p2_breadbug_actor` is used through
its existing public API.

- Driver `scripts/test_pikmin2_breadbug_actor_native.py` now builds the fixture
  from `--native/--build-dir/--head` (with `--prefix room-prefix.inc`) or runs a
  prebuilt `--exe`.
- Fixture `scripts/pikmin2_breadbug_actor_fixture.cpp`:
  - at frame 300 `pc_p2_breadbug_actor_reset()` (proxy draw declines),
  - then `pc_p2_breadbug_actor_setup()` re-registers (second `P2_BREADBUG_ACTOR_READY`),
  - then injected death `actor->mHealth=0`, and the proxy draw declines once dead.
- Evidence: run `output/lane18-breadbug-runtime2/92e45733ab604788841e9ca75e9cc3cf`
  (fixture SHA-256 `261bf516167001c66f6f85151e836892596aa3d953ca18dc4594d735f679b6b2`):
  birth `-150,30,1850`, max displacement 469.16 over 300 moving frames,
  `P2_BREADBUG_ACTOR_REENTRY`, `P2_BREADBUG_ACTOR_KILL frame=306`,
  `P2_BREADBUG_ACTOR_DEATH corpse=0`, PASS.
- **Corpse finding**: on injected death the P1 `TEKI_Collec` host leaves **no
  PelletView corpse** (`corpse=0`). Cleanup/unmapping passes; the P2 corpse
  carry/reward is still unimplemented and is not claimed.
- **Still lane-06/engine-gated**: P2 contested cargo, nest treasure storage and
  exactly-once AP receipt. Interface request posted on #441; this lane will not
  fork the Giant module's contest logic.
