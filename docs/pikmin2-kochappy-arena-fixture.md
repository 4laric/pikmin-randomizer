# Original Impact Site native Red observer

Issue #120 / #186. New observer replaces the entire old room-specific RoomApp class; original-map geometry is not required to be flat or centered at zero. Input red-arena-positions.txt derives from the staged arena manifest. It confirms two actual native generator actors, generator full XYZ and personality stored birth XYZ, Red initial/max200 and ordinary default health/identity. Postphysics position is logged separately.

240 normal game updates observe live, unfrozen actors, native state/motion/frame/target and position. There are no enemy state, target, velocity, or animation writes and no captain teleport. Advancing animation is required; active chasing is not inferred from an idle scene. Native Red renderer callback and a GL framebuffer capture establish render activity, not comprehensive material visual approval. Combat, delivery, cleanup, and P2 AI parity remain unmeasured.

Run `python -m experimental.pikmin2_kochappy_arena_fixture --stage <private arena> --exe <private instrumented exe> --output <new evidence folder>`. The tool records executable hash, command, duration, manifest hash and bounded exit/evidence. It never attaches to a live game. Compile instrument(source) against matching frozen native headers/objects; the production executable lacks these probes. The first build uses the immutable e704b268 snapshot, not a claim about later production changes.

## First original-map result: blocked

The immutable e704b268 private input snapshot compiled and linked both observer variants successfully. Initial run timed out after90s. Diagnostic run timed out after25s with repeated `ready=1 navi=1 teki=1 pause=0 ui=1 movie=0`: an active native UI overlay blocks normal updates. No flags were forcibly cleared. Red native READY confirms sourceID1/200health and configured XYZ; renderer callback fires. Stored-birth/control-health and 240 normal-update gates remain unmeasured. A legitimate startup UI dismissal or earlier fixture demo setup is the next bounded work.

Evidence: output/p2-red-arena-runtime/{observe,gates}/evidence.json. Diagnostic binary SHA2564504ee060f644360a87373ea9072aafd9e9c4a6d1ed57b48243fb8fc75c19f17. Private compile/link recipe and logs are in fixture-gates/. This is not a production gameplay success claim.
