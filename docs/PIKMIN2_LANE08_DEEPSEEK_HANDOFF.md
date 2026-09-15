# Lane 08 (Events) — DeepSeek worker handoff

Implementation owner: Codex through shared GitHub account `4laric`; executing agent
(session): DeepSeek. Parent issue #431 (events), tracking the #186 fan-out lane 08.

Concrete deliverable: migrate the **Creeping Chrysanthemum (Hana, EnemyID 84)**
gameplay effects — attack1 bite (`18:2` → attackNavi + Pikmin capture), attack1
swallow (`71:3` → InteractKill + White-Pikmin fp02 poison) and flick (`50:2` →
knockback) — off the per-state wall-time counter (`stateTime * 30` + a `firedEvents`
set) and onto the authoritative #431 sampled-animation clock. Missing ledger slice
addressed: *"Move one family gameplay effect onto authoritative simulation events"*
(exactly-once across frame skips, loops, pause, interruption and generation change).

## Source IDs and files owned

- Source identity: Hana / Creeping Chrysanthemum, EnemyID 84
  (`enemyInfo.h:143`, `Game::Hana::Obj` inheriting `ChappyBase::Obj`).
  Authored events (disc `enemyanimmgr.txt`, cross-checked
  `docs/PIKMIN2_GROUND_INVERTEBRATE_ASSETS.md:83`): `attack1 [[18,2],[71,3]]`,
  `flick [[50,2]]`, `type1 [[27,2],[30,0],[100,1],[103,3],[120,4]]`, `attack2 [[24,2],[62,3]]`.
- Native files: `pc_port/pc_p2_hana_events.h` (new), `pc_port/pc_p2_hana.cpp`
  (modified), `tools/test_p2_hana_events.cpp` (new), `CMakeLists.txt` (hook).
- Root files: `experimental/pikmin2_hana_events.py` (new),
  `tests/test_pikmin2_hana_events.py` (new).

## Ordered commits (both clean, nothing pushed)

Root branch `deepseek/p2-l08`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

1. `c840fda (+ ad109d3 handoff doc; integrator review-fix commit follows)` — `lane08: Hana event-mapping contract tests and harness (#431)`

Native branch `deepseek/p2-l08-native`, base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`:

1. `21d8939c` — `lane08: drive Hana bite/swallow/flick from the sampled event clock (#431)`
   (new `pc_p2_hana_events.h`, migrated `pc_p2_hana.cpp`, new probe `tools/test_p2_hana_events.cpp`)
2. `88c08fa4` — `lane08: register p2_hana_events_test CTest gate (hook) (#431)`
   (`CMakeLists.txt` only — the single shared-file hook, separately committed and labelled)

## Interfaces / hooks touched and why

- Reused the existing shared clock `p2sampled::Clock` (`pc_port/pc_p2_sampled_clock.h`);
  no new clock, no generic subsystem. The new `p2hanaevents::Receiver` (copy of the
  already-integrated `p2armorevents::Receiver`) owns one actor clock and maps crossed
  source events to `Action{Bite,Swallow,Flick}`. Hana's swallow rides event **type 3**
  (`KEYEVENT_3`), so `actionFor` adds a `Swallow` case the Armor reference did not need.
- `pc_port/pc_p2_hana.cpp` internal only: `Hana` state lost `biteFrame`/`swallowFrame`/
  `flickFrame`/`firedEvents` and gained one `p2hanaevents::Receiver`; `enter()` now starts
  the entered clip's clock (bumping generation and cancelling the previous clip's pending
  events); the `HANA_ATTACK`/`HANA_FLICK` states dispatch from `s.events.advance(dt)`.
  `stateTime`/`setPhase` remain the independent pose/completion projection, so displayed
  pose never substitutes for event execution. `setup()` now builds a `p2sampled::Clip`
  per bank row and does `s = Hana()` on bind to reject recycled-address stale state.
- No shared engine file was edited. `pc_p2_hana_setup/update/forget/clip/param_f/
  rejects_attack` keep their existing call sites (verified via source audit) unchanged.

## Build evidence (from `output/dsw/l08-build-evidence.txt`)

- `p2_hana_events_test`: built + run `PASS p2_hana_events`; exe SHA-256
  `3d82af7e255b64599194672f0057b84ddf15b927e35ebdc29e4abc21ced8f4a4`.
- `pikmin_pc`: `[603/603] Linking CXX executable bin\nectar.exe`; `ninja -n` →
  `ninja: no work to do.`; native `88c08fa4`; exe (nectar.exe) SHA-256
  `6671ddff77acbd1103ec0f00abd3f04c15a4918a8baef7804d2c5fc44937b809`.

