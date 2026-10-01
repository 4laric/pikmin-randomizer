# Muse lane l63 — Waterwraith autonomous encounter movement (#503)

Lane `muse-waterwraith` of the Muse admission wave (#491). Tracking issue
[#503](https://github.com/4laric/pikmin-randomizer/issues/503), family parent
[#443](https://github.com/4laric/pikmin-randomizer/issues/443), original parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175).
Implementation owner: Codex through shared account `4laric`. Executing
contributor: Muse Spark 1.3 through OpenCode (`opencode/muse-spark-1.3-contributor-free`).

## Scope

Prioritize BlackMan 99 autonomous source-correct movement to replace
pinned routes; Tyre 98 remains helper. This slice ports the source
`walkFunc` autonomous driver (research `blackMan.cpp:831-1027` at revision
`632af937`) around the retained-assembly map-graph search: the actor owns
target selection (captain chase outranks pod approach outranks seam route
fallback), the escape distance bands/timer/smoothing, the pod motion choice,
the route-find cadence counters and turn damping. Birth identity was audited
against source `onInit` (`blackMan.cpp:147-169`: Fall start off cave `y_01`,
exactly one Tyre child birthed via the Tyre manager, home/route at the birth
position, nearest map waypoint adopted) and is now observably reported at
runtime. Accepted lane-31 gates 3-6 are preserved unchanged; no damage, death,
corpse, receipt or teardown line was modified.

Owned files only:

- `native/pc_port/pc_p2_waterwraith_actor.{h,cpp}` — escape axis, chase/pod
  branches, cadence counters, turn damping, motion requests.
- `native/pc_port/pc_p2_waterwraith_encounter.{h,cpp}` — live captain feed,
  BIRTH/STEER/TIRED/REFRESH observation markers, travel stats.
- `experimental/pikmin2_muse_waterwraith.py` — fail-closed log observer.
- `tests/test_pikmin2_muse_waterwraith.py` — 13 observer contract tests.
- `docs/PIKMIN2_MUSE_WATERWRAITH_HANDOFF.md` — this document.
- `native/tools/p2_muse_waterwraith_fixture.cpp` — standalone log checker.

No shared-file edits. Lane-31 files (`pc_p2_waterwraith_register.*`,
`pc_p2_waterwraith_host.*`, `pc_p2_waterwraith_visual.*`, all
`tools/p2_waterwraith_*` runners) were used read-only and never modified.

## Commits (private branches, clean trees)

Root `codex/muse-l63-waterwraith` (base `72a2c450`):

1. `9cd4bc76` — lane63: Waterwraith autonomous-movement observer +
   fail-closed tests (#503).

Native `codex/muse-l63-waterwraith-native` (base `7b9ecaa6`):

1. `efeb6aa3` — lane63: actor-owned escape-chase/pod/cadence driver +
   BIRTH/STEER markers + log checker (#503).

## What changed and why

Demonstrated gap: locomotion target selection lived outside the actor. The
register seam fed a fixed one-waypoint route and the actor walked it blindly;
`beginEscape` never armed the source chase axis (`mEscapePhase = 2`,
`isTyreDead`, `:4060`); the escape bands, smoothing (`:926`), pod motion
choice (`:930-953`), cadence (`:997-1007`) and turn damping (`:1024-1027`)
had no portable implementation. The actor now owns all of them; the seam
route survives only as the last-resort fallback the source keeps for the
map-graph leg.

Source-correct details (all cited to `blackMan.cpp` at research `632af937`):

- `beginEscape` arms chase (`mEscapePhase = 2`, timer cleared).
- Chase bands on squared captain distance: beyond 800 stand Wait, 400-800
  Walk at `fp11`, inside 400 Run at `fp02` with the escape timer; past `ip05`
  the actor winds down to Tired. Chase speed smooths toward its target at
  0.2 per tick; chase rotation uses `fp03`/`fp04`.
- Pod approach steers to the Pod with `fp01` and requests Through inside 100
  else Move. The encounter reports `podValid=false` because the P1 economy
  exposes no live Pod position; the branch is engine-free verified.
- Route cadence: 60-tick cooldown, within 10 of the last route position the
  120-tick timer arms and `routeRefreshRequested` asks the seam for the next
  waypoint (the documented stand-in for `findNextRoutePoint`).
- Turn damping halves planar velocity while turning, before integration.
- Start-phase snap re-adopts the start parm while the roller is attached.

## Build evidence (leased private build)

- `output/muse-wave/l63/build-1789526809932668700.log`
  (`sha256 5ea3f61c2c386bb65d5d88015975593d934ce971599807188c34f3390d1cac25`):
  configure + `pikmin_pc` build exit 0 (616/616 linked) at native
  `efeb6aa36ad4c0f2dbbf614ce37e147eb45ba6c5` (clean) in
  `output/msw/native-l63-build`; `ninja -n` prints `ninja: no work to do.`
- Executable `output/msw/native-l63-build/bin/nectar.exe`
  (`sha256 f350a871eae6805869298660e7d7e963ba66fc8227b584af8f1768a5fca7ab0f`).
- Encounter fixture `output/muse-wave/l63/encounter-fixture-3`
  (`provenance.json` status `built`) rebuilt against the same native head
  with the worktree `scripts/build_pikmin2_fixture.py` (the script carries
  the rsp-expansion path; the older main-checkout copy rejects current
  Ninja link lines — reported, not patched);
  `fixture.exe`
  (`sha256 840d7d16b37738407e39c771abf0c80aba18c9bead315ba0dfd48b09ca782100`).
  Two earlier attempts are recorded as `rejected` in
  `encounter-fixture/provenance.json` and `encounter-fixture-2/provenance.json`
  (stale script copy, then reused output dir); no executable was produced
  from either.

## Fixture adoption (mandatory baseline)

- Squad: fresh private arena generated by the current
  `scripts/preview_pikmin2_room.py` overlay (`ensure_pikmin_squad` present at
  `scripts/preview_pikmin2_room.py:66,99` in this worktree); the run log
  records `[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20
  isolated=1` — 20 live red Pikmin, no immediate extinction.
- Window: `P2_WATERWRAITH_ENCOUNTER_WINDOW size=960x540` with
  `PIKMIN_P2_ROOM_WINDOW=960x540`; the fixture replacement main centers the
  window after init and the native default (`pc_port/pc_main.cpp:130-131`)
  applies to room-preview launches. `SDL_AUDIODRIVER=dummy` for the
  unattended run.
- Visuals: own `output/muse-wave/l63/visual-stage` (16 clips / 44 poses)
  staged from the verified lane-31 import directory (read-only input);
  converted room, actor profile with Pod/economy anchors and Purple stage
  reused read-only from `output/dsw/l31-out/`.
- Run: `output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5`
  (`verification.json` status `passed`, outcome `delivered`,
  `ENCOUNTER_PASS stuns=1 hits=55 crushes=18 damage=3300.0 ... delivered=1`,
  plain `PASS WATERWRAITH_ENCOUNTER_RUNTIME` with no assist marker).

## Natural vs injected, scope limits

The fixture only arranges live squad Pikmin near the registered actor and
converts three to Purple; all movement, combat, death, corpse, carry and
teardown are driven by the real engine tick. No state, HP, Transport, kill
or credit was injected; the observer and checker emit no markers. Staged
elements reported honestly: fixed placement profile (not a generated slot),
8-Pikmin staged squad, Pod chase branch unverified live (`podValid=false`).
The chase window in this run is brief (ticks 55-63: the exposed body is
zeroed at tick 62 by the natural combat chain), and Tired/route-refresh did
not fire inside it; they are engine-free verified (policy sim
`sim_chase_tired`, `sim_route_cadence`) and remain runtime-open.

## Concrete source ID

- Source ID: 99 `BlackMan` (Waterwraith); 98 `Tyre` is the helper roller
  (no independent gate table, not seeded).

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:892 fixed-encounter birth observed; generated triple open with muse-placement l52 | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:897 actor-owned route leg; stdout.log:959 actor-owned captain chase walk; stdout.log:972 chase travel accumulates | natural |
| 3. Attacks and receivers | PASS (natural) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1153 stuns=1 hits=55 crushes=18 damage=3300.0; docs/PIKMIN2_LANE31_DEEPSEEK_HANDOFF.md accepted gates 3-6 preserved | natural |
| 4. Death and corpse | PASS (natural) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:977 body zero; stdout.log:980 corpse registered; stdout.log:982 teardown | natural |
| 5. Actual transport and reward | PASS (natural) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1147 receipt generator=0 deliveries=1; corpse:waterwraith:0 value=2 | natural |
| 6. Cleanup and re-entry | PASS (natural) | output/muse-wave/l63/encounter-run-2/5c19c98038f342b78d70ba275c3ed1f5/stdout.log:1152 re-entry ready=1 attached=1 | natural |

## Tests run

- `py -3.12 -m unittest tests.test_pikmin2_muse_waterwraith` — 13/13 pass.
- Standalone policy sim (ignored `output/muse-wave/l63/tmp_policy_sim.cpp`,
  engine-free, labeled as such) — 7/7 groups pass: birth hold, route
  fallback, escape arming, chase bands, chase-to-Tired, pod approach, route
  cadence.
- Lane-31 actor regression `tools/p2_waterwraith_actor_test.cpp` used
  read-only (never edited) against the modified sources — 15/15 groups pass,
  including `actor_exposed_body_damageable`,
  `actor_dismounted_body_nonpurple` and `actor_natural_lifecycle`.
- `tools/p2_waterwraith_attack_policy_test.cpp` — PASS.
- Standalone log checker `tools/p2_muse_waterwraith_fixture.cpp` — exit 0 on
  the natural run log, exit 1 on a route-only log.

## Generated-placement hook (specified, not implemented)

For source 99, ordinary generated admission needs the same correlated triple
the observers verify: a placement slot/generator leg, a seed resolve with
`source_id=99`, and an actor bind to the same generator file id. Owned by
muse-placement (l52/#492); this lane consumes that contract when published
and claims nothing generated here.

## Remaining work

- Generated-spawn triple for 99 (consumer of l52); pod-live chase once a Pod
  position source exists; longer Tired/cadence runtime window.
- Review of this candidate by the live integrator.
