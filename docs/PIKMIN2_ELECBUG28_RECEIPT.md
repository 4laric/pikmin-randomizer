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

## Runtime status (fresh, this slice)

Two leased runs of the private replacement-main receipt fixture, same seed
`b0776d86120acdd6caf81a95965e45245e69061eb061cc89ff034b1f16228f10`, one
shared session ledger (`campaign/p2-delivery-receipts.txt`,
`output/workflow/autofill/enemy-elecbug28-receipt/runs/campaign/`):

- run1 `runs/run1/17f3886b3ecf4338a3e0fcfc7d115e5b/` (`capture/native.log`
  sha256 `9a76173c42a8bf1017a525ff59e45d93234dcd8229271d1bd09819fbb16a3312`):
  `P2_ELECBUG_DELIVERY_BIND generator=346002 source_id=28`,
  `...=346010...`, `P2_ELECBUG28_FLIPPED tick=195`,
  `P2_ELECBUG28_DIED tick=314 health=0.00`,
  `P2_ELECBUG28_CORPSE pellet=1 tick=411 deployed=19`,
  `P2_ORDINARY_P2_RECEIPT seed=b0776d86... id=onion:p2:28:0 generator=346002 new=1`,
  `P2_ELECBUG28_DELIVERED_TO_GOAL tick=957 moved=557.50`.
- run2 `runs/run2/b08a14f8532c42e7baabf7c4bb5ff26d/` (`capture/native.log`
  sha256 `9ad54a2688d74dc15f705725d4291bb77264bc695526c0b0e29fea54e752626f`):
  `... id=onion:p2:28:0 generator=346002 new=0`.
- Window `Experimental preview window set to 960x540 windowed and centered`;
  20-Pikmin starting squad; no `Extinction` in either log.
- Fixture `fixture-session/fixture.exe`; private build
  `output/autofill-native-585-build` at native `b687dba9` (clean),
  `nectar.exe` sha256 `e72ed7d10bea05d8ed1dfb97691d12deae389d02fd70f0dc28cab98ef0dc9576`.

Honesty boundary (same standard the integrator applied to #578): the arena is
a private instrumented replacement-main course and the fixture enables the
randomizer session itself, so this is **fixture-staged**, not natural story
gameplay. The receipt line is real and the death/corpse/haul are natural
inside the arena, but gate 5 `transport_reward` is therefore **not** claimed
as a natural gameplay PASS here; it is left UNTESTED (staged) for the
integrator's ruling exactly as #578 was. The staged Purple press is labelled
`flip=staged-press`. `haul alone never closes transport`; the receipt line is
required, and it was observed.

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
