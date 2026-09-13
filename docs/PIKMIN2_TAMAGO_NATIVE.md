# TamagoMushi (Mitite, EnemyID 68) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#165](https://github.com/4laric/pikmin-randomizer/issues/165); source contract
[#346](https://github.com/4laric/pikmin-randomizer/issues/346). Fourth species of
the Species behavior lane (after [Sokkuri](PIKMIN2_SOKKURI_NATIVE.md),
[Armor](PIKMIN2_ARMOR_NATIVE.md), [ElecBug](PIKMIN2_ELECBUG_NATIVE.md)). Owner:
Codex via shared `4laric`.

TamagoMushi adds the Astonish contact receiver and a honey reward path.

## Source contract implemented

`native/pikmin2-research/src/plugProjectMorimuraU/tamagoMushi.cpp` /
`tamagoMushiState.cpp` at decomp revision
`632af93787b9c95b63f0c13be32b161375ce3a96`. Retail parameters (GPVE01 rev 0):
life 50, move speed 100, sight 150, territory 120, home radius 30, appearance
range 80, honey rate 1.0, panic max time 30.

| Source behavior | Implementation |
|---|---|
| `Walk` / `Turn` / `Wait` | `move`/`wait` wander inside the territory/home clamp |
| `Appear` / `Hide` | `set` / `dive` surface-and-hide cycle |
| Astonish receiver (`collisionCallback`, tamagoMushi.cpp:239) | each Pikmin entering the collision radius is knocked back once per contact |
| Honey reward (`genItem`, tamagoMushi.cpp:326) | on death, one `OBJTYPE_Water` nectar drop; host corpse suppressed for exactly-once reward |
| `Dead` | `dead`; `die()` at clip end |

### Port adaptations (recorded, not retail-faithful)

- The P1 engine has no `InteractAstonish`; a contact is resolved as an
  `InteractFlick` knockback (the closest P1 panic/scatter receiver), applied once
  per contact.
- The source manager-owned group birth (`createGroup`, 10 surface / 30 cave) is
  not implemented; the staged actor runs the singleton FSM.
- `ItemHoney HONEY_Y` is resolved as the P1 `OBJTYPE_Water` nectar object.

## Files

- `native/pc_port/pc_p2_tamago.cpp`, `pc_p2_tamago.h` (new).
- Additive hooks: `include/teki.h` (param chain + `TPI_CorpseType`),
  `src/plugPikiNakata/tekibteki.cpp` (update), `tekimgr.cpp` (reset/forget),
  `pc_port/pc_p2_batch2.cpp` (clip override + bind log), `pc_port/pc_p2_preview.cpp`
  (setup), `CMakeLists.txt`.
- `experimental/pikmin2_tamago_behavior.py`, `tests/test_pikmin2_tamago_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | `331F29DE73C331D18C0893C839AA4B8011BF9CD817518510F4A4E76405132544` |
| Build | `cmake --build output/native-species-build --target pikmin_pc -j 6`; `ninja -n` → no work to do |
| Run directory | `output/p2-species-tamago/b351499f8ee844c2b51d99bd72956555` |
| Hashes | `native.log` `1CE0AC9E…25C4808`; `tamago-override.json` `2F6E7166…1A41C6`; `arena.json` `1EAB104A…244EA8` |

Fresh arena command:

```powershell
py -3.12 -m experimental.pikmin2_tamago_behavior run `
  --assets C:\Users\alari\pikmin-local\game\assets `
  --imported output/p2-lane-verify/ground `
  --output output/p2-species-tamago `
  --exe output/native-species-build/bin/nectar.exe --seconds 30
```

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_TAMAGO_BIND generator=346004 source_id=68`; `P2_BATCH2_BIND …ground|TamagoMushi visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | 247.7 XZ spread; `state=hide/appear/wait/walk` with clip phases |
| 3. Attacks / receivers | PASS (Astonish approximation) | `P2_TAMAGO_ASTONISH generator=346004 pikmin=1` (flick knockback once per contact); true panic state UNMEASURED |
| 4. Death + corpse | UNTESTED | `Dead` + honey drop implemented; no damage source in the run |
| 5. Transport + reward | UNTESTED (honey) | honey drop compiled; delivery receipt not exercised; host corpse suppressed |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired |

Focused suite: 19 passed (Sokkuri + Armor + ElecBug + TamagoMushi).

## Remaining work

- Manager-owned group birth; true Astonish panic; honey delivery receipt.
- Death/corpse/transport/cleanup (lifecycle #397).
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  stay integration-owned.