## Fixture adoption + runtime evidence (real-GL, slot `gl` wrapped)

- Run dir: `output/dsw/l08-out/d47cb7d92f5b4f4fbff7e7cfc107d847`;
  `capture/native.log` SHA-256 `e51dfbb05094bce75e87fd40a5c936d25a681da5701afc544f560d85325aa683`.
- Startup log: `Experimental preview window set to 960x540 windowed and centered`;
  `PIKMIN_P2_ROOM_WINDOW=960x540`; live starting squad (current starting-Pikmin overlay),
  `no_extinction` true.
- Observed (natural, timer-terminated at 40 s): state loop
  `sleep→emerge→walk→attack→eat→walk` ×4, and for each cycle
  `P2_HANA_ATTACK_NAVI frame=18`, `P2_HANA_BITE frame=18 pikmin=1`,
  `P2_HANA_EAT pikmin=1`. Bite frames are **exactly [18, 18, 18, 18]** (the source event
  frame), and eats are exactly one per bite — exactly-once across four natural attack
  state re-entries, no duplicate or dropped event. `motion_spread` 107.39.

## Six arena gates (natural vs injected)

| Gate | Result | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | **PASS** | `P2_HANA_BIND source_id=84`, `P2_ENEMY_READY species=Hana … attack=animation_event`, health 2500. Natural; position is an engineered behavior-fixture override (not production placement). |
| 2 Autonomous movement and animation | **PASS** | Natural FSM cycle + pose projection (`sleep/emerge/walk/attack/eat`), motion spread 107.4. |
| 3 Attacks and receivers | **PASS** | Bite captures a real Pikmin, `attackNavi`, exactly-once swallow kill at source frames 18/71 — clock-driven. Natural dispatch; starting squad is the injected overlay. |
| 4 Death and corpse | **UNTESTED** | Hana never died within 40 s (health 2500); corpse/carry not exercised. |
| 5 Actual transport and reward | **source-backed N/A** | No reward endpoint wired for ground inverts in this lane; not lane-08 scope. |
| 6 Cleanup and re-entry | **UNTESTED (runtime)** | Natural state-loop re-entry shows exactly-once events; recycled-address protection proven in the engine-free probe, not in a scene reset. |

Injected: fixed engineered Hana coordinate (behavior fixture), 20-red starting squad
(overlay). Natural: the event timing/effects themselves.

## Tests run

- Native probe (part of CTest): `p2_hana_events_test` → `PASS p2_hana_events`
  (steady bite→swallow order, frame skip, one-shot non-refire, loop-per-cycle,
  pause, mid-clip interruption, address reuse, visual-event filtering).
- Python: `py -3.12 -m pytest tests/test_pikmin2_hana_events.py
  tests/test_pikmin2_hana_behavior.py tests/test_pikmin2_animation_clock.py
  tests/test_pikmin2_armor_behavior.py tests/test_pikmin2_ground_inverts_assets.py -q`
  → `52 passed`. (The broader repo suite keeps its documented native-checkout-dependent
  failures because this private root worktree has no `native/`; not re-run.)

## Assumptions

- Hana clip *durations* are not stored in-repo; they come from the generated
  `p2-ground-bank.txt` at `setup()` time. The engine-free probe's `hanaRows()` therefore
  uses valid representative durations (bounded by the authored event frames) and is
  labelled as such; the runtime table is authoritative.
- Reused lane 14's read-only, hash-bound ground-inverts import
  (`output/dsw/l14-out/ground`, re-validated by `prepare()`) in place of re-extracting
  the disc. It is a deterministic artifact, not a lane runtime result.
- The migration changes only *when* the effects fire, not the effects: bite capture,
  InteractKill swallow, White poison and flick knockback are byte-identical to before.

## Remaining blockers / next consumers

- This lane owns the clock/event contract + the migration pattern. Remaining family
  consumers still on `stateTime * 30` / a fired-frame set (migrate with their owners):
  `catfish`, `dangomushi`, `hanachirashi`, `jigumo`, `kochappy_fsm` (13), `mar`,
  `snakejoint` (25), `tadpole`, `umimushi`, plus optional `batch3`/`mamuta`/`breadbug`.
- Full Hana natural combat/death/corpse/reward/re-entry and generated-session admission
  remain with lane 14 (`#165`) consuming 06/07/08/10; not this slice.
- Ask of lane 01: export the native series (`21d8939c`+`88c08fa4`) with root `c840fda`.

## Subagent usage

- `explore` #1 (source audit): used as-is — confirmed Hana's event frames/type mapping,
  the exact legacy lines, the Armor reference mechanics, the CMake probe block, and that
  no shared-hook edit is needed. Saved significant re-reading time.
