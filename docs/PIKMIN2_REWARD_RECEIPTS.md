# P2 reward, cargo and save receipts (#441)

Lane 06 contract for per-identity P2 rewards and exactly-once delivery. This is a
**schema and reconciliation slice**: it reads no retail asset, mutates no native
save, and implements no source family drop behavior. Native save mutation is
coordinated with lane 01 and is out of scope here.

Module: `experimental/pikmin2_receipts.py`. Tests:
`tests/test_pikmin2_receipts.py`.

## Reward descriptor (versioned)

A descriptor is one JSON-shaped mapping with the required `version`, `identity`,
`family`, `drop` and `ledger` fields and the optional `value`/`count` fields.

| Field | Meaning |
|---|---|
| `version` | Must equal `p2-reward-descriptor-v1` |
| `identity` | Unique reward/source key, e.g. `corpse:floor1:5000`, `treasure:dia_a_red`; `[A-Za-z0-9_:/-]{1,90}` |
| `family` | Owning family lane tag, e.g. `lane-13-bulborbs`; lower-case `[a-z0-9-]` |
| `drop` | One of `corpse`, `pellet`, `treasure`, `none` |
| `value` | Optional non-negative integer (Pokos/check value) |
| `count` | Optional non-negative integer (carry/seed count) |
| `ledger` | `onion`, `ap` (ordinary) or `pod` (experimental) |

The source drop *meaning* stays with the family lanes; this module only carries
the shared vocabulary. Source examples in the repo: `experimental/pikmin2_kogane_assets.py`
(`drop_for`), `experimental/pikmin2_cave_catalog.py` (`DROP_MODES`),
`experimental/pikmin2_flora_assets.py` (`reference_conversion`).

## Ledgers (ordinary vs experimental)

The ledger tag is mandatory and the two worlds must never mix:

- **Ordinary** `onion` and `ap`: P1 Onion cargo / Archipelago checks.
- **Experimental** `pod`: the Research Pod/Poko preview economy
  (`P2_POD_RECEIPT`, `pc_p2_preview_pokos`, `p2-economy.txt`).

A Pod-only descriptor may exist for the experimental economy, but it must not
cover an ordinary expected check.

## Exactly-once receipts

A grant event is `(seed, identity, slot_or_actor, encounter)`. `receipt_key`
normalizes it, and `ReceiptLedger` over a `ReceiptPersistence` backend records it
at most once. `InMemoryPersistence` provides the deterministic fake backend;
`ReceiptLedger.reload()` reopens the same persisted state.

- `grant(...)` returns `True` only for the first occurrence and persists.
- Replaying the same event returns `False` and changes nothing.
- Reopening the ledger does not re-grant (`reload`/restart).
- `grant_events(ledger, events)` grants an ordered batch and returns the booleans.

Persisted state is `{"version": "p2-receipt-ledger-v1", "receipts": [[seed,
identity, slot_or_actor, encounter], ...]}`. Unknown versions, missing fields,
non-string receipts and duplicates are rejected with `ValueError`.

## Durable host-side adapter

`JsonReceiptPersistence(path)` implements the same `ReceiptPersistence` protocol
as the in-memory fake but round-trips the ledger to an ordinary JSON document:

- It loads existing state on construction (a missing file starts empty).
- `store(...)` writes atomically: a temp sibling `<name>.tmp` in the same
  directory is written, flushed and `os.replace`d into place. An interrupted
  write leaves the previous good file untouched and at most a stale `.tmp`, which
  load ignores.
- The on-disk document is `{"schema": "p2-receipts-v1", "version":
  "p2-receipt-ledger-v1", "receipts": [...]}`. Unknown `schema` versions, a wrong
  ledger version, missing/extra fields and corrupt JSON are rejected with
  `ValueError` rather than silently resetting state.
- `ReceiptLedger.restart()` (and the `reload()` alias) builds a fresh ledger from
  the same persistence, modelling a process restart: prior receipts are not
  re-granted while a genuinely new event still is.

## Reconciliation

`reconcile(reward_descriptors, expected_checks, refuse_pod_leaks=True)` returns:

