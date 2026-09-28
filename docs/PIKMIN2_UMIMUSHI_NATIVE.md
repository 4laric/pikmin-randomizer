# UmiMushi (Toady Bloyster, EnemyID 71) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#167](https://github.com/4laric/pikmin-randomizer/issues/167). Fourth aquatic
species of the Species behavior lane. Owner: Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/UmiMushi.cpp` /
`UmiMushiState.cpp` (states `UmiMushi.h:57-69`); retail parameters and clip
events in `experimental/pikmin2_aquatic_assets.py`. Host is the P1 Chappy
placement vehicle (`TEKI_Chappy`), generator `374004`.

| Source behavior | Implementation |
|---|---|
| `Wait` / `Walk` / `Find` / `Search` / `Turn` | source locomotion with target search |
| `Attack` (tongue) | `attack1`; capture at the banked bite event frame 39, one kill at the banked `eat1` swallow |
| `Flick` | `flick1` at frame 9 / `attack1` event 66 |
| `Eat` | `eat1` |
| `Dead` | `dead1`; `die()` at clip end |

### Port adaptations

- No P2 water box / Hamon sea height; dry fallback presentation.
- The shared `UmiMushi::Mgr` base(100)/Blind(101) split is not representable:
  ordinary (71) parameters only; Blind half-scale / fp12=800 health are gaps.
- The seven-slot tongue (`kamu_joint1..7`) is not representable; the bite is an
  explicit capture inside the source fp22=170 hit radius at the banked bite
  frame, then one kill at the eat swallow.
- Port adaptation for the bite trigger: a Pikmin anywhere inside the source
  fp22=170 hit radius starts the attack (the source also gates on the fp23=15°
  cone, which the P1 host cannot align reliably). The latch-flick radius is
  reduced to 20 so it does not pre-empt every bite.

## Files

- `native/pc_port/pc_p2_umimushi.cpp`, `pc_p2_umimushi.h` (new).
- Additive hooks: `include/teki.h`, `tekibteki.cpp`, `tekimgr.cpp`,
  `pc_p2_batch3.cpp` (clip override + bind log), `pc_p2_preview.cpp`,
  `CMakeLists.txt`.
- `experimental/pikmin2_umimushi_behavior.py`, `tests/test_pikmin2_umimushi_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | combined `D1BFCAC21BBFC013BAFDEF09671F033B75710CCA06C17F4F7B7A1737785C9AF2` |
| Run directory | `output/p2-species-umimushi-fix2/4134cf2cdd0041968fd732b959fe41bb` |
| Hash | `native.log` `B5B231E1…BA52A86B` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_UMIMUSHI_BIND generator=374004 source_id=71`; `P2_BATCH3_BIND …key=aquatic|UmiMushi visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | states `walk/find/turn/flick/attack/eat`; 46.5 XZ spread |
| 3. Attacks / receivers | PASS | bites at frame 39 with exactly one `P2_UMIMUSHI_EAT` each |
| 4. Death + corpse | UNTESTED | `Dead` coded; no damage source |
| 5. Transport + reward | source-backed generic | host corpse/carry retained |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired |

## Remaining work

- Water box, Blind/base parameter split, boss phase staging, tongue geometry.
- Death/corpse/cleanup (#397).
