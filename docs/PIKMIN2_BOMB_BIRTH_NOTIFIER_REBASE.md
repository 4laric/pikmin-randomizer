# Bomb-birth notifier rebase (#726, unblocks #573)

Rebases the reviewed #715 notifier/hook (#677 engine hook) onto the wave line
`93603dc2`, where the evolved provider (`pc_p2_bomb_mgr_birth.*`,
`pc_p2_bomb_payload_actor.*`, `pc_p2_otakara_joint_capture.*`) exists but the
notifier TU and the hooked `generalEnemyMgr.cpp` do not. #186 design approved
(strong notify + LTO retention + PC_PORT_SOURCES membership).

## What changed (owned files only)

- `native/pc_port/pc_p2_bomb_notifier.h/.cpp`: verbatim from reviewed `a6ca7bc6`.
  Strong `pc_p2_bomb_birth_hook_notify` with `__attribute__((used))` LTO retention,
  bounded 16-ring, `P2_BOMB_BIRTH_HOOK_NOTIFY` receipt marker, test accessors.
- `native/pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp`:
  live research file + the exact 14-line #677 hook addition (weak decl, maybe-notify,
  Bomb + BombOtakara create-arm calls); byte-identical to reviewed `91c09444`.
  Uncompiled reference (never in CMakeLists), matching precedent.
- `native/tools/p2_bomb_birth_notifier_rebase_fixture.cpp`: guarded fixture mirroring
  the reviewed #715 shape (hook selectivity, pipe faithfulness, birth/payload handoff,
  forget/reset, guard-mirror).
- Root: `scripts/build_p2_bomb_birth_notifier_rebase.py` (leased configure + engine-free
  link + dry run), `docs/PIKMIN2_BOMB_BIRTH_NOTIFIER_REBASE.md` (this file),
  `experimental/pikmin2_bomb_birth_notifier_rebase.py` (pin/hook verification adapter),
  `tests/test_pikmin2_bomb_birth_notifier_rebase.py` (5 focused tests green).

## Not in scope (serialized)

- `native/CMakeLists.txt` `pikmin_pc` membership: owned by #725. Specified as follow-on;
  landed only after #725 releases the file.

## Evidence

- Fixture exe SHA-256 + hook log SHA-256 + `ninja -n` dry run recorded in the lane packet.
- Guard `scripts/p2_fixture_captain_guard.h` sha256 `d2f678c9...` adopted as predicate
  mirror (engine-free proof, no captain); future runtime consumers adopt the header.
- All six runtime gates UNTESTED; no ADMIT. Downstream: #573 with the bridge.