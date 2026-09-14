# Lane 25 handoff — DangoMushi Turn vulnerability application + Rock/Egg births (#174)

Worker: opencode (deepseek). Implementation owner: Codex via shared account `4laric`.
Lane 25 (Snagrets/Crawbster), tracking issue #174. This handoff delivers the
ledger's remaining-work item from `docs/PIKMIN2_LANE_COMPLETION.md`:
**"Crawbster Turn vulnerability application and actual Rock/Egg births; source
hazard decisions are integrated."** One concrete source ID (DangoMushi 94,
Segmented Crawbster) and the smallest end-to-end slice that advances the natural
combat / real damage-receiver gate: the previously *observed-only* Turn stickable
window is now a real damage-admission gate, and the Rock/Egg hazard decisions are
realized as real children (reusing the lane-20 `P2RockHazard`/`P2Egg` policies,
not forked).

## Source IDs and files owned

Family IDs: SnakeCrow 34, SnakeWhole 70 (shared `SnakeJointMgr` pair),
DangoMushi 94 (standalone `EnemyBase`/`EnemyBlendAnimatorBase`). This slice owns
DangoMushi 94.

Native files (owned): `pc_port/pc_p2_dangomushi.{h,cpp}`,
`pc_port/pc_p2_dangomushi_hazard.h`, `tools/p2_dangomushi_hazard_test.cpp`.
Root files (owned): `experimental/pikmin2_dangomushi_behavior.py`,
`tests/test_pikmin2_dangomushi_behavior.py`,
`docs/PIKMIN2_DANGOMUSHI_VULN_APPLY.md`,
`docs/PIKMIN2_DANGOMUSHI_HAZARD_RUNTIME.md`, `docs/PIKMIN2_DANGOMUSHI_NATIVE.md`.

## Ordered commits (both branches, clean)

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

