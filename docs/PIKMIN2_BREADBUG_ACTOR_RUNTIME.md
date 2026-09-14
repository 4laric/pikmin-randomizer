# Original P1 Breadbug proxy arena runtime

Scope #168/#186. New `pikmin2_breadbug_arena` stages the original Impact Site
practice map, collision/routes and base generator into a private chal0 slot.
It adds one native Collec (type 8) proxy 186081 at (-150,30,1850) and one ordinary Collec
control 186082 at (150,30,1550). These are engineering arena placements, not P2
source placements. Generator offset is zero, birth count/radius is made
explicit with the existing deterministic-birth helper, and every original
course file is byte-verified unchanged. No shared seed/assets are overwritten.

`pikmin2_breadbug_actor_fixture.cpp` uses ordinary native AI updates. It does
not reposition the enemy or write enemy velocity/state/health. It positions
only the fixture captain near the initial actor for camera framing, disables
further tutorial demo flags and provides a zero-input controller. Movement
acceptance requires over 15 units horizontal displacement and at least 15 frames
of native horizontal velocity. Mere gravity settling is not enough.

The driver verifies exact production readiness identity/type/full birth XYZ,
live visual delegation and movement evidence. The fixture keeps the control
alive, resets the family mapping and verifies that drawing now declines both
the proxy and ordinary control. This tests registration reset, not a full
stage unload/reload or natural death/corpse route. Source P2 FSM, cargo stealing,
receiver damage and rewards remain outside this proxy test.

Captures cover initial actor, later movement and post-reset visuals. A capture
must be inspected before reporting framing/appearance success. Native process
success alone does not establish source model fidelity. The binary and frozen
build inputs must be identified in the result/provenance; do not use current
production filenames as historical evidence.

Two driver tests cover fullXYZ, real movement threshold, missing draw and
multiple-ready rejection. Local staging passed at
`output/p2-lifecycle-batch/breadbug-arena-prepare-01`.

The private runtime also replaces the frozen current-source newPikiGame object
with the reusable instrument_tutorial helper from the Kochappy arena fixture.
It pulses A through the actual tutorial Controller; the ordinary tutorial
window update closes text 13 (extinction, from the zero-Pikmin fixture setup).
No overlay flag is force-cleared. Movement sampling starts only after the
normal pause and overlay gates clear. This is injected test input, not manual QA.

## Actual runtime result

The private arena passed with native base
`d7ff676bf8990a442002e1c3d7050f17a93b01a3` and the recorded existing dirty
`creatureCollision.cpp`/`goalItem.cpp` changes (tracked diff SHA256
`7c5baccf4deb14218bb8690dc795a9a6a0c629e3bf2d2f3b9eec501a6bb957ad`).
This is not evidence from a pristine commit. The private build made no shared
native changes.

Result: `output/p2-lifecycle-batch/breadbug-actor-native-01/result.json`.
Run: `9e02bb3ff3b04cf7ad00d4db04781ce4` under that directory.
The exact opted-in actor was type 8, generator 186081, full birth position
(-150,30,1850). It moved 480.690552 horizontal units with native horizontal
velocity in 300 observed frames. The ordinary control stayed alive. Production
draw delegation logged success, and after reset both actors declined the
family visual delegate. Tutorial 13 closed through normal Controller input.

Fixture: `output/p2-lifecycle-batch/breadbug-actor-runtime-link-02/fixture.exe`.
SHA256: `3ab9be485f629df411d70d151b8e2f22e4b06bc5de24e47f14d0421ec04693d3`.
The `commands.json` there records the private tutorial object and relink.
Its base `breadbug-actor-runtime-link-01/provenance.json` records copied build
inputs, freshness checks and source state. The private original and instrumented
tutorial source hashes are retained in the relink record. Implicit compiler
runtime/startup dependencies are not included in the copied input set.

The inspected initial PNG visibly shows the imported live model in the arena.
By the moved/reset captures the actor had wandered outside the camera edge;
those images do not establish visible reset appearance. Reset mapping behavior
is verified by the actual native API assertions. P1 corpse fallback is unchanged
by this implementation, but natural death, corpse delivery, cargo stealing,
stage reload and full P2 behavior remain untested.

Validation: 13 Python tests and 4 subtests passed across the actor runtime,
actor installer, visual installer and asset extractor suites. Private fixture
compilation/link and the actual native process exited successfully.

