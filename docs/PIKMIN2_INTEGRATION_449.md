# Integration sweep #449

Owner: Codex through shared account 4laric. Draft #432 only; root baseline bc9bfad.
Native baseline c80d7e22, integrated native a0b5dca4049ddbe79979eecc9f72c517e5d3a920.

## Integrated

- Lane 01 d56e6c2b hardlane native reconciliation, merged as 5fc265c4. BombSarai/Fuefuki/BigTreasure modules, setup/update/draw registration and standalone fixtures. Root reconciliation ledger/tests from 296d9bb, 5de77de and fb52b1e; Mar/Tadpole Python contracts included.
- Lane 32 native 2826d61c BigTreasure FSM host, with explicit production CMake registration. Compiled module and standalone test, **not yet connected to the production hardlane host tick** or ordinary Pikmin attacks.
- Lane 04 c64f657 boss encounter descriptors and coverage reporting.
- Lane 05 86766b7 staging manifest planning/verification. Preserved #446 destination/junction containment checks.
- Lane 06 969ed76 host JSON receipt persistence and registry. Integration fixes failed writes leaving an in-memory grant recorded; regression verifies retry and restart deduplication. Single-writer experimental host ledger, not native save or atomic gameplay reward delivery.
- Lane 22 7dc1a24 elemental/Dweevil Python behavior reference; lane 23 d6f87ab flora/Candypop reference. These do not repair native damage receivers or implement native species FSMs.
- Lane 31 c36cd59 Waterwraith policy documentation and candidate bundle preserved, not native-applied.

## Reviewed queue

- Species f9e56420/3f4a0aa: lane 01 reports 45 conflict blocks across 18 files. Needs per-family reconciliation preserving newer batch, cave, Armor, Kochappy and Long Legs code.
- Lane 27 975cd58 is an overlapping hardlane export. Its gameCoreSection update/draw hooks already exist in our merged native; exported from our actual native rather than replacing current files with its snapshot.
- Lane 11 1c96206 Bulbmin actor identity wiring remains queued for Piki/PikiHead shared-semantic review; existing pure policies remain integrated.
- Lane 07–09 4bd085e and lane 25/26 bac68c1 record worker-build evidence, not validation of this combined build. Centralized lifetime/provider changes remain queued.
- Waterwraith roller policy, broader species, projectile/reward host integration and all-family natural gameplay acceptance remain open. AP/CLI/native P2 selection remains unwired.

## Validation

Production build PASS in private `output/p2-upstream433-build`, native `a0b5dca4049ddbe79979eecc9f72c517e5d3a920`; Ninja Release MinGW, JAudio ON, test hooks OFF. Dry run: `ninja: no work to do.` Executable SHA-256 `079E580638F249043BF3B3DC30F5E405A542177DEBA42ABE5785C0D6CD303B80`. Export parity: all 1668 tracked text files match native.

Hardlane standalone gate: 16/16 PASS. BigTreasure FSM-host probe: all eight cases PASS with `-Wall -Wextra -Werror`.

Python suite: **1927 passed, 24 skipped, 1088 subtests passed** in 208.38s. Initial unscoped `pytest -q` collected CLI scripts and failed during argument parsing; corrected invocation is `pytest tests -q`. No new real-GL gameplay acceptance is claimed in this sweep. Prior #446 Flora evidence applies to its pinned build. New runtime acceptance must regenerate arenas with live starting Pikmin (default 20 reds) and the centred 960x540 fixture baseline; custom replacement mains must implement that startup explicitly.