1. `26fc84e` lane25: validator + docs for applied Crawbster vulnerability window (#174, #376)
2. `a87706f` lane25: validator + docs for real Crawbster Rock/Egg hazard births (#174, #376)
   (head `a87706f04e0e78576fd065f44db120f1fbf477e8`)

Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`:

1. `8a1dc217` lane25: apply Crawbster Turn vulnerability window as a damage gate (#174, #376)
2. `fdd38885` lane25: host lane-20 Rock/Egg policies as real Crawbster hazard births (#174, #376)
   (head `fdd388856ff35ec687925c343dbe9d780c93927d`)

Both worktrees clean. These are the reviewed lane-25 candidates pulled onto the
fresh `deepseek/p2-l25` / `deepseek/p2-l25-native` branches (same base as the
authoring `opencode/p2-crawbster-vuln-*` branches, so cherry-picks applied
cleanly). Author is Codex `<4laric@users.noreply.github.com>`.

## Interfaces / hooks touched and why

- `pc_port/pc_p2_dangomushi_hazard.h`: add pure predicate
  `P2DangoMushiHazardPolicy::attackRejected(bool stickable)` so the host damage
  gate and the engine-free fixture share one definition of the source
  `DangoMushiState.cpp:530` `EB_Invulnerable` rule.
- `pc_port/pc_p2_dangomushi.h/.cpp`: track `Dango::stickable` (set from the
  policy each Turn tick, cleared on every transition); add
  `bool pc_p2_dangomushi_invulnerable(const BTeki*)` (false for unregistered
  actors). Emits `P2_DANGOMUSHI_DAMAGE_REJECTED` on the first rejected
  attack/bomb per window and `P2_DANGOMUSHI_DAMAGE_ACCEPTED` while in-window
  damage is admitted. The Turn hazard tick now births the Rock rain and Egg via
  the lane-20 `P2RockHazard`/`P2Egg` policies (markers
  `P2_DANGOMUSHI_ROCK_BIRTH/_PHASE/_STRIKE/_DESTROY`,
  `P2_DANGOMUSHI_EGG_BIRTH/_CONTACT/_ITEM`).
- `src/plugPikiNakata/tekiinteraction.cpp` (shared, additive hook):
  `InteractAttack::actTeki` and `InteractBomb::actTeki` consult the gate and
  consume the interaction, mirroring the existing `pc_p2_hana_rejects_attack` /
  `pc_p2_kogane_attacked` idiom; both remain no-ops for unregistered P1 actors.
- `tools/p2_dangomushi_hazard_test.cpp`: assert the shared predicate in the
  existing window fixture.

No other shared module is modified. SnakeCrow/SnakeWhole and lane 20 modules are
untouched; `P2RockHazard`/`P2Egg` are used, not copied.

## Build evidence (output/dsw/l25-build-evidence.txt)

- `lane=l25 target=pikmin_pc native=fdd388856ff35ec687925c343dbe9d780c93927d
  dirty=no build_dir=...\native-l25-build exe=...\native-l25-build\bin\nectar.exe
  sha256=3fdf265de5a8865b08c4484230fc3ff224640fc935c987d67f445577a6e8700d
  ninja_n="ninja: no work to do."`
- `lane=l25 target=p2_dangomushi_hazard_test ...` -> `PASS DANGOMUSHI_HAZARD`.
- Config: Ninja + MinGW g++ (GCC 16.2.0), `-DCMAKE_BUILD_TYPE=Release
  -DPIKMIN_NATIVE_JAUDIO=ON`. (The default wrapper configure omitted JAudio; I
  reconfigured with `-DPIKMIN_NATIVE_JAUDIO=ON` via the slot wrapper, matching
  the maintained build.)

## Fixture adoption evidence

- Fresh arena regenerated into `output/dsw/l25-out/runs/` using the current
  `preview_pikmin2_room.overlay()` (live 20-red starting squad) and a freshly
  re-extracted snagret import (`output/dsw/l25-out/snagret-import`, source
  `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso`, GPVE01 rev 0, pose-limit 2).
- Private executable SHA-256
  `3fdf265de5a8865b08c4484230fc3ff224640fc935c987d67f445577a6e8700d`.
- `PIKMIN_P2_ROOM_WINDOW=960x540`; log line
  `Experimental preview window set to 960x540 windowed and centered`.
- Run directory `output/dsw/l25-out/runs/de5e903d01394561a7b5fd8e0b61dd23`;
  `capture/native.log` SHA-256
  `da053c2ddea07a91f7ee3829e11c18fd8c4268dae25d0a2a698deb16dbb3f536`.
- `dangomushi-validation.json` `passed=true`; marker counts: DAMAGE_REJECTED 3,
  DAMAGE_ACCEPTED 12, ROCK_BIRTH 2 (10/10 real each), ROCK_STRIKE 1
  (`kind=Press damage=10.0`), TURN_WINDOW 4, HAZARD 2.

## Six-gate table (natural vs injected; DangoMushi 94)

| Gate | Result | Evidence / label |
|---|---|---|
| 1 Exact identity + spawn | PASS (natural) | `P2_DANGOMUSHI_BIND generator=376003 source_id=94 visual_only=0`, `P2_ENEMY_READY ... source_FSM=implemented` |
| 2 Autonomous movement + animation | PASS (natural) | states stay/appear/wait/move/attack/turn/flick; XZ spread 229.56 |
| 3 Attacks + receivers | PASS (natural) | `DAMAGE_REJECTED` outside the window + `DAMAGE_ACCEPTED` inside (natural Pikmin attacks rejected while rolling, admitted during the flip). Roll HIT / InteractFlick as before (documented P1 proxy). |
| Hazard births | PASS (natural) | 10/10 real falling Rocks born per Turn, real `InteractPress` strike on a grounded Pikmin, floor destroy. Egg decision probability was 0 this run (probability = captain's Pikmin share), so real Egg birth is **UNTESTED-pending-roll** on this fresh run (the same code path passed on the authoring run, `egg_birth=true`). |
| 4 Death + corpse | UNTESTED | lifecycle host (#397); no damage source reaches 3000 HP in one fixture window |
| 5 Transport + reward | source-backed generic | host corpse/carry retained; no Pop/Poko assertion |
| 6 Cleanup + re-entry | UNTESTED | reset/forget wired; not exercised to death |

Injected state is limited to the deterministic fixture arena (engineered
placement + 20-red overlay squad + zeroed birth circle), all of which is labelled
in `arena.json` / `dangomushi-override.json`. The damage gate and births are
natural, driven by the live squad attacking during normal playback.

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_dangomushi_behavior.py -q` -> 13 passed.
- `py -3.12 -m pytest tests/test_pikmin2_dangomushi_behavior.py
  tests/test_pikmin2_snagret_assets.py tests/test_pikmin2_snagret_install.py -q`
  -> 45 passed, 11 subtests.
- `p2_dangomushi_hazard_test` (engine-free) -> `PASS DANGOMUSHI_HAZARD`.

## Assumptions made

- Adopted the reviewed lane-25 candidate commits (`opencode/p2-crawbster-vuln-*`)
  by cherry-pick onto the fresh lane branches rather than re-deriving a divergent
  receiver; the two commits already cover both ledger items together, so both are
  delivered in one handoff (vulnerability is the primary slice; births are the
  coupled follow-on).
- DangoMushi is invulnerable to attack/bomb/press everywhere except the Turn
  `LOOP_START..key-3` window; a rejected attack/bomb is *consumed* (`return
  true`, the Hana/Kogane idiom) rather than bounced.
- Rock fall/scale values are documented fixture host parms (not source
  constants); Egg drop chances are the disc proper parms; Mitites fall back to
  nectar (P1 has no Mitite manager). Rock pool is 16 slots with reuse (source
  reserves 30/10 per Crawbster).
- JAudio ON required for the Release link (as documented); configured through the
  slot wrapper because `build_lane.py` does not pass `-DPIKMIN_NATIVE_JAUDIO`.

## Remaining blockers (provider lane)

- Real Egg birth sighting on this fresh pair is probability-gated; a longer or
  repeated run (or a fixed `eggRoll` fixture) will show it. No lane dependency.
- True source `InteractPress` roll crush, `wallCallback` crash trigger, and the
  `dangomushi.brk` material loop remain lane-25-local approximations.
- Death/corpse/cleanup/re-entry requires the lifecycle host **#397** (lane 07).
- Natural terrain/placement acceptance belongs to **lane 04**; rewarded
  transport belongs to **lane 06**.

## One exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/dsw/l25-root && set PYTHONUTF8=1&& py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l25 -- py -3.12 -m experimental.pikmin2_dangomushi_behavior run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/snagret-import" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/runs" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l25-build/bin/nectar.exe" --seconds 45
```
