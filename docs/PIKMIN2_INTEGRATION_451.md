# Integration sweep #451

Owner: Codex through shared account 4laric. Draft #432 baseline root 0eac496 / native cf54e0f1. Native result 3213dd590de474331f67c2b65437e62d3c1b8236.

## Integrated

- Lane 01 batch D (0d6521b): reward lifecycle harness/tests and native fb6389ce corpse-registry rebind, applied as 41079d47. Rebind preserves generator-keyed receipts and in-flight entries; no change to the economy or native save protocol. Runtime duplicate-delivery acceptance remains unperformed on this build.
- Lane 25/27 ac73320: DangoMushi hazard policy, production compilation and CTest target, integrated as native 3213dd59. This is a policy module, not a natural actor/hazard spawn adapter.
- Lane 18b c167b01: Breadbug consumer of the shared receipt schema, restart/deduplication tests and helper exclusion. Experimental descriptor choices do not establish source drop parity or production reward delivery.
- Lane 18 0b1fb3e: worker evidence docs, explicit window evidence validation and run environment. Preserved #450 corrected alive assertion and existing 960x540 centred startup; harmonized its log marker and extended missing-evidence regression.
- Reward fixture integration fix: preserve the current exported room main/startup instead of requiring the obsolete fixed 960x720 init signature. Tested against the actual exported fixture source.

## Reviewed without duplicate application

- Lane 01 batch E 445b320/6bc15b2/1c9c83a repeats already integrated converter billboard and sampled-clock work. Clock source/test files match exactly. Converter differences are signature ordering, formatting and helper extraction: retained our bindings argument position, current normal policies and tests/pikmin2_synthetic_model.py helper. No stale converter test or old engine snapshot imported.
- Shared lifetime/provider, lane 11 identity/elemental/save-schema chain, Waterwraith and broad species reconciliation remain queued as described in #450. No new eligibility for the production P2 randomizer pool is inferred.

## Validation

Production build PASS at native 3213dd590de474331f67c2b65437e62d3c1b8236. Dry run for production and DangoMushi test: `ninja: no work to do.` Executable SHA-256 `E72294F64B99809278AE9EAF1A2CD6B28F1CF1222CA7C153283472D3EFF970F5`. All 1688 exported source files match native byte-for-byte.

DangoMushi CTest PASS; separate `-Wall -Wextra -Werror -UNDEBUG` policy probe PASS (assertions enabled independently of Release CTest flags). Reward fixture generated from current native room source compiles with production flags. Focused reward/Breadbug tests: 21 passed. Full suite: **1949 passed, 24 skipped, 1088 subtests passed** in 220.17s. Private Ninja Release build: output/p2-upstream433-build, MinGW, JAudio ON, test hooks OFF. No new real-GL acceptance in this sweep. Future runs require regenerated arenas with live starting Pikmin (default 20 reds) and centred 960x540 startup.
