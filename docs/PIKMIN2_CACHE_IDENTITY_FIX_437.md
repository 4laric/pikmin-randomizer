# Current combined candidate pin: P2 cache identity fix (#437)

Integration owner: Codex through shared account4laric. Root source `3e827571ad3f5e0ceddec2b9c3aa80a71162c513`, native `ae00c510f7f1dca6c26f49c00a6f6f96e9e52fe2` (clean). Maintained branch contains this export and subsequent fixture/evidence commits. This replaces native08bae251 for new candidate acceptance runs; it does not admit source44 or45.

Production executable: `C:/Users/alari/pikmin-randomizer/output/p2-integration-ae00c510/nectar.exe`; SHA256 `071c06ab8961d60cb4997cc7c4703d42dbea43c90eb2d9960771aea82c620611`. Pin and build evidence are alongside it. Private build `output/native-nectar-qol-build`, build PASS, Ninja dry run no work, 1996-source export. Native origin not pushed.

Change: P2-only sessions now persist and restore catalog generator IDs in the tagged stage-cache record, matching ordinary slot sessions. Missing required tags remain rejected. No roster or seed admission changes.

Runtime regression: [Orange lifecycle evidence](PIKMIN2_DWARF_ORANGE_NATURAL_RUN_461.md). Actual stage save/exit/reconstruction restores one bound Orange and the earned reward, with 20 stored Pikmin; exit0. The test uses an earned historical checkpoint and a replacement-main fixture with explicit 960x540 centered startup and initial live20. This proves live-actor reentry; it does not prove a fresh delivery or deceased-actor respawn behavior. Route92 gate work, fresh delivery, deceased-actor reentry and session reward restart now pass: see [current evidence](PIKMIN2_DWARF_ORANGE_ROUTE_ACCEPTANCE_440.md). The route requires ordinary gate opening. Historical Snow startup and Orange process-restart evidence retain their original pins.
