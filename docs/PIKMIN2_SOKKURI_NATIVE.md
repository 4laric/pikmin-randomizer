# Sokkuri (Skitter Leaf, EnemyID 79) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#165](https://github.com/4laric/pikmin-randomizer/issues/165); source contract
[#346](https://github.com/4laric/pikmin-randomizer/issues/346). First completed
species of the **Species behavior** lane
([fan-out](PIKMIN2_IMPLEMENTATION_FANOUT.md)). One owner: Codex through the
shared `4laric` account.

Sokkuri was chosen because it is the only ground invertebrate whose FSM is
self-contained on the batch-2 Chappy placement vehicle: no external manager
(TamagoMushi), plant (Imomushi), bridge (Armor), pairing (ElecBug) or
`ChappyBase` inheritance (Hana). That makes a *complete* first slice possible
before the lane expands the shared base to variants.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/SokkuriState.cpp`
(`Sokkuri.cpp` helpers) at decomp revision
`632af93787b9c95b63f0c13be32b161375ce3a96`. Retail parameters from
`experimental/pikmin2_ground_inverts_assets.py` (GPVE01 rev 0): life 120,
move speed 120, sight 150, home radius 150, territory 200, max travel 1.0 s,
wait probability 0.4, wait 1.75–3.25 s, underwater speed 25.

| Source state | Implementation |
|---|---|
| `Stay` (hidden leaf) | frozen `appear1` frame 0, no motion, `hidden=1` |
| `Appear` | `appear1`; target in sight radius at `Stay` entry |
| `Disappear` | `hide1`; returns to `Stay` when in home radius with no target |
| `Wait` | `wait1`; timer picks `Disappear`/`MoveGround` |
| `MoveGround` | `run1` loop; territory clamp, random heading, `inputDrive` |
| `MoveWater` | `wrun1` loop; source underwater speed/approach |
| `Flick` | `flick1`; event frame 18 flicks nearby Pikmin (`InteractFlick`) |
| `Dead` / `Press` | `dead1` / `pdead1`; `die()` at clip end; press receiver |

Runtime driving uses the `Teki` host's motion/velocity/health plus a per-frame
`pc_p2_sokkuri_update` hook; the batch-2 draw path is forced to the source clip
and phase for registered Sokkuri via `pc_p2_sokkuri_clip`.

### Port adaptations (recorded, not retail-faithful)

- View-angle detection is a full hemisphere: Sokkuri's general block carries
  fp12 (sight 150) but no fp13 angle; using 0 would never appear.
- Turn rate is a fixed ~π rad/s adaptation; source uses the fp turn class.
- Flick latch radius 25 and shake range/knockback 100/120 are P1-host
  approximations.
- `wallCallback` (source wall steer) is not ported; the actor can stall against
  geometry, visible as the late-run hold near x≈-258.
- `MoveWater` is implemented but no staged arena supplies a water box.

## Files

- `native/pc_port/pc_p2_sokkuri.cpp`, `pc_p2_sokkuri.h` (new).
- Additive hooks: `include/teki.h` (include + `getParameterF` life/attack
  params), `src/plugPikiNakata/tekibteki.cpp` (`BTeki::update`),
  `src/plugPikiNakata/tekiinteraction.cpp` (`InteractPress::actTeki`),
  `src/plugPikiNakata/tekimgr.cpp` (reset/forget),
  `pc_port/pc_p2_batch2.cpp` (Sokkuri clip override + bind log),
  `pc_port/pc_p2_preview.cpp` (setup), `CMakeLists.txt` (unit).
- `experimental/pikmin2_sokkuri_behavior.py`, `tests/test_pikmin2_sokkuri_behavior.py`.
- Every hook is a no-op for unregistered actors; no other family's module is
  touched.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root commit + dirty state / overlay source | `kimi/p2-bulblax-import` @ `9d346a9` + dirty; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native commit + dirty state / worktree / build | `opencode/p2-species-native` @ `356e9c08` + lane edits; `output/native-species`; `output/native-species-build` |
| Squad change present / window change present | root `a51b301`; native `1d5a242b` (ancestry) |
| Squad evidence | the 20-red fixture squad is present and no extinction occurs in the run |
| Executable SHA-256 | `52D69FF3F432A098E9FAED48C6F404E71DFC95A48F8A5EADD3F27EE3B4A9C292` |
| Window setting | `PIKMIN_P2_ROOM_WINDOW=960x540`; log `Experimental preview window set to 960x540 windowed and centered` |
| Private build | `cmake --build output/native-species-build --target pikmin_pc -j 6`; `ninja -n` → `no work to do` |
| Imported manifest | `output/p2-lane-verify/ground/ground_inverts.json` |
| Run directory | `output/p2-species-sokkuri-final/61d347df69d74790a9f9d9d1143f1375` |

Fresh arena command:

```powershell
py -3.12 -m experimental.pikmin2_sokkuri_behavior run \
  --assets C:\Users\alari\pikmin-local\game\assets \
  --imported output/p2-lane-verify/ground \
  --output output/p2-species-sokkuri-final \
  --exe output/native-species-build/bin/nectar.exe --seconds 30
```

Asset/config hashes (run directory): `native.log`
`71EF70A5…ABDE39`; `p2-ground-actors.txt` `2F0AC3C0…F5C62B`;
`p2-ground-bank.txt` `AB419330…D56A11E`; `sokkuri-override.json`
`EE0ED062…B8367903`; `arena.json` `57A5F584…4872C2F`.

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_SOKKURI_BIND generator=346005 source_id=79`; `P2_BATCH2_BIND …ground|Sokkuri visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | `P2_SOKKURI_STATE … state=moveground`; position spread 146.96 over 15 samples; clips `run1`/`wait1`/`flick1` with varying phase |
| 3. Attacks / receivers | receivers PASS (flick), press UNTESTED, attack N/A | flick event frame 18 plus Pikmin knockback; press path compiled/unit-tested, no Pikmin landed on Sokkuri; fp20/fp22/fp24 = 0 |
| 4. Death + corpse | UNTESTED | `Dead`/`Press` states and host corpse/carry path retained; not triggered (no damage source in the run) |
| 5. Transport + reward | source-backed generic | host corpse/carry retained; `type5` carry clip has 0 converted poses on this disc |
| 6. Cleanup + re-entry | UNTESTED | `pc_p2_sokkuri_reset`/`forget` wired into `tekimgr`; no scene teardown exercised |

Family gate `sokkuri_disguise` (previously `blocked: terrain-disguise state
changes are not ported`) is now **PASS** for the Sokkuri actor.

## Known limitations / next slice

- Wall response and press/death/transport runtime paths are unexercised; the
  lifecycle fixture (#397) is still required for gate 6.
- The converted ground bank names Sokkuri `appear1`'s only pose `_01` while the
  native loader reconstructs `_00`; the private runner copies it to `_00` before
  launch (`normalize_pose_names`). The shared fix belongs to the converter/install
  boundary (#128).
- `experimental/pikmin2_batch2_core.prepare` currently calls
  `installer(imported, run, actors)` while `install`/`verify_install` take `cfg`
  first; the lane runner binds `cfg` with `functools.partial`. The shared core
  needs the two call sites reconciled.
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  remain integration-owned; this evidence is from the lane's private Release build.
