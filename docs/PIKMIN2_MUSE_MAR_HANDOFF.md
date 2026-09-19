# Muse Mar29 (Puffy Blowhog) death/corpse/transport/re-entry observer - handoff (#375)

Lane `shard-enemies-2-mar29-observer`, issue #375, generation 4. Implementation
owner: Codex through shared account `4laric`; executing Muse Spark 1.3
Contributor. Setup repair #631: native provisioned at
`output/native-mar29-repair631`, pin
`e44b5d70f9a7c029682194d9b45ae2e9b8fd6fd1`. Outcome: **BLOCKED** on a native
receipt dependency for `transport_reward`; gates 1/2/3 preserved, `death_corpse`
and `cleanup_reentry` specified, no ADMIT and no ledger writes.

## What this lane must close

Mar (Puffy Blowhog, source ID 29) is a concrete spawnable enemy natively
implemented at `pc_port/pc_p2_mar.cpp` (`pc_p2_mar_setup/update/forget/reset`),
spawned as **`TEKI_Mar`** by `pc_port/pc_p2_batch3.cpp`. Required gates:
`death_corpse`, `transport_reward`, `cleanup_reentry`, following the merged
`armor15-death-transport-reentry-observer` precedent.

## Verified blocker (transport_reward cannot be closed on this base)

The armor15 precedent closes transport through the **generic Pod corpse credit**
in `pc_port/pc_p2_preview.cpp`. That path only resolves two ways:

1. `pc_p2_preview_rebind_corpses()` (line ~113) registers **only**
   `enemy->mTekiType==TEKI_Chappy` actors into the `corpses` map.
2. The delivery chain (`pc_p2_preview_deliver`, line ~383) falls through
   per-species `pc_p2_*_receipt()` hooks and finally the `corpses` map; an
   unknown `mPelletView` hits the `std::abort()` branch
   (`Unregistered P2 pod cargo ... refusing seed side effects`).

Mar is `TEKI_Mar`, so it is neither registered by the rebind scan nor covered by
any `pc_p2_mar_receipt()` (none exists: `rg -i mar_receipt` over `pc_port/`
returns nothing). A natural Mar corpse delivered to the Pod therefore reaches
`std::abort()` — it cannot produce `P2_POD_RECEIPT id=corpse:...:<gen>` without a
native change.

