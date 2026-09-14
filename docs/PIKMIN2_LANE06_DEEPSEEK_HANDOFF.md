# Lane 06 — DeepSeek handoff (rewards/persistence)

Tracking: #441. Implementation owner: Codex through shared account `4laric`; executing agent: DeepSeek lane-06 session (this worktree). Worktrees:

- Root: `C:/Users/alari/pikmin-randomizer/output/dsw/l06-root` — branch `deepseek/p2-l06`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`.
- Native: `C:/Users/alari/pikmin-randomizer/output/dsw/native-l06` — branch `deepseek/p2-l06-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`.

## Chosen slice

Provider slice. Lane 06 owns the shared reward/cargo/receipt interface; the still-open
ledger item is "connect one real P2 family drop through the ordinary Onion/AP endpoint
and prove no duplicate/lost reward across revisit/process restart" (host JSON dedupe and
injected Pod delivery do not pass; Pod/Poko kept separate).

This slice closes the **provider half** of that gap: a new engine-free `DeliveryReceiver`
that resolves a P2 family corpse to a durable ordinary reward identity distinct from the
P1-proxy Teki type it reuses, and grants it exactly-once over the existing
`pc_p2_receipt.h` ledger. One real consumer cohort (Snow + Dwarf Orange) exercises it
end-to-end at the interface level (native CTest + Python). The engine wiring that calls
this receiver from `GoalItem::suckMe` for a live P2 drop remains a lane-01 + family-13 +
real-GL integration step (explicitly out of scope for a provider lane; see blockers).

Consumer cohort (from `docs/PIKMIN2_ENEMY_ROSTER.json` / `pc_randomizer_p2_roster.h`,
both ids present and bindable):

| Identity | enum | source_id | native family |
|---|---|---|---|
| Snow Bulborb | YellowKochappy | 45 | Chappy (P1 `TEKI_Chappy` proxy, type 3) |
| Dwarf Orange Bulborb | BlueKochappy | 44 | Chappy (P1 proxy) |

Audit finding (drives this slice): both identities bind to a P1 `TEKI_Chappy` actor and
only override health/stun; they inherit the P1 Chappy corpse, so an ordinary Onion
delivery today maps by Teki type to the P1 check `Bestiary: Deliver Dwarf Bulborb`
(`goalItem.cpp:356-363` -> `pc_randomizer.cpp:710-718`, catalog keyed by `randomizerEnemyTypes[]`).
No P2 source_id appears anywhere in the bestiary/collection catalogs, and no module maps a
P2 source_id to the ordinary receipt ledger. This receiver supplies the missing identity
bridge without inventing checks or touching the shared bestiary catalog.

## Source IDs and files owned

- Native: `pc_port/pc_p2_delivery.h`, `tools/p2_delivery_receiver_test.cpp`,
  CMake test registration (small, separately committed labelled hook).
- Root: `experimental/pikmin2_delivery.py`, `tests/test_pikmin2_delivery.py`,
  `tests/test_pikmin2_receipt_native.py` (extended to compile/exercise the new header).

Reused (not modified): `pc_port/pc_p2_receipt.h` (ReceiptLedger, FileReceiptPersistence,
receiptKey, reconcileOrdinary), `experimental/pikmin2_receipts.py`.

## Ordered commits

Root base `ef1cace`:

1. `bf0e56b` — `lane06: P2 ordinary delivery receiver (Python) + tests (#441)`
   (`experimental/pikmin2_delivery.py`, `tests/test_pikmin2_delivery.py`,
   `tests/test_pikmin2_receipt_native.py`).

Native base `b805d9c6`:

1. `5243cdb3` — `lane06: P2 ordinary delivery receiver provider + consumer test (#441)`
   (`pc_port/pc_p2_delivery.h`, `tools/p2_delivery_receiver_test.cpp`).
2. `abbf3d34` — `lane06: register p2_delivery_receiver_test CTest (shared CMake hook) (#441)`
   (`CMakeLists.txt`).

Dirty state: both worktrees clean at publication (`git status --short` empty).

## Interfaces / hooks touched and why

`P2Delivery::DeliveryReceiver` (header-only, mirrors Python `DeliveryReceiver`):

- `p1ProxyIdentity(tekiType, stage)` -> `corpse:p1:<type>:<stage>`; `p2SourceIdentity(sourceId, stage)` -> `corpse:p2:<id>:<stage>`. Disjoint prefixes guarantee a P2 reward can never collide with a, and never alias a, P1-proxy reward.
- `identity(sourceId, tekiType, stage)` (sourceId==0 -> P1 proxy), `slotOrActor(generatorToken)` -> `g<token>`.
- `deliver(seed, sourceId, tekiType, stage, generatorToken, encounter)` -> `ledger.grant(...)` (True only on first grant); `delivered(...)` -> `ledger.has(...)`.
- `sourceDescriptor(sourceId, stage, family)` -> ordinary `p2-reward-descriptor-v1` for `reconcileOrdinary` (never pod).

No production-source change; the CMake edit only adds an `add_executable`/`add_test`
block for the engine-free test, following `p2_receipt_host_test` (lines ~1028).

## Build evidence (`output/dsw/l06-build-evidence.txt`)

```
2026-09-14T19:51:40 lane=l06 target=p2_delivery_receiver_test native=abbf3d34cfaf86fea32ee25857ba8038454fcda5 dirty=no build_dir=...\native-l06-build exe=...\native-l06-build\p2_delivery_receiver_test.exe sha256=89aa7277395297a8a372d5db1acc47488ccf9d48e70a84747fd4bd07cc39eff9 ninja_n="ninja: no work to do." seconds=0
```

CTest: `PASS p2_delivery_receiver_test` (test #62, 0.01s). Full `pikmin_pc` not rebuilt:
this slice changed no production translation unit (test-only, additive CMake).

## Fixture adoption evidence

Not applicable to this slice: no real-GL/input fixture was run (provider/interface slice,
engine-free). The maintained 960x540 centred-window + 20-red starting-Pikmin overlay is
required for gameplay slices and remains the responsibility of the family/runtime lanes
that wire this receiver (see blockers). This is reported honestly, not claimed as adopted.

## Six arena gates (natural vs injected)

| Gate | Result | Evidence / labels |
|---|---|---|
| 1 Exact identity and spawn | source-backed N/A (identity pinned; spawn is family/lane-13) | source_id 44/45 confirmed from roster JSON + `pc_p2_roster.h`; native bind logs (`P2_ENEMY_READY species=BlueKochappy source_id=44`, `species=YellowKochappy native_family=Chappy`). No live spawn in this slice. |
| 2 Autonomous movement / animation | source-backed N/A | family lane 13 owns Kochappy/Snow motion; not exercised here. |
| 3 Attacks and receivers | source-backed N/A | family lane 13 / receiver lane 10; not exercised here. |
| 4 Death and corpse | source-backed N/A (identity-level) | audit confirms cohort inherits P1 `TEKI_Chappy` corpse (`TEKICORPSE_LeaveCorpse` -> modelId = `TekiMgr::getTypeId(3)`); no P2 identity survives the corpse to the Onion. |
| 5 Actual transport and reward | interface PASS / natural UNTESTED | Interface-level exactly-once + P2/P1 disambiguation + restart PASS (native CTest + Python). Natural Onion transport of a live P2 corpse NOT wired in engine (concern: lane 01 + family 13 + real-GL). |
| 6 Cleanup and re-entry | source-backed N/A | lifetime/re-entry owned by lane 07; receiver leaves no state beyond the ledger. |

Persistence (admission gate F) at the provider/interface level: **PASS** — exactly-once
across process restart proven twice (native FileReceiptPersistence CTest, Python
`JsonReceiptPersistence`). All labels above distinguish injected/fixture-only evidence from
natural behaviour; this slice contains no injected health/animation/forced-drop evidence.

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_delivery.py tests/test_pikmin2_receipts.py -q` -> `38 passed, 19 subtests passed`.
- `PIKMIN_NATIVE_SOURCE=<native worktree> py -3.12 -m pytest tests/test_pikmin2_receipt_native.py -q` -> `2 passed` (compiles + runs `pc_p2_receipt.h`/`pc_p2_cargo_contest.h`/`pc_p2_delivery.h` with MinGW g++).
- Native CTest `p2_delivery_receiver_test` -> PASS (exit 0, `PASS p2_delivery_receiver_test`).

## Subagent usage

- `explore` #1 (source audit): used as-is — pinned source_id 44/45, `TEKI_Chappy=3`,
  `TEKI_TypeCount=35`, confirmed no P2 source_id anywhere in the bestiary/collection
  catalogs, and the corpse-delivery hop chain with file:line. Saved substantial recon time.
- `explore` #2 (candidate inventory): used as-is to locate the exact owned files and the
  sole ordinary-Onion consumer (`pc_p2_flora_actor.cpp`), and to confirm no existing
  P2-source->ordinary-receipt mapping. Corrected one detail in my handoff (the "p2-costs.txt"
  token I had assumed does not exist; discarded that assumption).
- `general` #3 (Python module + tests): used as-is — `experimental/pikmin2_delivery.py` +
  `tests/test_pikmin2_delivery.py` (6 tests) merged without signature changes; I authored the
  native mirror myself and extended `tests/test_pikmin2_receipt_native.py` (one correction:
  an inverted early-return guard in my own snippet, not the subagent's work).
  Net effect: saved the read-header + scaffold + first pytest pass; cost was modest
  re-verification to align the native/Python contracts.

## Assumptions

- The P1-proxy corpse identity should remain keyed by the reused Teki type
  (`corpse:p1:<type>:<stage>`), unchanged, so ordinary P1 bestiary behaviour is preserved;
  the P2 identity is additive and never rewrites it.
- `generatorToken` is the stable per-slot placement uid (per the existing placement/bind
  vocabulary), so seed+source_id+stage+generator reproduces across revisit/restart.
- No new bestiary check is invented: the receiver only maps a P2 source to a durable
  ordinary identity string; the actual check-name/AP entitlement lives in lane 02/03's
  catalog, which this slice does not touch.

## Remaining blockers / next step

1. **Lane 01 (integration) + family lane 13 + real-GL**: wire the live Snow/Dwarf-Orange
   corpse through `GoalItem::suckMe` -> a new narrow hook that passes `(sourceId,
   tekiType, stage, generatorToken)` into `P2Delivery::DeliveryReceiver::deliver`, then
   assert the recipient check is credited once and survives restart. Proposed hook contract
   (inputs/outputs/invariants) matches `deliver(seed, sourceId, tekiType, stage,
   generatorToken, encounter)`: caller = `goalItem.cpp` corpse path; identity/lifetime = the
   four-part receipt key; result = Granted/Duplicate/Error (Error must not consume the
   reward); failure = fail-closed, no Onion seed/poko side effect from the receipt call.
   One real acceptance case: kill Snow in the ordinary room, deliver its corpse to the
   Onion, restart the process, deliver nothing -> no duplicate, no lost check.
2. **Lane 02/03 (roster/seed)**: admit Snow (45)/Dwarf Orange (44) and provide the seed +
   ordinary check name the receiver's identity maps to; this slice deliberately does not add
   catalog entries.
3. Source-faithful four-part key confirming exactly-once for shared drop endpoints (Frog/
   Mamuta/Kogane/Breadbug consumers in the inventory) still goes through this same receiver.

## Exact reproduction command

```
py -3.12 -m pytest tests/test_pikmin2_delivery.py tests/test_pikmin2_receipts.py -q
```
(Native mirror: `py -3.12 output/deepseek-wave/build_lane.py l06 --target p2_delivery_receiver_test`
then `./p2_delivery_receiver_test.exe` in `output/dsw/native-l06-build`, or
`ctest -R p2_delivery_receiver_test`.)
