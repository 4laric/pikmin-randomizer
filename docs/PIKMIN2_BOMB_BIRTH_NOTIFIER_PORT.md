# Port Bomb birth hook-notifier (lane bomb-birth-hook-notifier-port-native, #715)

Bounded native implementation porting the exact residual the integrated #186
review packet specifies (items 1+2 CHANGES_REQUIRED; item-3 bridge is
integrator work, out of scope). Downstream: `enemy-bombotakara93-payload`
(#573) gates 1/3 once integrated alongside the bridge landing. Shared-line
landing requires #186 review; this lane lands nothing itself (private scoped
candidate + single-writer integration).

## Traced gap

#573 passes birth/joint verification but gates 1/3 stay BLOCKED. The engine
hook (`generalEnemyMgr.cpp` Bomb/BombOtakara create arms calling the weak
`pc_p2_bomb_birth_hook_notify`) exists at this pin, but (1) no TU defines the
strong notifier (only the #677 standalone fixture did), and (2)
`pc_p2_bomb_mgr_birth.cpp` is in no CMake target, so the provider never links
into `pikmin_pc`. Evidence: `output/workflow/autofill/enemy-bombotakara93-payload/gen15-note.md`.

## Implementation (owned files only)

- `native/pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp`:
  hook extern + notify calls already present at this pin (verified, not
  re-ported; the engine arms filter to Bomb/BombOtakara cases). No other
  change to this shared file.
- `native/pc_port/pc_p2_bomb_notifier.{h,cpp}` (new): strong notifier TU.
  Bounded ring record (never grows) + `P2_BOMB_BIRTH_HOOK_NOTIFY` receipt
  marker; faithful pipe (no invented filtering; the engine arms filter).
  Engine-free. Test accessors (`p2_bomb_notifier_count/last/reset`) for the
  fixture; tiny and harmless in the engine link.
- `native/CMakeLists.txt`: `pc_p2_bomb_mgr_birth.cpp` + `pc_p2_bomb_notifier.cpp`
  into `pikmin_pc` (`PC_PORT_SOURCES`, #186 review); new provider test target
  `p2_bomb_birth_notifier_test` (fixture + notifier + manager core + payload,
  `P2_BOMB_MGR_BIRTH_NO_HOST`, CTest registered). Neither TU added to small
  unrelated targets.
- `native/tools/p2_bomb_birth_notifier_fixture.cpp` (new): links the REAL
  notifier/manager/payload TUs (no redefinitions, no unity-include). Cases:
  hook-selective via a labeled arm mimic, notifier-pipe faithful, birth +
  payload handoff, forget/reset clean, guard mirror. Exit 0 only on all.
- `scripts/build_p2_bomb_birth_notifier.py`, this doc,
  `experimental/pikmin2_bomb_birth_notifier_port.py` (evidence verifier),
  `tests/test_pikmin2_bomb_birth_notifier_port.py`.

## Build / test (private, leased)

Build dir `output/bomb-birth-hook-notifier-build[-jaudioon]` (exclusive,
lane-private). Lease via the canonical registry; live elastic cap; release
after. Record configure/build/test exits, executable SHA-256, `ninja -n`.

## Captain safety #632

The provider fixture is engine-free (no captain/Navi/HP); its guard predicate
mirrors `scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) as a pure
check. Any future runtime consumer adopts that header before launch; its hash
is recorded in the lane packet, never claimed as a runtime run.

## Honest status

All six runtime gates UNTESTED; no playability claim; no ADMIT. Item-3 bridge
is integrator work (out of scope here).
