# Native Beasts party restoration diagnostic (#290)

Owner: Codex using shared 4laric account. A fresh native fixture process can now
load a supplied party snapshot through the existing `P2_CAVE_ENTRY_1` loader,
run 300 fixture updates, and compare its native outgoing health, species and
maturity to the input. Production restore code and its schema are unchanged.

The input JSON has exactly `health` and `squad` fields, using the snapshot format
from #287. This diagnostic accepts twenty Red/Purple survivors, finite positive
health up to one, and maturity 0–2. It rejects unsupported parties before staging.
The runner creates a fresh private overlay, copies the input into its hashed
inputs, creates a random entry token, and encodes native color IDs using the
existing campaign species mapping (Red=1, Purple=3).

The stage suppresses flowers using a declared generation count of twenty.
`--refund` cannot be combined with restoration. The native fixture checks
population, no sprouts/flowers and unchanged repairs, then emits its actual
party snapshot. The host additionally verifies the native loader's ordered
restore records, survivor order/species/maturity, health within float precision,
completion and no conversion/reward diagnostics. Inputs and executable remain
hash-checked during the run.

```powershell
python -m experimental.pikmin2_beasts_floor2_runtime --root ../.. --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --exe output/beasts290-final/linked/fixture.exe --output output/beasts290-repeat --global-purple-count 20 --restore-party output/beasts290-final/recorded-party.json
```

The recorded input was extracted from #287's refund run, with nine Reds and
eleven Purples. A second explicitly engineered input preserves that species
order, sets health to 0.625 and cycles maturity through leaf, bud and flower.
Both restored successfully and retained their fields through 300 updates.

This is **party restoration only**. It intentionally generates a fresh empty
floor, does not restore flower budgets, geometry state, receipts or individual
actor identities, and does not exercise descent. The production cave active
gate still excludes cargo-free Beasts, so no campaign handoff is enabled.
Native token authentication, actual floor transitions, single-ledger persistence
and playable floor3 remain open. It must not be presented as campaign resume.

Native fixture candidate: `3426fd87930a3c7b7bee3a02206c9795bda69fbf`.
Private provenance-bound link reports no pending production build work before
or after linking. Executable SHA256:
`49c8735c6fb8ebf391252ac0a961f04c02702d63b21229fed70c4983f2b604d3`.

Focused restore/snapshot/bridge/runtime/generation/checkpoint/lifecycle and
fixture-builder suites passed 47 tests and 113 subtests. Tests cover malformed
party fields, wrong health/species/maturity, missing loader evidence, unexpected
conversion/reward records, valid enum encoding and input immutability.

Native evidence under `output/beasts290-final/`:

| Case | Run directory | Log SHA256 |
|---|---|---|
| Recorded party | `recorded/ae778c0041024c70bb6fbd3f38e7c4d2` | `2931597914c2507f01ca7b7f0fe9e9ef1e3fc69b89fd4bcd5cf02a7769569051` |
| Health 0.625, mixed maturity | `mixed/53a6d7805313413b833dfdb9a55fc250` | `3de2d19005523af2fbba729e728ffd538e93ac8a84f8a8bbe433016bfb4aa25c` |
| Ordinary conversion regression | `ordinary/ccff065e5e2444f3a9ff3eda76e9d7c8` | `fd516fc37e7e63c02df01a224725e602c9bfa4fbf593f4e60da57c3d275cc013` |

All passed with zero cargo/Pokos and unchanged repairs/input/executable hashes.
The ordinary case retains ten Red-to-Purple conversions and a final ten Reds/
ten Purples. Both restoration logs also passed the final strict restore-record
validator after adding rejection of extra malformed records.
