# ElecBug28 delivery bridge and exactly-once ordinary Onion receipt (#585)

Lane `enemy-elecbug28-receipt`, issue #585, parent #569, family parent #495.
Implementation owner: Codex through shared account `4laric`; executing worker
muse-l61 generation 3. This slice mirrors the proven Sokkuri79 receipt
implementation pattern (#578) for ElecBug (source 28). It is independent of
#578's unintegrated commits: it uses the pre-existing lane-06 ordinary
endpoint plus ElecBug's own family module.

## Reserved files

- `native/pc_port/pc_p2_elecbug.cpp` / `.h` (family delivery bridge)
- `native/tools/p2_elecbug28_receipt_fixture.cpp` (new replacement-main app)
- `experimental/pikmin2_elecbug28_receipt.py` (new runner/auditor)
- `tests/test_pikmin2_elecbug28_receipt.py` (new focused tests)
- `docs/PIKMIN2_ELECBUG28_RECEIPT.md` (this spec)

No shared file is edited: the lane-06 endpoint already exists at the pinned
native `ce89a039f3d37e2f6c551b7dbb32e0864115a56c`.

## Native delivery bridge (additive, mirroring the reviewed Sokkuri hunk)

- `pc_p2_elecbug_setup()` now calls
  `pc_randomizer_p2_bind_source(actor, 28, generator)` for each registered
  ElecBug and prints `P2_ELECBUG_DELIVERY_BIND generator=<uid> source_id=28`.
  Source 28 is in the generated bindable roster (`pc_randomizer_p2_roster.h`).
- `pc_p2_elecbug_forget()` now calls
  `pc_randomizer_p2_forget_source(actor)` first, so a recycled actor address
  can never inherit source 28; the central lane-07 forget seam also clears it
  (idempotent).
- The existing `pc_randomizer_p2_corpse_delivered` ordinary endpoint
  (`goalItem.cpp:363`) grants `onion:p2:28:<stage>` exactly once and consumes
  the binding; the P1-proxy bestiary check is not also credited.

## Scenario and honesty

- A paired 2-ElecBug roster lets the pair discharge naturally (Yellow parked
  in the sweep proves the lane-11 immunity).
- Death requires the source Reverse flip, because an unflipped ElecBug
  swallows every attack (source `init` invulnerability). The host has no
  Purple hipdrop state, so the fixture stages a Purple landing to trigger the
  family-local press adaptation. This is labelled `flip=staged-press`; it is
  a stimulus, not an enemy health/state write.
- After the flip, the free squad drains 500 HP through the real receiver and
  the beetle dies naturally; the corpse is grasped and hauled by free Pikmin
  to the room container, where `GoalItem::suckMe` fires the ordinary receipt.
- No enemy health/state write, no Transport assignment, no kill, no credit,
  no direct `suckMe` call, and no forget/re-entry in the run (the single-use
  bind must survive until delivery; re-bind is not scene re-entry).

## Acceptance mapping

- Bind source 28 with `P2_ELECBUG_DELIVERY_BIND` + idempotent forget
  clearance: native bridge above.
- Exactly-once `onion:p2:28` receipt (new=1 then duplicate new=0 across a
  process restart sharing the session ledger) with natural-carry markers in
  the same run: `pikmin2_elecbug28_receipt.py` `run_session` + `validate`.
- Honest six-gate evidence, no ADMIT: this document plus the handoff.

## Runtime status

The receipt runs are produced by `experimental/pikmin2_elecbug28_receipt.py`
(a private replacement-main fixture, released only with a validated
session ledger). Per the #578 integrator ruling, a fixture-staged private
course is **not** natural story gameplay: the receipt line is real and the
haul markers are natural inside the arena, but gate 5 `transport_reward` is
reported with the staged boundary made explicit and is left for the
integrator to rule, exactly as #578 was. `haul alone never closes transport`;
the receipt line is required.

## Verification

- `py -3.12 -m pytest tests/test_pikmin2_elecbug28_receipt.py -q` -> 15
  passed (synthetic logs only; no engine, session or retail assets touched).
- `check_ordinary_corpse_source` reads the read-only retail
  `src/plugProjectNishimuraU/ElecBug.cpp` and requires
  `startCarcassMotion`.

## Remaining / blocked

- Natural (non-fixture) story gameplay for gate 5 needs the randomizer
  session inside an ordinary campaign encounter, not a private instrumented
  course. This is the same blocker the integrator recorded for #578.
- Gate 6 scene re-entry stays UNTESTED.
- Shared cargo changes, if ever required, are a focused #491 request, not a
  lane edit.
