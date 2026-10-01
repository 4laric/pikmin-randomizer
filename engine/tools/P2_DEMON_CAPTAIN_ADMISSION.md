# Demon captain admission: source-backed Walk+Idle capture (#242, #186)

Lane 30 (Snitchbugs / `Demon` ID 32, `Sarai` ID 23) workstream E. This slice
replaces the private P1 bridge's Walk-only captain capture gate with a
source-backed, deny-by-default captain admission set, so the natural Demon can
grab an **idling** captain and keep the mouth-stick relationship across the whole
carry/drop.

## Why this is a shared change

Retail P2 targets a captain independently of its neutral locomotion state: the
Swooping/Bumbling Snitchbug grab lands while the captain idles (`NaviStateWait`)
as well as while it walks, and the mouth-stick relation is retained across both.
The P1 bridge admitted capture only from `NAVISTATE_Walk` and detached ownership
the moment the captain left Walk, so every natural fixture had to hold the
captain in Walk and could not exercise an idle target (documented as a limit in
`P2_DEMON_NATURAL_CAPTOR.md`).

Changing which captain states may own a mouth stick is captain semantics. The
semantic commits below are submitted for **#186** and **lane-12 (#130)**
review; they are isolated from the fixture work so they can be reviewed and
reverted independently.

## Capture-eligible allowlist

`pc_port/pc_p2_demon_admission.h` (`pc_demon_captain_admission_eligible`) is a
deny-by-default list. A captain is a valid mouth-stick owner/capture target only
in:

- `NAVISTATE_Walk` (0) - ordinary ground locomotion.
- `NAVISTATE_Idle` (17) - the neutral/wait state retail P2 grabs from.

Every other `NaviState` is explicitly rejected because it owns control,
animation, damage, impulse, UI or life semantics a captor must not pre-empt:

| Rejected state(s) | Why |
|---|---|
| `Dead` (29) | not a live target |
| `Stuck` (18) | Puffmin-stuck/stunned control |
| `Rope` (10) / `RopeExit` (11) | rope/climb control (also `mRope`) |
| `Container` (12) | Onion/container UI (invincible) |
| `Ufo` (13)/`UfoAccess` (14)/`PartsAccess` (15) | ship interaction (invincible) |
| `Bury` (19) / `Geyzer` (20) | buried / launched (invincible, own motion) |
| `Pressed` (7) / `Flick` (8) | own damage/impulse state (invincible) |
| `Nuku` (5) / `NukuAdjust` (6) | plucking Pikmin from the ground |
| `Throw` (1)/`ThrowWait` (2)/`Pick` (16) | held/aimed Pikmin contract is live |
| `Gather` (3) / `Release` (4) | issuing/releasing a Pikmin command |
| `Water` (27) | separate aquatic semantics |
| `Attack` (28) | melee action in progress |
| `Push` (30)/`PushPiki` (31)/`Lock` (32) | wall/push/locked control |
| `PikiZero` (33) | game-over countdown |
| `Pellet` (24)/`Sow` (26)/`Clear` (34)/`IroIro` (35) | scripted/special states |
| `DemoWait` (21)/`DemoInf` (22)/`Starting` (23)/`DemoSunset` (25) | scene owns control |
| `DemonDrop` (36)/`DemonEscape` (37) | already in a receiver; no re-admission |

The accepted stimulus/attachment semantics and the existing invalidation guards
(`isAlive`, `isStickTo`, `mRope`, exact-owner/part match, bouncy mouth, owner
token) are unchanged. No generic damage or transition handling is reordered.

### A/B toggle

`PIKMIN_DEMON_WALK_ONLY_ADMISSION=1` restores the historical Walk-only gate in
the same binary (read once per process); the default is the source-backed set.
This is the only switch and it is used solely for the A/B evidence below.

## Changed files

- `pc_port/pc_p2_demon_admission.h` (new): the allowlist and toggle.
- `pc_port/pc_p2_demon_bridge.cpp`: `pc_demon_capture` and `pc_demon_bound` use
  the allowlist instead of a literal `NAVISTATE_Walk` check.
- `pc_port/pc_p2_demon_drop_state.cpp`: `pc_demon_drop_begin` admits the
  allowlisted pre-drop state (Idle or Walk).
- `pc_port/pc_p2_demon_escape_state.cpp`: `pc_demon_escape_begin` uses the same
  allowlist so an idling carried captain can escape consistently.
- `tools/p2_demon_host_runtime.cpp`: new `natural_idle` fixture mode plus the
  Walk-only A/B control assertion.

## Build provenance

- Native worktree `output/native-demon-host-clock`, branch `codex/demon-host-clock`.
- Base `2c08d6b8`; semantic HEAD `31d2e48a`; fixture HEAD `4e864125`.
- Private build `output/native-demon-host-clock/build-demon`;
  `ninja -n pikmin_pc` -> `ninja: no work to do.`
- `bin/nectar.exe` SHA-256 `C79C80E4DBAF9371463719D1CB3DC3970E275D8AAB6BD7D6115FBB8FF1EC958F`.
- Fixture `output/demon-idle-fixture-01`, `status=built`, expected native head
  `4e864125bfe7ab2951e1b46ca44db713f6a94847`; `fixture.exe` SHA-256
  `FFA23066D7F470EFDE2707DBAA2BF33531441E862023E683F920F8659BB69C32`.