- `missing_sources`: expected checks with no source descriptor.
- `pod_leaks`: expected checks covered only by a `pod` descriptor. Refused with
  `ValueError` by default; set `refuse_pod_leaks=False` to report instead.
- `unexpected_sources`: ordinary Onion/AP sources not in `expected_checks`
  (invented checks).
- `ordinary_sources` / `experimental_sources`: the accepted split.
- `ok`: true only when nothing is missing, leaked or invented.

Required checks are therefore never lost and no new checks are invented.

## Reward registry

`RewardRegistry` holds validated descriptors keyed by identity:

- `add(descriptor)` validates and stores one descriptor; a duplicate identity is
  a `ValueError`.
- `get(identity)` returns a copy or `None`; `descriptors` returns copies in
  insertion order.
- `reconcile_all(expected_checks, refuse_pod_leaks=True)` delegates to
  `reconcile`, so an ordinary `ap`/`onion` check with no source is reported in
  `missing_sources` and a `pod`-only source covering an ordinary check is refused
  by default.

## Malformed input

`validate_descriptor`/`validate_descriptors` raise `ValueError` for an unknown
version, duplicate identity, invalid drop kind, negative/non-integer counts,
unknown ledger tag, missing/unknown fields, or a malformed identity/family.
`ReceiptLedger` rejects a malformed or wrong-version persistence state, and
`JsonReceiptPersistence` rejects corrupt JSON, unknown `schema`/`version` values
and invalid receipt rows.

## Limitations

