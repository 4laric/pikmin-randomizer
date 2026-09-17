# Shared-hook candidate: Bomb birth provider (#616) for #186 review (#666)

Producer lane `bomb-birth-shared-hook-candidate` (#666); owner Codex through
shared account 4laric. Private scoped candidate ONLY: no maintained/shared/
family edits, no runtime, no ADMIT. All six runtime gates UNTESTED. This
packet gives the #186 reviewer the exact pins, hashes and decision needed to
land the Bomb birth provider for consumer #573
(`enemy-bombotakara93-payload`, gates 1/3 BLOCKED on this integration).

## Context consumed read-only (not duplicated)

- #616 `provider-bomb-mgr-birth` (done gen 5): root `b779b00f`, native
  `6d4cbc4a`; review-ready outcome, no CLI handoff (provenance builder @rsp
  limitation, separately owned by #509 tooling).
- #659 `provider-rsp-canonical-landing` (done): improved @rsp patch handoff.
- Downstream: #616 integration, then #573 gates 1/3.

## Item 1 - engine Bomb birth path

Retail manager-creation switch
(`native/pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp`):

| Line | Code | Role |
|---|---|---|
| 322-323 | `case EnemyTypeID::EnemyID_Bomb:` / `mgr = new Bomb::Mgr(limit, viewNum);` | Bomb manager creation arm |
| 421-422 | `case EnemyTypeID::EnemyID_BombOtakara:` / `mgr = new BombOtakara::Mgr(limit, viewNum);` | BombOtakara manager creation arm |

No registry lane owns this file. Any engine birth-path hook for the provider
sits on this shared switch and needs #186 review, not a silent edit.

## Item 2 - provider CMake membership

Maintained anchors (`native/CMakeLists.txt`): `enable_testing()` line 552;
registration pattern `add_executable` + `add_test` (e.g. generator-cache
validation lines 557-561). Provider files verified present with hashes (read
from the #616 native worktree, read-only):

| File | sha256 |
|---|---|
| pc_port/pc_p2_bomb_mgr_birth.h | `94b09e5510413bc9ee8daee502598f746bc45328c539c27e6ff840e08340a1f0` |
| pc_port/pc_p2_bomb_mgr_birth.cpp | `ec36bf049c785e1028b7a0f0248754bd1b8867f76d9f035e14469fc7de68c081` |
| tools/p2_bomb_mgr_birth_test.cpp | `de37a9f87debb7f4d1a15813a8e50b218250413ffe84e8b527d85472755a5e66` |

Registering these in maintained CMake/CTest is a shared edit for #186.

## Item 3 - dynamic-bridge source 93

The runtime bridge binding Bomb birth output to the source-93 BombOtakara
consumer is the #577 payload API consumed by #616 (cherry-pick `d9ca3b08` as
native `3aad911e`), verified present with hashes (read-only):

| File | sha256 | Pin |
|---|---|---|
| pc_port/pc_p2_bomb_payload_actor.h | `9c831a3715b23ea84b7cfefac4a5d6b0662e192d17387b46af2c1bd079368a46` | line 42 `struct P2BombPayloadConfig` |
| pc_port/pc_p2_bomb_payload_actor.cpp | `6b1a0bd29181287f3292b95c914a68548bf68e3d370574294ca904b72c28cca2` | line 1 payload include |

No "dynamic bridge" module exists by that name; the seam above is the real
binding and needs #186 review as shared birth/consumer seam (not family FSM).

## #186 decision requested (exact)

Approve, in this order: (1) the engine birth-path hook point for the
provider on the manager-creation switch; (2) maintained CMake/CTest
membership for the three provider files above; (3) the source-93 dynamic
binding through the #577 payload API. Then #616 re-validates, integrates,
and #573 consumes. No ADMIT is requested or granted by this packet.

## Boundaries

No maintained/shared/family edits, no builds, no runtime runs, no manifest
writes, no ADMIT. All pins re-verified by the focused suite (9 tests green);
anything unverifiable would have been recorded ABSENT (nothing was).
