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

## Slice 2 — first real consumer (GoalItem::suckMe -> durable ordinary receipt)

### What was wired

1. **Engine-free delivery host** `pc_port/pc_p2_delivery_host.{h,cpp}`: owns a
   persistent `FileReceiptPersistence` + `P2Delivery::DeliveryReceiver` in its own TU;
   `pc_p2_delivery_host_deliver(seed, sourceId, tekiType, stage, generatorToken,
   encounter)` always `p1Proxy=false` and rejects `sourceId==0`.
2. **Randomizer glue** (`pc_port/pc_randomizer.{h,cpp}`): `pc_randomizer_p2_bind_source
   (tekiview, sourceId, generatorUid)` captures the bound source at bind/spawn time
   (the Teki's `mGenerator` is nulled by `dieSoon` before the corpse reaches the Onion);
   `pc_randomizer_p2_source_for` / `_generator_for` read it back;
   `pc_randomizer_p2_corpse_delivered(tekiview, type, stage, gameplay)` opens the durable
   host at `campaignDirectory/p2-delivery-receipts.txt` (identity `onion:p2:<sourceId>:
   <stage>`, slot `g<generatorUid>`, seed = manifest `fingerprint`, encounter `corpse`).
3. **Engine hook** `src/plugPikiKando/goalItem.cpp` (the corpse branch of
   `GoalItem::suckMe`, separate labelled commit): when the corpse's `PelletView` has a
   bound source, call `pc_randomizer_p2_corpse_delivered` so a P2 reward is granted under
   its own identity, never the P1-proxy `Bestiary: Deliver Dwarf Bulborb` check.

### Runtime proof (960x540, real-GL, two processes)

Reproducer: `scripts/p2_delivery_fixture.cpp` (replacement main) +
`scripts/p2_delivery_runtime.py`. Fixture binds source 44 (Dwarf Orange) onto the live
Chappy host, kills it (frame 9), drives the real corpse through `GoalItem::suckMe`, and
the host grants `onion:p2:44:1` exactly once; a second process over the same ledger
re-delivers -> Duplicate.

```text
run1  P2_ORDINARY_P2_RECEIPT seed=225221..ab9d84 id=onion:p2:44:1 generator=185597288 new=1
run2  P2_ORDINARY_P2_RECEIPT ... new=0      EXACTLY_ONCE_ACROSS_RESTART: True
```

Evidence in `output/dsw/l06-out/` (`slice2-evidence.txt`, `delivery-run-final/`,
`ctest-delivery-slice2.txt`). Fixture SHA-256 `ad81e84720c9…fc90`; production
`nectar.exe` SHA-256 `a991c44dc697…ad15f3` (native `45eb7fa6`, clean, `ninja` no-work).

Natural vs injected: kill, corpse, Onion endpoint and durable receipt are real;
the P2 source bind is a labelled fixture intervention (standing in for lane 13), and
natural carry is injected (`natural_carry=0` -> `onion->suckMe` fallback; transport stays
lane 04). Window `960x540` windowed/centred; `Direct boot: Forest of Hope day 2, 20 reds`
(starting squad, no extinction).

### New commits (this slice)

Root (`deepseek/p2-l06`, base `ef1cace`):
- `144c0bf` mixed-dump test drives real `pikmin2_reward_lifecycle.validate` counter.
- `87d11c8` P2 delivery runtime fixture + two-process runner.
- `8ee171c` include `Generator.h` in P2 delivery fixture.
- `1f1d1e0` clean P2 delivery fixture + parent-poll two-process runner.
- `0f26698` handoff Slice 2 (first real consumer + runtime proof).
- `f3791d7` pin native commit SHAs in Slice 2 handoff.

Native (`deepseek/p2-l06-native`, base `b805d9c6`):
- `314a32af` review fixes (fix1).
- `e193f65a` `pc_p2_delivery_host.{h,cpp}` + `tools/p2_delivery_host_test.cpp` + CMake (production + CTest).
- `bee402dd` `pc_randomizer_p2_bind_source/_source_for/_generator_for/_corpse_delivered` (randomizer glue).
- `1efcbaeb` `GoalItem::suckMe` -> `pc_randomizer_p2_corpse_delivered` (shared engine hook).
- `45eb7fa6` drop the bridge-flag gate for the runtime binding (authoritative signal).

### Six arena gates (natural vs injected)

| Gate | Result |
|---|---|
| 1 Identity/spawn | interface PASS / natural N/A — source 44 bound at spawn (labelled fixture bind; lane 13 supplies it in a generated session). |
| 2 Movement/animation | source-backed N/A (P1 proxy; family FSM is lane 13). |
| 3 Attacks/receivers | source-backed N/A (single InteractAttack kill; receivers are lane 10). |
| 4 Death/corpse | PASS — natural Chappy death -> `PELTYPE_Corpse` pellet (frame 9). |
| 5 Transport/reward | interface PASS, transport INJECTED — `onion:p2:44:1` granted exactly once via real `GoalItem::suckMe`; natural carry did not move the corpse (`natural_carry=0`). |
| 6 Cleanup/re-entry | source-backed N/A (lane 07). |

Persistence (admission gate F): **PASS at the runtime level** — one durable receipt row
across a fresh process (run2 Duplicate).

### Subagent usage (slice 2)

- `explore` #1 (corpse->source_id recovery + seed/restart mechanism): used as-is. Confirmed
  `Pellet::mPelletView` is the Teki, that `mGenerator` is nulled by `dieSoon` (so the
  source must be captured at bind), that `fingerprint` is the stable cross-restart seed
  coordinate, and the receipt host needs an explicit stable path (not the per-run cwd).
  Saved substantial recon. The parent-poll (vs background thread) fix came out of the
  followed-on runtime debugging, not this audit.
- `explore` #2 (runtime/stager inventory): used as-is to confirm the ordinary-room blueprint
  (chal0 `TEKI_Chappy` host, `practice.ini` Onion) and that no ordinary consumer writes the
  receipt host yet. The targeted reproduction path was largely already known; cost was low.
- `general` #3 (mixed-dump test): used as-is — rewrote the mixed-dump test to call the real
  `experimental.pikmin2_reward_lifecycle.validate`; 42 passed, 19 subtests. No corrections needed.

## Slice 2 review fixes (fix2)

### Resolution status (items 1-8)

1. **Double credit — FIXED.** `pc_randomizer_p2_corpse_delivered` now returns `bool`
   (true = it delivered a bound P2 source); `GoalItem::suckMe` credits the P1-proxy
   bestiary check only when that returns false. Verified: run1 log has 0
   `Bestiary: Deliver Dwarf Bulborb` / `CHECK 30` lines beside the `onion:p2:44:1` receipt.
2. **Production open path exercised — FIXED.** Fixture no longer pre-opens via
   `PIKMIN_P2_RECEIPT_PATH`; `pc_randomizer_p2_corpse_delivered` opens the handle at
   `campaign/p2-delivery-receipts.txt`, and the runner reads that path. Run evidence shows
   the ledger at `<session>/campaign/p2-delivery-receipts.txt`.
3. **Checkpoint save — RELABELLED honestly.** A real `saveCurrentGame()` (`save_failed=0`,
   `CAMPAIGN_SAVED generation=1`) made the second process resume day 2 instead of
   cold-booting (it stalled at `CAMPAIGN_RESUMED`, no world). So the save trigger is
   dropped and Persistence is labelled "process restart only, no checkpoint save"; the
   durable `campaign/` sidecar still proves exactly-once across restart.
4. **Stale pointer keys — FIXED.** The binding is single-use: `pc_randomizer_p2_corpse_delivered`
   consumes it after the grant, and `pc_randomizer_p2_forget_source(const void*)` is called
   from the central `pc_p2_forget_teki` lifetime seam, so a recycled Teki address can never
   inherit a P2 binding or credit the P1 proxy as `onion:p2`.
5. **Unbindable id abort — FIXED.** `pc_randomizer_p2_bind_source` logs-and-returns instead of
   `fail()`; `tools/p2_*_host_test.cpp` temp dirs are pid-scoped.
6. **Wave merge — DONE.** Merged `claude/p2-deepseek-wave-native` (commit `b9702636`),
   keeping lane 03's `pc_randomizer_bind_generator(..., sourceId70=0)`,
   `pc_randomizer_p2_room_bootstrap`, `pc_randomizer_p2_source_for_id` and un-guarded bridge
   lookups alongside the lane-06 bind/deliver functions. Rebuilt clean.
7. **Per-consumer ledgers — DONE.** `pc_p2_receipt_host` and `pc_p2_delivery_host` are now
   handle-per-path registries: `open(path)` returns a handle; `grant`/`deliver`/`close` take
   it. Flora (p2-flora-receipts.txt), kogane (p2-kogane-onion-receipts.txt, lazy-reopen
   workaround retired) and the randomizer (p2-delivery-receipts.txt) each hold their own
   handle. New `p2_receipt_host_multi_test` (two consumers, independent ledgers). Header docs
   updated to describe the handle contract.
8. **Handoff fixes — DONE.** All six root commits listed; "40/40 tests"; one
   `build_lane.py l06 --target p2_delivery_host_test` line at the committed head; runner no
   longer hardcodes the MinGW path (guarded `MINGW_BIN`) and uses a descriptive seed.

### New commits this pass

Native (`deepseek/p2-l06-native`, base `b805d9c6`):
- `b9702636` merge `claude/p2-deepseek-wave-native`.
- `b4480fca` per-consumer handle-per-path receipt/delivery host ledgers (its own commit).
- `ea236072` exactly-once delivery, no P1 double-credit, single-use binding.

Root (`deepseek/p2-l06`, base `ef1cace`):
- `a6c6429` fixture drops pre-open, triggers a real save; runner reads campaign ledger.
- `fc683cd` relabel persistence (process restart; no checkpoint save).
- (also the three Python/subagent edits: `144c0bf`, then this pass's delivery test additions,
  see `tests/test_pikmin2_delivery.py`.)

### Build + runtime evidence

- Production `nectar.exe` SHA-256 `9395256dfc92…8474a31`, native `ea236072` clean,
  `ninja: no work to do`.
- Fixture `cdc637b4aea0…602f7`. Two-process run `delivery-run-fix2b`: run1 `new=1`, run2
  `new=0`, `EXACTLY_ONCE_ACROSS_RESTART: True`, one row in `campaign/p2-delivery-receipts.txt`.
- CTest 4/4: `p2_receipt_host_test`, `p2_receipt_host_multi_test`, `p2_delivery_receiver_test`,
  `p2_delivery_host_test`. pytest `42 passed, 19 subtests`; `test_pikmin2_receipt_native.py`
  `2 passed`. Evidence file: `output/dsw/l06-out/slice-fix2-evidence.txt`.

### Subagent usage (fix2)

- `explore` #1 (wave-branch diff + save mechanism + consumer blast-radius): used as-is — the
  exact `bind_generator(...,sourceId70=0)`/`p2_room_bootstrap`/`p2_source_for_id` signatures,
  the `MemoryCard::saveCurrentGame()` recipe, and the consumer call-site list drove the merge
  and the handle refactor. The save-triggers-resume complication was discovered by the actual
  runtime, not this audit.
- `explore` #2 (host/test inventory + doc locations): used as-is to find every
  `pc_p2_receipt_host_*`/`pc_p2_delivery_host_*` caller and the exact CTest blocks; flagged the
  kogane lazy-reopen and the stale "registered as CTest" doc claim I must correct.
- `general` #3 (root per-path ledger tests): used as-is — added the two independent-ledger
  tests to `tests/test_pikmin2_delivery.py` (42 tests pass).

## Slice 3 — provider sweep

Deterministic provider fixes, the published consumer contract, and one more
end-to-end consume (lane 31 Waterwraith view-less corpse). All build/test evidence
is at committed native head `8e5e09b4` (dirty=no).

### Carry-forward fixes (this pass)

1. Closed-handle UB: `pc_p2_receipt_host_grant` / `pc_p2_delivery_host_deliver`
   now resolve the handle through the registry (`*HostByHandle`, the same lookup
   `_path()` uses), returning `Error` for a closed/invalid handle instead of
   dereferencing a dangling host.
2. Count accessor: `pc_p2_receipt_host_count(handle)` — lane 17 stops re-parsing
   its sidecar to count receipts.
3. Delivery-handle reset: `pc_randomizer_p2_delivery_reset()` closes the once-opened
   `p2DeliveryHost`, wired into `pc_p2_reset_all_teki` (stage-boundary seam).
4. Restored the atomic-write failure-path assertion in `tools/p2_receipt_host_test.cpp`.
5. `PIKMIN_MINGW_BIN` env override for the runner's MinGW DLL path.

### Consumer contract (published)

`pc_port/pc_p2_receipt_host.h` (and `docs/PIKMIN2_REWARD_RECEIPTS.md` §"Family
consumer contract") now spells out the two paths:
- **Ordinary Onion/AP**: per-consumer `pc_p2_receipt_host_open(path)` handle +
  `grant`/`count`/`close`; durable exactly-once across restart.
- **Experimental Pod**: `bool pc_p2_<family>_receipt(PelletView*|Pellet*, ...)`
  dispatched by `pc_p2_preview_deliver`; view-less number-pellet corpses use the
  `Pellet*`-keyed form and carry a synthetic identity token.

### Consume #2 (lane 31 Waterwraith) — lane-31-owned

Lane 31's fixed-placement seam drops a **view-less** number-pellet corpse (no
`mPelletView`, no generator id). Lane 06 briefly added a duplicate
`pc_p2_waterwraith_receipt(Pellet*, std::string&)` hook + preview dispatch; that was
**removed** (fix3), and the wave now carries lane 31's own
`pc_p2_waterwraith_receipt(Pellet*, unsigned&)` + `sCorpses` map + liveness sweep.
The `BlackMan`/Waterwraith gate row therefore belongs to lane 31 (no source-99 table
here). Lane 31's free-mode fixture and its natural reference run are cited in the
fix4 section.

### Six-gate table

## Concrete source ID
- Source ID: 44 `BlueKochappy`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PARTIAL (fixture-binds 44 onto the Chappy host) | output/dsw/l06-out/delivery-run-fix2b/session-dc0da662/runs/e64887c2be1c7806da348aa1b0b499b0d2ddbfd6253fba4ac6456822ff906a1d/native.log:937 | injected |
| 2. Autonomous movement and animation | N/A (family lane 13) | docs/PIKMIN2_SNOW_BULBORB.md | natural |
| 3. Attacks and receivers | N/A (family lane 13 / receiver lane 10) | docs/PIKMIN2_SNOW_BULBORB.md | natural |
| 4. Death and corpse | PARTIAL (real kill/corpse, P1-proxy) | output/dsw/l06-out/delivery-run-fix2b/session-dc0da662/runs/e64887c2be1c7806da348aa1b0b499b0d2ddbfd6253fba4ac6456822ff906a1d/native.log:938 | natural |
| 5. Actual transport and reward | PARTIAL (receipt real, carry injected) | onion:p2:44:1 output/dsw/l06-out/delivery-run-fix2b/session-dc0da662/runs/e64887c2be1c7806da348aa1b0b499b0d2ddbfd6253fba4ac6456822ff906a1d/native.log:991 | injected |
| 6. Cleanup and re-entry | N/A (lane 07) | docs/PIKMIN2_REWARD_RECEIPTS.md | natural |

(The former `BlackMan`/Waterwraith table is removed: that identity is owned by lane 31,
not lane 06, and its gate-4 cell had mis-cited the source-44 Onion line. Lane 31's own
evidence is authoritative; the lane-06 reference-run answer is in the fix4 section.)

### Checker output

```
44 BlueKochappy (role=source):
  1. identity_spawn     ignored [PARTIAL]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [PARTIAL]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    ignored [N/A]
99 BlackMan (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [PARTIAL]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [N/A]
```
(checker exit 0; no refused PASS rows — lane 06 is a provider lane, so the
spawn/movement/attacks/cleanup gates are source-backed N/A and the reward gates
are PARTIAL/UNTESTED with the injected/proxy label.)

### Commits this pass

Native (`deepseek/p2-l06-native`, base `b805d9c6`):
- `5be052c8` closed-handle UB fix, count accessor, delivery reset, atomic-write assert.
- `8e5e09b4` Waterwraith view-less corpse credit via Pellet*-keyed receipt.

Root (`deepseek/p2-l06`, base `ef1cace`):
- `2986eef` consumer contract doc, PIKMIN_MINGW_BIN override, count/two-path tests.

### Build + test evidence

- `build_lane.py l06` (production `pikmin_pc`) native `8e5e09b4` dirty=no,
  `nectar.exe` SHA-256 `783ab689e94259eb5611b15eaa4ea4c1b5d0d13fa1e0a0281aa8fa5c48e4978a`,
  `ninja -n` no work.
- `build_lane.py l06 --target p2_delivery_host_test` SHA `a39c60aac1…a96ba424`.
- `build_lane.py l06 --target p2_receipt_host_multi_test` SHA `08799de3ef…21e4b53`.
- CTest 4/4: `p2_receipt_host_test` (count + closed-handle), `p2_receipt_host_multi_test`,
  `p2_delivery_receiver_test`, `p2_delivery_host_test`.
- pytest `44 passed, 19 subtests`; `test_pikmin2_receipt_native.py` `2 passed`.
- Evidence: `output/dsw/l06-out/delivery-run-fix2b/…/native.log` (the fix2 two-process
  delivery run; reused here for the 44 table line citations).

### Subagent usage (slice 3)

- `explore` #1 (Pod corpse-receipt branch + Waterwraith/Groink/Kogane): used as-is — gave
  the exact `pc_p2_preview_deliver` dispatch, the `pc_p2_<family>_receipt` signatures
  (PelletView*-keyed; flora Pellet*-keyed), the Waterwraith `spawnWraithCorpse` view-less
  number-pellet path (no generator id), and the Groink `KillPellet/RequestBirth` gap. This
  directly shaped the contract doc and the Waterwraith hook.
- `explore` #2 (family-receipt inventory + gate-table spec + test tallies): used as-is —
  located the 4 existing `_receipt` hooks, the `wave-root` gate-table spec/validator, and
  reconciled the "44" vs "42" test count. The gate-table regex details saved a round-trip
  on the checker (the enum-name + backtick binding requirement).
- `general` #3 (count-accessor + two-path Python tests): used as-is — added
  `test_ledger_count_accessor_and_independence` and `test_two_paths_pod_vs_onion_vocabulary_do_not_collide`;
  confirmed `ReceiptLedger` exposes `__len__` (mirrored by `pc_p2_receipt_host_count`).

## Slice 3 review fixes (fix3)

### Items 1, 2, 4 — delivered

1. Dropped the lane-06 Waterwraith hook. Merged `claude/p2-deepseek-wave-native`
   (~lane 31 fix2, commit `6dfd8c8e`) and took lane 31's
   `pc_p2_waterwraith_receipt(Pellet*, unsigned&)` + `sCorpses` map + per-tick
   liveness sweep + its own `pc_p2_preview.cpp` dispatch (after otakara), removing
   my `std::string&`-signature duplicate, `spawnedPellet` field, and my preview
   branch (merge commit `27225e43`).
2. Moved `pc_randomizer_p2_delivery_reset()` from the per-actor
   `pc_p2_forget_teki` into `pc_p2_reset_all_teki` (the stage-boundary seam it
   documents), and restored the tab indentation at the forget-source hook.
4. Repo path corrected (`native/pc_port` -> `engine/pc_port`) in
   `docs/PIKMIN2_REWARD_RECEIPTS.md`; the two-path vocabulary test now asserts
   through the real identity helpers + `pikmin2_reward_lifecycle.validate` instead
   of a hand-built list; CTest log archived at `output/dsw/l06-out/ctest-fix3.txt`
   (4/4 pass at native `27225e43`, dirty=no).

Added the free-mode requirement to the Pod contract (both the header block and
`docs/PIKMIN2_REWARD_RECEIPTS.md`): natural pickup needs free-mode Pikmin
(`Piki::graspSituation` only runs from `ActFree`; `mIdleWorkSearchRange` 100.0);
reference fixtures must release the squad (`Navi::releasePikis` /
`Piki::changeMode(FreeMode)`).

### Item 3 (end-to-end GL reference) — BLOCKED (owner: lane 19)

After merging the wave (which brings lane 19's `pikmin2_mamuta_install.py` fix
`f4c29aa`, so the `miulin_{wait,dead,attack1}.mod` singles stage and there is no
"invalid profile" exit), the natural Mamuta corpse→Pod reference is not
reproducible because the captain dies before the kill — a deterministic
DPS/park race in **lane 19's** fixture `scripts/pikmin2_mamuta_pod_fixture.inc`
(owner line `:1`): the captain parks only 20 units from the Miurin
(`parkDist=20.0f`, `:70-71`), the captain-down detector `naviDown` (`:24`) fires
in the window the 20th bury pound lands, and the ring squad has not yet killed
the Mamuta. Lane 19's own stored runs are flaky on the same binary
(`l19-out/mamuta-pod-deliver-02/…/native.log` `P2_MAMUTA_POD_CAPTAIN_DOWN tick=524`,
`deliver-04` `tick=497`, `died=0`; vs passes at `deliver-01/-03/-05/-06/-07`).
Lane 06 does not own that fixture and does not run it further.

**Void-run disclosure.** The four lane-06 "natural" runs
(`output/dsw/l06-out/mamuta-reference-{2,3,4,5}`) were executed against a
**dirty** working copy of `scripts/pikmin2_mamuta_pod_fixture.inc` (park `+250`→`+20`,
an injected `PikiAction::Attack`/`AttackMode` on the squad, `if(false)` disabling the
repark, forced `FreeMode` on death). That edit was uncommitted and is now reverted
(`git checkout -- scripts/pikmin2_mamuta_pod_fixture.inc`; `git status --short`
clean). **Those four runs are VOID as natural evidence** and are not cited by the
table above.

**Waterwraith (source 99) alternative — YES, lane-31-owned.** Lane 31's free-mode
release is now on the wave (`tools/p2_waterwraith_encounter_runtime.cpp:262`,
`squad[i]->changeMode(PikiMode::FreeMode, navi);`, commits `e857a7dc`/`b76b93b0`/
`0e6c4fff`/`7812cc04`), and lane 31 has a staged **natural** PASS:
`l31-out/waterwraith-encounter-run/5b9a375fcc7a470f9db1d5b6325705d5/stdout.log`
emits `P2_WATERWRAITH_SQUAD_FREE`, `P2_WATERWRAITH_CARRY_OBSERVE … carriers=2`,
`P2_WATERWRAITH_POD_RECEIPT generator=0 deliveries=1`,
`[Pikipelago] P2_POD_RECEIPT id=corpse:waterwraith:0 value=2 new=1 pokos=2 seeds=0`
and `PASS WATERWRAITH_ENCOUNTER_RUNTIME` (no `ASSISTED` suffix). So the source-99
reference can use lane 31's free-mode fixture; lane 06 does not re-run it (item-1
instruction) and owns no source-99 table.

