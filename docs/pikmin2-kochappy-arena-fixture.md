# Original Impact Site native Red observer

Issue #120 / #186. New observer replaces the entire old room-specific RoomApp class; original-map geometry is not required to be flat or centered at zero. Input red-arena-positions.txt derives from the staged arena manifest. It confirms two actual native generator actors, generator full XYZ and personality stored birth XYZ, Red initial/max200 and ordinary default health/identity. Postphysics position is logged separately.

240 normal game updates observe live, unfrozen actors, native state/motion/frame/target and position. There are no enemy state, target, velocity, or animation writes and no captain teleport. Advancing animation is required; active chasing is not inferred from an idle scene. Native Red renderer callback and a GL framebuffer capture establish render activity, not comprehensive material visual approval. Combat, delivery, cleanup, and P2 AI parity remain unmeasured.

Run `python -m experimental.pikmin2_kochappy_arena_fixture --stage <private arena> --exe <private instrumented exe> --output <new evidence folder>`. The tool records executable hash, command, duration, manifest hash and bounded exit/evidence. It never attaches to a live game. Compile instrument(source) against matching frozen native headers/objects; the production executable lacks these probes. The first build uses the immutable e704b268 snapshot, not a claim about later production changes.

## First original-map result: blocked

The immutable e704b268 private input snapshot compiled and linked both observer variants successfully. Initial run timed out after90s. Diagnostic run timed out after25s with repeated `ready=1 navi=1 teki=1 pause=0 ui=1 movie=0`: an active native UI overlay blocks normal updates. No flags were forcibly cleared. Red native READY confirms sourceID1/200health and configured XYZ; renderer callback fires. Stored-birth/control-health and 240 normal-update gates remain unmeasured. A legitimate startup UI dismissal or earlier fixture demo setup is the next bounded work.

Evidence: output/p2-red-arena-runtime/{observe,gates}/evidence.json. Diagnostic binary SHA2564504ee060f644360a87373ea9072aafd9e9c4a6d1ed57b48243fb8fc75c19f17. Private compile/link recipe and logs are in fixture-gates/. This is not a production gameplay success claim.

## Legitimate tutorial input diagnostic

`instrument_tutorial` applies only to a private frozen copy of `src/plugPikiColin/newPikiGame.cpp`. It logs `createTutorialWindow` textID and sends one A press per30 tutorial update calls through the actual Controller argument to `handleTutorialWindow`. `zen::ogScrTutorialMgr::update` delegates to `ogScrMessageMgr::update`; `ogMessage.cpp` handles A/B at lines678/700. The existing normal handler then invokes deleteTutorialWindow when STATUS_Exiting is returned. No runtime pause/UI flags are assigned by the instrumentation. The private replacement object precedes the unmodified legacy archive in the link, leaving all production source and archives untouched. This is UI-only fixture input, not enemy AI manipulation.

## Corrected startup run: passed bounded observer

`output/p2-red-arena-runtime/ui/evidence.json` exits0 after25.81s. Executable SHA25628b1cab9edfcd49b4d54d10613068fab828b6262a77bedeaf34298ace0b38c33. The logged tutorial is13, TUT_Zenmetu. `gameCoreSection.cpp:1293` updates container counts; its following zero-population/owned-Onion condition schedules DEMOFLAG_PostExtinctionSeed. This empty arena caused the tutorial; it was not a renderer stall. Normal spaced A input dismissed it. Stock map and course hashes remain unchanged.

Both generator and personality stored birth match fullXYZ; Red initial/max200 and control130/default pass. 240 live/unfrozen normal updates each advance animation. Red stayed idle in state15 (no target or displacement); control visited6/7/15 and moved33.06units. Thus autonomous update/animation observation passes but chasing/combat do not gain acceptance. The captured original-map frame was inspected; Red appearance is present, but no comprehensive close-up/material or collision sign-off is implied. Original timed-out logs remain preserved. Four focused tests pass.
