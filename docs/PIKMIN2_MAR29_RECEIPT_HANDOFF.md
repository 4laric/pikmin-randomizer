# Mar29 corpse receipt provider handoff (#650, downstream #375)

Lane `enemies-2-mar29-receipt-provider`, issue #650 (OPEN, assigned 4laric),
role implementation, heavy true. Owner: Codex through shared account 4laric.
This lane implements the missing TEKI_Mar corpse receipt path that blocks the
stranded observer `shard-enemies-2-mar29-observer` (#375, transport_reward):
family receipt adapter mirroring Sokkuri79 (#578) / ElecBug28 (#585), binding
the Mar29 corpse to an exactly-once ordinary receipt. No ADMIT.

## Problem (traced missing input)

#375 is blocked because TEKI_Mar has no `pc_p2_mar_receipt` and the Pod corpse
path (`pc_p2_preview_deliver`) registers only TEKI_Chappy-vehicled corpses via
its `corpses` map, aborting on any unregistered delivered corpse
(`pc_p2_preview.cpp` fallback). No producer for the Mar receipt path existed
(verified: no lane owns these files; receipt planner shard #606 is
generic-only). This lane is that producer.

## Deliverables (6 owned files, committed on private codex branches)

Root worktree `.../prepared/mar29-receipt-provider-root` @ `533e7f4a`:
- `experimental/pikmin2_mar29_receipt.py`: runner + checker (bind-once,
  corpse resolution, exactly-once ledger grant, natural haul with Pod
  deferred, injection/captain-down rejection) + preview splice helper.
- `tests/test_pikmin2_mar29_receipt.py`: 12 focused tests, all green.
- `docs/PIKMIN2_MAR29_RECEIPT_HANDOFF.md`: this file.

Native worktree `.../prepared/mar29-receipt-provider-native` @ `7b9ecaa6`:
- `native/pc_port/pc_p2_mar_receipt.{h,cpp}`: bind/resolve registry for Mar
  actors (idempotent bind, first-resolution `P2_MAR_CORPSE_READY`, forget/reset
  clearing, count/registered probes). No other lane module modified.
- `native/tools/p2_muse_mar_receipt_fixture.cpp`: RoomApp spliced into
  `tools/preview_p2_room.cpp`. Binds Mar generator 375001, registers via the
  adapter, kills by REAL squad Attack orders (no health writes), observes
  natural death + engine corpse, resolves via the adapter, credits exactly-once
  through the lane-06 receipt host (identity `enemy:29`), re-grants to prove
  Duplicate, observes natural haul, then exits BEFORE Pod goal entry (labelled
  `pod=deferred`) because the shared dispatch arm is pending #186 review.
  Captain guard (#632) runs FIRST after engine idle, before pause/movie/UI and
  all observation; captain parked 150u out; CAPTAIN_DOWN exits 86 BLOCKED.

## Shared hook requiring #186 owner review (NOT silently edited)

Registering TEKI_Mar in the shared `pc_p2_preview` corpse path needs the exact
dispatch arm plus include, submitted as a focused #186 request with
contract+hashes (see `../mar29-receipt-provider-output/p2-preview-mar-dispatch-186-request.md`).
Until approved, Pod delivery of a Mar corpse still hits the aborting fallback,
so gate 5 (transport_reward via Pod) stays BLOCKED. The adapter-level
exactly-once receipt + natural haul are proven without it.

## Acceptance status (honest)

- Adapter + fixture + runner/tests/doc implemented and committed; 12/12 root
  tests green; native standalone syntax check green (see below).
- Runtime floor-1 boot NOT yet run: leased private build + GL fixture run
  remain (exact commands recorded under Remaining work). All six gates
  UNTESTED except gate 5, which is BLOCKED on the #186 dispatch arm.
- No injected Transport/kill/credit anywhere; no shared-file edits; no ADMIT.
- Preserves #375 gates 1-3 (untouched files/evidence); gate 6 UNTESTED.

## Remaining work

1. #186 owner review of the dispatch arm (request filed with exact patch +
   hashes); on approval, apply the 5-line arm + include and rebuild.
2. Leased private build of the pinned native source in a private build dir
   (elastic cap; never `native/build-randomizer`); record exe SHA-256 +
   `ninja -n`.
3. GL fixture run with fresh arena + starting squad + 960x540 centred window +
   captain guard; validate the run log with
   `experimental/pikmin2_mar29_receipt.py`; submit the runtime handoff.
4. Downstream #375 then closes transport_reward via the Pod path.