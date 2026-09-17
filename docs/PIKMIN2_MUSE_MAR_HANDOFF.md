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
