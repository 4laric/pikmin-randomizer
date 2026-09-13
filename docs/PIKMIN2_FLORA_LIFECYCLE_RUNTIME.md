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
| Gate-5 delivery: native / fixture | `fb6389ce2968ae4c6da4563580f5ce672a9e32f7` / `output/p2-flora-deliver-fixture/fixture.exe` (SHA-256 `2be01c43afcaac15657a2ecf0c66e8123029efeb6ba80db263642b43e0d62b43`, provenance `built`) |
| Gate-5 delivery run | `output/p2-flora-deliver-evidence/a34e00c954ca4ea79ab977d3dd0e927e` (converted Pod room; log SHA-256 `ec4c77cca31d4d9a8d2d7bce622980dcab26f1c638dca6b1b22f7833f4b6d2b9`; `lifecycle-evidence-deliver.json`) |

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
| 5 | Actual transport and reward | PASS (P1-proxy reward) | Converted Pod room, native `fb6389ce`: `P2_POD_READY`, 20 carriers attach, corpse traverses 93.68→129.97 and enters the goal, then `P2_POD_RECEIPT id=corpse:353001 value=2 new=1 pokos=2 seeds=0` — exactly-once (`new=1`), no seeds, repairs unchanged (`P2_DELIVER_RECEIPT delta=2 repairs=1`). The corpse uses the flora bank (`P2_BATCH2_DRAW corpse=1 key=flora\|Pelplant`). Source Pelplant pellet→seed reward is N/A to the proxy. Log SHA-256 `ec4c77cc…3f4b6d2b9`. |
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
- **Gate 5 is PASS at the P1-proxy reward level, not the source reward.** On the
  converted Pod room the proxy corpse is attached (20 carriers), traverses
  ~134 units, enters the goal and produces exactly one Pod receipt
  (`corpse:353001`, 2 Pokos, `new=1`, `seeds=0`, repairs unchanged). The source
  Pelplant pellet release/capture and Onion seed reward are **not** implemented:
  the corpse is a P1 Chappy corpse drawn with the flora bank. The earlier
  cargo-free arena stalls mid-route and is not the gate-5 fixture. Run evidence:
  `output/p2-flora-deliver-evidence/a34e00c9…/lifecycle-evidence-deliver.json`.

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