Mar does leave a carcass in source terms (`docs/PIKMIN2_FLYING_REMAINDER_ASSETS.md`
line 177: "Mar/Hanachirashi have no `carcass_config` entry; default enemy corpse
physics apply"), so the missing piece is the **receipt/registration hook**, not
the corpse itself.

### Required dependency (needs existing-owner review before any family change)

Closing `transport_reward` requires an additive native change outside this lane's
four owned files, and the brief forbids family edits without existing-owner
review ("propose the contract instead"):

- Family: add `bool pc_p2_mar_receipt(PelletView*, unsigned& generator)` to
  `pc_port/pc_p2_mar.{h,cpp}` returning the bound `TEKI_Mar` generator for a
  delivered corpse, mirroring `pc_p2_armor_receipt`/`pc_p2_kurage_receipt`.
- Shared: register that hook in the `pc_p2_preview_deliver` chain and admit
  `TEKI_Mar` in the corpse rebind scan (`pc_port/pc_p2_preview.cpp`).

Both files are read-only here (`pc_p2_mar.*` is family-owned; `pc_p2_preview.cpp`
is shared). This lane therefore proposes the contract and stops.
## Six-gate status

| Gate | Status | Evidence | Method |
|---|---|---|---|
| 1. identity_spawn | PASS (natural, preserved) | `P2_MAR_BIND generator=... source_id=29` / `P2_ENEMY_READY species=Mar` emitted by `pc_p2_mar_setup` (`pc_p2_mar.cpp:422-431`); preserved, not relabelled | natural |
| 2. movement_animation | PASS (natural, preserved) | `P2_MAR_STATE` Wait/Move/Chase + `P2_MAR_POS ... clip=` (`pc_p2_mar.cpp:465-541`); preserved | natural |
| 3. attacks_receivers | PASS (natural, preserved) | `P2_MAR_BLOW generator=... pikmin=N` at the source attack frame (`pc_p2_mar.cpp:270-277`); preserved | natural |
| 4. death_corpse | SPEC (not run this turn) | death path `P2_MAR_DEAD ... health=0` then `actor->die()` (`pc_p2_mar.cpp:450-457,530`); corpse via default enemy corpse physics | natural |
| 5. transport_reward | BLOCKED | no `pc_p2_mar_receipt`; `TEKI_Mar` absent from rebind + deliver chains (`pc_p2_preview.cpp:113-124,382-386`); delivery aborts | dependency |
| 6. cleanup_reentry | SPEC (not run this turn) | `pc_p2_mar_forget`/`pc_p2_mar_reset`/`pc_p2_mar_setup` re-bind on generator rebirth | natural |

Gates 1/2/3 are cited from the merged family implementation and are preserved
as-is; they are never upgraded or relabelled by this lane. Gates 4 and 6 are
specified against the same additive-observer method as armor15 but were not run
because gate 5 is hard-blocked and a delivery attempt aborts the process.

## Additive observer contract (owned files)

- `experimental/pikmin2_muse_mar.py`: marker regexes, `validate()` (dependency-free
  run-log reader) and `dependency_report()`; the reader REFUSES any log carrying
  `P2_MUSE_MAR_INJECT`/`P2_LIFECYCLE_INJECT` and any log claiming a Pod receipt
  for a Mar generator while the receipt dependency is unresolved.
- `tests/test_pikmin2_muse_mar.py`: negative tests (injected receipt rejected,
  missing `P2_MAR_DEAD` rejected, proxy carry rejected, duplicate delivery
  rejected) plus `dependency_report()` assertions.
- `native/tools/p2_muse_mar_fixture.cpp`: additive `RoomApp` observer (no
  `mHealth`/`TransportMode` writes) that adopts `scripts/p2_fixture_captain_guard.h`
  captain safety (#632), observes natural death by real squad Attack orders,
  observes the corpse if present, and emits `BLOCKED transport=missing_receipt`
  rather than attempting an aborting Pod delivery.
- `docs/PIKMIN2_MUSE_MAR_HANDOFF.md`: this document.

## Build / run provenance

No build or runtime run was performed this turn: gate 5 is hard-blocked and the
Pod delivery path aborts, so a leased build would only reproduce the abort. The
fixture and module are committed as the proposed host shape and are **unbuilt /
unrun**; `fixture_adoption` is labelled accordingly, not adopted.

## Captain safety (#632)

`native/tools/p2_muse_mar_fixture.cpp` includes and calls
`p2_fixture_require_captain(orimaDead, NaviDead, hp, tick)` before observation
ticks, emitting `P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED` and exiting 86.
The captain is parked outside Mar attack reach for the duration; no blanket
invincibility is used.

## Residual / next

1. Existing-owner review approves the `pc_p2_mar_receipt` + preview
   registration contract above.
2. Re-run this lane (gates 4/5/6) on a leased build with the starting-Pikmin
   overlay and 960x540 adoption; emit the six-gate handoff and checker EXIT=0.
3. Hanachirashi (55) and ShijimiChou (77) remain; admission still denied.

## Generation 5 reassessment (armor15 prerequisite integrated)

A prerequisite carries new verified integration evidence:
`armor15-death-transport-reentry-observer` (#165), root `0eccc77c`, native
`b1c5a1d4`, validation
`output/workflow/autofill/armor15-death-transport-reentry-observer/integration-validations.log`
(sha256 `baecf1ae...5f`). Reassessed against the Mar29 blocker:

- Root `0eccc77c` is a single-file export: `engine/tools/p2_muse_armor_fixture.cpp`
  (+136). Native `b1c5a1d4` is the matching single-file merge:
  `tools/p2_muse_armor_fixture.cpp` (+136). Neither commit touches
  `pc_p2_preview.cpp`, any `pc_p2_mar.*` family file, or any receipt/registration
  path. Neither is an ancestor of this lane's pins, but that is immaterial: the
  prerequisite contains no Mar-relevant change.
- The necessary prerequisite set for the Mar29 slice is therefore EMPTY. No
  merge, no conflict resolution, and no duplicate observer were created.
- The `transport_reward` blocker is UNCHANGED: TEKI_Mar still has no
  `pc_p2_mar_receipt`, and the generic Pod corpse path still registers only
  TEKI_Chappy with an abort fallback. The required dependency remains
  existing-owner review of an additive `pc_p2_mar_receipt()` plus a
  `pc_p2_preview.cpp` registration (tracked on #186).

Lane stays blocked on `4laric/pikmin-randomizer#186`. No runtime run, no ADMIT,
no ledger writes.

## Generation 6 reassessment (mar29-pod-dispatch-candidate #665 integrated)

A second prerequisite carries new verified integration evidence:
`mar29-pod-dispatch-candidate` (#665), root `6d9da34b`, **native `null`**,
validation
`output/workflow/integration-recovery/species-owner/hooks-665-666-batch-validation.log`
(sha256 `75d8e568...c2`), source worktree
`output/workflow/autofill/prerequisites/mar29-pod-dispatch-candidate-root`.

This is the first prerequisite that is Mar-relevant, so it was inspected in
full. Finding: it is a **root-only decision packet, not a landed change**.

- The prerequisite commit `117b5ade` adds exactly three new root files:
  `docs/PIKMIN2_MAR29_POD_DISPATCH_CANDIDATE.md`,
  `experimental/pikmin2_mar29_pod_dispatch_candidate.py`,
  `tests/test_pikmin2_mar29_pod_dispatch_candidate.py` (+304). It edits no
  `pc_port/` file; `native_commit` is null.
- The packet's own doc and its #186 decision record say the arm is
  **APPROVED but must be re-derived** onto the current native-wave preview: the
  candidate preview blob (`sha 14607674...`, base `7b9ecaa6`) is stale and
  **lacks the Queen receipt arm** (`pc_p2_queen_teki.h` include,
  `pc_p2_queen_teki_receipt` dispatch arm, `pc_p2_queen_teki_name` term), so
  landing it verbatim would regress Queen. `186-decisions-gen45.md` line 42:
  "Do NOT commit the stale candidate blob."
- The adapter `pc_p2_mar_receipt.{h,cpp}` is **absent from the species native
  line**; `186-decisions-gen45.md` lines 17-19 assign its landing to
  `mar-native-registration-668` (#668).

### Verified against this lane's pins (native e44b5d70)

- `pc_p2_mar_receipt` is ABSENT from `pc_port/pc_p2_preview.cpp`; no
  `pc_p2_mar_receipt.*` exists in the native tree.
- The same preview already carries `pc_p2_queen_teki_receipt`,
  `pc_p2_long_legs_receipt`, `pc_p2_groink_receipt` and the
  `pc_p2_kurage_teki.h` include — i.e. the modern multi-arm chain the stale
  candidate would clobber.
- Registry: `enemies-2-mar29-receipt-provider` (#650) is `done` and **NOT
  integrated**; `mar-native-registration-668` (#668) is `waiting_resource`.

### Conclusion: dependency NOT cleared

No accepted native change can be brought into this lane's private worktrees.
The #186 decision approves the dispatch arm in principle but explicitly defers
landing to the single writer, requires a re-derivation, and requires the #668
adapter to land first. Applying the stale candidate blob here would be a
forbidden shared source edit **and** would regress an already-integrated arm.
Per the standing rule ("clear a dependency only with recorded supporting
evidence"), the transport dependency remains open.

Concrete remaining gap (in order):

1. `mar-native-registration-668` (#668) lands the #650-owned
   `pc_p2_mar_receipt.{h,cpp}` adapter + fixture on the native line.
2. The single-writer integrator re-derives the #186-approved 4-line additive
   `else if(pc_p2_mar_receipt(...))` arm directly after the longlegs arm in the
   current `native-wave` `pc_p2_preview.cpp`, keeping every existing arm
   (Queen included) intact.
3. Leased rebuild + guarded GL fixture run (captain safety #632); only then may
   #375 claim `transport_reward` and re-run gates 4/5/6.

Lane stays blocked. No shared source edit, no merge of the stale blob, no
duplicate observer, no runtime run, no ADMIT, no ledger writes.

## Generation 7 reassessment (mar-native-registration-668 integrated) - runtime slice

A third prerequisite landed a real native change:
`mar-native-registration-668` (#668), root `c20a22ec`, **native `07b46063`**,
validation
`output/workflow/integration-recovery/species-owner/mar668-batch-validation.log`
(sha256 `fcd96dd6...e2`), native worktree
`output/workflow/autofill/prerequisites/mar-native-registration-668-native`.

### Prerequisite merge (accepted change brought into this private worktree)

`07b46063` descends from this lane's native pin `e44b5d70`, and it touches no
file this lane's fixture owns, so it was merged into the private native
worktree `codex/mar29-repair631` (merge commit `bc8cc270`). Verified present
after the merge: `pc_port/pc_p2_mar_receipt.{h,cpp}`, the Mar dispatch arm plus
the Queen arm in `pc_port/pc_p2_preview.cpp`, the `pc_p2_mar.cpp` receive hooks,
the CMake test target, and this lane's `tools/p2_muse_mar_fixture.cpp`.

### Upstream integration defect found (fixed privately, needs re-land)

The accepted native commit `07b46063` **does not compile**. The Queen-preserving
merge resolution left a duplicate closing brace at `pc_port/pc_p2_preview.cpp`
line 386 (immediately before the `else {` corpse fallback), which breaks the
receipt `else if` chain. The producer commit `780de444` is structurally correct,
so the defect was introduced by the integration resolution; the #668 integration
"ran no new native build (no toolchain on PATH)" and therefore never caught it.
Reported to #186/#668 for re-land.

Private unblock (commit `645c0a49`): removed the single duplicate brace. No
semantic change - this restores the #186-approved chain placement. Nothing else
in the accepted change was altered.

### Runtime slice (leased private build + guarded GL run)

- Native build: `output/mar29-repair631-build`, configured Ninja + MinGW
  (Release, JAUDIO=ON, OPTIMIZE=OFF); `pikmin_pc` build initially FAILED on the
  duplicate brace above, then linked `bin/nectar.exe` SHA-256
  `56e1979471fccbf5f8bd634bf5c01421f02bb2b65c08431cbf84c4ee0e180b89`.
- Fixture: spliced `room.cpp` -> `output/mar29-fixture1/fixture.exe` SHA-256
  `24d122c1c50442c34d878bd6be826bfd8826b4e305bf07728ae27ed03e259c93`
  (`{"status": "built"}`).
- Arena assets: GPVE01 flying bank freshly extracted to
  `output/mar29-flying-out` (`flying.json` sha `9b9d9e13...`); batch-3 flying
  arena + a staged pr05 Pod cargo for the corpse dispatch.
- Run: `output/mar29-run/f3beffa386d2486cb92af70f0171c37a`, exit 1,
  `native.log` SHA-256
  `8c2eedc3167b05e83d022782050d8cde42ed3fb1c87e0ad475fd88fc287e30d3`.
- Captain safety #632: `scripts/p2_fixture_captain_guard.h` adopted
  (`p2_fixture_require_captain`); the run exited clean, no
  `P2_FIXTURE_CAPTAIN_DOWN`, policy = unprotected observation, no blanket
  invincibility.

Observed: `P2_MUSE_MAR_READY squad=20`, `P2_MAR_BIND generator=375001
source_id=29`, live wait/move/chase states, 41-52 real `P2_MAR_BLOW` wind
events, `P2_ENEMY_READY species=Mar`, 960x540 window, `no_inject=1`,
`captain_safe=1`. The fixture then hit `FAIL P2_MUSE_MAR drain_timeout`.

### Concrete remaining gap: Mar is not attackable on the ground contract

`PC_MAR_HP` stayed at `health=3000.00` with `atk=20` for the whole run (0 drain
events) even after the fixture was changed to place the attacking squad at
Mar's own altitude (commit `7c8311b6`) and re-run. Root cause:
`pc_p2_mar_param_f` (`pc_port/pc_p2_mar.cpp:305-314`) returns `0.0f` for
`TPF_AttackableRange` / `TPF_AttackableAngle` / `TPF_AttackHitRange`, and the
engine computes the Pikmin attack window as `getAttackableRange() + 1.0f`
(`src/plugPikiNakata/tekibteki.cpp:1328`). With a range of ~1 unit, a grounded
squad cannot connect with the airborne P1 Mar (source flight height fp01=80,
and Fall/Land/Ground are documented bounded gaps, so it never lands).

Therefore `death_corpse`, `transport_reward` and `cleanup_reentry` cannot be
closed naturally. Per the brief, no `mHealth`/HP injection was used and none
will be, so gates 4/5/6 stay open. Clearing this needs an existing-owner review
of a family change: `pc_p2_mar_param_f` must expose the source attackable range
(or an equivalent accepted reach contract for airborne melee), tracked on #186
and the flying family issue #166. The #668 dispatch arm + adapter otherwise make
the transport path present and ready once Mar is killable.

Lane stays blocked. No injection, no ADMIT, no ledger writes, no shared-source
edit (the private brace fix is confined to this lane's worktree and is reported
upstream for re-land).

## Generation 8 (mar-attackable-build-evidence-native #687) - consumer verification

A fourth prerequisite landed the missing family change:
`mar-attackable-build-evidence-native` (#687), root `5ed68649`, **native
`b5a2611a`**, validation
`output/workflow/integration-recovery/species-owner/mar687-attackable-batch-validation.log`
(sha256 `dd9bade2...a3`). `pc_port/pc_p2_mar.cpp` now serves
`TPF_AttackableRange` (fp20 = 200) and `ATTACKABLE_ANGLE` (0.785398), plus
retail steering and landing-flag management. `b5a2611a` descends from `07b46063`
and its preview already carries the brace correction (matching the private Gen-7
fix), so it merged cleanly into the private native worktree (`31e2c40a`).

### Consumer verification: PASSED (prerequisite_resolved=true)

- Verification id `a0b1e493...`, consumer `shard-enemies-2-mar29-observer`,
  generation 8, recorded via `python -m workflow.consumer_verification`.
- Evidence (independent of the producer validation logs):
  `output/workflow/autofill/planning-shards/enemies-2/prepared/mar29-observer-output/mar29-consumer-verification.json`
  sha256 `e8c7f999...32`.
- Command: the Gen-7-independent observer run
  (`.../mar29-observer-output/run_mar29.py`) with `b5a2611a` merged into the
  private native worktree and the owned guarded fixture.
- Expected: the grounded squad lands natural damage (`P2_MUSE_MAR_HP`
  decreases, >= 1 event); the pre-fix Gen-7 run stayed at `health=3000.00` with
  0 drain for the whole run.
- Observed: **health 3000.00 -> 270.00 with 167 damage events**, squad=20
  atk=20, no `mHealth`/`TransportMode` write (`no_inject=1`), captain safe (no
  `CAPTAIN_DOWN`). The original 0-drain defect is resolved.
- Independent hashes: `native.log` `6d981e431b713db609205e9ec3003394e1bf2d27cd040aaaf057b09677ea0f33`, `fixture.exe`
  `7c8d639aef72bcfa16da9b37ea732549ff3574af7cf8e15475f06c785c0419bd`,
  `nectar.exe` (rebuilt on the merged tree, `[6/6] Linking`).

### Remaining gap (blocked, different from the resolved one)

The full natural kill did not complete: damage **stalled at 270.00 HP**
(events=167 unchanged from tick ~12690 to 22140, ~9400 ticks), naming no
state change and no injection. The P1-port Mar returns to source flight height
(fp01=80) between ATTACK windows, and the grounded squad cannot convert the last
~9% before the app exits (SDL window shutdown at ~742 s, exit 0, before the
40 000-tick timeout). Gates 4/5/6 (`death_corpse`, `transport_reward`,
`cleanup_reentry`) therefore remain open. The receipt/adapter path is present
and the attackable contract now works; closing the remaining gap needs either a
retail-faithful airborne-reach/landing cadence (family `pc_p2_mar.cpp`, #166) or
an accepted accepted-melee/throw technique for the owner fixture - tracked on
#186/#166.

## Generation 9 (mar-airborne-reach-technique #709) - natural kill completes

A fifth prerequisite delivered the airborne-reach technique:
`mar-airborne-reach-technique` (#709), root `c32ad57f`, **native null**,
validation
`output/workflow/integration-recovery/species-owner/mar709-airborne-batch-validation.log`
(sha256 `48230619...c2`). Root-only cadence contract
(`experimental/pikmin2_mar_airborne_reach_technique.py`): wait_for_chase,
preposition, throw_on_landing, swarm_attack, reclump, hold, complete_kill,
encoding the integrated #687 constants and the retail descent-landing rationale.
No native file is touched, so nothing was merged; the technique was executed in
the owned fixture.

### Fixture cadence (owned file only)

`native/tools/p2_muse_mar_fixture.cpp` now gates on Mar's height above ground:
outside TOUCHDOWN_BAND (> 12) it only logs `hold_between_windows`; inside the
low window it moves the captain onto the approach path, calls the engine's
`Navi::throwPiki` on every non-stuck / non-attacking Pikmin, re-parks the
captain, and logs `P2_MUSE_MAR_CADENCE action=throw_on_landing height=..
thrown=..`. No `mHealth` or `TransportMode` write exists in the fixture.

### Consumer verification: PASSED (prerequisite_resolved=true)

- Verification id `4750d514...`, consumer `shard-enemies-2-mar29-observer`,
  generation 9, recorded via `python -m workflow.consumer_verification`.
- Independent evidence (distinct from producer validations):
  `output/workflow/autofill/planning-shards/enemies-2/prepared/mar29-observer-output/mar29-consumer-verification-9.json`
  sha256 `84480fc6...ea`.
- #709 adapter (`validate_technique.py` against the accepted adapter):
  `preconditions`, `reachable` (18 ATTACK windows), `captain_guard`, `no_nan`
  all true, `cadence` valid (155 steps, 127 throws).
- Runtime: **natural kill completes** - health `3000.00 -> 0.00` with 155 damage
  events, `P2_MAR_DEAD generator=375001 source_id=29 health=0`,
  `P2_MUSE_MAR_DRAIN events=155 min=15.00 start=3000.00`, exit 0, `no_inject=1`,
  captain safe (`scripts/p2_fixture_captain_guard.h` adopted; no
  `CAPTAIN_DOWN`). The Gen-8 stall (270 HP) is resolved.

### Gate disposition

| Gate | Status | Evidence |
|---|---|---|
| 4. death_corpse | death PASS; corpse OPEN (source-backed N/A) | `P2_MAR_DEAD`, drain min=15->0, `injected=0`; no corpse pellet |
| 5. transport_reward | OPEN | no corpse pellet to carry/deliver on generator 375001 |
| 6. cleanup_reentry | PASS | `P2_MUSE_MAR_FORGET count=0 registered=0`, `P2_MUSE_MAR_REENTRY ... stale=0 fresh=1 count=1` |

### Remaining gap (blocked, different from the resolved technique defect)

The port Mar leaves **no corpse pellet**: the fixture scans `pelletMgr` for a
pellet whose `mPelletView` is the Mar actor for 9000 ticks after death and finds
none, so it emits `P2_MUSE_MAR_CORPSE pellet=0 ... source_backed_na=1` and skips
the carry/deliver stages (no null deref). `BTeki::die()` only sets `mDeadState`
and calls `pc_p2_otakara_died` (a no-op for Mar); corpse creation lives in
`dieSoon()` behind `TPI_CorpseType == TEKICORPSE_LeaveCorpse`, which the port's
`pc_p2_mar_param_f` does not serve. `transport_reward` therefore cannot be
demonstrated and stays open. Clearing it needs an existing-owner-reviewed family
or engine change (Mar corpse emission / `TPI_CorpseType`) plus the present #668
receipt arm - tracked on #166/#186. The kill path itself is now proven.

Lane stays blocked. No injection, no ADMIT, no ledger writes, no shared-source
edit.