Consequence: no positive `P2_POD_RECEIPT id=corpse:…` run is claimed by lane 06; the
provider contract's Pod path is documented (free-mode requirement now also in
`pc_p2_receipt_host.h`). The `44 BlueKochappy` Onion-path reference
(`delivery-run-fix2b`) is unchanged.

### Checker output (after fix3)

```
44 BlueKochappy (role=source):
  1. identity_spawn     ignored [PARTIAL]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [PARTIAL]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    ignored [N/A]
99 BlackMan (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [PARTIAL]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    ignored [N/A]
```
(checker exit 0; no refused PASS rows.)

### Commits this pass

Native (`deepseek/p2-l06-native`): `27225e43` merge wave + drop duplicate Waterwraith
hook + move delivery reset to stage boundary.
Root (`deepseek/p2-l06`): `787eb72` repo-path fix + de-tautologized two-path test;
`fc476bd` free-mode contract note.

### Subagent usage (fix3)

- `explore` #1 (lane-31 merged receipt + free-mode facts): used as-is — gave the exact
  wave signature `pc_p2_waterwraith_receipt(Pellet*, unsigned&)` + `sCorpses` + sweep,
  my exact lines to remove (register.cpp:28/61/221-231, register.h:28/32/64-67,
  preview.cpp:29/344-348), and the free-mode pickup facts
  (`graspSituation` piki.cpp:912/1102-1128, `mIdleWorkSearchRange` 100.0,
  `ActFree::exec` aiFree.cpp:182, `Navi::releasePikis`). This made the merge removal and
  the contract free-mode note exact and fast.