- **Source Pelplant pellet/Onion behavior is not implemented.** Pelplant pellet
  capture/release, pellet-to-Pom conversion and Onion seed/sprout grants remain
  family-owned work (#397, lane 23). A proxy Chappy corpse is not source Pelplant
  and must not be counted as one. This slice only defines and reconciles the
  descriptor/receipt contract.
- **This is not the native save path.** `JsonReceiptPersistence` is a host-side
  fake that writes a plain JSON file; it is not a Pikmin 2 save/memory-card
  layout. It must never be pointed at a real save. Native save mutation, binary
  layout and lane 01 coordination are untouched.
- `InMemoryPersistence` remains the default deterministic fake for tests.
- No retail assets are consumed, and no family drop value is asserted as source
  truth here.
- Coverage is a host-side bookkeeping check, not a runtime or AP-logic proof.

## Native provider surface

The C++ counterpart ships in `native/pc_port/pc_p2_receipt.h` (engine-free, no
engine types and no save layout):

- `P2Receipt::ReceiptLedger` — exactly-once grants over a `ReceiptPersistence`
  backend. `grant(seed, identity, slot_or_actor, encounter)` returns `true` only
  for the first occurrence; `reload()` re-opens the same state and never
  re-grants. Backends: `MemoryReceiptPersistence` (tests) and
  `FileReceiptPersistence` (atomic temp-sibling plus `os.replace`/`MoveFileEx`,
  ordinary sidecar text, **not** the native save). The same key tuple and
  `P2_RECEIPTS_1` header as the Python ledger.
- `P2Receipt::validateDescriptor` / `reconcileOrdinary` — versioned
  `p2-reward-descriptor-v1` descriptors and the ordinary/pod split. A `pod`
  descriptor covering an ordinary expected check is refused by default.
- `pc_port/pc_p2_cargo_contest.h` — the lane-18 cargo-contest provider surface:
  `P2CargoContest` takes cargo identity, source token, min/max thresholds,
  required/max carriers and a freeze window; `update()` returns
  `Held | Stolen | ReleasedToSource`; carriers are value tokens (never engine
  pointers), so no recycled address can leave a dangling helper. State is owned
  by the cargo and cleared on release, death, interruption, revisit and reset.
  `grantReceipt(ledger, seed, slot, encounter)` is the exactly-once hop; helpers
  and aliases never earn a receipt because the identity is the cargo only.

Consumer agreement with lane 18 (#220): the small PanModoki / nest keeps only
per-species parameters and consumes this transition table instead of forking the
contest in `pc_p2_giant_breadbug_actor.cpp`.

Tests: `native/tools/p2_receipt_test.cpp`,
`native/tools/p2_cargo_contest_test.cpp` (registered as CTest
`p2_receipt_test` / `p2_cargo_contest_test`) and the root
`tests/test_pikmin2_receipt_native.py` which compiles the headers against the
resolved native source.

### Runtime regression (experimental Pod ledger)

The `pikmin2_reward_lifecycle` fixture was rebuilt with the provenance builder
against the reconciled native candidate (`opencode/p2-lanes67-native` @
`4c3b32e6`, private build `output/lane67-native-build`; fixture SHA-256
`85EB567D946303391F3DEAA2AF7F9195A3AC3E42898C6EECA8BFFC4E70E1303B`) and run on
the real Snow-Chappy + Research-Pod room with a 960x540 centred window.

```text
P2_POD_RECEIPT id=corpse:385875968 value=2 new=1 pokos=2 seeds=0
P2_POD_RECEIPT id=corpse:385875968 value=2 new=0 pokos=2 seeds=0   # exactly-once
P2_REWARD_SUMMARY generator=385875968 deliver1=1 deliver2=1 pokos=2 corpses=1
```

`reward-evidence.json`: `passed=true`, `ledger_exact=true`, one ledger row.
Run `output/lane67-root/output/lane67-reward-run/2d34475d222347728f11014131e2d3b9`;
log SHA-256 `C46D38D93A3EEA9A76299E0C18D1B8C8A656FFB79F008B8CDDEE4118F3A832BF`.
This is the **experimental `pod`** ledger reached by **injected Pod delivery**
(labelled intervention), i.e. regression evidence, not the ordinary Onion/AP
endpoint acceptance the next wave requires.

### Runtime evidence — ordinary Onion endpoint (exactly-once across restart)

A private fixture (`scripts/p2_ordinary_receipt_fixture.cpp`, native
`opencode/p2-lanes67-native` @ `87740f5d`) boots an ordinary campaign stage with
the **real native randomizer ready** (schema 9, `gameplay-checks-v9`, staged from
`randomizer.seed.generate` with `collection_checks=True`). It kills a real Dwarf
Bulborb, then drives the real corpse through the real Onion absorption endpoint
(`GoalItem::suckMe` -> `pc_randomizer_corpse_delivered` -> `pc_randomizer_check`)
and reads the durable `checks.txt` journal. Reproducer:
`scripts/p2_ordinary_receipt_runtime.py --exe <fixture.exe> --output <new dir>`.

```text
run1  [Pikmin Randomizer] CHECK 30 Bestiary: Deliver Dwarf Bulborb
      checks.txt: 50 30 51
run2  (same session, new process; state.txt already carries the check)
      target CHECK lines: 0      checks.txt: (empty)
EXACTLY_ONCE_ACROSS_RESTART: True
```

- Fixture SHA-256 `42A487E94D74F71665F6927BC9AD3B6BA38E6D14B967C36CF9EA0387BE515D83`.
- Run1 `output/lane67-ordinary-run2/session-32986a81/runs/7237a1ff1828…`
  (log SHA-256 `DA278DEBFEC11B08F7E03FC447CD6ED2E73B8171458388ABA50B2CE44E1D2CBF`).
- Run2 `output/lane67-ordinary-run2/session-32986a81/runs/c72e85290cc1…`
  (log SHA-256 `CA36C6D43C5273567C0739D89133E4FE322A439C60319862673277DC38E4A8D1`).
- Window `960x540` windowed/centred.

Labelled limits: the Pikmin **carry** step is injected — the fixture's natural
carry did not move the corpse (`natural_carry=0`), so it calls the same public
Onion endpoint (`onion->suckMe(corpse)`) directly with the real corpse pellet.
The family drop (real kill -> real corpse), the endpoint, and the durable
ordinary receipt across a fresh process are all real; natural transport remains
lane-04 ownership. This is the ordinary Onion/AP ledger, explicitly not the
experimental Pod path.

### Still open

This surface is not yet wired into a real family transport endpoint in the
maintained engine. The native ordinary endpoint (`GoalItem::suckMe` ->
`pc_randomizer_corpse_delivered` -> `pc_randomizer_check`, durable `checks.txt`)
already exists for P1-proxy corpses; connecting one P2 family drop through it,
and proving no duplicate/lost required reward across revisit/process restart on
a real generated session, remains the lane-06 next slice (needs lane 01 +
real-GL).

