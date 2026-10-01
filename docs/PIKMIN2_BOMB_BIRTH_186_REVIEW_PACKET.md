# Bomb birth #186 shared-hook review packet (#186 -> unblocks #573)

Lane `provider-bomb-birth-186-review-packet`, issue #186 (OPEN). Implementation
owner: Codex through shared account 4laric. Produces the machine-readable #186
shared-hook review packet the single-writer integrator consumes to land (or
refuse with exact required changes) the Bomb birth provider for the stranded
consumer `enemy-bombotakara93-payload` (#573). Read-only review: no
shared/native/CMake/provider edits, no build/runtime, no ADMIT. All six runtime
gates UNTESTED.

## Traced input (not rediscovered)

#573's recorded dependencies are exactly (1) `#616 provider-bomb-mgr-birth
integration` and (2) `#186 shared-hook review (engine Bomb birth path, provider
CMake membership, dynamic-bridge source 93)`. The engine/provider work was
executed and integrated through `bomb-birth-shared-hook-candidate` (#666),
`bomb-birth-engine-hook-native` (#677), `bomb-birth-manager-arm-native` (#684),
`bomb-engine-birth-real-native` (#691), `bomb-joint-matrix-capture-native`
(#700) and the landing packet `provider-bomb-mgr-birth-landing` (#703). The
remaining unresolved gate is the #186 decision for the three gated items.

## Verified candidates (fresh this turn)

| Issue | Lane | root commit | native commit |
|---|---|---|---|
| #666 | bomb-birth-shared-hook-candidate | `9cfb154a` | - |
| #677 | bomb-birth-engine-hook-native | `1fa6c05d` | `5d03a790` |
| #684 | bomb-birth-manager-arm-native | `12578a87` | `deb8bb8b` |
| #691 | bomb-engine-birth-real-native | `d348acdd` | `552657a3` |
| #700 | bomb-joint-matrix-capture-native | `8ba9ad68` | `0a7017c1` |
| #703 | provider-bomb-mgr-birth-landing | `fe03f39c` | - |
| #616 | provider-bomb-mgr-birth | `b779b00f` | `6d4cbc4a` |

Read-only reference: the #666 shared-hook candidate at commit `9cfb154a` pins
the same three items; this packet independently re-verifies the artifacts
rather than trusting it.

## The three gated items and code-verified verdicts

The maintained line (`native/`, CMakeLists.txt) does NOT yet carry any of the
three integrations, so every verdict is CHANGES_REQUIRED with the exact missing
change. This is a code-derived result, not an invented approval.

1. **engine-bomb-birth-path** -- CHANGES_REQUIRED.
   Maintained `native/pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp`
   sha256 `a01db128...` keeps the retail arms (`EnemyTypeID::EnemyID_Bomb`,
   `EnemyTypeID::EnemyID_BombOtakara`) but has no `pc_p2_bomb_birth_hook_notify`
   hook. Candidate #677 sha256 `301503f2...` adds the extern at line 216 and the
   notify calls at lines 549/649. Missing change: land the additive hook and
   define the notifier in a port provider TU (only the candidate fixture defines
   it today).
2. **provider-cmake-membership** -- CHANGES_REQUIRED.
   Maintained `native/CMakeLists.txt` sha256 `077809d2...` has `enable_testing()`
   (line 552) and the `pc_generator_cache_validation_test` pattern (lines
   557/561) but NO `pc_p2_bomb_mgr_birth` membership. Missing change: add
   `pc_port/pc_p2_bomb_mgr_birth.cpp` to the pikmin_pc target and register the
   provider test mirroring that pattern. Verified candidate provider files:
   `pc_port/pc_p2_bomb_mgr_birth.h` `94b09e55...`, `.cpp` `ec36bf04...`.
3. **dynamic-bridge-source-93** -- CHANGES_REQUIRED.
   The maintained native line has none of `pc_p2_bomb_payload_actor.{h,cpp}` or
   `pc_p2_otakara_joint_capture.{h,cpp}`. Verified candidates: payload
   `.h` `9c831a37...` / `.cpp` `6b1a0bd2...` (#577), joint capture
   `.h` `0865c525...` / `.cpp` `9d919d72...` (#700, commit `0a7017c1`). Missing
   change: land both and bind source 93 (BombOtakara) through
   `pc_p2_bomb_birth_hook_notify`.

## Integrator landing/refusal steps

1. Refuse to land while any gated item is CHANGES_REQUIRED; the exact missing
   change is recorded per item.
2. On a fresh APPROVED decision: land the candidate commits per item onto the
   maintained root/native line in order (#666/#677/#684/#691/#700), then the
   #703 landing validation, then the provider CMake membership.
3. Re-run this packet against the maintained line; only a fresh APPROVED
   decision unblocks the #561/#573 consumers.

## Downstream

`enemy-bombotakara93-payload` (#573, stranded) is the consumer; #616 is the
provider and #703 the landing packet. Every gated item carries its downstream
issue list in the packet.

## Fail-closed contract

`experimental/pikmin2_bomb_birth_186_review_packet.py` hash-verifies every
candidate artifact against its pin and refuses (`DriftError`) on a missing or
mismatched input; it also derives each verdict from a fresh code review and
`validate_packet()` rejects any packet whose recorded verdict or integration
evidence does not match that fresh review (no tampered approval). Nothing is
simulated and no approval is invented.

## Verification

`tests/test_pikmin2_bomb_birth_186_review_packet.py`: 11 tests pass --
integrated-line positive (all APPROVED + validate_packet), missing-integration
CHANGES_REQUIRED with exact missing change, missing candidate artifact refused,
missing maintained base refused, hash mismatch refused, candidate token gap
detected, tampered verdict rejected, tampered schema rejected, unsubstantiated
approval rejected, packet names #573/#616/#703 + integrator steps + three items
+ six UNTESTED gates, candidate evidence hashes.

## Captain safety #632

Tooling-only, no runtime run: guard adoption is N/A here. Any runtime consumer
must adopt `scripts/p2_fixture_captain_guard.h`
(sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`)
with orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, a parked
captain and labelled protection.