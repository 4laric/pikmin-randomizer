# Landing review: committed #616 Bomb::Mgr birth provider (#703)

Implementation owner: Codex through shared account 4laric. This lane lands
the committed #616 provider read-only: no re-derivation of its six files, no
duplication of #616/#659/#691 files, no family/shared edits, no runtime, no
ADMIT. All six runtime gates UNTESTED. Consumer #573 (gates 1/3) unblocks at
integration plus #186 review; detonation firing stays #573 runtime work and
bridge 93 stays #186 review (neither duplicated here).

## Committed source under review

- #616 provider lane `provider-bomb-mgr-birth` (issue #616, gen 5, done with a
  review disposition, never submitted, never integrated; owner gone).
- Root cap `b779b00fe26326451d10b6b68f7ad054f63f91c2` (branch
  `codex/autofill-616-root`), worktree pristine.
- Native cap `6d4cbc4afc112c02b7166ef30d8a1f684c7f3ba5` (branch
  `fork/codex/autofill-616-native`, includes the #577 cherry-pick), worktree
  pristine.

## Re-verified review pins (sha256, measured this lane)

| File | sha256 |
|---|---|
| docs/PIKMIN2_BOMB_MGR_BIRTH_PROVIDER.md | `005b8cf4d460ad8e485c00ce441cc77273964497431051eb8a79f582429b5920` |
| experimental/pikmin2_bomb_mgr_birth_provider.py | `58d61f2eb123f6da2e05d76384bbf1dbe2188f51f058750d9c11a3a924d635c3` |
| tests/test_pikmin2_bomb_mgr_birth_provider.py | `4cf753252c60126a7a15b89ed94861ffd58aa08b047b73d67730fdcfaac7658b` |
| native/pc_port/pc_p2_bomb_mgr_birth.h | `94b09e5510413bc9ee8daee502598f746bc45328c539c27e6ff840e08340a1f0` |
| native/pc_port/pc_p2_bomb_mgr_birth.cpp | `ec36bf049c785e1028b7a0f0248754bd1b8867f76d9f035e14469fc7de68c081` |
| native/tools/p2_bomb_mgr_birth_test.cpp | `de37a9f87debb7f4d1a15813a8e50b218250413ffe84e8b527d85472755a5e66` |

The doc and fixture pins match the #616 draft handoff; all three native pins
match the #666 candidate table. Hash-identical, no drift.

## Validation against integrated work

- #577 payload API (cherry-pick `d9ca3b08` as native `3aad911e`): the #616
  header includes `pc_p2_bomb_payload_actor.h` and owns a `P2BombPayloadPool`;
  nothing is reimplemented. Neither file is on the maintained line yet, so the
  integrator lands #577 first, then #616, in that order.
- #691 real engine birth (`bomb-engine-birth-real-native`, done, native
  `552657a30d2e77a795c3ccc0514b53bc03a3cb0a`): adds Section 3
  (`pc_p2_bomb_engine_birth_poll`, +52/+9 lines) which consumes the #616
  manager API (`birth`, `isRegistered`, `findLive`) instead of duplicating the
  core. #616 files carry no Section-3 code. #691 replaced the #616 test TU
  with its own fixture (`p2_bomb_engine_birth_fixture.cpp`); the integrator
  picks one test TU (both are standalone replacement mains, never co-linked).
- #659 canonical @rsp landing (`provider-rsp-canonical-landing`, done): the
  maintained `scripts/build_pikmin2_fixture.py` now expands Ninja response
  files, so the #616-era "no CLI handoff" blocker is cleared on the canonical
  line; this handoff submits normally.
- #666 shared-hook candidate (`bomb-birth-shared-hook-candidate`, done,
  root-only): engine birth-path anchors (generalEnemyMgr.cpp :322-323,
  :421-422), CMake membership anchors, and dynamic-bridge source 93 through
  the #577 API. The #616 requested hook (tekibteki update block, lifetime
  forget/reset, CMake membership) sits inside that candidate scope; #186
  decides all three items, then #616 integrates and #573 consumes.

## What this lane adds (owned files, this branch only)

- `experimental/pikmin2_bomb_mgr_birth_landing.py`: pin + reference
  validator (fail-closed; hermetic unit surface).
- `tests/test_pikmin2_bomb_mgr_birth_landing.py`: focused suite, green.
- `docs/PIKMIN2_BOMB_MGR_BIRTH_LANDING.md`: this file.

## Integration order for the single writer

1. Land #577 payload API (already has a submitted handoff).
2. Land #616 provider files (this packet), then #691 Section-3 arm on top
   (additive; keep exactly one of the two test TUs as the CMake target).
3. #186 decides the #666 shared-hook items (birth-path hook point, CMake
   membership, source-93 binding); wire the tekibteki/lifetime entries.
4. #573 consumes for gates 1/3; detonation firing is #573 runtime work.

## Captain safety #632

No runtime in this lane (read-only review + hermetic tests), so no guard
evidence applies. Any future runtime work here must adopt
`scripts/p2_fixture_captain_guard.h (sha256
d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474)`
with orimaDead/NaviDead/HP<=1 checks before pause/movie returns or observed
ticks, CAPTAIN_DOWN exit BLOCKED, and a parked captain; record guard/source
hashes at adoption.
