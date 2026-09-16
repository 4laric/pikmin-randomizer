# Catfish (Water Dumple, EnemyID 26) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#167](https://github.com/4laric/pikmin-randomizer/issues/167); source contract
[#347](https://github.com/4laric/pikmin-randomizer/issues/347). Second aquatic
species of the Species behavior lane (after [Tadpole](PIKMIN2_TADPOLE_NATIVE.md)).
Owner: Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/` Catfish/KochappyBase states;
retail parameters, state IDs and clip events in
`experimental/pikmin2_aquatic_assets.py`. Host is the P1 Water Dumple
(`TEKI_Namazu`), generator `374001`.

| Source behavior | Implementation |
|---|---|
| `Wait` / `Turn` / `Walk` | `wait1`/`move1` wander with source speed/territory |
| `Attack` (bite) | `attack` clip; one capture inside the source attack sweep at the banked bite event (frame 17), one kill at the banked swallow event (frame 75) |
| `Flick` | `flick` clip; knockback at the banked flick event frames (25/47) |
| `Dead` | `dead`; `die()` at clip end |

### Port adaptations

- The P2 two-slot mouth swallow is not representable on the P1 `TEKI_Namazu`
  host; it is resolved as an explicit capture inside the source attack sweep at
  the bite frame, then exactly one `InteractKill` at the swallow frame.
- Catfish ships no `waitact1`; the `Turn` state reuses `wait1`. Attack/receiver
  host params are zeroed so all damage is FSM-driven.

## Files

- `native/pc_port/pc_p2_catfish.cpp`, `pc_p2_catfish.h` (new).
- Additive hooks: `include/teki.h`, `tekibteki.cpp`, `tekimgr.cpp`,
  `pc_p2_batch3.cpp` (clip override + bind log), `pc_p2_preview.cpp`,
  `CMakeLists.txt`.
- `experimental/pikmin2_catfish_behavior.py`, `tests/test_pikmin2_catfish_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | combined `A04CBCBE400FD20A848C0930EF2697E4E29AFC833FFE600BCF0DE339DF5C33C2` |
| Run directory | `output/p2-species-catfish-final/8b8ff1936c864825bd89ca489032e4e4` |
| Hash | `native.log` `B10FD77F…F42ACA50` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_CATFISH_BIND generator=374001 source_id=26`; `P2_BATCH3_BIND …key=aquatic|Catfish visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | states `turn/walk/attack/flick`; 155.5 XZ spread |
| 3. Attacks / receivers | PASS | bites at frame 17.0 inside the source window; `bite_eat_accounting` exactly once per bite; flick receiver observed |
| 4. Death + corpse | UNTESTED | `Dead` coded; no damage source in the run |
| 5. Transport + reward | source-backed generic | host corpse/carry retained |
| 6. Cleanup + re-entry | UNTESTED | reset/forget wired |

## Remaining work

- Two-slot mouth attachment visual; `attackNavi`/poison swallow.
- Death/corpse/cleanup (#397).
