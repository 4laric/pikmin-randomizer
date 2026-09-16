# P2 handoff reconciliation diagnosis and fenced repair (#511)

Owner: Codex via shared 4laric; contributor muse-p2-reconcile (lane 75, generation 1).
Scope: Kogane (#494), Fuefuki (#497), BombSarai (#499) integration blockers only.
No gameplay change, no relaunched implementation, no ADMIT, no SQLite edits.

## 1. False premise corrected: output/dsw exists and holds the ancestry

The shepherd/blocked outcomes for muse-fuefuki and muse-bombsarai claim their
integration receipts are "invalid at the source" because they point at a
"non-existent output/dsw wave" and propose producer lane heads instead.

Both premises are wrong, verified locally:

- `output/dsw/wave-root` exists, HEAD `1c8810e4` ("wave: re-export engine/ at
  native f05e3162"). `output/dsw/native-wave` exists, HEAD `f05e3162`.
- Receipt commits are genuine integrated wave merges and ancestors of HEAD:
  - l54/Kogane: root `7b61c0ce` ("wave: merge muse lane 54 ..."), native
    `239c7528` ("wave-native: merge muse lane 54 ...").
  - l57/Fuefuki: root `339b17b5` ("wave: merge muse lane 57 Fuefuki41 ..."),
    native `48219915` ("wave-native: merge muse lane 57 ...").
  - l59/BombSarai: root `e7049cb1` ("wave: merge muse lane 59 BombSarai58 ..."),
    native `a2ae0513` ("wave-native: merge muse lane 59 ...").
  - All six verified with `git merge-base --is-ancestor <receipt> HEAD`.
- Receipt semantics require integrated commits, not producer heads: the
  proposed "corrections" (`a67bc805`/`499e513c`, `4e9235e2`/`cb760b27`) are the
  producer lane heads. `receipt()` itself enforces this direction (lane head
  must be an ancestor of the record commit). Substituting producer heads
  would invert the check.
- All three receipts' export/validation evidence hashes still match the files
  on disk (`export-evidence.json`, `integration-validations.log`).

The l68/l70/l71 review dispositions (muse-review-494/497/499, all `done`)
repeat the producer-head receipt proposal; that part of the reviews is
incorrect and was not actioned. Their gate evidence findings stand.

## 2. Exact failures reproduced (natural evidence, hashes verified)

| Lane | Issue | State / worker | Reproduction | Root cause |
|---|---|---|---|---|
| muse-kogane (muse-wave l54) | #494 | `handoff_ready`, worker pid 4656 **alive** (exact identity match via `workflow process`) | `validate-handoff` on `output/muse-wave/l54/handoff.json` returns `Evidence hash mismatch: adoption` | Post-submission commit `59b5ed11` edited `docs/PIKMIN2_MUSE_KOGANE_HANDOFF.md`, which is pinned as both `adoption` and `source` evidence (recorded `aec14f69…`, now `ccb7c913…`). Only the live owner may submit a NEW handoff. Do not touch this lane. |
| muse-fuefuki (muse-wave l57) | #497 | `blocked`, worker pid 22896 **dead** | `receipt` with `output/muse-wave/l57/integration-receipt.json` returns `Validated implementation handoff required`. Ancestry/hash gates ahead of it pass. | Shepherd `finish(blocked)` parked a valid handoff in a state with no return path (see §3). Handoff revalidates clean; 11 shared-review pendings on l52/l53 files remain. |
| muse-bombsarai (muse-wave l59) | #499 | `blocked`, worker pid 8056 **dead** | Same `Validated implementation handoff required` on its receipt. | Same structural blocker as l57. |

Read-only `check_handoff` against the production registry (new code path,
zero writes): l57/l59 PASS with 11 pending reviews each; l54 correctly
rejected with the adoption mismatch.

## 3. Supported-API gap (no safe transition exists)

- `receipt()` requires state in (`handoff_ready`, `integrating`); blocked lanes fail closed.
- `TRANSITIONS['blocked']` is only {`ready`, `running`}; both clear the handoff record (`registry.py`, checkpoint into ACTIVE). Returning to `running` would destroy finished evidence and risk duplicate implementation.
- `submit_handoff` rejects blocked lanes, so a corrected handoff cannot even be filed for l57/l59 while blocked.
- `integrate()` additionally requires zero pending reviews, so restoring eligibility does not weaken review gating.

## 4. Fenced correction delivered (private worktree only, not deployed)

`workflow/control.py`: new `ControlMixin.reconcile_handoff(key, generation,
revision, summary, evidence)` — blocked → handoff_ready only, failing closed
unless: fresh generation/revision; recorded worker confirmed dead (live or
uninspectable refused); no live/unknown lease or queued request for the
lane/generation; no in-flight controller launch for the lane/generation; the
submitted handoff plus all referenced evidence revalidates via the existing
`check_handoff`. Preserves handoff record, source identities and pending
reviews; clears only the stale blocked outcome/dependencies; bumps revision;
records a `handoff_reconciled` event. `integrate()` behaviour is untouched.

`scripts/reconcile_pikmin2_handoffs.py`: thin audited wrapper (explicit
key/generation/revision); all guards stay in the registry method.

`tests/test_pikmin2_reconciliation.py`: 10 tests — happy path through to
`integrate`/`done`; stale generation/revision; live and unknown owner
refusal; handoff-file and evidence drift refusal; non-blocked and
handoff-less rejection; pending reviews surviving reconcile with integrate
still refusing (`Resolve shared reviews before integration`); in-flight
launch refusal; live-lease refusal with dead-lease tolerance.

Validation: 10/10 new tests pass; existing
`test_pikmin2_workflow` + `test_pikmin2_controller` +
`test_pikmin2_fixture_build` pass (76 tests, no regressions).

## 5. Exact invocation for the root coordinator (after tooling integration)

Do not run against production from this private worktree. After the method is
integrated into maintained tooling, for each of muse-fuefuki (gen 2) and
muse-bombsarai (gen 2), with a FRESH revision read from `status` and a hashed
diagnosis evidence file:

```powershell
py -3.12 scripts/reconcile_pikmin2_handoffs.py --root C:/Users/alari/pikmin-randomizer `
  --key muse-fuefuki --generation 2 --revision <fresh> `
  --summary "Reconcile #511: dead owner, handoff revalidated" `
  --evidence output/workflow/integration-speedup/l75/reconcile-evidence.md
```

Expected: state `handoff_ready`, handoff sha unchanged, 11 pending reviews
preserved. Then the species integrator approves the shared l52/l53 reviews
through a NEW versioned handoff (only it can), and completes `receipt` with
the existing valid receipt files. Kogane (#494) is excluded: its worker is
alive and its evidence must be refreshed by its owner first.

## 6. Remaining work (not done in this slice)

- Integrator decision on the 11 shared l52/l53 reviews for l57/l59 and the
  corrected NEW handoffs carrying approvals.
- Kogane owner resubmission after evidence refresh (lane live; untouched here).
- Root-tooling integration of `reconcile_handoff` + CLI wiring (method is
  additive; no existing behaviour changed).
- Issue #511 update with this evidence and the inbox coordination record.
