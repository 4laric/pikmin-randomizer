# Catfish26 corpse->receipt registration (#652)

Lane `shard-enemies-5-catfish26-corpse-registration`, generation 2. Owner:
Codex through shared account `4laric`. Parent family work: legacy lane l16
(#167 Frog family) and the #641 receiver review, which names exactly this
registration. This implements that named additive registration; it does not
re-observe the family FSM.

## What changed (owned files only)

- `native/pc_port/pc_p2_catfish.cpp` (+19/-0): a `corpses` map
  (actor -> generator) plus a single `P2_CATFISH_CORPSE_READY
  generator=<gen> source_id=26 receipt=corpse:catfish:<gen>` emission inside
  the existing once-guarded natural-death edge (beside the `CATFISH_DEAD`
  transition), gated by `generator != 0` and by prior registration.
  `pc_p2_catfish_forget` erases the actor's entry; the module reset clears
  the set. No ledger grant, no reward computation, no save change; Houdai
  and all other families untouched.
- `native/tools/p2_catfish_corpse_registration_test.cpp` (new, standalone
  engine-free): contract model proving exactly-once registration, dark
  negative, forget-rebind, reset-clears and no-double-report. Compiles clean
  (`-Wall -Wextra -Werror`), exits 0.
- `tests/test_pikmin2_catfish_corpse_registration.py` (new): 11
  dependency-free run-log contract tests (full chain, partial registration,
  missing legs, mismatches, wrong order, injected rejection, captain-down
  block, empty). All pass.
- This file.

## Pins

- Root base `36b868391e62cccf37d992aa2f796f3cc9c6dc31` (tooling slice; root
  owns the test + doc only).
- Native base `ab81cf5d0fa1856f46cc80b527b7e184afec97eb` + repair commit
  (host registration).

## Shared receipt-namespace review

The `corpse:catfish:` receipt namespace touches the shared Pod ledger
contract. Routed to the existing family owner and #186 via a `shared_reviews`
entry (status requested) in the lane handoff; the owner decision is recorded
there when it lands. No ledger semantics changed by this slice.

## Gates (honest: enables, does not claim)

All six gates UNTESTED by this slice. It supplies the missing corpse
registration the #641 review proved was absent, enabling a future natural
receiver observation; that observation (with its own captain-safe run) is a
separate lane. No runtime/gameplay PASS claimed here. No ADMIT, no ledger
writes.

## Checks

- Standalone fixture: compiles clean, `ALL_FIXTURE_PASS`, exit 0.
- `py -3.12 -m pytest tests/test_pikmin2_catfish_corpse_registration.py -q`
  -> 11 passed.
- Private leased build (`pikmin_pc` + `ninja -n` dry run) with executable
  hash recorded in the lane handoff; fixture provenance for the checker.