- `explore` #2 (candidate inventory): used as-is — gave the complete module/test/doc
  map, the `P2_HANA_*` marker list, and flagged the root `engine/` mirror (which I did
  not touch) and the Hanachirashi same-prefix trap. Prevented editing the wrong copy.
- `general` #3 (root tests/harness): used as-is — created `experimental/pikmin2_hana_events.py`
  + `tests/test_pikmin2_hana_events.py`, `6 passed`. I added nothing beyond committing them.
  Net: all three results were incorporated without correction; the parallel split kept
  the native implementation, build, GL run and handoff in the main context.

## Exact reproduction command

```
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l08
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l08 --target p2_hana_events_test
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l08 -- \
  py -3.12 -m experimental.pikmin2_hana_behavior run \
    --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets \
    --imported C:/Users/alari/pikmin-randomizer/output/dsw/l14-out/ground \
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l08-out \
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l08-build/bin/nectar.exe \
    --seconds 40
```

## Slice 2

Implementation owner: Codex through shared account `4laric`; executing agent (session): DeepSeek.

Two deliverables this slice: (a) fix the runtime-layer delta drop so a >0.5 s hitch no
longer discards a whole update before the sampled clock sees it; (b) migrate a second
family consumer — **Catfish (Water Dumple, EnemyID 26)** — onto the sampled clock.

### (a) Runtime delta-drop fix (Hana + Catfish)

`pc_p2_hana.cpp`/`pc_p2_catfish.cpp` used `if (dt <= 0.0f || dt > 0.5f) return;`, which
returned out of the entire update on a >0.5 s hitch, so the crossed animation events
never reached the clock (undercutting exactly-once-across-frame-skips). Both now reject
only non-positive `dt` and clamp a larger `dt` to `0.5f`, keeping `stateTime` and the
sampled clock in lockstep while no longer dropping the update. Probe case added:
`testTwoSecondHitch` (advance 2.0 s in one call → bite once, no swallow; resume → swallow
once) in both `tools/test_p2_hana_events.cpp` and `tools/test_p2_catfish_events.cpp`.

### (b) Catfish event-clock migration

Catfish previously fired `attack` (bite 17:2 / swallow 75:3) and `flick` (knockback 25:2 /
restore 47:3) through `fireAttackEvents`/`fireFlickEvents` with a `firedEvents` set plus
`stateTime < frame/30` dedupe. New `pc_port/pc_p2_catfish_events.h`
(`p2catfishevents::{Row,makeClip,Action{None,Bite,Swallow,Flick,FlickRestore},actionFor,
Receiver,catfishRows}`) mirrors the Hana header; `pc_p2_catfish.cpp` now owns one
`Receiver` per actor, starts it in `transition()`/bind, and dispatches crossed events in
the ATTACK/FLICK states. The residual two-slot mouth (`slots[]`/`consumed`) and the
White-Pikmin fp02 poison are untouched; only *when* the events fire changed. actionFor
maps `attack:2→Bite, attack:3→Swallow, flick:2→Flick, flick:3→FlickRestore`; Python
mirror `ACTIONS={'attack':{'2':'bite','3':'swallow'},'flick':{'2':'flick','3':'restore'}}`
was diffed against it (agree).

### Commits (slice 2; both clean, nothing pushed)

Root branch `deepseek/p2-l08`, base `ef1cace…`:
- `902066af` `lane08: Catfish event-mapping contract tests and harness (#431)`

Native branch `deepseek/p2-l08-native`, base `b805d9c6…` (head was `e2411c43` after review):
- `52e7de6f` `lane08: drive Catfish bite/swallow/flick from the sampled event clock (#431, #167)`
- `de297cd7` `lane08: clamp dt instead of dropping the update (Hana + 2s-hitch probe) (#431)`
- `b555c5df` `lane08: register p2_catfish_events_test CTest gate (hook) (#431)` (CMake only)

### Build evidence (`output/dsw/l08-build-evidence.txt`)

- `p2_catfish_events_test`: built + run `PASS p2_catfish_events`; probe exe SHA-256
  `1d4c548d88aa67641a54b9e25fede53b1f546697f788f111da10103da456dfee`.
- `p2_hana_events_test` re-run `PASS p2_hana_events` (incl. the new 2s-hitch case).
- `pikmin_pc`: `[3/3] Linking CXX executable bin\nectar.exe`; `ninja -n` → no work; native
  `b555c5df`; nectar.exe SHA-256 `dbc18a0da9cc6c7444c92ffcc805b7a3feadeab0792a9d59c165980fdd2ed514`.

### Runtime evidence (Catfish, real-GL slot wrapped)

