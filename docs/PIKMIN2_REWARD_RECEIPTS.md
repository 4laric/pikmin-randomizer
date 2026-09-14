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

## Malformed input

`validate_descriptor`/`validate_descriptors` raise `ValueError` for an unknown
version, duplicate identity, invalid drop kind, negative/non-integer counts,
unknown ledger tag, missing/unknown fields, or a malformed identity/family.
`ReceiptLedger` rejects a malformed or wrong-version persistence state.

## Limitations

- **Source Pelplant pellet/Onion behavior is not implemented.** Pelplant pellet
  capture/release, pellet-to-Pom conversion and Onion seed/sprout grants remain
  family-owned work (#397, lane 23). A proxy Chappy corpse is not source Pelplant
  and must not be counted as one. This slice only defines and reconciles the
  descriptor/receipt contract.
- No native save is read or written; persistence is an in-memory fake. Real save
  mutation, binary layout and lane 01 coordination are untouched.
- No retail assets are consumed, and no family drop value is asserted as source
  truth here.
- Coverage is a host-side bookkeeping check, not a runtime or AP-logic proof.
