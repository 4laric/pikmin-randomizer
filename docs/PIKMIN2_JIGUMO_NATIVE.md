# Jigumo (Crawmad, EnemyID 63) native source behavior

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407), parent
[#167](https://github.com/4laric/pikmin-randomizer/issues/167). Third aquatic
species of the Species behavior lane. Owner: Codex via shared `4laric`.

## Source contract implemented

`native/pikmin2-research/src/plugProjectNishimuraU/Jigumo.cpp` /
`JigumoState.cpp`; retail parameters, state IDs and clip events in
`experimental/pikmin2_aquatic_assets.py`. Host is the P1 Chappy placement vehicle
(`TEKI_Chappy`), generator `374003`.

| Source behavior | Implementation |
|---|---|
| Nest `Wait` / `Search` / `Appear` | `fsearch1`/`search1`-style nest cycle |
| Short attack | `sattack1`; capture at the banked bite frame 13, one kill at the banked swallow frame 115 |
| Carry → Eat | internal carry path (carry speed 75) |
| `Dead` | `dead1`; `die()` at clip end |

### Port adaptations

- No `PanHouse`/nest actor on the P1 host; the nest is the home point and
  Appear/Hide are animation-only (source nest-follow root motion not
  representable).
- The source mouth joint is not representable; the bite is an explicit capture at
  the source frame plus one `InteractKill` at the swallow frame.
- Full-hemisphere view/search angle; turn rate/flick radius/shake are P1-host
  values; source `damageCallBack` part rule and water-box effects omitted.

## Files

- `native/pc_port/pc_p2_jigumo.cpp`, `pc_p2_jigumo.h` (new).
- Additive hooks: `include/teki.h`, `tekibteki.cpp`, `tekimgr.cpp`,
  `pc_p2_batch3.cpp` (clip override + bind log), `pc_p2_preview.cpp`,
  `CMakeLists.txt`.
- `experimental/pikmin2_jigumo_behavior.py`, `tests/test_pikmin2_jigumo_behavior.py`.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root / overlay source | `kimi/p2-bulblax-import`; `ensure_pikmin_squad` root `a51b301` in ancestry |
| Native / worktree / build | lane branch `opencode/p2-species-native`; `output/native-species`; `output/native-species-build` |
| Window | `PIKMIN_P2_ROOM_WINDOW=960x540`; log line present |
| Executable SHA-256 | isolated `E3CB37E7A8EF45C1B049090FF29E48D6D8642C3E94CAB0A625C48C57592AD0D0` |
| Run directory | `output/p2-species-jigumo/6f509fd099a84992a95ec6c11e48f1c5` |
| Hash | `native.log` `A2E78708…9B841966` |

## Six arena gates

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | `P2_JIGUMO_BIND generator=374003 source_id=63`; `P2_BATCH3_BIND …key=aquatic|Jigumo visual_only=0 native_fsm=implemented` |
| 2. Autonomous movement + animation | PASS | states `appear/wait/search/attack`; 95.5 XZ spread (host AI drift noted) |
| 3. Attacks / receivers | PASS (attack) | three bites at frame 13 with exactly one `P2_JIGUMO_EAT` each |
| 4. Death + corpse | UNTESTED | `Dead` coded; no damage source in the run |
| 5. Transport + reward | UNTESTED | internal Carry→Eat implemented; short-attack path selected |
| 6. Cleanup + re-entry | PASS (wiring) | reset/forget wired into `tekimgr` |

## Remaining work

- Nest (`PanHouse`) actor, water-box effects, `damageCallBack` part rule.
- Death/corpse/cleanup (#397).
