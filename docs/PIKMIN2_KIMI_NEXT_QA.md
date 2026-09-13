# Kimi: next independent QA pass

Use issue #184 for the independent Emergence acceptance lane. The fixed package passed its source, asset and executable preflight again on 2026-09-12. Preserve the package checkout and use its fresh session; do not update it underneath a run.

```powershell
Set-Location C:/Users/alari/pikmin-randomizer/output/p2-manual-qa-bundle
py -3.12 -m scripts.prepare_pikmin2_manual_qa launch output/manual-qa-02/qa-launch.json
```

This command needs the existing local assets and checkout; it is not a portable installer. It starts a fresh session only. Record the manifest, logs and session paths in the report. The fixed package contains a corrected manual App and the earlier fixed cave binary, not a moving development executable.

Priority acceptance is real F6 confirmation/cancellation, settings-open F6 suppression, normal two-floor play, geyser return, and restart after return without duplicated rewards. Compare the actual party, maturity and health at boundaries. The earlier headless QA and injected fixtures do not establish these physical-input cases. If physical input is unavailable, mark these blocked rather than replacing them with fixture success.

A useful independent read-only alternative is to audit the floor-2 partial evidence at `output/p2-floor2-runtime/validation05/partial-evidence.json` against native logs and `docs/PIKMIN2_FLOOR2_FIXTURE.md`. Confirm the report distinguishes successful startup/config rejection from the incomplete second Violet conversion. Report discrepancies on #154; the implementation worker owns the stall diagnostic. Do not edit the live fixture, source or evidence in that lane.

Keep #184 open until its manual gates are actually satisfied. Record new defects separately with exact build hashes and reproducible steps.

## Run 4 handoff

Kimi reports two independent resumes restore the committed floor-entry state: 19 red leaf Pikmin, health 0.899999976, zero receipts. The unsaved late casualty rolls back as intended. Floor-2 egress remains blocked after bounded navigation; do not repeat blind sweeps. Preserve manual-qa-02 and ledger revision 2.

Implementation follow-up #193 owns opt-in position diagnostics and marker audit. The native renderer can draw an imported transition model instead of the cyan fallback ring, so detector absence alone is not a defect. Wait for a concrete navigation handoff or separately versioned diagnostic package; never replace the fixed binary in place.

After egress, verify boundary party/health, completed-trip re-entry refusal and post-return restart preservation. Duplicate-reward coverage requires a nonzero collected receipt and remains UNTESTED.