- Run dir `output/dsw/l08-out/7213745821654e14bdf8047b92d416cb`; `capture/native.log`
  SHA-256 `1ef4afcd2c76baf8efcb1bc27915d4c1448855a64bb0ed24f6f079264cb7124f`.
- 960×540 centred window, no extinction, `P2_CATFISH_BIND source_id=26`,
  `P2_ENEMY_READY species=Catfish … attack=animation_event`.
- Natural, timer-terminated at 40 s: three flick cycles
  `P2_CATFISH_FLICK frame=25 event=knockback hit=20/2/13` then `frame=47 event=restore`;
  attack cycles `P2_CATFISH_BITE frame=17 pikmin=1 slot=0/1` (both mouth slots) then
  `P2_CATFISH_EAT slot=0/1` — exactly-once per re-entry, bite at source frame 17, swallow
  kill exactly once per captured Pikmin. Validator `passed`, bite frames `[17.0, 17.0, 17.0]`.

### Six arena gates (slice-2 slice: Catfish event timing only)

| Gate | Result | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | **PASS** | `source_id=26`, `P2_ENEMY_READY species=Catfish`, health 200. Natural; position is the engineered behavior-fixture override. |
| 2 Autonomous movement and animation | **PASS** | wait/turn/walk/attack/flick loop, motion spread 149.8, 23 sampled positions. |
| 3 Attacks and receivers | **PASS** | banked bite (17) captures two Pikmin across both mouth slots, swallow kills each once; flick knockback hits at source frame 25, restore at 47. Natural dispatch; injected squad. |
| 4 Death and corpse | **UNTESTED** | Catfish never died within 40 s; corpse/carry not exercised. |
| 5 Actual transport and reward | **source-backed N/A** | No reward endpoint for Catfish in this lane; not lane-08 scope. |
| 6 Cleanup and re-entry | **UNTESTED (runtime)** | Natural attack/flick state re-entry shows exactly-once; recycled-address protection proven in the probe. |

### Tests run (slice 2)

- Native probes: `PASS p2_hana_events` (now with 2s-hitch), `PASS p2_catfish_events`.
- Python: `py -3.12 -m pytest tests/test_pikmin2_catfish_events.py
  tests/test_pikmin2_catfish_behavior.py tests/test_pikmin2_catfish_residual_behavior.py
  tests/test_pikmin2_hana_events.py tests/test_pikmin2_hana_behavior.py
  tests/test_pikmin2_animation_clock.py tests/test_pikmin2_armor_behavior.py -q` →
  `62 passed`.

### Assumptions / notes

- Catfish clip durations are not in-repo (disc-derived at `setup()`); the probe's
  `catfishRows()` uses representative valid durations (labelled), as Hana's does.
- Fresh aquatic import extracted by this lane into `output/dsw/l08-out/aquatic` from the
  pinned disc (`Downloads/PIKMIN2 for GAMECUBE.iso`, GPVE01 rev 0) and the read-only
  decomp checkout (`native/pikmin2-research` @ `632af937…`), which was not edited.
- The dt clamp caps a single simulation step at 0.5 s; brief ≤0.5 s frame skips are
  fully processed by the clock (exactly-once), and the pathological >0.5 s case is
  clamped rather than dropped. The probe's 2s-hitch test proves the clock itself is
  exactly-once for a 2 s delta.

### Remaining / next consumers

- Same-family siblings still on `stateTime*30`/fired-frame sets reported in slice 1
  (`dangomushi`, `hanachirashi`, `jigumo`, `kochappy_fsm`, `mar`, `snakejoint`, `tadpole`,
  `umimushi`, `sokkuri`, optional `batch3`/`mamuta`/`breadbug`) migrate with their family
  owners; lane 08 provided the pattern (three worked examples now: Armor, Hana, Catfish).
- Ask of lane 01: export native `52e7de6f`+`de297cd7`+`b555c5df` with root `902066af`.

### Subagent usage (slice 2)

- `explore` #1 (Catfish source audit): used as-is — event table (17/2, 75/3, 25/2, 47/3),
  exact `firedEvents`/`stateTime` lines, residual-policy reuse, and confirmation that no
  shared-hook edit is needed.
- `explore` #2 (candidate inventory): used as-is — full module/test/doc map, all
  `P2_CATFISH_*` markers, and the `engine/` mirror warning (not edited).
- `general` #3 (root mirror + tests): used as-is after I diffed `ACTIONS` against the
  native `actionFor` (agree). Created `experimental/pikmin2_catfish_events.py` +
  `tests/test_pikmin2_catfish_events.py`, `7 passed`.
  Net: all three incorporated without correction; the mapping-diff was done in the main
  context (the slice-1 lesson). The parallel split again kept the native implementation,
  build, GL run and handoff off the subagent path.