- Session `output/demon-idle-run-01/8e087e5357aa411d82046e4350eb2c4c`,
  `PIKMIN_P2_ROOM_WINDOW=960x540`, 20-red baseline arena.

## New mode: natural_idle (natural, not injected)

The captain is placed in the real engine `NaviStateWait` at arena start and is
**never transited to Walk**. `mNeutralTime` is held below the engine's
`Idle`->`Pellet` threshold (140 s) while the captain is unbound; this holds only
the neutral timer, not the Walk state. The natural Demon still performs its own
target acquisition, capped-turn approach, source Attack window,
`pc_demon_capture` admission, CatchFly/FallMeck clock and the registered 10-HP
drop. No frame, target, END, capture or drop is injected.

```text
P2_DEMON_HOST_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
DEMON_NATURAL_BEGIN mode=natural_idle host=(0.00,100.00,100.00) captain=(0.00,100.00,160.00) state=17 neutral=11.0
DEMON_NATURAL mode=natural_idle tick=150 phase=2 host=(6.27,29.80,146.12) cap=(-0.20,0.00,160.13) hp=100.0 state=17 stuck=0 ...
DEMON_NATURAL_IDLE carry tick=165 state=17 stuck=1 bound=1 hp=100.0
DEMON_NATURAL mode=natural_idle tick=240 phase=4 host=(6.27,29.80,146.12) cap=(-6.36,90.23,143.33) hp=100.0 state=17 stuck=1 ...
DEMON_STATE_DAMAGE generation=1 accepted=1 before=100.000 after=90.000
DEMON_NATURAL mode=natural_idle tick=270 phase=2 host=(6.27,29.80,146.12) cap=(-24.39,0.00,176.60) hp=90.0 state=36 stuck=0 ...
DEMON_STATE_HANDOFF next=0 quenched=1
PASS DEMON_HOST natural_idle_captor_acquire_attack_capture_drop (ticks=300)
```

The gate requires `NAVISTATE_Idle` for every unbound approach frame, requires
`pc_demon_bound` + `NAVISTATE_Idle` for the entire carry, and only passes once
the registered `DemonDrop` has delivered its 10-HP drop and the captain has
returned to Walk.

### A/B control (Walk-only toggle)

Same binary, same Idle captain and same natural host, with
`PIKMIN_DEMON_WALK_ONLY_ADMISSION=1`:

```text
DEMON_NATURAL_BEGIN mode=natural_idle host=(0.00,100.00,100.00) captain=(0.00,100.00,160.00) state=17 neutral=11.0
PASS DEMON_HOST natural_idle_walk_only_admission_refuses_capture (ticks=901)
```

The host reaches its attack phase but the historical gate never admits the Idle
captain, so no capture occurs.

## Regression evidence (same fixture/session)

All PASS, all `centered=1` at `960x540`, no `FAIL DEMON_HOST` in any capture:

| Mode | Marker |
|---|---|
| `natural` | `natural_captor_acquire_attack_capture_drop (ticks=302)` |
| `natural_escape` | `natural_captor_voluntary_escape (ticks=190 edges=24)` |
| `natural_interrupt` | `natural_captor_interruption_release_teardown (ticks=168)` |
| `natural_teardown` | `natural_captor_grounded_release_teardown (ticks=164)` |
| `ordinary` | `ordinary_spawned_captor_acquire_attack_capture_drop (ticks=860)` |
| `drop` | `injected_capture_catchfly_drop_recovery` |
| `livecapture` | `live_owner_mouth_capture_release` |
| `teardown` | `teardown` |

## Still simulated / not claimed

- Private single-room converted arena, not a generated-seed/randomizer-admitted
  encounter; the `ordinary` anchor is the Dwarf Bulborb placeholder
  (`TEKI_Chappy`), not a native P2 `Demon` teki.
- The `natural_idle` captain is fixture-placed; its neutral timer is clamped to
  stay Idle, but the fixture never holds it in Walk.
- No patrol/turn-to-scan state: the ordinary enable widens the view cone to 360
  degrees and the territory/sight radii to cover the room.
- Admission uses the rest-pose mouth effector while the stick follows the
  sampled animated joint.
- Terrain/water/slope, scene teardown during an active drop and the `Sarai` ID
  23 source actor remain separate gates.
- The Walk-only A/B is an environment toggle, not a retail behavior.

## Review request (#186 / lane-12 #130)

Requested: review the captain admission set in `pc_p2_demon_admission.h` and its
use in `pc_p2_demon_capture`, `pc_p2_demon_bound`, `pc_p2_demon_drop_begin` and
`pc_p2_demon_escape_begin` as the canonical captain-as-mouth-stick-owner
contract for captor lanes. Confirm that `NAVISTATE_Walk` + `NAVISTATE_Idle` is
the intended initial admission set, that the rejected special states are the
right deny set, and whether the `PIKMIN_DEMON_WALK_ONLY_ADMISSION` toggle should
be removed after review. No generic damage/transition handling is changed.