## Maintained-line reset/re-entry + injected death cleanup (lane 18, 2026-09-14)

Extends the small PanModoki (`TEKI_Collec`) proxy fixture with the two gates
left `UNTESTED` above. No native change; `pc_p2_breadbug_actor` is used through
its existing public API.

- Driver `scripts/test_pikmin2_breadbug_actor_native.py` now builds the fixture
  from `--native/--build-dir/--head` (with `--prefix room-prefix.inc`) or runs a
  prebuilt `--exe`.
- Fixture `scripts/pikmin2_breadbug_actor_fixture.cpp`:
  - at frame 300 `pc_p2_breadbug_actor_reset()` (proxy draw declines),
  - then `pc_p2_breadbug_actor_setup()` re-registers (second `P2_BREADBUG_ACTOR_READY`),
  - then injected death `actor->mHealth=0`, and the proxy draw declines once dead.
- Evidence: run `output/lane18-breadbug-runtime/11445227953f4e4a89641c8eda90f50e`
  (fixture SHA-256 `6be31afa3c475176c9397873f5309910c530216fcfb1c58d5b05503c85c98cfa`):
  birth `-150,30,1850`, max displacement 478.44 over 300 moving frames,
  `P2_BREADBUG_ACTOR_REENTRY`, `P2_BREADBUG_ACTOR_KILL frame=306`,
  `P2_BREADBUG_ACTOR_DEATH corpse=0`, PASS.
- Fixture baseline adopted: env-driven window (`PIKMIN_P2_ROOM_WINDOW`, default
  960x540) with `pc_window_center()` and the standard log line; 20-red starting
  squad via `ensure_pikmin_squad` in the arena overlay; no extinction screen.
- Native base `a0b5dca4049ddbe79979eecc9f72c517e5d3a920` (`output/lane18-native`),
  private build `output/lane18-native-build` (`ninja -n pikmin_pc`: no work).
- **Corpse finding**: on injected death the P1 `TEKI_Collec` host leaves **no
  PelletView corpse** (`corpse=0`). Cleanup/unmapping passes; the P2 corpse
  carry/reward is still unimplemented and is not claimed.
- **Still lane-06/engine-gated**: P2 contested cargo, nest treasure storage and
  exactly-once AP receipt. Interface request posted on #441; this lane will not
  fork the Giant module's contest logic.

## Reward receipts — lane-06 consumer (lane 18, 2026-09-14)

`experimental/pikmin2_breadbug_rewards.py` builds the breadbug reward
descriptors on lane 06's shared `experimental.pikmin2_receipts` schema and
proves exactly-once grant + restart persistence for the family. Root-only; no
native change, no save mutation.

- Descriptors: `enemy:38` PanModoki → `pellet` on the Onion ledger; `enemy:40`
  OoPanModoki → `corpse` on the AP ledger. Helpers/aliases `alias:39`
  (PanModokiNest) and `helper:83` (PanHouse) deliberately have no descriptor and
  are rejected by `grant_defeat`.
- `resolve_encounters` grants each `(identity, actor, encounter)` once; a revisit
  of the same actor/encounter in one seed adds no second reward.
- `reconcile_runs` delegates coverage/leak checks to lane 06's `reconcile`, so
  missing sources and Pod-only leaks behave identically to other lanes.
