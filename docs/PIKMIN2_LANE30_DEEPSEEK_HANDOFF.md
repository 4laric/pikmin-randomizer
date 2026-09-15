# Lane 30 — DeepSeek handoff (Sarai Pikmin mouth-capture receiver)

Tracking: #242. Implementation owner: Codex through shared account `4laric`; executing agent: DeepSeek lane-30 session (this worktree). Worktrees:

- Root: `C:/Users/alari/pikmin-randomizer/output/dsw/l30-root` — branch `deepseek/p2-l30`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`.
- Native: `C:/Users/alari/pikmin-randomizer/output/dsw/native-l30` — branch `deepseek/p2-l30-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.

## Chosen slice

Enemy ID **23 — Swooping Snitchbug (`Sarai`)**. The ledger's open work is "remaining
Sarai capture FSM, source actor parity and generated placement"; the next-wave goal for
the family is "ordinary captor target/admission, moving attachment, escape/drop and
teardown". The Demon (ID 32) captain captor is already integrated; the Pikmin side of the
Sarai flight lifecycle had only an isolated FSM (`pc_p2_sarai_fsm.h`) and a visual host
with two live mouth `CollPart`s — no receiver attached Pikmin to the mouth.

This slice closes that gap: the **mouth capture/attachment receiver** — source-faithful
admission (`eatPikmin`/`catchTarget`), carrying (stick-to-mouth, never swallowed), the
`fallMeckGround` drop/damage receiver and the `flickStickTarget` escape receiver, plus
owner/scene teardown. The still-open natural FSM-driven captor (Attack→catch→CatchFly→
FallMeck→Move on an ordinary spawned actor) and generated placement remain separate gates.

**Plainly: there is no ordinary-spawned Sarai actor wired to this yet.** The receiver is
exercised by a native unit test (dependency-free decisions), a Python parity harness, and
a committed runtime fixture that captures *live* arena Pikmin into the host mouth. The
runtime fixture has not been executed in this session (no reserved real-GL slot), so its
gate is reported UNTESTED with the exact reproduction command below.

## Source IDs and files owned

