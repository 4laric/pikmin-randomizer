# Maintained-export repair manifest

Read-only tooling for the sole integration owner. Issue: #854. Lane:
`export-repair-manifest` (`native = null`).

## What it is for

The compact operator (`py -3.12 -m workflow.operator --root <canonical> --json`)
flags every integrated native lane whose recorded integration receipt cannot
prove a real maintained export. That debt is historical: the lane is already
`done` and its integration receipt is immutable.

`workflow/export_repair.py` reproduces that exact classification and emits one
grouped manifest so the integration owner can run the single maintained export
once and reconcile the exact affected lanes without rewriting history.

## Classification

Each integrated lane with a `native` source record and an `integration` receipt
is classified exactly as the operator does:

| Reason | Meaning |
|---|---|
| `Recorded export evidence hash mismatch` | The evidence file exists but its current SHA-256 differs from `integration.export_sha256`. |
| `Recorded export evidence says none-performed` | The evidence hash matches, but the JSON records `{"action": "none-performed"}`. |
| `Recorded export evidence unavailable` | The recorded `export_evidence` path cannot be read/hashed. |
| *(no reason)* | The lane is not export-repair debt. |

Lanes without an integration receipt, and integration receipts without a native
source record (`native = null`), are never classified as debt.

## Usage

```powershell
# Plan only (default): print the grouped manifest as JSON, write nothing.
py -3.12 -m workflow.export_repair --root C:/Users/alari/pikmin-randomizer

# Inspect one lane's receipt, recorded hash and current evidence hash.
py -3.12 -m workflow.export_repair --root C:/Users/alari/pikmin-randomizer --json --lane muse-kogane

# Write the manifest under output/workflow/export-repair/.
py -3.12 -m workflow.export_repair --root C:/Users/alari/pikmin-randomizer --write

# Fail closed if any recorded receipt or observed evidence changed since a
# previously written manifest.
py -3.12 -m workflow.export_repair --root C:/Users/alari/pikmin-randomizer \
  --write --baseline output/workflow/export-repair/repair-manifest.json
```

## Manifest contents

- `lanes` / `classifications`: the exact debt lane list and each lane's reason.
- `receipts`: every `integration` receipt copied verbatim.
- `recorded_hashes`: per lane `export_evidence`, recorded `export_sha256`,
  currently `observed_sha256`, and the validation path/hash.
- `receipt_fingerprints` / `debt_fingerprints`: fail-closed identities of the
  immutable receipt and of the classified evidence state.
- `maintained_export`: the single maintained step
  `py -3.12 scripts/export_native_source.py`, run by the sole integration lead
  from the canonical root.
- `reconciliation`: one entry per lane with the read-only `--lane` inspect
  command, the operator command, the receipt and both hashes, and an explicit
  `preserve_receipt: true`.

## Guarantees

- The registry is only read. No lane state, integration record or hash is ever
  written or fabricated; all derived output stays under ignored `output/`.
- `prepare`/`--write` takes two registry snapshots and refuses to write if any
  receipt or observed evidence changed between them.
- A `--baseline` manifest makes the run fail closed if any debt lane's receipt
  or evidence identity changed since that baseline.
- The manifest does not replace the maintained export, shared review or
  integration gates. It never merges, exports or accepts work itself.

## Reproduced debt (2026-09-21)

Run from the canonical root against the shared registry:

```powershell
py -3.12 -m workflow.operator --root C:/Users/alari/pikmin-randomizer --json
py -3.12 -m workflow.export_repair --root C:/Users/alari/pikmin-randomizer --write
```

Both the operator and the manifest report **77 integrated lanes**:

- `Recorded export evidence says none-performed`: **70**
- `Recorded export evidence hash mismatch`: **7**

Local (ignored) evidence from that run:

- Manifest: `output/workflow/export-repair/repair-manifest.json`
  SHA-256 `08263dd555d0140fff61f7af5d8a9f3d0369a1af66a9de59750128673d5a6aec`
- Reproduction summary: `output/workflow/export-repair/debt-reproduction.json`
  SHA-256 `bdbedb0701e5de9b4d24b375a3bcf26d9356893226d2adfa773c92ab3e9ff6d9`

The `muse-kogane`/`muse-kurage`/`muse-identityqa` lanes are hash-mismatch
examples; `muse-cave50`/`muse-cave51` are explicit none-performed examples.
Result: a single maintained export is needed before the 77 receipts can be
reconciled; no historical receipt is rewritten.
