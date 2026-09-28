# Demon private two-pose display (#222)

Native successor to8579ba19. Fixture reuses private initialization/capture
helpers from the earlier Groink fixture; only DemonVisualApp is instantiated.
It loads Demon attack frames0/17, with red/blue radius3 markers at the two
model-space mouth-joint translations. Source capture radius remains15; these
smaller spheres visualize centers only. Model and centers share the same
identity-scale, zero-yaw owner translation. Latest owner Y100 is an explicit
display intervention, not flight simulation. The captain is pinned at0,0,100.

Build with existing private fixture builder against native-groink-policy
756515d57088f7ea7241c451e2e5b968bf9c7c6d and build-groink-runtime. New fixture
path is tools/p2_demon_visual.cpp. Always choose a fresh external output path.
No shared native hooks/build are changed. The runner checks built executable
hash and selected model hashes, then makes a fresh room overlay and records
input/manifest/provenance/log/capture hashes:

```
py -3.12 tools/p2_demon_visual_run.py --root ../p2-groink-prototype --assets C:/Users/alari/pikmin-local/game/assets --room ../pikmin2-room105 --demon ../demon-assets-03 --fixture ../demon-visual-fixture-03 --output ../demon-visual-sessions
```

Runner status captured_requires_visual_review is deliberately not alignment
acceptance. Timings choose two baked poses for inspection; they do not execute
source animation events. No ownership, captain capture, flight, release,
damage or lifecycle gameplay is implemented.

Earlier fixture01 failed compile due to a missing projection matrix argument,
fixed by0cc5fd96. Fixture02 built and captured both poses in session
521f702898bb466ba399aa3521e1d35b; visual review found control Pikmin obscuring
markers at Y30. a6b97fd9 raises model and markers together for a fresh check.
Original failed/limited evidence remains preserved.

Fixture03 built successfully and captured both poses in fresh session
70767e2d46d54617ba0ed40b5cac481e. Inspected demon0.png and demon17.png:
Demon and both red/blue centers are visible, with marker positions changing
between poses. Centers appear below the visible hands; this observation does
not yet establish exact source hand/captain alignment. Verify source mouth
joint offsets/scale against a captured captain before accepting attachment.
Materials and thin wing/antenna rendering remain approximations. Runtime
PASS establishes two captures, not full visual fidelity or gameplay.
