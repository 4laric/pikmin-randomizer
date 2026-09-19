# Yakushima boot-flag delivery verification

Bounded read-only delivery successor for the DONE lane
overworld-course-boot-flag-native (issue #767, gen 4). It verifies the
producer handoff and emits an integrator-ready admission packet for the
blocked downstream consumer p2-overworld-yakushima-p1-native-runtime
(issue #150). No implementation, no builds, no native changes, no runtime,
no worker launches, no ADMIT.

## Pinned inputs (launch config.json)

- handoff sha256
  cc151854d6c15132d6f8b56754dfefd540bd7bdc05bceb04c28353167163222e
- source pins root e07eaab951c8ade41742038373b5ba94bd6ebd97
- source pins native a7545226fb2586e4bda852c45ff31fcebe811c83
- lane root base fdd558123223f94d706b9a00973037553e864756
- downstream lane p2-overworld-yakushima-p1-native-runtime, issue 150
- issue #767 OPEN and assigned to 4laric (live gh check at verification time)

## Owned files (this lane only)

- scripts/p2_yakushima_boot_flag_delivery.py: the verifier described below
- tests/test_p2_yakushima_boot_flag_delivery.py: fail-closed test driver
- docs/PIKMIN2_YAKUSHIMA_BOOT_FLAG_DELIVERY.md: this document

## Verifier behavior

The checker reads the pinned launch config and the canonical registry with
the standard library only, then checks in order:

1. producer lane overworld-course-boot-flag-native is done
2. registry handoff sha equals the pinned handoff sha
3. handoff file bytes hash to the pinned sha
4. producer registry source pins equal the pinned pins
5. handoff embedded root and native heads equal the pinned pins
6. all 11 producer handoff evidence entries exist with matching hashes
7. producer root and native worktree HEADs equal the pinned pins (read-only
   git rev-parse; preserved source presence)
8. issue proof file names issue 767

Any failure prints DELIVERY_REFUSED with the exact reason and exits 2.
Success writes the packet JSON and prints DELIVERY_VERIFIED, exit 0.

## Commands

- verify and emit packet:
  python scripts/p2_yakushima_boot_flag_delivery.py --root
  C:/Users/alari/pikmin-randomizer --config <launch>/config.json
  --issue-proof <launch>/issue-767-proof.json --out
  <output>/yakushima-boot-flag-delivery-packet.json
- run tests:
  python tests/test_p2_yakushima_boot_flag_delivery.py --root
  C:/Users/alari/pikmin-randomizer --report <output>/test-report.json

## Packet

The packet names the verified handoff path and sha, the source pins, all 11
verified evidence entries with hashes, the downstream lane and issue with the
routing action, and the read-only verifier identity. Admission itself remains
with the integrator; this lane makes no gameplay claim and all six arena gates
stay UNTESTED.
