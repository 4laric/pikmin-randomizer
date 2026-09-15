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

**Plainly: no family module calls the receiver yet.** The only current consumers are the
native CTest and the Python tests, which drive the Snow (45) / Dwarf Orange (44) identity
constants. The proposed first real consumer is **lane 13 (Snow corpse -> Onion)** — see
"Remaining blockers" for the exact call site.

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

## Review fixes (this revision)

Three blocking contract issues + three smaller items, all applied:

1. **`corpse:` -> `onion:` prefix.** `p1ProxyIdentity`/`p2SourceIdentity` now emit
   `onion:p1:<type>:<stage>` / `onion:p2:<id>:<stage>`. This is required because the Pod
   economy's ids are `corpse:<generator>` / `corpse:floor{n}:<gen>` and
   `experimental/pikmin2_reward_lifecycle.py:148,169` (and `pikmin2_snow_lifecycle.py:100`)
   count Pod rows by `startswith('corpse:')`; an ordinary `corpse:`-prefixed key would be
   miscounted in a shared dump. `onion:` is confirmed unclaimed (`grep`, no producer/consumer).
   A mixed-dump test now proves the split (see tests).
2. **No default family.** `sourceDescriptor(sourceId, stage, family)` requires the family
   tag; the "lane-13-bulborbs" default was removed from the shared header.
3. **Explicit proxy flag.** `identity`/`deliver`/`delivered` take an explicit
   `bool p1Proxy`; the P2 path rejects an unbound `sourceId == 0` (throws
   `std::runtime_error` / `ValueError`) instead of silently crediting the P1-proxy check.
   The engine hook must pass the bound source_id (documented in the header).
4. **CTest temp-dir collision**: the consumer test's durable sidecar directory is
   pid-scoped.
5. CTest/exe output saved under `output/dsw/l06-out/` (cited below); root commit `7695630`
   added to the ordered-commit list; typo "prexes" -> "prefixes" fixed.
6. First-consumer call site named (lane 13 Snow corpse -> Onion) — see blockers.

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
2. `7695630` — `lane06: handoff for P2 ordinary delivery receiver slice (#441)`
   (`docs/PIKMIN2_LANE06_DEEPSEEK_HANDOFF.md`).
3. `3856373` — `lane06: review fixes — onion: prefix, explicit p1_proxy, mixed-dump counting test (#441)`
   (`experimental/pikmin2_delivery.py`, `tests/test_pikmin2_delivery.py`,
   `tests/test_pikmin2_receipt_native.py`).

Native base `b805d9c6`:

1. `5243cdb3` — `lane06: P2 ordinary delivery receiver provider + consumer test (#441)`
   (`pc_port/pc_p2_delivery.h`, `tools/p2_delivery_receiver_test.cpp`).
2. `abbf3d34` — `lane06: register p2_delivery_receiver_test CTest (shared CMake hook) (#441)`
   (`CMakeLists.txt`).
3. `314a32af` — `lane06: review fixes — onion: prefix, explicit p1Proxy, no default family, pid-scoped temp dir (#441)`
   (`pc_port/pc_p2_delivery.h`, `tools/p2_delivery_receiver_test.cpp`).

Dirty state: both worktrees clean at publication (`git status --short` empty).

## Interfaces / hooks touched and why

`P2Delivery::DeliveryReceiver` (header-only, mirrors Python `DeliveryReceiver`):

- `p1ProxyIdentity(tekiType, stage)` -> `onion:p1:<type>:<stage>`; `p2SourceIdentity(sourceId, stage)` -> `onion:p2:<id>:<stage>`. Disjoint `onion:p1:`/`onion:p2:` prefixes guarantee a P2 reward can never collide with, or alias, a P1-proxy reward, and neither starts with `corpse:` (Pod-safe).
- `identity(sourceId, tekiType, stage, p1Proxy)`: `p1Proxy=true` -> P1-proxy identity; otherwise requires a bound `sourceId != 0` (rejects 0). `slotOrActor(generatorToken)` -> `g<token>`.
- `deliver(seed, sourceId, tekiType, stage, generatorToken, encounter, p1Proxy)` -> `ledger.grant(...)` (True only on first grant); `delivered(...)` -> `ledger.has(...)`.
- `sourceDescriptor(sourceId, stage, family)` -> ordinary `p2-reward-descriptor-v1` for `reconcileOrdinary` (never pod); family is a required argument.

No production-source change; the CMake edit only adds an `add_executable`/`add_test`
block for the engine-free test, following `p2_receipt_host_test` (lines ~1028).

## Build evidence (`output/dsw/l06-build-evidence.txt`)

Latest clean-head record:

```
2026-09-14T20:13:31 lane=l06 target=p2_delivery_receiver_test native=314a32aff1c9a28f85ab1d9ef0fc61d09dbeae17 dirty=no build_dir=...\native-l06-build exe=...\native-l06-build\p2_delivery_receiver_test.exe sha256=1e508f18e771fed76e807ec5129ddd8885f7b7fcbe405dfa0450829a51dc636e ninja_n="ninja: no work to do." seconds=0
```

