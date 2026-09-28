# Breadbug visual native fixture

Scope #168/#186. `scripts/pikmin2_breadbug_visual_fixture.cpp` is a private App
using a frozen prefix of the existing native room fixture for window/bootstrap
and framebuffer capture. It uses production visual setup/draw/reset hooks;
there are no family actors or behavior injections.

`test_pikmin2_breadbug_visual_native.py` stages the existing private actor scaffold
but restores the original P1 chal0.ini, preserving its practice map/collision/
routes. It installs the verified source visual models, holds their config under
a fixture-only filename, and starts with the production profile disabled.
The fixture grounds one engineered display per run near the stationary captain using
actual mapMgr ground queries. It writes its exact final XYZ, enables the
production setup, captures two pose times, resets visuals and captures again.
Idle, move and nest use separate fresh processes at the same visible ground point. Another fresh process never enables the profile and verifies fallback.
Enemy actor count must stay unchanged in every run.

The late fixture-triggered setup temporarily selects SYSHEAP_App because normal
App idle has no allocation heap selected. The production startup hook already
runs in its normal asset-loading context. An initial fixture run without this
heap selection failed before rendering and is retained as failure evidence.
The captain state is logged rather than requiring the tutorial room's Walk
state: P1 stage startup uses a different state during this visual-only test.

Displays remain visual-only and have no collision, health, AI, cargo or receipts.
Their final coordinates are fixture-selected map-ground positions, not source
P2 generator placements. The profile contains source animation/model assets.
Two screenshots at different times require visual inspection before claiming
visible motion. Reset evidence is explicit module reset in a running fixture,
not a complete stage unload/reload acceptance test.

Build against a completed root build using `scripts/build_pikmin2_fixture.py`.
The private fixture source includes `room-prefix.inc`, copied from the existing
preview_p2_room.cpp up to the optional fixture includes. The helper records
native HEAD/dirty state, freshness, all hashes and private link inputs; it never
rebuilds production. Source/input history limitations in its report still apply.

Driver CLI accepts --assets, --converted (existing room105 scaffold assets),
--profile (breadbug-visual-01), --exe (private fixture), --output (fresh) and
--timeout. Output contains exact executable identity, source stage hash, final
config, native logs, captures and process exits. Two focused driver tests verify
strict enabled/disabled readiness log expectations.

The first simultaneous three-display capture loaded all models but the hillside
occluded two displays. That evidence remains partial; individual runs avoid
claiming visibility from readiness logs alone. The initial private profile
writer also produced WindowsCRLF while hashing LF bytes. The runtime profile
copy normalizes the saved config to its already-recorded LF hash; the small
writer fix is separately requested from the root integration owner.

Runtime evidence: `output/p2-lifecycle-batch/breadbug-native-05/result.json`.
All four private processes exit0 (wait, move, nest, disabled), with unchanged
enemy count. Inspected images show Breadbug pose changes, source nest geometry,
and display removal after reset. The hillside/ship smoke partly obscures the
nest and lighting; this passes rendering smoke coverage, not presentation
fidelity or a clean gameplay arena. No stage unload/reload was exercised.

Fixture SHA256: d837eced129e6e3bdd96072b8fb855ad0d2ddf1286d98253f75751357ac2a23a.
Final private link recipe is `breadbug-runtime-link-05/commands.json`; its base
snapshot is `breadbug-runtime-link-02/provenance.json`. Snapshot native HEAD is
e704b268348ec4f87e947658c6ad4d740722c15e with recorded tracked dirty changes in
creatureCollision.cpp/goalItem.cpp, diff hash
7c5baccf4deb14218bb8690dc795a9a6a0c629e3bf2d2f3b9eec501a6bb957ad.
It is not a pristine commit-only build. Eight Python tests pass across driver,
profile installer and asset reference.
