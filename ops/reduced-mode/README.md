# Reduced-mode toolkit

Handbook: `docs/PIKMIN2_REDUCED_MODE_INTEGRATOR.md`. State lives in the workspace, not here:
`output/reduced/lanes.json` (lane manifest) and `output/reduced/briefs/`.

| Tool | Use |
|---|---|
| `triage.py <out.json>` | read-only: branches with commits not on the canonical lines |
| `check_lanes.py --root <ws> rd-...` | read-only: is a new lane's issue or file held by an unfinished lane |
| `setup-lanes.ps1 -Root <ws> -Lanes @(...)` | worktrees, brief, opencode.json, provision + configure launch (controller stopped; call with `&`) |
| `reduced_setup.py kickoff --root <ws> --lanes ...` | plan first launch of configured lanes (`validate` checks controller-side config) |
| `land-batch.ps1 root\|native <sha>` | fast-forward a line to a merge-tested sha and push |
| `record_landing.py --root <ws> --lane rd-x [--dry-run]` | integration receipt for a landed lane (frees its worker) |
| `apply-reduced-mode.ps1` / `revert-reduced-mode.ps1` | config patch in / out (`reduced-mode.patch.json`) |
| `add-reduced-lanes.ps1` | optional config.json lane entries (`reduced-lanes.patch.json`); registry launch specs suffice |
| `retire_old_lanes.py [--dry-run\|--undo <json>]` | remove pre-reduced launch specs, with undo record and registry backup |
| `tests/` | scratch-registry fixtures used to rehearse the retire/setup steps |