- Evidence: `py -3.12 -m pytest tests/test_pikmin2_breadbug_rewards.py -q` →
  10 passed (with lane 06's `test_pikmin2_receipts.py`: 42 passed, 19 subtests).
- This closes the "rewards once" consumer half. The native contested-cargo half
  is still gated on lane 06's native contest surface (#441).

## Contested cargo, interruption and release model (lane 18, 2026-09-14)

`experimental/pikmin2_breadbug_contest.py` models the source `PanModokiBase`
cargo rules that the arena gates must observe, plus the release outcomes. Root
tests: `tests/test_pikmin2_breadbug_contest.py` (7 passing).

- **Eligibility:** `targetable()` encodes the source variant split — small (38)
  targets strictly lighter cargo, Giant (40) targets at-or-above (ip01=1) — and
  rejects a stuck passenger, non-carryable cargo or a full 15-slot treasure hold.
- **Contest strength:** `carry_strength()` is `(min+max)/2`; `carriers_win()`
  reflects the audited 1-pellet case (1.5 beats one carrier, loses to two).
- **Release outcomes:** `release_plan()` distinguishes `eat` (slot 0 kept in the
  nest), interruption `drop` (`giveup`), contest `recover` and `digest`; the
  death throw-up geometry returns every held slot at nest +10y on a `TAU*i/n`
  ring (skipped for a single slot), and `reconcile_death()` proves none are
  created or duplicated.

Native change: `native/pc_port/pc_p2_giant_breadbug_actor.cpp`
`pc_p2_giant_breadbug_actor_press` now releases the held cargo in place on a valid
Purple press (source `Damage::init` `giveup(2)`), logging
`P2_GIANT_INTERRUPT generator=... reason=press released=1`. This is the missing
interruption-release half of the "contested cargo / interruption / death release"
slice; the existing contest-lost and death throw-up paths are unchanged.

Remaining: the same interruption is not wired for the small Breadbug proxy
(P1 `TEKI_Collec`), and native exactly-once receipt persistence still needs the
lane 01/06 native save bridge. Both remain open on #168/#220/#441.

`pikmin2_breadbug_rewards.resolve_contest()` ties the contest model to the
lane-06 ledger: only a death grants the family reward (once), and it returns the
thrown-back held treasure; `eat`/`drop`/`recover`/`digest` grant nothing. Four
tests cover interruption/digest non-grants, exactly-once death grant, an unknown
outcome and a helper identity. The rewards suite is now 14 tests.

## Small-vs-Giant arbitration and nest ownership (lane 18, 2026-09-14)

`experimental/pikmin2_breadbug_contest.py` now carries the audited variant table,
the single-channel arbitration and the parent-bound nest lifetime. Root tests:
`tests/test_pikmin2_breadbug_contest.py` (14 passing) plus the rewards consumer
suite (16 passing).

- **Variant parameters:** `variant_params('small'|'giant')` returns a copy of
  `VARIANT_PARAMS` — health 1100/2000, weight threshold ip01 11/1, carry speed
  fp03 35/45, press damage fp06 200/100, nest scale 1.0/2.0, and
  `purple_only_press` False/True. Both species set
  `nest_house_type = NEST_BREADBUG (1)`.
- **Arbitration:** `arbitrate(claim_strength, challenger_strength)` implements
  the source `PelletCarry::pullable`/`pull` rule. An idle or same-channel
  challenge is accepted with no stall; a cross-channel challenge wins only with
  strictly greater strength and then stalls the pellet `TAKEOVER_STALL_SECONDS`
  (0.5 s, 15 frames). Defaults model the Breadbug `PCS_Unk2` drag against the
  Pikmin `PCS_Carry` channel.
- **Frame sequence:** `contest_frames(breadbug_strength, carrier_power_by_frame)`
  returns `DRAG` (Back) while the Breadbug holds and `PULLED` once the carriers
  strictly out-pull it, reusing `arbitrate` per frame.
- **Nest ownership:** `nest_ownership(owner_alive, house_type)` reports the
  parent-bound nest state (`NEST_BREADBUG=1` for both Breadbug species,
  `NEST_JIGUMO=0` for the Jigumo crawmad, `enemyNest.cpp:60-67`).
  `nest_collision_after_death(frames_since_kill)` keeps collision for 79 frames
  and drops it at/after `NEST_DEATH_FADE_FRAMES=80` (`enemyNestMgr.cpp:143-152`).
- **Purple-only press:** `press_damage(variant, purple=...)` returns 0.0 for a
  non-Purple Giant press (`panModoki.cpp:1738-1744`) and 100.0 for a Purple one;
  the small Breadbug accepts either (200.0). `pikmin2_breadbug_rewards.resolve_press`
  applies that gate before the ledger: a resisted press neither drops cargo nor
  grants; an accepted press is a `drop` interruption and still grants nothing.

## Small-Breadbug proxy contested-cargo observation (lane 18, 2026-09-14)

`experimental/pikmin2_breadbug_contest_observation.py` is the private validator
for the small PanModoki (source 38) P1 `TEKI_Collec` proxy. It stages the existing
private proxy arena, feeds one real red level-0 number pellet through the
unchanged `scripts/pikmin2_breadbug_cargo_fixture`, and parses the host log into
the P1 grab/drag/release timeline. It reports the two strength scales
**separately** and never claims P2 contest semantics:

- `native_offset_power = 2.0` is the P1 `TEKI_Collec` host carry power that
  actually drags the pellet (`taicollec.cpp:509`).
- `source_strength = (pelletMin + pelletMax) / 2` is the P2 `PanModokiBase`
  contest strength for the same pellet; the staged red 1..2 number pellet gives
  `1.5`.
- The two are unequal (`2.0` vs `1.5`) and every observation records
  `p2_contest_semantics=False`; the read-only native hook now emits
  `P2_BREADBUG_CONTEST generator=<id> native_power=2 carriers=<n>` and the
  validator parses it into `native_carriers`/`native_power`, setting
  `native_hook=True` without changing the `p2_contest_semantics=False` claim.
- `observe()` raises when the birth marker is missing/mismatched or the log does
  not hold exactly one completed `P2_BREADBUG_CARGO_RESULT`, so a clean process
  exit is never mistaken for a completed observation. `run()` stages the arena
  and writes `result.json` for the coordinator's serialized GL slot.

### Read-only small-proxy cargo-carrier introspection (lane 18, 2026-09-14)

`native/pc_port/pc_p2_breadbug_actor.cpp` now exposes a **read-only**
`pc_p2_breadbug_actor_tick()`, wired next to the existing giant tick in
`src/plugPikiKando/gameCoreSection.cpp`. For each registered proxy actor it reads
the P1 host's own held-cargo pointer (`getCreaturePointer(2)`) and counts the
Pikmin `Stickers` on the pellet, mirroring the Giant module's `carriers` helper.
When the held state or carrier count changes it logs a bounded
`P2_BREADBUG_CONTEST generator=<id> native_power=2 carriers=<n>` marker. The
tick only reads the existing pointer; the P1 `TEKI_Collec` host remains the cargo
owner and nothing is released, claimed or written. Shared cargo/physics/contest
semantics are unchanged.

The validator reports `native_carriers`/`native_power` next to `source_strength`
and keeps `p2_contest_semantics=False`. This is honest introspection, not P2
contest parity: the P2 pull channel, ownership and release still belong to the
lane 06/07/giant surfaces.

The `P2_BREADBUG_CARGO_VISUAL`/`P2_BREADBUG_CARGO_RESULT` markers already prove
grab/drag/release through the existing family draw path; this validator adds the
source-vs-native strength split, the read-only native carrier count and honest
`p2_contest_semantics=False`. Tests:
`tests/test_pikmin2_breadbug_contest_observation.py` (9 tests; with the proxy
cargo and contest suites, `py -3.12 -m pytest` → 29 passed).

## What remains (lane 18)

- **Small-Breadbug interruption is still a real gap, not an omission.** The small
  proxy `native/pc_port/pc_p2_breadbug_actor.cpp` has **no cargo owner to
  release**: cargo is the P1 `TEKI_Collec` host's own `getCreaturePointer(2)`
  state, which the proxy does not own or mutate. The new
  `pc_p2_breadbug_actor_tick()` is strictly read-only (observe the held pointer
  and `Stickers` carriers); it never releases, claims or writes cargo. The
  interruption model above stays host-side until the P2 FSM/cargo port gives the
  small actor ownership (or the giant module's
  `endStickTeki`/`clearCreaturePointer` release path is reused under an agreed
  lane-07 lifetime owner).
- **Small-Breadbug P2 contest is shared-semantics-gated.** The proxy observation
  validator above separates the P1 carry power (2) from the source strength
  (1.5) and now reports the read-only native carrier count, but it still cannot
  observe a P2 pull channel or drive P2 carriers: those need the shared
  cargo/reward endpoint (lane 06) or the centralized forget/rebind lifetime
  owner (lane 07). A true contested-cargo run stays open until one of those
  surfaces exists; no P2 contest semantics are claimed.
- **Giant cargo/press runtime fixture:** the release path
  (`pc_p2_giant_breadbug_actor_press`) still needs an ordinary-arena run that
  observes a Purple press releasing held cargo and a non-Purple press being
  resisted, plus the contest-lost and death throw-up paths. Existing evidence is
  code-only.
- **Native receipt persistence:** exactly-once family reward persistence across
  process restart still needs the lane 01/06 native save bridge; the Python
  ledger/receipt work is a host-side contract, not a save mutation.
- Open on #168/#220/#441.

## Giant actor arena runtime � combined build (lane 18, 2026-09-14)

The prior private Giant actor fixture (`giant-actor-build-02/fixture.cpp`, native
`e91bb22b`) was rebuilt against the combined lanes 16-18 native build and re-run
on its staged arena. It now also probes the interruption release added in this
wave (a valid Purple press must release held cargo in place).

- Fixture source committed as `scripts/pikmin2_giant_breadbug_actor_fixture.cpp`;
  arena reused from `output/p2-lifecycle-batch/giant-actor-native-14/stages/...`.
- Native `opencode/p2-lanes16-18-native` @ `d37d000718cdd98dcac8bbd688f1fd673a2e3e17`,
  build `output/lanes16-18-native-build` (exe `ABB537EB...`). Fixture built via
  `scripts/build_pikmin2_fixture.py`.
- Run `output/lane18-giant-arena-c/run1` (copied stage), exit 0:
  `P2_GIANT_ARENA_PRESS non_purple=resisted purple_damage=100 health=1900.0`,
  `P2_GIANT_ARENA_INTERRUPT natural=1 released=1 health=1800.0` (the Giant grabs
  the bait pellet through its own FSM, then a Purple press releases it in place),
  `P2_GIANT_ARENA_CONTEST released=1 tick=122 strength=1.5 carriers=2`,
  `P2_GIANT_ARENA_DIGEST healed=1 health=2000.0`, `P2_GIANT_DEFEATED thrown_back=2`,
  `P2_GIANT_THROWUP pellets=2 nest=...`,
  `PASS P2_GIANT_BREADBUG_ARENA spawn_identity press contest digest_heal
  defeat_throwup nest_linked`.
- This is the first runtime confirmation of the interruption (`giveup`) release,
  now with natural cargo acquisition (no `setCreaturePointer`/`startStickTeki`
  invite for the held state). The small Breadbug proxy still has no cargo owner,
  so its interruption path remains unimplemented.

### Standard 960x540 preview window (lane 18, 2026-09-14)

`scripts/pikmin2_giant_breadbug_actor_fixture.cpp` no longer hardcodes a
960x720 window. Its `main` mirrors `pc_main.cpp`'s `pc_test_window_size` sequence:
it reads `PIKMIN_P2_ROOM_WINDOW` (default 960x540, `WxH` override, `=off` keeps the
persisted size), calls `pc_window_init` at that size, then — after
`pc_settings_init()` — applies `pc_window_set_display_mode(...WINDOWED)`,
`pc_window_set_window_size(...)` and `pc_window_center()`, and logs
`Experimental preview window set to 960x540 windowed and centered`. The arena logic
above is unchanged; only startup window handling moved to the maintained standard.

### Exactly-once Giant press/contest/defeat receipt bridge (lane 18, 2026-09-14)

`experimental/pikmin2_breadbug_rewards.py` adds `resolve_giant_step` and
`resolve_giant_sequence` on top of the existing `resolve_press` / `resolve_contest`
/ `grant_defeat` helpers. A sequence is an ordered list of
`{'kind': 'press'|'contest'|'defeat', ...}` steps: a press carries `purple` (and
optional `held_slots`), a contest carries a `reason`, a defeat carries optional
`held_slots`. Semantics:

- A **resisted** press (non-Purple Giant) never releases and never grants.
- A **Purple press** that only releases cargo (`drop`) is an interruption: it
  returns the held cargo and never grants.
- A **contest loss** (`recover`) returns cargo to the carriers and never grants.
- Only the **defeat** grants, exactly once, and returns every held treasure.
- Because the grant goes through lane 06's `ReceiptLedger`, replaying the same
  ordered sequence after a `restart()` (or through a fresh
  `JsonReceiptPersistence`) grants nothing again, while a genuinely new
  actor/encounter still grants.

Tests: `tests/test_pikmin2_breadbug_rewards.py` adds a full ordered
press/contest/defeat sequence and a `JsonReceiptPersistence` restart replay.

- Remaining: the small Breadbug proxy still has no cargo owner, and native
  exactly-once receipt persistence across process restart still needs the lane
  01/06 native save bridge. Both remain open on #168/#220/#441.
