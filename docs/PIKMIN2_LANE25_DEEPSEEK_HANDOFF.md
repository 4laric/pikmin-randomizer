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
3. `841f40e` lane25: record DangoMushi vulnerability + Rock/Egg births handoff (#174)
4. `eab90c6` lane25: review fixes for Crawbster hazard host (#174)
5. `0074d3d` lane25: note fixture timer-termination quirk in handoff (#174)
   (root head `0074d3dd8ce1df96034295ffef7f4f2734c1e1c8`)

Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (fix1, rewritten unpushed series):

1. `7bbf5c8c` lane25: expose rock host binding for consumers (lane 20 primitive) (#174)
2. `ff6f50ec` lane25: apply Crawbster Turn vulnerability window as a damage gate (#174, #376)
3. `a0b38135` lane25: hook InteractAttack/InteractBomb to pc_p2_dangomushi_invulnerable (#174, #376)
4. `f11cec6c` lane25: host lane-20 Rock/Egg policies as real Crawbster hazard births (#174, #376)
   (native head `f11cec6c6b832403bfdddac5e06fcb56f23edb7e`)

The two original native commits were rewritten on request to split the shared
`tekiinteraction.cpp` hook into its own commit (commit 3) and to expose the
lane-20 rock host binding as its own commit (commit 1) before the births commit
consumes it. Commits are authored by the repository user (Alaric McKenzie-Boone); implementation owner is recorded per AGENTS.md as the shared account.

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
- `pc_port/pc_p2_rock_host.{h,cpp}` (new, shared; fix1): the lane-20 static-map
  trace proxy + `RockMapBinding` + `ScriptRng` + `detectRock`, extracted from
  `pc_p2_projectiles.cpp`'s anonymous namespace and consumed by both lane 20 and
  lane 25. `pc_p2_projectiles.cpp` was refactored to use it (no behaviour change).
- `pc_port/pc_p2_rock_hazard.{h,cpp}` (lane-20 primitive, additive; fix1):
  `P2RockHazard::forceDeath()` so the DangoMushi host can cull a rain rock after
  its 30 s lifetime (source `birthArg.mExistenceLength`).

No other shared module is modified. SnakeCrow/SnakeWhole are untouched. The only
lane-20 edits are the extracted host (its own `lane25:` commit) and the additive
`forceDeath()` primitive extension; `P2RockHazard`/`P2Egg` policies themselves are
consumed, not copied.

## Build evidence (output/dsw/l25-build-evidence.txt)

- `lane=l25 target=pikmin_pc native=f11cec6c6b832403bfdddac5e06fcb56f23edb7e
  dirty=no build_dir=...\native-l25-build exe=...\native-l25-build\bin\nectar.exe
  sha256=7bf0c81260fa501f93f37e55af0c7e7f22eaf7bfe7bfc518bba9f0c852b77691
  ninja_n="ninja: no work to do."`
- `lane=l25 target=p2_dangomushi_hazard_test ...` -> `PASS DANGOMUSHI_HAZARD`;
  stdout saved to `output/dsw/l25-out/p2_dangomushi_hazard_test.stdout.txt`.
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
  `7bf0c81260fa501f93f37e55af0c7e7f22eaf7bfe7bfc518bba9f0c852b77691`.
- `PIKMIN_P2_ROOM_WINDOW=960x540`; log line
  `Experimental preview window set to 960x540 windowed and centered`.
- Run directory `output/dsw/l25-out/runs/9093da5e6b7d45b6b86857f2ca2d4152`;
  `capture/native.log` SHA-256
  `6df20f075dca6f7fbd5d0d0273a6bde52db6a3a9888b6e9e5939c5ff52e9ecc9`
  (see also `dangomushi-validation.json`).
- Natural-chain markers (run 9093da5e): `DAMAGE_REJECTED` (state=appear/recover),
  `TURN_WINDOW stickable=1..0`, `DAMAGE_ACCEPTED ×6`, `ROCK_BIRTH requested=10
  real=10`, `ROCK_STRIKE kind=Press damage=10.0`, `ROCK_DESTROY reason=floor`,
  `HAZARD egg=1`, `EGG_BIRTH real=1`, `EGG_CONTACT health=0`,
  `EGG_ITEM kind=2 real=1 item=nectar`.
- `dangomushi-validation.json` reports `exit_code=1 timed_out=true`: the fixture
  is timer-terminated at the requested observation window (pre-existing validator
  counter), not an engine failure.

## Six-gate table (natural vs injected; DangoMushi 94)

| Gate | Result | Evidence / label |
|---|---|---|
| 1 Exact identity + spawn | PASS (natural) | `P2_DANGOMUSHI_BIND generator=376003 source_id=94 visual_only=0`, `P2_ENEMY_READY ... source_FSM=implemented` |
| 2 Autonomous movement + animation | PASS (natural) | states stay/appear/wait/move/attack/turn/flick; XZ spread 227.14 |
| 3 Attacks + receivers | PASS (natural) | `DAMAGE_REJECTED` outside the window + `DAMAGE_ACCEPTED` inside (natural Pikmin attacks rejected while rolling, admitted during the flip). Roll HIT / InteractFlick as before (documented P1 proxy). |
| Hazard births | PASS (natural) | 10/10 real falling Rocks born per Turn, real `InteractPress` strike on a grounded Pikmin, floor destroy; a real Egg born and broken into real nectar this run. Egg decision is probabilistic (`formationPikis/allPikis`), so a given run may roll `egg=0`; run 9093da5e rolled `egg=1`. |
| 4 Death + corpse | UNTESTED | lifecycle host (#397); no damage source reaches 3000 HP in one fixture window |
| 5 Transport + reward | source-backed generic | host corpse/carry retained; no Pop/Poko assertion |
| 6 Cleanup + re-entry | UNTESTED | reset/forget wired; not exercised to death |

Injected state is limited to the deterministic fixture arena (engineered
placement + 20-red overlay squad + zeroed birth circle), all of which is labelled
in `arena.json` / `dangomushi-override.json`. The damage gate and births are
natural, driven by the live squad attacking during normal playback.

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_dangomushi_behavior.py -q` -> 14 passed.
- `py -3.12 -m pytest tests/test_pikmin2_dangomushi_behavior.py
  tests/test_pikmin2_snagret_assets.py tests/test_pikmin2_snagret_install.py -q`
  -> 46 passed, 11 subtests.
- `p2_dangomushi_hazard_test` (engine-free) -> `PASS DANGOMUSHI_HAZARD`
  (stdout saved to `output/dsw/l25-out/p2_dangomushi_hazard_test.stdout.txt`).

## Subagent usage

Three subagents were run in parallel at the start of this fix1 slice, per the
brief:

1. **`explore` — source audit** (DangoMushi receiver/vulnerability/window frames,
   Rock/Egg spawner rule, lane-20 `P2RockHazard`/`P2Egg` API surface and the exact
   anonymous-namespace line ranges of the forked helpers). Used as-is: its
   `P2RockHazard` "no public force-death method" finding drove the additive
   `forceDeath()` primitive extension, and its `P2Egg::reset()` finding confirmed
   item 4 (skip egg spawn while active). Also confirmed the fork locations for the
   host extraction.
2. **`explore` — candidate inventory** (every module/hook/test touching the
   family; the full `P2_DANGOMUSHI_*` marker set; exact fix line numbers; CMake
   source-list lines). Used as-is for pinpointing edits and placing the
   `pc_p2_rock_host.cpp` CMake entry.
3. **`general` — validator/pytest** (added an egg-gate limitations note and a
   focused test, ran `pytest`). Result corrected rather than taken as-is: its
   note labelled the Egg path "structurally unreachable", but the fix1 fresh run
   actually observed a real Egg birth (real nectar), so I rewrote the note to
   "probabilistic (formationPikis/allPikis), observed on run 9093da5e".

Net: the two `explore` agents saved substantial file-navigation/citation time; the
`general` agent's test scaffolding was kept with a corrected note. No subagent
built, ran a fixture, committed, or touched native sources.

## Assumptions made

- The four native commits were re-authored (not cherry-picked verbatim) to meet
  items 1 and 7: the shared `tekiinteraction.cpp` hook is its own commit, and the
  lane-20 rock host exposure precedes the births commit that consumes it.
- DangoMushi is invulnerable to attack/bomb/press everywhere except the Turn
  `LOOP_START..key-3` window; a rejected attack/bomb is *consumed* (`return
  true`, the Hana/Kogane idiom) rather than bounced.
- Rock fall/scale values are documented fixture host parms (not source
  constants); Egg drop chances are the disc proper parms; Mitites fall back to
  nectar (P1 has no Mitite manager). Rock pool is 16 slots with reuse (source
  reserves 30/10 per Crawbster).
- JAudio ON required for the Release link (as documented); configured through the
  slot wrapper because `build_lane.py` does not pass `-DPIKMIN_NATIVE_JAUDIO`.
- `P2RockHazard::forceDeath()` is accepted as a small additive lane-20 primitive
  extension (labelled `lane25:`); lane 20 otherwise owns the Rock/Egg policies.

## Remaining blockers (provider lane)

- True source `InteractPress` roll crush, `wallCallback` crash trigger, and the
  `dangomushi.brk` material loop remain lane-25-local approximations.
- Death/corpse/cleanup/re-entry requires the lifecycle host **#397** (lane 07).
- Natural terrain/placement acceptance belongs to **lane 04**; rewarded
  transport belongs to **lane 06**.

## One exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/dsw/l25-root && set PYTHONUTF8=1&& py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l25 -- py -3.12 -m experimental.pikmin2_dangomushi_behavior run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/snagret-import" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/runs" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/native-l25-build/bin/nectar.exe" --seconds 45
```

## Slice 2

SnakeCrow / SnakeWhole — the shared-base snagret pair (source IDs 34 / 70),
delivering the ledger's remaining snagret item: **source burrow/emerge/bite/jump
and the vulnerable/death lifecycle**, proven with **no injected health**.

Native commits (on `deepseek/p2-l25-native`, base `ff958c36`):

1. `87dff2e0` lane25: SnakeCrow/SnakeWhole vulnerable-while-emerged gate, joint fidelity + cleanup markers (#174)
2. `e488fa1f` lane25: hook InteractAttack/InteractBomb to pc_p2_snakejoint_invulnerable (#174)
   (native head `e488fa1ff037d36c54b391d676940de6550b6a00`)

Root commit `09feb4d1` on `deepseek/p2-l25` (base `2fbc0aae`).

### What changed

- `pc_port/pc_p2_snakejoint.h/.cpp`: add
  `bool pc_p2_snakejoint_invulnerable(const BTeki*)`. Source-faithful gate: the
  snagret sets `EB_Invulnerable` only in `StateStay::init`
  (`SnakeCrowState.cpp:110` / `SnakeWholeState.cpp:113`) and clears it only in
  `StateStay::cleanup` (`:213` / `:217`), so the head is damageable in every emerged
  state and invulnerable while buried (`Stay`). The receiver emits
  `P2_SNAKEJOINT_DAMAGE_REJECTED` (first attack per buried period) and
  `P2_SNAKEJOINT_DAMAGE_ACCEPTED` (per emerged period). Also emit
  `P2_SNAKEJOINT_JOINTS` at bind (joint-fidelity measurement) and a
  `P2_SNAKEJOINT_FORGET` marker from `pc_p2_snakejoint_forget` (cleanup seam).
- `src/plugPikiNakata/tekiinteraction.cpp`: `InteractAttack::actTeki` and
  `InteractBomb::actTeki` consult the gate (own labelled commit).
- Root: `experimental/pikmin2_snakejoint_behavior.py` now also parses the
  DAMAGE_REJECTED/DAMAGE_ACCEPTED/JOINTS/DEAD markers per species (both species);
  `experimental/pikmin2_snakejoint_slice2.py` is the isolated natural-kill harness
  (replacement-main fixture that assigns the real squad into `PikiMode::AttackMode`,
  the same assignment the production preview fixture uses at phase 3->4).

### Joint-fidelity gap (measured, not assumed)

The source rig drives six spinal joints `bodyjnt3..bodyjnt8` (SnakeJointMgr.cpp:47)
feeding the head (`bodyjnt8` -> `kamujnt1..3`); the P1 host drives a flat
translation-only Chappy body with zero driven spinal joints, so the drawn pose is
the per-species clip override. The bind marker encodes this explicitly:
`P2_SNAKEJOINT_JOINTS ... source_joints=6 host_joints=1 pose=clip_override`.

### Evidence (real GL, isolated SnakeCrow, natural kill, no injected health)

- Production build: `pikmin_pc` native `e488fa1f`, exe SHA-256
  `df6a6e8709acec760c361c60922f772119556c21ecc904e4543930253867eab6`, `ninja -n`
  no work.
- Replacement-main fixture exe SHA-256
  `4b8ef4c9d604f976b1dd476c1461d90ee5457e6de4d3bc126dcd66494316ffaa`.
- Run `output/dsw/l25-out/runs/fd20e74ffece4ee8879760f741211b6c`, `passed=true`
  (`snakejoint-slice2-validation.json`), window 960x540 centred, live 20-red squad.
- Marker timeline: `SLICE2_ATTACK_ASSIGNED count=20` ->
  `DAMAGE_REJECTED state=stay` (buried) -> `DAMAGE_ACCEPTED state=appear1`
  (emerged) -> `BITE frame=34` (directional bite) -> `SLICE2_PROGRESS health=270`
  -> `DAMAGE_REJECTED state=stay` -> `DAMAGE_ACCEPTED state=appear1` ->
  `DEAD source_id=34 health=0` (natural kill) -> `BATCH3_DRAW corpse=1 clip=dead`.

### Six-field status

| Field | Result | Evidence |
|---|---|---|
| Vulnerable only while emerged | PASS (natural) | `DAMAGE_REJECTED state=stay` + `DAMAGE_ACCEPTED state=appear1` |
| Natural squad kill (real receiver, no injected health) | PASS (natural) | health 1500 -> 270 -> 0 via real 20-red Pikmin AttackMode; no mHealth write |
| Directional bite | PASS (documented approximation) | `BITE frame=34` (banked `hit` KEYEVENT_3); nearest target, normal `hit` stem |
| Death animation + corpse | PASS (natural) | `DEAD ... health=0` + `BATCH3_DRAW corpse=1 clip=dead` |
| Cleanup / forget | wired, not observed here | `pc_p2_snakejoint_forget` hooked to `BTeki::doKill` + `TekiMgr::newTeki`; free-mode corpse is drawn not consumed, so the death funnel is deferred |
| Joint fidelity | measured | `source_joints=6 host_joints=1 pose=clip_override` |

### Tests

- `py -3.12 -m pytest tests/test_pikmin2_snakejoint_behavior.py tests/test_pikmin2_snakejoint_slice2.py -q`
  -> 17 passed.

### Subagent usage (slice 2)

Three subagents were run in parallel at the start:

1. **`explore` — source audit** (snagret state enums, the exact
   `EB_Invulnerable` set/clear lines, 5-way directional bite, death/corpse, and the
   6-joint `SnakeJointMgr` rig). Used as-is; its finding that `EB_Invulnerable` is
   set/cleared *only* in `Stay` turned the gate from a hand-waved "buried vs
   emerged" into the exact single-state predicate, and its 6-joint/`kamujnt1..3`
   citations became the joint-fidelity marker's numbers.
2. **`explore` — candidate inventory** (every snakejoint hook/setup/marker, the
   DangoMushi receiver pattern to mirror, and confirmation the forget/reset/update
   lifecycle seam is already wired). Used as-is for exact line navigation and to
   place the new `tekiinteraction` hook.
3. **`general` — validator/pytest** (added DAMAGE_REJECTED/ACCEPTED/JOINTS/DEAD
   parsing to the both-species validator + tests). Used as-is (its 10 tests still
   pass); I added a separate isolated slice-2 harness on top.

Net: the two `explore` agents saved substantial source-navigation/citation time;
the `general` agent's validator extension was kept unchanged. This slice spent the
bulk of its wall-clock on understanding the preview room's Pikmin AI — idle
free-mode Pikmin never auto-attack, so "natural squad kill" required the
replacement-main fixture that assigns real `PikiMode::AttackMode` (the same
mechanism the production preview fixture uses for its combat pass). No subagent
built, ran a fixture, committed, or edited native sources.

### Slice-2 reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/dsw/l25-root && set PYTHONUTF8=1&& py -3.12 -m experimental.pikmin2_snakejoint_slice2 build --native "C:/Users/alari/pikmin-randomizer/output/dsw/native-l25" --build-dir "C:/Users/alari/pikmin-randomizer/output/dsw/native-l25-build" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/slice2-fixture" --head e488fa1ff037d36c54b391d676940de6550b6a00
cd C:/Users/alari/pikmin-randomizer/output/dsw/l25-root && set PYTHONUTF8=1&& py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l25 -- py -3.12 -m experimental.pikmin2_snakejoint_slice2 run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --imported "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/snagret-import" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/runs" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l25-out/slice2-fixture/fixture.exe" --seconds 120
```