- `explore` #2 (assets + proven-family inventory): used as-is — identified `l31-out`
  staged assets and named Mamuta (lane 19) as the only proven corpse→Pod→receipt family
  with its runner command; also confirmed the Waterwraith carry is architecturally blocked.
  Directly shaped the item-3 attempt and the honest BLOCKED record.
- `general` #3 (de-tautologize the two-path test): used as-is — rewrote
  `test_two_paths_pod_vs_onion_vocabulary_do_not_collide` to assert via the real helpers
  + `validate` (44 passed); I committed it with the doc fixes.

## Slice 3 fixes (fix3b) — wave merge + free-mode header + reference retry

Merged both wave branches (root `37785c2`, native `fd890d77`), which resolves the
Mamuta install/staging half of the item-3 blocker. Added the free-mode natural-pickup
requirement to `pc_port/pc_p2_receipt_host.h` (previously only in the root doc).
Added a Mamuta receipt-shape test (reworded in fix4 to drop the provider-coverage
implication — it only checks vocabulary strings, not a provider path).

Commits:
- Root `deepseek/p2-l06`: `37785c2` (ff to wave), `349fb3a` Mamuta reference test.
- Native `deepseek/p2-l06-native`: `fd890d77` (ff to wave), `6a8d33d3` free-mode header.

