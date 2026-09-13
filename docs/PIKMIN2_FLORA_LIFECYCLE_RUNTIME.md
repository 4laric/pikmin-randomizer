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
| Native worktree / commit | `output/native-lifecycle-397` @ `356e9c08ad5c681be0d00232cd31d0409fee50ea` |
| Private build | `output/native-lifecycle-397-build` (`RelWithDebInfo`) |
| Fixture source | `output/converter-lane/flora_lifecycle_room.cpp` (private) |
| Fixture source SHA-256 | `e1c68fb58b71b5c064959dad8e4635340a5efc121129b8f0762ff9aa16539e41` |
| Fixture executable | `output/p2-flora-397-fixture/fixture.exe` |
| Executable SHA-256 | `878f5d46116c3edcaff88366e4bbe43395ac47810bc51382bc922dd845abd9ab` |
| Provenance status | `built` (`output/p2-flora-397-fixture/provenance.json`) |
| Arena run | `output/p2-flora-397-evidence/61f4407845144c84a35f9c9b1a9bef91` |
| Arena SHA-256 | `d40442be7e63980bc49e503ce579dca34f8993fc9736e6ece3cba532497cd4bb0` |
| Native log SHA-256 | `502d084278aba3428fb7f7e36911257ce33c7f012c99b30a8092ea3441fbc3db` |
| Evidence JSON | `output/p2-flora-397-evidence/.../lifecycle-evidence.json` |

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
| 5 | Actual transport and reward | BLOCKED / source-backed N/A | Pelplant pellet capture/release and the Pod reward path are not implemented; no carry route was driven. |
| 6 | Cleanup and re-entry | PASS with limitation | `P2_LIFECYCLE_CLEANUP live=1`, `P2_LIFECYCLE_RESPAWN_INJECT generator=353001`, `P2_LIFECYCLE_REENTRY id=353001 frame=384 reused=0`, control alive. `P2_LIFECYCLE_REBIND_SKIPPED present=6 expected=7`: the visual re-bind was skipped because the shared `pc_p2_batch2_setup()` requires every configured arena actor present (one flora proxy was killed by the Pikmin squad). |

`PASS P2_LIFECYCLE_RUNTIME` is present and the process exits 0.

## Explicit limitations (not folded into the PASSes)

- **Animation-event execution:** source Pelplant key events (wait loop bounds,
  grow/damage/dead) are data only. No growth FSM, no pellet attach/release, no
  withering.
- **Material fidelity:** sampled poses with the approximate converter material
  policy; no TEV/BTK/BRK parity claim.
- **Runtime failures / narrow registration gap:** re-binding a respawned proxy
  after a partial family death is blocked by the strict all-actors-present
  re-scan in `pc_p2_batch2_setup()` (native `pc_port/pc_p2_batch2.cpp:225`).
  The lifecycle gate itself passes; the visual re-bind on re-entry does not.
  Fixing it is a narrow registration change and is left for #397/#186 review.
- **Identity:** the proxy is a Dwarf Bulborb vehicle, so this does not establish
  source Pelplant AI, collision or reward semantics.
- **Gate 5** is not tested; the Pikmin squad did attack and kill a flora proxy,
  which is why the re-bind count is 6/7.

## Reproduction

```powershell
# 1. stage the refreshed flora arena (Pelplant included from the #405 bank)
py -3.12 -m experimental.pikmin2_flora_arena `
  --assets "C:\Users\alari\bbft\dist\cohesion\pikmin\assets" `
  --imported output/p2-converter-evidence/run1 `
  --output output/p2-flora-397-evidence

# 2. write lifecycle-positions.txt from the run arena.json (id type registered x y z)

# 3. build the fixture (private)
py -3.12 scripts/build_pikmin2_fixture.py `
  --source output/native-lifecycle-397 --build output/native-lifecycle-397-build `
  --fixture output/converter-lane/flora_lifecycle_room.cpp `
  --expected-native-head 356e9c08ad5c681be0d00232cd31d0409fee50ea `
  --output output/p2-flora-397-fixture

# 4. run from the staged run directory
$env:PATH='output\native-lifecycle-397-build\bin;C:\msys64\mingw64\bin;'+$env:PATH
$env:SDL_AUDIODRIVER='dummy'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
& output\p2-flora-397-fixture\fixture.exe --experimental-pikmin2-room
```

Focused tests: `py -3.12 -m pytest tests/test_pikmin2_batch2.py
tests/test_pikmin2_batch2_runtime.py -q`.

## Non-claims

No source FSM, pellet receptor, transport/reward, campaign persistence, mixed-scene
performance or material parity is claimed. The proxy identity is deliberately not
source identity. Disc assets, generated models, executables and logs stay under
private `output/`.
