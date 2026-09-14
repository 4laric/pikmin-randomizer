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

## Runtime adoption (reconciled candidate)

Re-run on a freshly re-staged arena against this reconciled native candidate. The
#397 non-invincible lifecycle fixture and the isolated marker-gated forget probe
were both rebuilt with [the provenance builder](PIKMIN2_FIXTURE_BUILDS.md) from
the same private build.

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #397 / lane 07 / Codex via shared 4laric
Root commit + dirty state / overlay source: opencode/p2-lanes67-next @ d250e08 (clean);
  scripts/preview_pikmin2_room.py overlay() -> ensure_pikmin_squad (20 reds)
Native commit + dirty state / worktree / private build directory: 4c3b32e6 (clean) /
  output/lane67-native / output/lane67-native-build (Ninja/Release/MinGW, JAudio ON)
Squad change present / window change present (ancestry or source evidence): yes / yes
Fresh arena command / run directory / asset and config hashes: re-staged from
  output/tracks/p2-lanes789/flora-arena-05 via experimental.pikmin2_lifecycle_runtime
  --existing; probe run output/lane67-forget-run/cd88653162324602b73ef3a477bc0bf1;
  lifecycle run output/lane67-root/output/lane67-lifecycle-run/49c6a69d96e0431ea167eae13a31ccd6;
  default.gen sha256 8f0fc1cd69f011b941c37936c9ac96f44c9009f85f826fa51b994c912b5230bf
  (20 ikip); arena.json sha256 f5b88b0ac7ee03e910ba8156d82da47944f53d438c261baff942cf4315bb09ea
Executable SHA-256 / fixture provenance status: engine-forget probe
  8AD020C06FC33B8B2474D59AE800CC6CB4F9D3A3C7464E5B0151B9044AC524B1 (status built);
  lifecycle fixture FF16D2C2F8161BA94F7E9C55928DCD7F03CB320C2DDFFF6EC5D1C89B61098173
Window setting / observed size and centring evidence: lifecycle log
  "Experimental preview window set to 960x540 windowed and centered"; probe window
  "SDL2 Window & OpenGL Context initialized successfully (960x540)" + pc_window_center()
Live starting Pikmin / active gameplay / no immediate extinction evidence: 20 reds
  (`P2_LIFECYCLE_SQUAD alive=20`); active gameplay reached; no extinction screen
PASS, FAIL, or BLOCKED; remaining work: PASS (engine-forget + full lifecycle)
```

### Results

Engine-forget probe (isolated, `deadPtr->kill(false)` -> `BTeki::doKill`):

```text
P2_LIFECYCLE_CLEANUP id=353001 live=1 registered=1     # corpse retains registration
P2_FORGET_PROBE before=1
P2_FORGET_PROBE after_engine_dokill=0                  # pc_p2_forget_teki ran
PASS P2_FORGET_PROBE
```

Full lifecycle fixture (`PASS P2_LIFECYCLE_RUNTIME`, exit 0):

```text
P2_LIFECYCLE_BIRTH 353001..353007 registered=1 invincible=0; 353008 (control) registered=0
P2_LIFECYCLE_TARGET id=353001
P2_LIFECYCLE_DEATH id=353001 frame=5
P2_LIFECYCLE_FORGET id=353001 before=7 after=6 registered_before=1 registered_after=0
P2_LIFECYCLE_RESPAWN_INJECT id=353001 generator=353001
P2_LIFECYCLE_REENTRY id=353001 frame=126 reused=0     # late birth + clean re-registration
P2_LIFECYCLE_SUMMARY family=7 alive=6 moved=5 death=5 reentry=126 reused=0 control=1
```

Logs: `output/lane67-forget-run/.../native-forget-probe.log` sha256
`A970EC51F895957878A63F37423329E61804C8E06BB9253F9C9EFDF043E4627B`;
`output/lane67-root/output/lane67-lifecycle-run/.../native.log` sha256
`E192222B5EA3B4D9A1114DAB67F8C4BCC4B0DC53EA8347706B1CA3DAA3FA4D4C`.

### Gates closed / still open

- **Closed (runtime):** natural death funnel, engine-driven `pc_p2_forget_teki`
  (no fixture `_forget` call), late birth (respawned actor re-registered after
  start), control actor unaffected (`control=1`), window/squad baseline.
- **Still open:** engine pool **address reuse** (`reused=0`; the retained corpse
  keeps the slot, so `newTeki` does not hand the address back in this scenario)
  and **full scene/day teardown** (the manager `reset()` path is narrower
  evidence). Both need the corpse-release/hard-teardown probe on a GL host.

Two-line divergence note: the approved native baseline `f14c6851` still differs
from the maintained room-preview native tip; lane 01 owns reconciling the
material/queen paths. This candidate is pinned to the approved baseline.

## Non-claims

## Non-claims

No gameplay/reward semantics change. No corpse-path change. This does not make a
stale key impossible to *read* by a future iteration; it makes the documented
contract true. Does not add new family registrations.