- Enemy ID 23 (`Sarai`, Swooping Snitchbug), family Snitchbugs/Demon (lane 30, #242).
- Native (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/native-l30`):
  - `pc_port/pc_p2_sarai_capture.h` (new) — dependency-free capture/drop decision.
  - `pc_port/pc_p2_sarai_capture_bridge.h/.cpp` (new) — Piki stick-to-mouth engine glue.
  - `pc_port/pc_p2_sarai_host.h/.cpp` (modified) — capture/release/drop/flick surface.
  - `tools/p2_sarai_capture_test.cpp` (new) — standalone unit test.
  - `tools/p2_sarai_capture_runtime.cpp` (new) — live-Pikmin runtime fixture.
  - `CMakeLists.txt` (modified, additive only) — bridge source + `p2_sarai_capture_test`.
- Root (worktree `C:/Users/alari/pikmin-randomizer/output/dsw/l30-root`):
  - `experimental/pikmin2_sarai_capture.py` (new) — Python parity mirror.
  - `tests/test_pikmin2_sarai_capture.py` (new) — 13 pytest cases.

## Ordered commits and dirty state

Native branch `deepseek/p2-l30-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`:

- `4f40b54cbd7b2f01d6a68c22db39c32f0def383b` — `lane30: Sarai Pikmin mouth-capture receiver and bridge (#242)`.

Root branch `deepseek/p2-l30`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

- `fd20fdd8563ee22cd1e3481e61d34eda17acbf3c` — `lane30: Sarai capture parity harness and tests (#242)`.

Both worktrees are clean at handoff (`git status` empty). No push, no `main` mutation, no
shared-checkout edit, no `gh`.

## Interfaces / hooks touched and why

- `pc_p2_sarai_capture.h` (header-only, composes `pc_p2_sarai_policy.h`): `captureEligible`
  (alive && isPikmin && !stuckToMouth && !stickerIsSelf && withinMouthRadius),
  `selectMouthCaptures` (nearest-first, up to `kMouthSlots=2`), `fallMeckReleaseVelocity`
  (−fp41=200), `fallMeckDamage` (general attack damage 10). No engine objects, no I/O.
- `pc_p2_sarai_capture_bridge.*`: per-`Piki*` binding map over `Creature::startStickMouth`/
  `endStickMouth`; API `pc_p2_sarai_piki_capture` / `_bound` / `_owned_by` / `_slot` /
  `_release`, `pc_p2_sarai_drop_owned` (FallMeck: `InteractFlick` detach+damage then
  downward velocity), `pc_p2_sarai_flick_owned` (escape: detach, damage 0),
  `pc_p2_sarai_carried_count`, `pc_p2_sarai_owner_lost`, `pc_p2_sarai_scene_exit`,
  `pc_p2_sarai_forget`. Generation-qualified owner token for exactly-once/address reuse.
- `P2SaraiHost`: `capturePiki`, `releasePiki`, `carriedCount`, `dropOwned`, `flickOwned`;
  `sceneExit()` now revokes ownership (`pc_p2_sarai_owner_lost`) before mouth teardown.
- No shared-file hooks (`teki.h`, `navi.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
  `gameCoreSection.cpp`, `pc_p2_preview.cpp`) were modified. CMake got only two additive
  lines (bridge source + one test name).

Port adaptations (recorded, not retail-faithful): the source `eatPikmin` iterates the
Pikmin manager in encounter order and admits the first eligible Pikmin per free slot;
`selectMouthCaptures` selects **nearest-first** instead (matches the Demon target choice;
harmless because the admit predicate and radius are unchanged). `InteractFallMeck` does
not exist in P1, so the drop uses `InteractFlick` (which detaches the mouth link in
`actCommon` and applies damage in `actPiki`) followed by the source `setVelocity(0,-200,0)`.
The source `EatPikminDefaultCondition` does not explicitly test `isAlive`; the receiver
keeps the `alive` guard as a super-set (dead Pikmin are never admitted).

## Build evidence (`output/dsw/l30-build-evidence.txt`)

```
2026-09-15T05:32:42 lane=l30 target=pikmin_pc native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=yes build_dir=...native-l30-build exe=...bin\nectar.exe sha256=5795c473eb34e7b614f66e7796587a25d1c845f011fded9ab91b80385239a748 ninja_n="ninja: no work to do." seconds=115
2026-09-15T05:32:49 lane=l30 target=p2_sarai_capture_test native=b805d9c626e4f4558c95aef7cac311a5d9a2068f dirty=yes build_dir=...native-l30-build exe=...p2_sarai_capture_test.exe sha256=afe49d62cdaf1b2a2a093e002e0cffeb530028bb0098217db85a8f1ef2439c2b ninja_n="ninja: no work to do." seconds=0
```

Production `pikmin_pc` links clean at head `4f40b54c` (the `b805d9c6` label above is the
base recorded before the commit; the tree built is `4f40b54c`, `dirty=yes` because the
commit landed after configure). `nectar.exe` SHA-256 `5795c473…85239a748`.

## Fixture adoption / runtime evidence

Committed live-Pikmin fixture `tools/p2_sarai_capture_runtime.cpp` (fixture-driven, not a
natural FSM captor): loads `sarai0.mod` + `sarai-attack-mouths.txt` /
`sarai-attack-poses.txt`, opens a 960×540 centred window (logs
`P2_SARAI_CAPTURE_WINDOW size=960x540 … centered=1`), finds a live arena Pikmin, then
asserts capture admission, moving-mouth follow, FallMeck drop (`damage=10`, `vel=-200`),
Flick escape (`damage=0`) and teardown, printing
`PASS SARAI_CAPTURE live_pikmin_capture_drop_flick_teardown`.

- **Not executed this session** (no reserved GL slot). Run command in "Reproduction".
- The receiver is not an "ordinary spawned captor": the anchor actor / signature spawn
  path for Sarai ID 23 is separate, as is FSM-driven attack admission.

## Six-gate table (PASS/FAIL/BLOCKED/UNTESTED/source-backed N/A)

| Gate | Result | Evidence / labels |
|---|---|---|
| 1 Exact identity and spawn | UNTESTED | No ordinary-spawned Sarai actor; host is fixture-loaded (`courses/pikmin2room/sarai0.mod`). |
| 2 Autonomous movement and animation | UNTESTED | Visual host + two live mouth joints build/link; no run this session. |
| 3 Attacks and receivers (capture admission + drop/escape) | PASS (unit/parity) / UNTESTED (runtime) | Native `p2_sarai_capture_test` 21 checks PASS; Python `test_pikmin2_sarai_capture.py` 13 PASS; `InteractFlick` drop/escape receiver wired but the live-Pikmin capture run is fixture-driven and **not yet executed** (labeled injected/fixture-driven). |
| 4 Death and corpse | source-backed N/A | Sarai carries, does not swallow; no lethal path in this slice. |
| 5 Actual transport and reward | source-backed N/A | Mouth-hold carry has no reward/transport endpoint here. |
| 6 Cleanup and re-entry | PASS (unit) / UNTESTED (runtime) | `owner_lost`/`scene_exit`/`forget` detach exactly-once (bridge test coverage), runtime teardown in committed fixture, unrun. |

## Tests run

- `p2_sarai_capture_test.exe` → `p2_sarai_capture_test PASS checks=21`.
- `py -3.12 -m pytest tests/test_pikmin2_sarai_capture.py -q` → `13 passed`.
- `p2_sarai_fsm_test` / `p2_sarai_policy_test` → recompiled standalone (warning-clean)
  `PASS checks=37` / `PASS checks=49`; unchanged by this slice. (Note: `cmake --build
  --target p2_sarai_fsm_test/p2_sarai_policy_test/p2_demon_*_test` fails *silently* in this
  CMake configure — the exact `g++` command succeeds when run by hand — a pre-existing
  tooling anomaly on this base, unrelated to these changes; `p2_sarai_capture_test` builds
  through CMake fine.)

## Assumptions

- Source general attack damage default 10.0f and `FallMeckSpeed` fp41 = 200 used as
  receiver defaults (from `EnemyParmsBase.h` defaults / `Sarai.h:102`); retail data files
  not read in this slice.
- One-slot-at-a-time, two-slot maximum mouth capture, exactly-once per Pikmin via the
  `Piki*`-keyed map.
- Fixture is a bounded, injected capture harness; it is not a natural gameplay PASS.

## Remaining blockers (provider lane named)

- Natural FSM-driven captor (Attack catch window → `capturePiki` → CatchFly height
  decision → FallMeck) on an ordinary spawned Sarai actor: needs lane **12** (captain/squad
  semantics stay with the Demon captain path) and lane **07/08** (lifetime fixtures +
  animation-event clock) plus a staged Sarai arena.
- Generated placement / admission: lanes **03/04** seed-bridge + placement; Sarai has no
  admitted identity yet (lane **02** roster remains deny-by-default).

## Subagent usage

- `explore` #1 (source audit): returned a full Sarai.cpp/SaraiState.cpp/Sarai.h/Demon.*
  table with file:line citations. Used as-is to confirm the receiver constants
  (radius 15, fp41=200, flick 10/0, attack damage 10, 2 slots rkamujnt/lkamujnt). Two
  corrections adopted: `eatPikmin` iterates in encounter order (I keep nearest-first and
  documented it), and `EatPikminDefaultCondition` omits an explicit `isAlive` (I keep the
  alive guard as a super-set). Saved ~45 min of manual decomp reading.
- `explore` #2 (candidate inventory): confirmed file/module surface, ctest registration,
  marker lines, and that the header-only policy tests were previously compiled manually
  (not via CMake) — this explained the silent CMake `--target` failure. Used as-is. Saved
  ~30 min.
- `general` #3 (Python tests): wrote `experimental/pikmin2_sarai_capture.py` +
  `tests/test_pikmin2_sarai_capture.py`, ran `13 passed`. Reviewed and accepted as-is
  (semantics match `pc_p2_sarai_capture.h`; one simplification — empty-list vs None input
  — is fine). Saved ~20 min.

## Reproduction (exact, verified)

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l30 --target p2_sarai_capture_test && C:/Users/alari/pikmin-randomizer/output/dsw/native-l30-build/p2_sarai_capture_test.exe
py -3.12 -m pytest tests/test_pikmin2_sarai_capture.py -q
```

Pending GL run (not executed; requires stage with `sarai0.mod` + `sarai-attack-*.txt`
pose banks in a fresh `preview_pikmin2_room.prepare()` arena, then run under the GL slot):

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l30 -- env PIKMIN_P2_ROOM_WINDOW=960x540 PYTHONUTF8=1 fixture.exe --experimental-pikmin2-room
```
