# Bomb birth hook call site (#732)

Lane `bomb-birth-hook-callsite-native`, issue #732. Implementation owner:
Codex through shared account 4laric. Coordinator consumer-repair for stopped
consumer `enemy-bombotakara93-payload` (#573, gen 17): the #726 notifier was
strong-defined but never invoked (no engine caller, no pikmin_pc membership,
no generalEnemyMgr tree in the port build).

## Wire (native worktree, base 93603dc2)

1. `native/pikmin2-research/src/plugProjectYamashitaU/generalEnemyMgr.cpp`
   (new): research-mirror call-site TU. Strong-defines
   `pc_p2_bomb_birth_hook_notify(int)` in the production graph (emits
   `P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=%d`, the #726 contract line) and ports
   the two retail `createEnemyMgr` Bomb-family arms
   (research generalEnemyMgr.cpp:322-323 `Bomb::Mgr`, :421-422
   `BombOtakara::Mgr`; IDs from enemyInfo.h:95,152) as
   `pc_p2_general_enemy_mgr_birth(enemyID, actor)`: only 36/93 route to the
   real `pc_p2_bomb_engine_birth_poll` seam on the live engine actor; the
   notifier fires on a real birth, everything else is refused fail-closed.
   Free-function seams are declared locally; the #726 header stays
   read-only. No captain/Navi/HP state is touched (#632 N/A on this path).
2. `native/CMakeLists.txt`: adds `pc_port/pc_p2_bomb_mgr_birth.cpp`,
   `pc_port/pc_p2_bomb_payload_actor.cpp` and the call-site TU to the
   explicit `PC_PORT_SOURCES` (no GLOB covers `pikmin2-research`).
3. `native/tools/p2_bomb_birth_hook_callsite_fixture.cpp` (new):
   replacement-main harness linked against the private pikmin_pc graph (all
   objects except `pc_main`). It never defines or calls the notifier (nm:
   `U` on the entry, no notify symbol); it offers each live registered
   carrier to the production entry with retail ID 93, after the #632 guard
   and a deterministic non-bomb-ID negative.

Native commits (branch `codex/autofill-bomb-birth-hook-callsite-native`):

- `42e223396106013d56234ef51831721f251f1172` call site + membership + fixture
- `46f8c684472f4d4e6db131defde9238bd4f7a3fa` local seam declarations
- `eeb3a49f5f472a975afdfdf132f215a8aa3d88e2` fixture setup/ready declarations

## Compiled evidence (private leased build `output/bomb-birth-hook-callsite-build`)

- `ninja: no work to do.` (`ninja -n` dry run exit 0).
- Engine `bin/nectar.exe` sha256
  `82804be772d8a644280a469d91bfc45586b2b77511f81e64132729beb60d3507`.
- Fixture exe sha256
  `259f8e4db513ee2add20eb8e04ccf179e8b8725831c163236a21db6a8ab34773`.
- Symbol provenance (`nm`): production `generalEnemyMgr.cpp.obj` defines
  (`T`) both `pc_p2_bomb_birth_hook_notify` and
  `pc_p2_general_enemy_mgr_birth`; the fixture object only references (`U`)
  the entry.

## Runtime proof (`run-732/callsite0/hook.log`, sha256 `4e32d064…fd33c8`)

Sidecar `p2-bomb-mgr-birth.txt` (`P2_BOMB_MGR_BIRTH_1`, 1 id, 349005) plus
`p2-cargo-free.txt`, `--experimental-pikmin2-room`, 960x540, exit 0:

- Live carrier census: generator=349005 type=3 alive=1.
- `P2_BOMB_MGR_BIND`, `P2_BOMB_MGR_BIRTH` (slot 0, generation 1),
  `P2_BOMB_ENGINE_BIRTH ... engine_driven=1`.
- `P2_GENERAL_ENEMY_MGR_BIRTH_CALLSITE enemyID=93` then
  `P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=93` — the hook fired from the engine
  TU on a real birth.
- `P2_BOMB_CALLSITE_NEGATIVE_PASS refused_id=1`; no abort; no
  `P2_FIXTURE_CAPTAIN_DOWN` (guard vendored from
  `scripts/p2_fixture_captain_guard.h` sha256 `d2f678c9…3c3474`).

Guard adoption: #632 vendored truth table + self-test in the fixture;
observation-only, captain parked by the room scenario (no captain-damage
claim). All six runtime gates UNTESTED by this lane; no ADMIT.

## Handoff

Downstream consumer `enemy-bombotakara93-payload` (#573): the hook it
consumes now has a production engine caller and pikmin_pc membership; its
fenced game run can observe `P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=93`, then
gates 1/3. #186 shared-owner review required before shared-line landing
(`PC_PORT_SOURCES` is a shared build file).
