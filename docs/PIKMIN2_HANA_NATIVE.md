# Hana (Creeping Chrysanthemum, EnemyID 84) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#165](https://github.com/4laric/pikmin-randomizer/issues/165); source contract
[#346](https://github.com/4laric/pikmin-randomizer/issues/346). Sixth and final
ground species of the Species behavior lane. Owner: Codex via shared `4laric`.

Hana inherits `ChappyBase` in source; this slice implements the source ambush
wrapper on the P1 Chappy host as a new additive module without touching the
bulborb/Chappy lane modules.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/Hana.cpp` / `HanaState.cpp`
and the inherited `ChappyBase` attack states at decomp revision
`632af93787b9c95b63f0c13be32b161375ce3a96`. Retail parameters (GPVE01 rev 0):
life 2500, move speed 100, territory 300, home radius 15, sight 500 (angle 90),
attack damage 10, sweep 75/80, foot range 30, poison 2500.

| Source behavior | Implementation |
|---|---|
| `Sleep` (buried) | hidden; `type1` frame 0; wakes when a Pikmin/Navi enters the sight radius |
| `Appear`/emerge (`type1`) | burrow emerge, then `Walk` |
| `Walk`/`GoHome` | `move1` chase inside territory/home clamp |
| `Attack` (`attack1`) | capture the nearest Pikmin only inside the banked bite window, then one kill at the banked swallow event frame |
| `Eat` | `waitact1` recovery after the swallow |
| `Flick` / `Dead` | `flick` / `dead` |

Bite/swallow frames are parsed from the validated `p2-ground-bank.txt`
(`attack1 18:2` bite, `71:3` swallow) with the audit frames as fallback.

### Port adaptations (recorded, not retail-faithful)

- The P2 `kamu1..3` mouth slots are resolved as an explicit capture inside the
  attack sweep during the bite window, then a single `InteractKill` at the
  swallow frame; exactly once per bite.
- The source `setUnderGround` invulnerability/no-atari is not exposed on the P1
  Chappy host, so "buried" suppresses the FSM/pose only; damage is accepted from
  surfaced states.
- Wake test uses the source sight radius (fp12=500); `isWakeup` uses a private
  radius in source. `attackNavi` captain damage and `fp02` poison are not wired.

## Files

- `native/pc_port/pc_p2_hana.cpp`, `pc_p2_hana.h` (new).
- Additive hooks: `include/teki.h` (param chain), `tekibteki.cpp` (update),
  `tekimgr.cpp` (reset/forget), `pc_p2_batch2.cpp` (clip override + bind log),
  `pc_p2_preview.cpp` (setup), `CMakeLists.txt`.
- `experimental/pikmin2_hana_behavior.py`, `tests/test_pikmin2_hana_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Isolated executable SHA-256 | `5BC0B3297C2217E8348CE401DCA6F5E47E0EF28E92D02FDD32580DF7617BC66E` |
| Combined six-species exe | `AAF17C0D36BA0C86AB621C4924C5826FCF43883A25E5CA085B9F12A6D8003ADB` |
| Isolated run directory | `output/p2-species-hana-final/c07f4ca440374f80a8583afdb4be417f` |
| Combined run directory | `output/p2-species-combined/4550a6a23d9b43a19d7701325e7b7026` |
| Hashes | isolated `native.log` `E6956786…6D5713`; `hana-override.json` `008C5D75…F71860`; combined `native.log` `C12A87E1…D1DA03` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_HANA_BIND generator=346006 source_id=84`; `P2_BATCH2_BIND …ground|Hana visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | `state=sleep` → `emerge` → `walk` → `attack` → `eat`; 53.7 XZ spread |
| 3. Attacks / receivers | PASS | `P2_HANA_BITE generator=346006 frame=18.1/18.2` inside the source bite window; each followed by exactly one `P2_HANA_EAT` |
| 4. Death + corpse | UNTESTED | `Dead` + host corpse retained; no damage source in the run |
| 5. Transport + reward | source-backed generic | host corpse/carry retained |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired; no teardown cycle |

## Remaining work

- `setUnderGround` invulnerability/no-atari; `attackNavi` captain damage; `fp02` poison.
- Death/corpse/transport/cleanup (lifecycle #397).
- Maintained `native/build-randomizer` rebuild and `scripts/export_native_source.py`
  stay integration-owned.
