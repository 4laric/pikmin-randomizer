# Native receipt-ledger endpoint binding for overworld runtime (#749)

Provider treasure-receipts scope: binds the four #724 pins behind an
engine-free native API plus a guarded standalone fixture, for the blocked
#150 overworld runtime consumer (recovery 3768bed8). No family FSM work, no
second ledger, no divergent treasure implementation, no ADMIT.

## Owned files (NEW)

- `native/pc_port/pc_p2_receipt_ledger_endpoint.{h,cpp}` - engine-free ordered
  four-stage policy over the existing `P2Receipt::ReceiptLedger`
  (header-inline; TU reserved for integrator wiring under #186 review).
- `native/tools/p2_receipt_ledger_endpoint_fixture.cpp` - standalone
  stdlib-only checker (guard self-test, happy path, 8 negatives).
- `experimental/pikmin2_receipt_ledger_binding.py` - Python binding contract
  mirroring the stage machine plus the log-grammar validator.
- `tests/test_pikmin2_receipt_ledger_binding.py` - focused tests.
- `docs/PIKMIN2_RECEIPT_LEDGER_ENDPOINT.md` - this doc.

## Pinned call sites (#724 discovery, read-only)

| Stage | Site | Line |
|---|---|---:|
| SuckReady (gate check) | Onyon::isSuckReady | 195 |
| ActOnyon (suck action) | InteractSuckDone::actOnyon | 403 |
| ObtainPellet (payload) | PlayData::obtainPellet_Main | 800 |
| LedgerWrite (durable grant) | ledger write | 832 |

Contract: the four stages occur in order per receipt attempt. Out-of-order,
repeated or malformed stages are refused with a marker and leave state
unchanged. The durable grant goes through the caller-supplied ledger, so
exactly-once and persistence are inherited, never reimplemented.

## #186 owner decision (recorded)

No engine landing is requested by this slice: `Onyon.cpp`,
`InteractSuckDone`, and `PlayData.cpp` hooks are NOT touched, and no shared
file is modified. The endpoint is additive-only (3 new native files + 3 new
root files). Any future hook landing requires explicit #186 review first;
silence is not consent. No such review has occurred or is claimed here.

## Verification

- Native: `g++ -std=c++17 -Wall -Wextra -Werror` clean; contract PASS
  (4 stages, 8 negatives); guard self-test 7/7; negative exit 86.
- Python: 8 focused tests pass (happy path, order/malformed refusals,
  duplicate grant, log validator incl. captain-down).
- Downstream consumer `p2-overworld-yakushima-p1-native-runtime` (#150)
  named; all six runtime gates UNTESTED; no gameplay claim.
