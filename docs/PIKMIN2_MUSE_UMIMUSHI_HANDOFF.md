# Muse UmiMushi handoff - natural death/corpse + re-entry observer (shard, #374)

Worker: Muse Spark 1.3 (`opencode/muse-spark-1.3-contributor`, lane
shard-enemies-6-umimushi71-observer, generation 2). Implementation owner: Codex
through shared GitHub account `4laric`. Parent #167; family lane #374.
Source IDs 71 UmiMushi (slice target) + 101 UmiMushiBlind (shared module).

## Scope result: gate 4/6 BLOCKED with exact structural evidence (no substitutes)

A full natural-death run executed (102 genuine throw-release events, staged
captain once, captain guard #632 active): the bound ordinary Bloyster took
15 HP of 1500 across the first 20 throws, then held 1485.0 flat across
1000+ further ticks with 31 flick-offs and 12 swallows, while the parked
captain was dragged ~270 units by repeated flick knockbacks and killed at
tick 1273 (guard fired `P2_FIXTURE_CAPTAIN_DOWN`, exit 86 BLOCKED, no false
PASS). No health/mode/attack writes exist anywhere in the fixture
(machine-audited); no values invented.

Root causes, read from the untouched family module
(`pc_port/pc_p2_umimushi.cpp`, lane 16 owned, read-only here):

- `flickNearby` clears every Pikmin AND the Navi within `SHAKE_RANGE` with
  `SHAKE_DAMAGE = 0.0f` (source fp18 default): landed Pikmin are swept
  before latching, so stick damage never accumulates; `isStartFlick` also
  triggers on the Navi, and repeated `SHAKE_KNOCKBACK` walked the parked
  captain 400 -> 129 units into `ATTACK_HIT` (170) range where
  `attackNearbyNavi` (`ATTACK_DAMAGE = 10.0f`, source fp24) killed him.
- Whether Pikmin fail to latch at all or latch damage is unrouted to
  `mHealth` (written only at bind, never per-tick) cannot be distinguished
  from these markers; both halves need lane-16 receiver instrumentation.

Exact missing prerequisite: lane-16 receiver verdict on latched-stick
damage routing for the Chappy-hosted umimushi FSM, plus a validated safe
park distance (arena bounds survey) for unattended long runs. Bounded
follow-ons: (a) lane-16 verdict; (b) non-red squad composition (species
lanes, out of scope); (c) dedicated Blind-target run reusing this fixture
with a target parameter (101 gates stay UNTESTED: bound and observed, never
targeted). Gates 1/2/3 (71) and gate 3 (101) preserved, never relabelled;
gate 5 stays source-backed N/A (no corpse observed, none invented).

## Source IDs

- Source ID: 71 `UmiMushi`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md gate table; output/umimushi71-death-log.txt: BIND re-observed | natural (preserved, not relabelled) |
| 2. Movement and animation | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md gate table (walk/flick/attack/eat) | natural (preserved) |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md bite receiver (frame 39, once/eat) | natural (preserved) |
| 4. Death and corpse | BLOCKED | output/umimushi71-death-log.txt: 102 genuine throws, HP 1500.0->1485.0 then flat 1000+ ticks; family DEAD never fired | natural combat, zero substitutes; no death claimed |
| 5. Transport and reward | N/A | docs/PIKMIN2_UMIMUSHI_NATIVE.md: no verified source loot; no corpse observed | source-backed N/A |
| 6. Cleanup and re-entry | BLOCKED | gated on gate 4 (rebirth pass runs only after a validated death) | not run; no claim |

- Source ID: 101 `UmiMushiBlind`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | - | - |
| 2. Movement and animation | UNTESTED | - | - |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_UMIMUSHI_NATIVE.md blind bite+eat (blind=1) | natural (preserved) |
| 4. Death and corpse | UNTESTED | bound and observed (BIND 374006) but never targeted; dedicated run is the bounded follow-on | - |
| 5. Transport and reward | UNTESTED | - | - |
| 6. Cleanup and re-entry | UNTESTED | - | - |

Gate detail (death-run1/pass1/<uuid>/native.log, 1297 lines): staged
captain once (400 east of birth, outside every documented reach);
102 genuine throw-release events (dist 400.0 -> 128.9 as the captain was
dragged); HP trail 1500.0 -> 1485.0 then flat; 6 EAT + 2 FLICK on 374004
plus crossfire on the far blind; captain guard fired once on genuine
captain death (tick 1273, hp=0.000, dead_state=1); exit 86. A forced-kill
log (DEAD row, no throws) is rejected by the validator (unit-tested).

## Source IDs and files owned

- Source IDs: 71 UmiMushi (slice target); 101 UmiMushiBlind (shared
  module, bound + observed, death not targeted).
- Native (worktree `.../prepared/umimushi71-observer-native`,
  branch `codex/shard-enemies-6-umimushi71-observer-native`):
  `tools/p2_muse_umimushi_fixture.cpp` (new, owned). `pc_port/pc_p2_umimushi.*`
  inspected, not modified (no defect fix attempted; funnel path verified
  present for the follow-on).
- Root (worktree `.../prepared/umimushi71-observer-root`,
  branch `codex/shard-enemies-6-umimushi71-observer`):
  `experimental/pikmin2_muse_umimushi.py` (new),
  `tests/test_pikmin2_muse_umimushi.py` (new, 18 passed),
  `docs/PIKMIN2_MUSE_UMIMUSHI_HANDOFF.md` (this file).

## Ordered commits (dirty: clean on both)

Root (`codex/shard-enemies-6-umimushi71-observer`, base `8ff3001e4e469cf9d33430e0ff769c15738270e3`):
- 24d4de9e observer fixture/runner/tests/doc + death-pass negative evidence

Native (`codex/shard-enemies-6-umimushi71-observer-native`, base `6a87eb2994b66355b05ce40bf3a8823884236299`):
- e993e8fb observer fixture fragment (+ funnel drive + captain guard)

Heads: root 24d4de9e / native e993e8fb (doc finalized in follow-up commit); handoff head is this doc commit.

## Interfaces / hooks touched

- None in shared engine code. The fixture drives two public engine APIs
  exactly as the throw state machine does on `KEY_Action0`
  (`Piki::mFSM->transit(p, PIKISTATE_Flying)` + `Navi::throwPiki(p, aim)`
  after direct idle-Pikmin selection), plus the public `pcEscapeNow()`
  death-funnel helper (never reached: no death occurred).
- One staged captain `Navi::resetPosition` at tick 1 (reported staging, not
  gameplay); everything else is engine AI/physics. Captain guard
  `p2_fixture_require_captain` (canonical `scripts/p2_fixture_captain_guard.h`
  sha256 `d2f678c9...3474`, vendored) runs before every pause/movie return
  and observed tick; it fired exactly once on genuine captain death.

## Build evidence

- Private build dir `output/umimushi71-build`, native `e993e8fbc8546d062a7a9c34920c1b9072560455`
  (dirty: clean); `pikmin_pc` linked, `ninja: no work to do.` dry run.
  Production exe `bin/nectar.exe` sha256 `13aba5a65057c130043f24d5c92e0e3caf86213fcc4c65f8fd594639e83b1993`.
- Fixture `umimushi71-fx1` provenance `built` for expected head `e993e8fb`;
  `fixture.exe` sha256 `c0b7d1853b350fa776b359809924e4af89b6c99290e0d0ce9a048f8cfc1cff95` -- the binary that ran.
- Fixture adoption: fresh arena via current overlay (24 generators incl.
  20-red starting squad), observed 960x540 centred startup, live room at
  ~30 fps, no immediate extinction (squad survived; captain death at tick
  1273 is captain, not squad, loss).
- Build-dir note: the brief template path under the launch out dir makes
  the provenanced link line exceed the Win32 32K limit (proven by failed
  attempt, log kept); lane-private `output/umimushi71-build` +
  `output/umimushi71-fx1` used instead (same isolation guarantees,
  tadpole-lane precedent).
