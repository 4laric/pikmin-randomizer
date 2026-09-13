# ElecBug (Anode Beetle, EnemyID 28) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#165](https://github.com/4laric/pikmin-randomizer/issues/165); source contract
[#346](https://github.com/4laric/pikmin-randomizer/issues/346). Third species of
the Species behavior lane (after [Sokkuri](PIKMIN2_SOKKURI_NATIVE.md) and
[Armor](PIKMIN2_ARMOR_NATIVE.md)). Owner: Codex via shared `4laric`.

ElecBug adds the electrical receiver and invulnerable-until-flipped rule the
previous slices did not cover.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/ElecBugState.cpp` /
`ElecBug.cpp` at decomp revision `632af93787b9c95b63f0c13be32b161375ce3a96`.
Retail parameters (GPVE01 rev 0): life 500, move speed 30, sight 200, territory
200, home radius 100, flip time 5.0, wait 1.5, discharge 3.0, sweep radius 70.

| Source state | Implementation |
|---|---|
| `Wait` / `Turn` / `Move` | `wait`/`turn`/`move` wander; Charge when a target enters sight |
| `Charge` | `charge`; after the source charge delay → Discharge |
| `Discharge` | `discharge`; shocks the nearest non-Yellow Pikmin within the source sweep radius once, for 3.0 s, then `Return` |
| `Return` | `recover`; back to `Wait` |
| `Reverse` | entered by press; disables invulnerability for the source flip time, then recovers |
| `Dead` | `dead`; `die()` at clip end |

Invulnerability: registered ElecBugs swallow attacks until pressed into
`Reverse` (`InteractAttack::actTeki` hook), matching the source `Obj::init`
invulnerability + `Reverse` teardown.

### Port adaptations (recorded, not retail-faithful)

- The source two-beetle `Charge`/`ChildCharge` partner link is not implemented on
  the P1 host; the beetle runs a **singleton** Charge → Discharge → Return cycle.
- The P1 engine has no `InteractDenki`; between-beetle Denki geometry is resolved
  as the single nearest non-Yellow Pikmin within the source sweep radius, shocked
  once per discharge via `InteractKill`. Yellow exclusion is source-backed;
  broader Bulbmin/immunity exclusions are not modelled.
- View angle is a full hemisphere; charge/return/wander durations are port values.

## Files

- `native/pc_port/pc_p2_elecbug.cpp`, `pc_p2_elecbug.h` (new).
- Additive hooks folded into the lane files: `include/teki.h` (param chain),
  `src/plugPikiNakata/tekibteki.cpp` (update), `tekiinteraction.cpp`
  (attack + press), `tekimgr.cpp` (reset/forget), `pc_port/pc_p2_batch2.cpp`
  (clip override + bind log), `pc_port/pc_p2_preview.cpp` (setup),
  `CMakeLists.txt`.
- `experimental/pikmin2_elecbug_behavior.py`, `tests/test_pikmin2_elecbug_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import` (`cc2ee2e`+); `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | `4058BCD3A5B7FBF7E03FFBB635CC0431EDB431EDF86B02EFBECF8E792927C2B1` |
| Build | `cmake --build output/native-species-build --target pikmin_pc -j 6`; `ninja -n` → no work to do |
| Run directory | `output/p2-species-elecbug-final/b6e3baed2e0641ae885672f70ac94bba` |
| Hashes | `native.log` `8FAA63AC…8B2D52`; `elecbug-override.json` `9EE417D2…B29F27`; `arena.json` `EC89038F…5EE8F2` |

Fresh arena command:

```powershell
py -3.12 -m experimental.pikmin2_elecbug_behavior run `
  --assets C:\Users\alari\pikmin-local\game\assets `
  --imported output/p2-lane-verify/ground `
  --output output/p2-species-elecbug-final `
  --exe output/native-species-build/bin/nectar.exe --seconds 30
```

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_ELECBUG_BIND generator=346002 source_id=28`; `P2_BATCH2_BIND …ground|ElecBug visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | `P2_ELECBUG_POS` states `move`/`wait` with clip phases |
| 3. Attacks / receivers | PASS (discharge), press UNTESTED | 4 × `P2_ELECBUG_DISCHARGE` with 2 × `P2_ELECBUG_SHOCK` (one non-Yellow Pikmin per discharge); press→Reverse compiled but not exercised unattended |
| 4. Death + corpse | UNTESTED | `Dead` state + host corpse retained; no damage source in the run |
| 5. Transport + reward | source-backed generic | host corpse/carry |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired; no teardown exercised |

Focused suite: 15 passed (Sokkuri + Armor + ElecBug).

## Remaining work

- Two-beetle partner link and full Denki immunity matrix; press-to-flip runtime path.
- Death/corpse/transport/cleanup (lifecycle #397).
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  stay integration-owned.
