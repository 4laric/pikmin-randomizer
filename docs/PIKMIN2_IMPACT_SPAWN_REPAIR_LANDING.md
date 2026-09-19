# Impact spawn-repair landing (#756)

Lane `impact-spawn-repair-landing` (generation 2). Owner: Codex through shared
account `4laric`. Coordinator consumer-repair for the stopped consumer
`p1-challenge-impact-runtime-acceptance` (#565, gen 4): #745 proved squad
spawn but never handed it off (owner gone). No live handoff owner exists.

## What was re-verified (read-only, this turn)

Committed #745 (native `2e54daf9` on fork branch
`codex/autofill-impact-squad-spawn-repair-native`, base `8b9d8992`; root
`49f3ba3a` on origin same-name branch, base `ecf5f53a`): both commits present
in their repositories, both branches exist locally and remotely.

Evidence bundle, hash-identical to the #745 report:
- Fixture exe sha256
  `3d5fe18a5b6398019017ae58017f1bffb9bdb91c76ab2b71de38d9d9d3ec21a3`.
- Headed chal0 run log sha256
  `2ce41e11f88812bb016b97e7114ca0ec03a8976132395a4bab1d4629fd0df145`
  (50,826 bytes): `P2_CHALLENGE_PARK_ALIVE pikis=21`,
  `P2_CHALLENGE_SQUAD pikis=40`, `P2_CHALLENGE_BOOT level=0 slot=chal0`,
  `PASS P2_CHALLENGE_GUARDED_BOOT boot1 squad_alive`, no captain-down and
  no extinction markers anywhere in the file.

## Files owned (all new, additive; #745 read-only)

- `experimental/pikmin2_impact_spawn_repair_landing.py` - pinned hashes plus
  `validate_log` (spawn/boot markers, captain-down/extinction rejection) and
  `verify` (hash + marker re-verification of the live bundle).
- `tests/test_pikmin2_impact_spawn_repair_landing.py` - 7 tests (5 synthetic
  log cases + pinned-hash checks + live bundle verification). All pass.
- `docs/PIKMIN2_IMPACT_SPAWN_REPAIR_LANDING.md` - this file.

## Six gates (honest)

All six runtime gates UNTESTED. Proven facts are spawn + boot only
(PARK_ALIVE 21, SQUAD 40, BOOT, PASS); they are not gameplay acceptance.
No duplication of #745 files, no family/shared/native edits, no runtime,
no ADMIT, no ledger writes.

## Packet

`out/impact-spawn-repair-packet.json` names exact commits/hashes and the
downstream consumer `p1-challenge-impact-runtime-acceptance` (#565, gen 4
blocked): the single-writer integrator may apply the #745 evidence to that
consumer on receipt.
