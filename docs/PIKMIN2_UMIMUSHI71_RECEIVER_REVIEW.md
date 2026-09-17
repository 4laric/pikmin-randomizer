# UmiMushi71 receiver registration review (issue #662)

Lane `enemies-6-umimushi71-receiver-review`. Implementation owner: Codex
through shared account 4laric; executing contributor Muse Spark 1.3.
Prescribed by the #648 pin-audit verdict item 3 for stranded
`shard-enemies-6-umimushi71-observer` (#374, BLOCKED). Verdict items 1-2
(death/corpse + cleanup/re-entry runs) stay #374-owner business. Read-only
review; no runtime, no native build, no shared edits, no ADMIT. All six
gates UNTESTED. This answers the #374 lane's stated dependency from the
UmiMushi side without touching that lane.

## 1. Evidence reviewed (read-only)

- #648 pin-audit anchors (retail, verbatim line citations):
  - `umiMushiState.cpp:510` `StateAttack::exec` — tongue-latch attack
    (`mIsTongueActive` at :512).
  - `umiMushiState.cpp:606` `StateEat::exec` — swallow at animation end
    (`KEYEVENT_END` at :608).
  - `umiMushi.cpp:467` `Obj::damageCallBack` — receiver entry (bittered
    guard at :469).
  - `umiMushi.cpp:843` `Obj::isChangeNavi` — captain-change routing, checks
    `mBloysterType == EnemyID_UmiMushiBlind` at :845.
- Native `pc_p2_umimushi.cpp` (read-only reference checkout): latch/attack
  paths exist and are marker-observed - `P2_UMIMUSHI_EAT generator=<gen>
  pikmin=1` (exactly one InteractKill per captured Pikmin at :825),
  flick/Navi legs (:239/:247/:256), forget accounting
  (`pc_p2_umimushi_forget`, :518-520), module reset (:512-516).
- Completed-family comparison (same checkout): Sarai emits
  `P2_SARAI_CORPSE_READY ... receipt=corpse:sarai:<gen>`; Kurage emits
  `P2_KURAGE_CORPSE_READY ... receipt=corpse:kurage:<gen>`. UmiMushi emits
  `P2_UMIMUSHI_DEAD generator=<gen> source_id=<71|101> health=0`
  (`pc_p2_umimushi.cpp:680-681`, beside the UMI_DEAD transition at :685)
  but NO `P2_UMIMUSHI_CORPSE*` marker and NO `receipt=corpse:umimushi:`
  token. Therefore a natural UmiMushi death can never reach the Pod receipt
  ledger today. The blind identity (101) shares the same death path
  (`s.sourceId` at :681), so one registration covers both.

## 2. Exact additive registration (mirrors the TEKI_Mar pattern)

Receiver present in source but unregistered in the routing table:

1. In the death path that emits `P2_UMIMUSHI_DEAD` (beside `setState(...,
   UMI_DEAD, "dead1")` in `pc_p2_umimushi.cpp`), emit once per natural
   death: `P2_UMIMUSHI_CORPSE_READY generator=<gen> source_id=<71|101>
   receipt=corpse:umimushi:<gen>`.
2. Track corpse registrations (actor -> generator) with cleanup in
   `pc_p2_umimushi_forget` and the module reset, mirroring the sarai
   `corpses` set, so a forgotten/recreated actor cannot double-report.
3. **Family-owner review REQUIRED before any shared edit**: the
   `corpse:umimushi:` receipt namespace touches the shared Pod ledger;
   route through the existing shared-review path, never silently.

## 3. Checker and tests

- `experimental/pikmin2_umimushi71_receiver_review.py` - reusable
  evidence checker: correlates bindings/deaths/eats per source id,
  detects corpse/receipt registration, rejects injected markers, and
  otherwise prints the exact registration above. Read-only; emits nothing.
- `tests/test_pikmin2_umimushi71_receiver_review.py` - 6 focused tests
  (full log, partial log, blind identity, injected markers, wrong source,
  empty log), all passing.

## 4. Downstream scope for #374 (recorded for the publication reviewer)

Consumer: `shard-enemies-6-umimushi71-observer` (issue #374) verdict items
1-2 (death/corpse + cleanup/re-entry runs). Once the registration above is
reviewed and implemented by its owner, that lane can re-observe natural
death against a real `receipt=corpse:umimushi:` token instead of failing
closed. Verdict items stay #374-owner business; this review performs none
of them.

All six runtime gates UNTESTED here. No ADMIT. Shared findings via #186
review draft only.
