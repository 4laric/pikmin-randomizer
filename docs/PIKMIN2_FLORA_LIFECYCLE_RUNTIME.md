# Flora / Pelplant lifecycle arena runtime (#397)

Issue: [#397](https://github.com/4laric/pikmin-randomizer/issues/397) (parent
[#171](https://github.com/4laric/pikmin-randomizer/issues/171); source
[#353](https://github.com/4laric/pikmin-randomizer/issues/353); converter
[#405](https://github.com/4laric/pikmin-randomizer/issues/128)). Worker: Codex
via shared `4laric` account.

This is the first family to exercise the #397 cleanup/re-entry fixture: a
**non-invincible** Pelplant proxy is staged, killed, forgotten, respawned by its
generator and re-entered. It adopts the refreshed #405 Pelplant bank (10/10
clips) and the mandatory 960x540 centred fixture baseline.

## Fixture and provenance

| Item | Value |
|---|---|
| Native worktree / commit | `output/native-lifecycle-397` @ `5c9492c651ff1a9d75b228f9bf72ea31aa2b326e` (adds `pc_p2_batch2_rebind`) |
| Private build | `output/native-lifecycle-397-build` (`RelWithDebInfo`) |
| Fixture source | `output/converter-lane/flora_lifecycle_room.cpp` (private) |
| Fixture source SHA-256 | `a74c3c3147dec792f961fb001d7c89e9e0090af720510b1ea09188086104357f` |
| Fixture executable | `output/p2-flora-397-fixture-rebind/fixture.exe` |
| Executable SHA-256 | `1c44c368e66a3ee659b94de6cd5c32634fc6f6dc048716776c8d2e243a5423ac` |
| Provenance status | `built` (`output/p2-flora-397-fixture-rebind/provenance.json`) |
| Arena run | `output/p2-flora-397-evidence/61f4407845144c84a35f9c9b1a9bef91` |
| Arena SHA-256 | `d40442be7e63980bc49e503ce579dca34f8993fc9736e6ece3cba532497cd4bb0` |
| Native log SHA-256 | `79ceeef4868ff77b55096e22432f138c4c8075060c3879de193d561485ed23a6` |
| Evidence JSON | `output/p2-flora-397-evidence/.../lifecycle-evidence-rebind.json` (SHA-256 `87ab400f1e42e33426d419bfbd88d873f109542e72dc3892e792f1464b3c5571`) |

The fixture is a replacement main (`preview_p2_room.cpp` pattern). Because it
does not run the production `pc_main.cpp` path, it performs its own
`pc_window_init(..., 960, 540)` and `pc_window_center()`, matching the #404
mandatory baseline. The starting squad comes from the arena `overlay()`
(`ensure_pikmin_squad`, 20 red Pikmin). The log is UTF-16 (PowerShell
redirection); the evidence JSON decodes it explicitly.

## Six-gate table (Pelplant, enemy ID 0)

| # | Gate | Result | Evidence |
|---|---|---|---|
| 1 | Exact identity and spawn | PASS (proxy) | `P2_BATCH2_BIND generator=353001 key=flora|Pelplant`; `P2_LIFECYCLE_BIRTH id=353001 type=3 registered=1 invincible=0 x=-360 y=30 z=1850`. Identity is the config key on the neutral `TEKI_Chappy` placement vehicle; a native Pelplant class does not exist, so identity is a proxy, not source identity. |
| 2 | Autonomous movement and animation | PASS with limitation | Pelplant bank binds and loads (7 banks, `flora_Pelplant_*` MODs opened); flora draw path emits `P2_BATCH2_DRAW corpse=0 key=flora|RedPom clip=wait`. Source Pelplant is stationary: locomotion is the P1 Chappy vehicle and the growth FSM is not executed. |
| 3 | Attacks and receivers | PASS (injected) | The proxy is non-invincible and accepts an injected `InteractAttack(...,100000)` per frame; the target reaches death. Natural P1-proxy combat is also observed (a flora corpse draw). This is a proxy receiver, not the source Pelplant "Full only" damage rule. |
| 4 | Death and corpse | PASS (proxy) | `P2_LIFECYCLE_DEATH id=353001 frame=203`; `P2_BATCH2_DRAW corpse=1 key=flora|RedPom clip=dead`. The source Pelplant pellet corpse (PelletView release) is not produced by the proxy. |
| 5 | Actual transport and reward | BLOCKED (partial) | Native attachment PASS: `P2_CARRY_ATTACH carriers=20 min=3`, corpse uses the flora bank (`P2_BATCH2_DRAW corpse=1 key=flora\|Pelplant clip=wait1`). Cargo-free arena: corpse traverses to max XZ distance 426.87 then stalls (`state=0`). Pod-room attempt (native `fb6389ce`, staged converted room + `p2-pod.txt`): `P2_POD_READY treasure=map01 value=200 weight=3 capacity=20`, Pelplant bound and corpse attached at x=-701 z=578, but the corpse never moves (`distance=0.00` for 25 samples) and the route times out — no `P2_POD_RECEIPT`. Evidence: `lifecycle-evidence-carry.json` (carry log SHA-256 `2a42e0d3…389e10`; Pod log SHA-256 `03af2203…ecece94`). |
| 6 | Cleanup and re-entry | PASS | `P2_LIFECYCLE_CLEANUP live=1`, `P2_LIFECYCLE_RESPAWN_INJECT generator=353001`, `P2_LIFECYCLE_REENTRY id=353001 frame=384 reused=0`, control alive. `P2_BATCH2_MISSING family=flora found=6 wanted=7` is tolerated and the respawned `generator=353001 key=flora\|Pelplant` is re-bound by the new `pc_p2_batch2_rebind()`; the proxy is drawable again after re-entry. |

`PASS P2_LIFECYCLE_RUNTIME` is present and the process exits 0.

## Explicit limitations (not folded into the PASSes)

- **Animation-event execution:** source Pelplant key events (wait loop bounds,
  grow/damage/dead) are data only. No growth FSM, no pellet attach/release, no
  withering.
- **Material fidelity:** sampled poses with the approximate converter material
  policy; no TEV/BTK/BRK parity claim.
- **Runtime registration:** scene start keeps the strict all-actors-present
  `pc_p2_batch2_setup()` contract; re-entry uses the new additive
  `pc_p2_batch2_rebind()` (native commit `5c9492c6`,
  `pc_port/pc_p2_batch2.cpp`), which tolerates legitimately absent actors and
  re-binds the rest. It is a narrow additive hook; the startup contract is
  unchanged. Native export and #186 shared-semantics review are still required.
- **Identity:** the proxy is a Dwarf Bulborb vehicle, so this does not establish
  source Pelplant AI, collision or reward semantics.
- **Gate 5 (transport/reward) is BLOCKED, with partial evidence.** The arena is
  cargo-free (`pc_p2_preview_cargo_free_ready()`), so there is no Pod, and the
  original-stage carry route does not connect the z≈1850 arena row to the Onion:
  the proxy corpse is attached (20 carriers) and traverses 426.87 units, then
  stalls in carry state without entering the goal, so no reward is issued.
  A converted Pod room was then staged at `output/p2-flora-deliver-evidence`
  (`room.mod`/`treasure.mod`/`pod.mod` + `p2-pod.txt`); against native
  `fb6389ce` the run reaches `P2_POD_READY` and binds/attaches the Pelplant
  proxy corpse at `x=-701 z=578`, but the corpse **does not move**
  (`distance=0.00` over 25 samples) and the route times out, so no
  `P2_POD_RECEIPT` is produced. Source Pelplant pellet release/capture is also
  not implemented (the proxy corpse is a P1 Chappy corpse). Gate 5 is handed to
  the active #397 native reward-lifecycle work (the shared branch already
  carries `fb6389ce` "additive corpse-registry rebind for the reward lifecycle
  fixture").

## Reproduction

```powershell
# 1. stage the refreshed flora arena (Pelplant included from the #405 bank)
py -3.12 -m experimental.pikmin2_flora_arena `
  --assets "C:\Users\alari\bbft\dist\cohesion\pikmin\assets" `
  --imported output/p2-converter-evidence/run1 `
  --output output/p2-flora-397-evidence

# 2. write lifecycle-positions.txt from the run arena.json (id type registered x y z)

# 3. build the native rebind candidate and the fixture (private)
#    branch opencode/p2-lifecycle-native @ 5c9492c6 adds pc_p2_batch2_rebind()
cmake --build output/native-lifecycle-397-build --target pikmin_pc -j 6
py -3.12 scripts/build_pikmin2_fixture.py `
  --source output/native-lifecycle-397 --build output/native-lifecycle-397-build `
  --fixture output/converter-lane/flora_lifecycle_room.cpp `
  --expected-native-head 5c9492c651ff1a9d75b228f9bf72ea31aa2b326e `
  --output output/p2-flora-397-fixture-rebind

# 4. run from the staged run directory
$env:PATH='output\native-lifecycle-397-build\bin;C:\msys64\mingw64\bin;'+$env:PATH
$env:SDL_AUDIODRIVER='dummy'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
& output\p2-flora-397-fixture-rebind\fixture.exe --experimental-pikmin2-room
```

Focused tests: `py -3.12 -m pytest tests/test_pikmin2_batch2.py
tests/test_pikmin2_batch2_runtime.py -q`.

## Non-claims

No source FSM, pellet receptor, transport/reward, campaign persistence, mixed-scene
performance or material parity is claimed. The proxy identity is deliberately not
source identity. Disc assets, generated models, executables and logs stay under
private `output/`.
