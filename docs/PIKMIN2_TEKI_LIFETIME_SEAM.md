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

Earlier handoffs (`b9fcf751`, `72bed79a`) were deferred by
[pass #446](PIKMIN2_INTEGRATION_446.md) because they were built on a divergent
native line and referenced then-absent `purple-direct`/`white-poison` providers.
This reconcilation re-pins the seam against the **approved native baseline
`f14c6851473ac1161be56c8b98f4f905232f3635`** and mirrors the current maintained
family list exactly.

## Change

One authoritative list of families that hold a `BTeki*` registration map, called
from both the death funnel and slot reuse:

- New `native/pc_port/pc_p2_teki_lifetime.{h,cpp}`:
  `void pc_p2_forget_teki(BTeki*)` — `nullptr`-safe, idempotent, single list
  mirroring the current `TekiMgr::newTeki` fork (snow, sheargrub, kochappy,
  giant-breadbug-actor, breadbug-actor, frog, kogane, mamuta, tank, qurione,
  kurage-teki, onikurage-teki, batch2, projectiles, sokkuri, armor, batch3,
  long-legs). No absent providers are referenced. Queen/King track `Piki*` and
  keep their own Piki forgets.
- `BTeki::doKill` (`native/src/plugPikiNakata/tekibteki.cpp`) calls
  `pc_p2_forget_teki(this)` at the top. `doKill` is reached by natural death,
  corpse-pellet removal and `killAll`; it is **not** on the corpse-display path,
  so corpse rendering is unaffected.
- `TekiMgr::newTeki` (`native/src/plugPikiNakata/tekimgr.cpp`) now calls the same
  helper instead of its inline 18-call list. Adding a family is a one-line change
  in `pc_p2_teki_lifetime.cpp`.
- `CMakeLists.txt` adds `pc_port/pc_p2_teki_lifetime.cpp` to `PC_PORT_SOURCES`.

Per-family `_reset()` stays for stage teardown; this only changes the death
funnel. `_forget` remains an idempotent `map::erase`, so double-clearing is a
no-op and calls for unregistered/derived actors are harmless.

## Evidence

- Root branch `opencode/p2-lanes67-next`, base `codex/p2-main-review` @ `3851d4b`.
- Native branch `opencode/p2-lanes67-native`, base (approved) `f14c6851`, ordered
  commits `ec6e1448` (lifetime seam), `4c3b32e6` (lane-06 receipt surface).
  Private worktree `output/lane67-native`.
- Private build `output/lane67-native-build` (Ninja/Release/MinGW,
  `PIKMIN_NATIVE_JAUDIO=ON`): `[545/545] Linking CXX executable bin\nectar.exe`,
  exit 0; `ninja -n` -> `no work to do`. `nectar.exe` SHA-256
  `F0356477373EF45BAAA0F5975A107D4BEA1CC0D9B81866A050F5B3FF56831E4F`.
- CTest `p2_receipt_test` and `p2_cargo_contest_test` pass; the #397 lifecycle
  fixture API is unchanged and was not modified here.

## Runtime adoption (BLOCKED in this environment)

This host has no local P1 assets / disc image and no real-GL slot available to
this session, so the natural-death forget/re-entry observation could not be
re-run. It is **BLOCKED**, not re-asserted from the earlier worker build. The
prior lane-07 runtime adoption (`output/tracks/p2-lanes789/*`) is pinned to that
worker's executable and remains valid for its line only.

Exact reproducer once a GL host and assets are available:

```powershell
py -3.12 -m experimental.pikmin2_lifecycle_runtime build --native output/lane67-native \
  --build-dir output/lane67-native-build --output output/lane67-lifecycle-fixture --head <native-head>
py -3.12 -m experimental.pikmin2_lifecycle_runtime run --family long-legs \
  --assets <P1 assets> --existing output/tracks/p2-lanes789/flora-arena-05 \
  --output output/lane67-lifecycle-run --exe output/lane67-lifecycle-fixture/baseline/fixture.exe
```

Gate status: compile + no-work dry run PASS; runtime forget/re-entry observation
**BLOCKED** (no assets/GL host here), shared-semantics review pending #186.

## Next slice

Close the remaining next-wave acceptance on a GL host: natural death with the
engine-driven `pc_p2_forget_teki`, **late birth**, engine pool **address reuse**,
**full scene teardown / new scene** (not manager reset alone) and a hard
**control-actor-unaffected** gate. The host fixture already records
`P2_LIFECYCLE_FORGET`/`REENTRY`/`same_address` and a control survivorship line;
extending it needs the real-GL slot.

## Non-claims

No gameplay/reward semantics change. No corpse-path change. This does not make a
stale key impossible to *read* by a future iteration; it makes the documented
contract true. Does not add new family registrations.
