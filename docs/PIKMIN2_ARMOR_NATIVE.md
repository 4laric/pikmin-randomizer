# Armor (Cloaking Burrow-nit, EnemyID 15) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#165](https://github.com/4laric/pikmin-randomizer/issues/165); source contract
[#346](https://github.com/4laric/pikmin-randomizer/issues/346). Second species of
the Species behavior lane (variant expansion after the
[Sokkuri slice](PIKMIN2_SOKKURI_NATIVE.md)). Owner: Codex via shared `4laric`.

Armor is the ground invertebrate with an actual animation-driven attack, so it
adds the "animation-driven attack + receivers" gate the passive Sokkuri slice left
source-backed N/A.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/ArmorState.cpp` /
`Armor.cpp` at decomp revision `632af93787b9c95b63f0c13be32b161375ce3a96`.
Retail parameters (GPVE01 rev 0): life 300, move speed 50, sight 200, territory
400, home radius 30, attack sweep 75, attack angle ~45°, bite damage 10.

| Source state | Implementation |
|---|---|
| `Stay` (buried) | frozen `appear` frame 0; wakes when a target is in sight radius |
| `Appear` | `appear`; on end → `Move` (or `Dead` if health ≤ 0) |
| `Move` | `move` loop; turn/walk to the nearest Pikmin/Navi, attack in range+angle |
| `GoHome` | `move`; returns home, attacks in range, `Dive` inside the home radius |
| `Attack2` | `attack2`; capture within the sweep radius only while `17 < motion frame < 27`; on end → `Eat` if captured else `Fail` |
| `Eat` | `eat`; single `InteractKill` at the source event frame 60; on end → `Move` |
| `Flick` | `flick`; knocks back nearby Pikmin at the clip's first event frame |
| `Fail` / `Dive` / `Dead` | `attack_fail` / `dive` / `dead`; `Dive` → `Stay`, `Dead` → `die()` |

Bridge states (`Attack1`, `MoveSide/Centre/Top`) are **source-backed N/A**: the
arena has no `ItemBridge` and `Obj::isBreakBridge()` is never true.

### Port adaptations (recorded, not retail-faithful)

- The P2 mouth-slot swallow is resolved as an explicit capture inside the source
  attack sweep radius at the attack2 frame window, then a single `InteractKill`
  at the eat event. Exactly-once per bite (runtime: 3 bites, 3 eats).
- The source `damageCallBack` part-id rule (`dmg1`/bittered) is not representable
  on the P1 host; damage is accepted while surfaced. The receiver rule is
  UNMEASURED at runtime.
- View angle is a full hemisphere (fp13 absent from the Armor general block);
  turn rate and flick radius are documented port adaptations.
- `attackNavi` captain damage (attack2 event 3) is not yet wired.

## Files

- `native/pc_port/pc_p2_armor.cpp`, `pc_p2_armor.h` (new).
- Additive hooks folded into the existing lane files: `include/teki.h`
  (param chain), `src/plugPikiNakata/tekibteki.cpp` (`BTeki::update`),
  `src/plugPikiNakata/tekimgr.cpp` (reset/forget), `pc_port/pc_p2_batch2.cpp`
  (clip override + bind log), `pc_port/pc_p2_preview.cpp` (setup),
  `CMakeLists.txt` (unit).
- `experimental/pikmin2_armor_behavior.py`, `tests/test_pikmin2_armor_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root commit / overlay source | `kimi/p2-bulblax-import` @ `e172a6f`+; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native commit / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | `6A97D06D9752A393D4C9515482C0823E13978B32FA767DA92A82ADC5B21BC2E7` |
| Private build | `cmake --build output/native-species-build --target pikmin_pc -j 6`; `ninja -n` → `no work to do` |
| Run directory | `output/p2-species-armor-final/6b9d59c4c6794a67b24655e1250eaf15` |
| Hashes | `native.log` `F5B629D6…A86895`; `armor-override.json` `F43057C7…621CC7`; `arena.json` `6568BB95…6FCF78` |

Fresh arena command:

```powershell
py -3.12 -m experimental.pikmin2_armor_behavior run `
  --assets C:\Users\alari\pikmin-local\game\assets `
  --imported output/p2-lane-verify/ground `
  --output output/p2-species-armor-final `
  --exe output/native-species-build/bin/nectar.exe --seconds 30
```

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_ARMOR_BIND generator=346001 source_id=15`; `P2_BATCH2_BIND …ground|Armor visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | `state=appear` → `state=move` → `state=attack2` with `attack2` clip phases |
| 3. Attacks / receivers | PASS (bite), UNMEASURED (dmg1 rule) | `P2_ARMOR_BITE generator=346001 frame=17.9/17.9/17.8` inside the source 17–27 window; capture→`state=eat`→`P2_ARMOR_EAT` exactly once per bite |
| 4. Death + corpse | UNTESTED | `Dead` state + host corpse/carry retained; no damage source in the run |
| 5. Transport + reward | source-backed generic | host corpse/carry retained (Armor `carry` clip) |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired; no scene teardown exercised |

## Remaining work

- Runtime death/corpse/transport/cleanup (lifecycle #397).
- `dmg1` part-id receiver rule and `attackNavi` captain damage.
- Bridge states remain N/A until an ItemBridge arena exists.
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  stay integration-owned.