Build/test: production `nectar.exe` SHA-256 `76badca1bc2ac7f11a6b31ce4622a8c139f999ade5067c6fd77a724eb3341fb9`
(native `6a8d33d3`, dirty=no, ninja no-work); pytest `45 passed, 19 subtests`.

### Subagent usage (fix3b)

- `explore` #1 (Mamuta install/fixture audit): used as-is — pinned `experimental/pikmin2_mamuta_install.py`
  `f4c29aa` (writes `miulin_{wait,dead,attack1}.mod` singles) and the fixture's
  `changeMode(FreeMode)` ring deploy; this is exactly why the pre-merge setup
  exited 3 and why the post-merge staging is clean.
- `explore` #2 (post-wave inventory + baseline): used as-is at the time — confirmed lane 31's
  free-mode fixture was **absent then** (it landed later on native tip `3a73ad3a`, corrected
  in fix4), the historical natural Mamuta PASS evidence
  (`l19-out/mamuta-pod-deliver-03/…/native.log:894`), the header-free-mode gap, and
  the 45-test baseline.
- `general` #3 (Mamuta receipt-shape test): used as-is — added
  `test_mamuta_pod_reference_receipt_shapes_through_provider`; reworded in fix4 to
  `test_mamuta_pod_receipt_vocabulary_shape_disjoint_from_onion` (vocabulary-shape only).