Runtime evidence (this revision): `output/dsw/l06-out/ctest-delivery.txt` (CTest #62,
`Passed`, 0.01s, "100% tests passed out of 1") and `output/dsw/l06-out/delivery-exe.txt`
(`PASS p2_delivery_receiver_test`, exit 0). Full `pikmin_pc` not rebuilt: this slice
changed no production translation unit (test-only, additive CMake).

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
| 5 Actual transport and reward | interface PASS / natural UNTESTED | Interface-level exactly-once + P2/P1 disambiguation + Pod-safe prefix + restart PASS (native CTest + Python). Natural Onion transport of a live P2 corpse NOT wired in engine (concern: lane 01 + family 13 + real-GL). |
| 6 Cleanup and re-entry | source-backed N/A | lifetime/re-entry owned by lane 07; receiver leaves no state beyond the ledger. |

Persistence (admission gate F) at the provider/interface level: **PASS** — exactly-once
across process restart proven twice (native FileReceiptPersistence CTest, Python
`JsonReceiptPersistence`). All labels above distinguish injected/fixture-only evidence from
natural behaviour; this slice contains no injected health/animation/forced-drop evidence.

## Tests run and results

- `py -3.12 -m pytest tests/test_pikmin2_delivery.py tests/test_pikmin2_receipts.py -q` -> `40 passed, 19 subtests passed`.
- `PIKMIN_NATIVE_SOURCE=<native worktree> py -3.12 -m pytest tests/test_pikmin2_receipt_native.py -q` -> `2 passed` (compiles + runs `pc_p2_receipt.h`/`pc_p2_cargo_contest.h`/`pc_p2_delivery.h` with MinGW g++).
- Native CTest `p2_delivery_receiver_test` -> PASS (exit 0, `PASS p2_delivery_receiver_test`).

## Subagent usage

fix1 round (three delegated tasks, run in parallel):

- `explore` #1 (source audit / hook-site): used as-is. Confirmed every Pod `corpse:`
  producer (`pc_p2_preview.cpp:112,328,331,336`) and the `startswith('corpse:')` counters
  (`pikmin2_reward_lifecycle.py:148,169`, `pikmin2_snow_lifecycle.py:100`), and that a bound
  P2 source_id is NOT reachable at `goalItem.cpp:356-363` today (must be threaded into
  `pc_randomizer_corpse_delivered`; `pc_randomizer_p2_source(target)` exists but is
  unwired). This directly supported fix items 1 and 6. Time saved vs. manual re-grep.
- `explore` #2 (prefix-collision inventory): used as-is. Proved `onion:` is unclaimed and
  enumerated all `corpse:`/`enemy:` producers and example strings. Used to justify the
  `onion:` choice in the handoff.
- `general` #3 (Python module + tests rework): used as-is — rewrote
  `experimental/pikmin2_delivery.py` and `tests/test_pikmin2_delivery.py` to the new
  `onion:`/explicit-`p1_proxy` contract and added the mixed-dump + bound-source-id tests.
  I then made one one-line normalization (`p1_proxy is True` -> `p1_proxy` truthiness) so the
  Python mirror matches the native `if (p1Proxy)`, and I updated the embedded C++ in
  `tests/test_pikmin2_receipt_native.py` myself. Net: saved the pytest/rewrite cycle.

Overall the subagents saved the read-heavy re-verification of the prefix corpus and the
Python test rework; the native header/test edits, build, CTest and commits were done by me.

## Assumptions

- The ordinary identities now key on the `onion:` prefix (P1 proxy `onion:p1:<type>:<stage>`,
  P2 source `onion:p2:<id>:<stage>`), preserving the ordinary-P1 bestiary behaviour
  (its check names live in the catalog, not in this receiver) and never colliding with the
  Pod `corpse:` economy.
- `generatorToken` is the stable per-slot placement uid, so
  seed+identity+generator+encounter reproduces across revisit/restart.
- No new bestiary check is invented: the receiver only maps a P2 source to a durable
  ordinary identity string; the actual check-name/AP entitlement lives in lane 02/03's
  catalog, which this slice does not touch.

## Remaining blockers / next step

1. **Lane 13 (Snow corpse -> Onion) is the proposed first real consumer.** Exact call site:
   `GoalItem::suckMe` (`src/plugPikiKando/goalItem.cpp:354-364`) currently maps
   `config->mModelId.mId` to a P1 Teki type and calls `pc_randomizer_corpse_delivered(type,
   stage, gameplay)`. To use this receiver, a bound P2 source_id must be threaded into that
   path: recover the corpse's originating generator + placement target token, resolve the
   source_id (via an integration-wired `pc_randomizer_p2_source(target)`), and call
   `P2Delivery::DeliveryReceiver::deliver(seed, sourceId, tekiType, stage, generatorToken,
   encounter, /*p1Proxy=*/false)` with the bound source_id. Requires lane 01 (integration) +
   family 13 + real-GL; not performed here (provider boundary).
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
