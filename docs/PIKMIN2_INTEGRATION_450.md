# Integration sweep #450

Owner: Codex through shared account 4laric. Draft #432, baseline root 0d24349 / native a0b5dca4. Native result cf54e0f1435a10cbb39b9bd26c317f59b8ce84b1. No main merge or upstream writes.

## Integrated handoffs

- Lane 01 root d1c7d51 / native 3f87459b: cannon Stone, Egg hazard, Kabuto cannon, projectile host, Rock hazard and opt-in preview runtime. Preserved existing family hooks and added projectile setup/update/reset/forget registrations. Native cherry-pick 43c5ca1a; export from actual combined source rather than the worker snapshot. Five projectile probes added to the existing 16-test gate.
- Lane 33 794cecf: QA manifest importer and natural-evidence classification guardrails.
- Lane 18 149a3a8: Small Breadbug manager reset/re-entry and injected-death fixture checks. Fixture code, not a new P2 carry/contest implementation.
- Lane 32 e3faa4f/ac3b56b: updated provenance and four-weapon BigTreasure real-GL fixture. Native tools from 6391a5a7, c4c40954 and 0a4aedb3 integrated, retaining our existing CMake registration and current startup code. Worker run is pinned to its own build and injected receiver API, not natural attacks or this combined binary.

## Remaining queue and scope limits

- Projectile contacts are observed/logged; target-health mutation, natural spawned carrier wiring and reward delivery are not established by these tests.
- BigTreasure normal hardlane tick still uses the older host entry; the FSM host is compiled and exercised by its dedicated fixture, not wired into ordinary combat.
- Lane 11 now reaches 5b1e981 (identity, elemental receiver routing, versioned species policy and schema-3 cave checkpoints). These shared actor/save changes remain queued for coordinated semantic review; existing pure policy integration is unchanged.
- Lane 07–09 fb1d8c1/d1fbc48: worker doKill-forget evidence and specular measurement blocker reviewed. Centralized lifetime/provider candidate remains unapplied. Lane 27 7e2b1a1 is additional worker build evidence for the already integrated hardlane modules.
- Large species umbrella still requires per-family conflict reconciliation. Waterwraith roller candidate, full receiver/reward integration and production P2 randomizer eligibility remain open.
- Mandatory runtime baseline remains live starting Pikmin (default 20 reds), regenerated arenas and centred 960x540 windows. No new combined real-GL gameplay acceptance is claimed here.

## Validation

Production build PASS at native cf54e0f1435a10cbb39b9bd26c317f59b8ce84b1. Dry run: `ninja: no work to do.` Executable SHA-256 `6F96F25685ED6D2411507FB2075150485094F2B610CCEE46729917EDA3535B8E`. Exact export parity: all 1685 tracked text files match. Native hardlane/projectile probes: **21/21 PASS**.

Full Python run: 1931 passed, 23 skipped, 1088 subtests passed; one stale Breadbug fixture-record test failed after the new re-entry/death markers became mandatory. Updated the test record and replaced its obsolete duplicate-ready rejection (re-entry legitimately registers again) with missing re-entry/death evidence rejection. Focused Breadbug + QA rerun: **24 passed**. The full suite was not repeated after this localized correction.

Review also corrected the Breadbug C++ fixture's post-injection alive assertion and replaced its old 960x720 startup with windowed 960x540 plus centring after settings load. Compiled the corrected fixture translation unit with the exact production compile flags; exit 0. This compile used the existing private lane18 room-prefix.inc and does not establish runtime acceptance.

BigTreasure exact-build replacement-main fixture: **built**, fixture executable SHA-256 `7d9d6464ccc16ec4a0bc1b7f720579ab653a30410ff70267c8aeb7a6436b882a`. Its provenance pins native cf54e0f1 and verifies unchanged production inputs. Not launched in this sweep. Evidence is private under output/p2-integration450-*; build directory output/p2-upstream433-build (Ninja Release, MinGW, JAudio ON, test hooks OFF).