## Slice 3 fixes (fix4) -- shared-fixture revert, wave re-merge, item-3 owner

### Blocking fixes

1. **Shared fixture reverted.** `scripts/pikmin2_mamuta_pod_fixture.inc` was found
   dirty in the working copy (park `+250`->`+20`, injected `AttackMode` on the squad,
   `if(false)` repark, forced `FreeMode` on death) and is now reverted via
   `git checkout -- scripts/pikmin2_mamuta_pod_fixture.inc`; `git status --short` is
   clean. The four `mamuta-reference-{2,3,4,5}` runs used that dirty fixture and are
   **void as natural evidence** (see the fix3 item-3 block).
2. **Item 3 marked BLOCKED-on-lane-19**, with the exact race citation
   (`scripts/pikmin2_mamuta_pod_fixture.inc:70-71` park=20; `naviDown` `:24`/`:33`;
   lane 19's own flaky runs `deliver-02` tick 524, `deliver-04` tick 497). No further
   GL runs from lane 06. Waterwraith (99) answer below.

### Non-blocking fixes

3. Deleted the mis-cited `Source ID: 99` table (its gate-4 cited the source-44 Onion
   line `delivery-run-fix2b/.../native.log:991`; no real Waterwraith line exists in
   `l06-out`).
4. Re-merged the wave (root `claude/p2-deepseek-wave` -> `6c529ffe`; native
   `claude/p2-deepseek-wave-native` -> `d4be6bab`), landing lane 31's free-mode
   fixture.
5. Reworded the over-claiming test to
   `test_mamuta_pod_receipt_vocabulary_shape_disjoint_from_onion` (docstring:
   vocabulary-shape only, no provider/GL/native claim). Commit lists: the branches
   carry **24 root / 14 native `lane06:` commits**; run
   `git -C <root> log --oneline --grep=lane06` and
   `git -C <native> log --oneline --grep=lane06` for the ordered set (the per-pass
   summaries in this handoff are historical, not the full list).

### Waterwraith (99) reference answer -- YES (lane-31-owned)

Lane 31's free-mode release is on the wave
(`tools/p2_waterwraith_encounter_runtime.cpp:262`,
`squad[i]->changeMode(PikiMode::FreeMode, navi);`; commits
`e857a7dc`/`b76b93b0`/`0e6c4fff`/`7812cc04`), and lane 31 has a staged **natural**
PASS: `l31-out/waterwraith-encounter-run/5b9a375fcc7a470f9db1d5b6325705d5/stdout.log`
emits `P2_WATERWRAITH_SQUAD_FREE`, `P2_WATERWRAITH_CARRY_OBSERVE ... carriers=2`,
`P2_WATERWRAITH_POD_RECEIPT generator=0 deliveries=1`,
`[Pikipelago] P2_POD_RECEIPT id=corpse:waterwraith:0 value=2 new=1 pokos=2 seeds=0`,
and `PASS WATERWRAITH_ENCOUNTER_RUNTIME` (no `ASSISTED` suffix). So the source-99
reference can use lane 31's fixture; lane 06 does not re-run it and owns no source-99
table.

### Build/test

Native production sources changed in the re-merge, so `build_lane.py l06` was re-run:
native `d4be6babbe0346b49d52ef402621d819e4467dc9` dirty=no, `nectar.exe` SHA-256
`1e7ffa34240eea351658e2b8473138226832097f1558c37f993a6dccda91d14c`, `ninja -n` no work.
Root tests: `45 passed, 19 subtests`.

### Subagent usage (fix4)

- `explore` #1 (lane-19 race + lane-31 free-mode): used as-is -- corrected the stale
  citations (`naviDown` `:24`/`:33`, not `:21`; park `parkDist=20.0f` at `:70-71`,
  not `z+250`), proved the lane-19 flakiness on the same binary, and confirmed lane
  31's natural `P2_POD_RECEIPT id=corpse:waterwraith:0` PASS.
- `explore` #2 (commit list + gate/test inventory): used as-is -- produced the full
  root/native `lane06` commit list and confirmed the `:438` mis-citation and the
  `test_..._through_provider` over-claim; both fixed.
- `general` #3 (reword the test): used as-is -- renamed/reworded the test to a
  vocabulary-shape contract; 45 pass.

### Checker output (after fix4)

```
44 BlueKochappy (role=source):
  1. identity_spawn     ignored [PARTIAL]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [PARTIAL]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    ignored [N/A]
99 BlackMan (role=source): warning (shared table) - named in prose but no table of its own; give it a `Source ID` line + six-gate table to claim its gates
```
(checker exit 0; no refused PASS rows. The `99 BlackMan` line is a non-blocking
"shared table" warning: source 99 is lane-31-owned and deliberately has no lane-06
table.)

