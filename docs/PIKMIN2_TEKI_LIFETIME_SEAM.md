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

## Runtime adoption (pending)

The #397 Long Legs/Waterwraith/Flora non-invincible fixture can now observe the
engine clearing registrations on death instead of calling `*_forget` itself.
That run needs the real-GL/input slot. Exact reproducer once integrated:

```powershell
py -3.12 scripts/build_pikmin2_fixture.py --source output/native-<lane> \
  --build output/native-<lane>-build --fixture <fixture.cpp> \
  --expected-native-head <native-head> --output output/<lane>-lifecycle-<attempt>
```

Gate status: compile PASS; runtime forget/re-entry observation **UNTESTED**
(awaiting the GL slot and #186 review).

## Non-claims

No gameplay/reward semantics change. No corpse-path change. This does not make a
stale key impossible to *read* by a future iteration; it makes the documented
contract true. Does not add new family registrations.
