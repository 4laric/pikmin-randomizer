# Shared Teki actor-lifetime seam (#397, #186)

Engine/toolchain lane (07), Codex through shared account `4laric`. This closes
the #186 finding *"family registration maps are never cleared on Teki death"*:

> A family's `pc_p2_*_forget(BTeki*)` hook was called only on slot reuse in
> `TekiMgr::newTeki()`, never on the death path. The `BTeki*` key stayed in the
> family's `std::map` until `TekiMgr::reset()` or until the same pool address was
> handed back.

The import-pipeline contract (`docs/PIKMIN2_ENEMY_IMPORT_PIPELINE.md` §5) says a
family must *"clear registrations and references on death/reset; never assume a
pointer cannot be reused."* The old behaviour violated that.

## Change

One authoritative list of families that hold a `BTeki*` registration map, called
from both the death funnel and slot reuse:

- New `native/pc_port/pc_p2_teki_lifetime.{h,cpp}`:
  `void pc_p2_forget_teki(BTeki*)` — `nullptr`-safe, idempotent, single list
  (snow/kochappy/sheargrub/purple-direct/breadbug-actor/frog/kogane/mamuta/tank/
  qurione/batch2/batch3/long-legs/white-poison).
- `BTeki::doKill` (`native/src/plugPikiNakata/tekibteki.cpp`) calls
  `pc_p2_forget_teki(this)` at the top. `doKill` is reached by natural death,
  corpse-pellet removal and `killAll`; it is **not** on the corpse-display path,
  so corpse rendering is unaffected.
- `TekiMgr::newTeki` (`native/src/plugPikiNakata/tekimgr.cpp`) now calls the same
  helper instead of its inline 14-call list. Adding a family is a one-line change
  in `pc_p2_teki_lifetime.cpp`.
- `CMakeLists.txt` adds `pc_port/pc_p2_teki_lifetime.cpp` to `PC_PORT_SOURCES`.

Per-family `_reset()` stays for stage teardown; this only changes the death
funnel. `_forget` remains an idempotent `map::erase`, so double-clearing is a
no-op and calls for unregistered/derived actors are harmless.

## Evidence

- Native branch `opencode/p2-lanes789-native`, base `f9e139d8`, candidate commit
  `b9fcf751` (private worktree `output/tracks/p2-lanes789/native`).
- Production build `output/tracks/p2-lanes789/native-build`
  (`PIKMIN_NATIVE_JAUDIO=ON`, MinGW g++): `[521/521] Linking CXX executable
  bin\nectar.exe`; `ninja -n` -> `no work to do`.
- API/behaviour is exercised by the existing #397 lifecycle fixture only after a
  rebuild; the shared-semantics change requires #186 review before integration.

## Runtime run (flora lifecycle fixture, adopted baseline)

Fresh arena `output/tracks/p2-lanes789/flora-arena-02/655b0834372842b59226c3e18bf8fade`
staged with the current `preview_pikmin2_room.overlay()` (staged `default.gen`
sha256 `8f0fc1cd…` = arena.json `birth_policy.after_sha256`), and the
replacement-main fixture built from
`output/converter-lane/flora_lifecycle_room.cpp` against native `b185ff89`:
`PASS P2_LIFECYCLE_RUNTIME`, exit 0. 960x540 window
(`[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)`),
no immediate extinction.

The candidate must be read with the corpse semantics, which this run made
explicit:

- `P2_LIFECYCLE_CLEANUP id=353001 live=1 registered=1` — the proxy leaves a
  corpse, so at death+1 it is still a status-0 manager actor drawn as a corpse;
  its registration is intentionally retained. `doKill` (and therefore
  `pc_p2_forget_teki`) runs on corpse-pellet removal / `killAll`, not on
  `dieSoon`.
- `P2_LIFECYCLE_REENTRY id=353001 frame=384 reused=0` after
  `pc_p2_batch2_rebind()`; control alive.

So the death funnel is exercised end-to-end (death → corpse → respawn →
re-entry, no pointer reuse), but this fixture cannot isolate "engine cleared the
registration before the fixture's rebind": the corpse legitimately keeps its
entry, and the re-entry path resets the maps anyway. An isolated engine-forget
observation needs a non-corpse death, or a probe issued after the corpse pellet
is removed and before any rebind. Recorded **PARTIAL / not isolated**, not FAIL.

The tolerant `pc_p2_batch2_rebind()`, registration queries
(`pc_p2_batch2_count`/`_registered`, `pc_p2_long_legs_*`) and corpse-registry
rebind from `opencode/p2-lifecycle-native` (`5c9492c6`, `4a16ef98`, `fb6389ce`)
are cherry-picked onto this lane branch and remain candidates pending #186
review.

## Non-claims

No gameplay/reward semantics change. No corpse-path change. This does not make a
stale key impossible to *read* by a future iteration; it makes the documented
contract true. Does not add new family registrations.

