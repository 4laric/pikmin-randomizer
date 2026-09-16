# Muse l66 identityqa handoff — independent generated identity contract regression (#506)

Lane muse-identityqa, child of #440, wave #491. Implementation owner: Codex
through shared GitHub account 4laric; contributor Muse Spark 1.3 via OpenCode.
Private root `output/msw/l66-root`, private native `output/msw/native-l66`.

## Scope

Independent audit of candidate contracts produced by muse-placement (l52/#492)
and muse-packaging (l53/#493) for source IDs 41, 57, 58, 78. Additive
adversarial regression runner covering swapped source IDs, mismatched
generator/slot, missing assets, stale replay and unsupported terrain. Owns new
identityqa files only; shared placement/packaging files and the four consumer
observers (l57-l60) untouched. No ADMIT writes, no admission-flag edits, no
natural gate PASS invented: this is verification tooling supporting the
closest-to-ADMIT families.

## Artifacts

- `experimental/pikmin2_muse_identityqa.py` — stdlib-only adversarial runner:
  `audit_log` (per-candidate log verdict + classified findings),
  `audit_assets` (manifest/hash check), `audit_replay` (plan-digest /
  cache-generation freshness), `run_adversarial` (expectation runner).
- `tests/test_pikmin2_muse_identityqa.py` — 21 tests + 4 subtests, all passing
  (evidence `output/muse-wave/l66/pytest-identityqa.log`).
- `native/tools/p2_muse_identityqa_fixture.cpp` — stdlib-only C++ checker,
  `-Wall -Wextra -Werror` clean under MinGW g++ 16.2.0; exit 0 on a correlated
  triple sample, exit 1 on a swapped-source sample; Python runner agrees on
  both (`output/muse-wave/l66/sample-pos.log`, `sample-neg.log`,
  `p2_muse_identityqa_fixture.exe`).
- Consumer contract sources read (read-only): l57 Fuefuki observer + tests,
  l58 Kurage observer, l52 `plan-findings.md`, l53 `plan.json`, roster entries
  41/57/58/78 (all spawnable, `use_own_id`; 58 carries child Bomb x2).

## Adversarial classes pinned by tests

1. swapped-source: resolve/placement naming another source id, or another
   family's binding, on the audited slot — FAIL with exact ids.
2. generator-slot: resolve/placement slot disagreement, binding generator
   mismatch, `bound=0` refusal — FAIL.
3. missing-assets: manifest entry absent or staged hash disagreeing — finding.
4. stale-replay: plan-digest / cache-generation disagreement — finding.
5. unsupported-terrain: water/air terrain, missing `xyz=1` fix, `slot=0`,
   missing `route=1` — FAIL (mixed shore allowed only for Kurage57).
6. injected-taint: `injected`/`health_zero` on birth/correlated markers —
   FAIL, labelled; can never close a natural gate.

## Six-gate evidence (per identity, honest)

No natural runtime has been run by this lane and none is claimed. Gate 1 is
BLOCKED on the reviewed l52 placement bind + l53 packaging staging
candidates (neither has published `dependency-ready.json` yet). Gates 2-6
belong to the consumer lanes (l57/l58/l59/l60) and legacy holders; UNTESTED
here, nothing relabelled.

## Concrete source ID

- Source ID: 41 `Fuefuki`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | output/muse-wave/l66/sample-pos.log correlated-triple contract verified on synthetic samples only; no real generated run yet — needs l52/#492 case-41 bind + l53/#493 staging | natural (no runtime claim) |
| 2. Autonomous movement and animation | UNTESTED | owned by muse-fuefuki l57/#497; not re-evaluated here | natural |
| 3. Attacks and receivers | UNTESTED | owned by muse-fuefuki l57/#497; not re-evaluated here | natural |
| 4. Death and corpse | UNTESTED | owned by muse-fuefuki l57/#497; not re-evaluated here | natural |
| 5. Actual transport and reward | UNTESTED | owned by muse-fuefuki l57/#497; not re-evaluated here | natural |
| 6. Cleanup and re-entry | UNTESTED | owned by muse-fuefuki l57/#497; not re-evaluated here | natural |

## Concrete source ID

- Source ID: 57 `Kurage`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | output/muse-wave/l66/pytest-identityqa.log mixed-terrain rule pinned for Kurage57; no real generated run yet — needs l52/#492 case-57 bind + l53/#493 staging | natural (no runtime claim) |
| 2. Autonomous movement and animation | UNTESTED | owned by muse-kurage l58/#498; not re-evaluated here | natural |
| 3. Attacks and receivers | UNTESTED | owned by muse-kurage l58/#498; not re-evaluated here | natural |
| 4. Death and corpse | UNTESTED | owned by muse-kurage l58/#498; not re-evaluated here | natural |
| 5. Actual transport and reward | UNTESTED | owned by muse-kurage l58/#498; not re-evaluated here | natural |
| 6. Cleanup and re-entry | UNTESTED | owned by muse-kurage l58/#498; not re-evaluated here | natural |

## Concrete source ID

- Source ID: 58 `BombSarai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | output/muse-wave/l66/sample-neg.log swapped-source (58-vs-41) correctly refused by both runners; no real generated run yet — needs l52/#492 case-58 bind + l53/#493 staging | natural (no runtime claim) |
| 2. Autonomous movement and animation | UNTESTED | owned by muse-bombsarai l59/#499; not re-evaluated here | natural |
| 3. Attacks and receivers | UNTESTED | owned by muse-bombsarai l59/#499; not re-evaluated here | natural |
| 4. Death and corpse | UNTESTED | owned by muse-bombsarai l59/#499; not re-evaluated here | natural |
| 5. Actual transport and reward | UNTESTED | owned by muse-bombsarai l59/#499; not re-evaluated here | natural |
| 6. Cleanup and re-entry | UNTESTED | owned by muse-bombsarai l59/#499; not re-evaluated here | natural |

## Concrete source ID

- Source ID: 78 `MiniHoudai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | tests/test_pikmin2_muse_identityqa.py MiniHoudai78 binding contract pinned; no real generated run yet — needs l52/#492 case-78 bind + l53/#493 staging | natural (no runtime claim) |
| 2. Autonomous movement and animation | UNTESTED | owned by muse-groink l60/#500; not re-evaluated here | natural |
| 3. Attacks and receivers | UNTESTED | owned by muse-groink l60/#500; not re-evaluated here | natural |
| 4. Death and corpse | UNTESTED | owned by muse-groink l60/#500; not re-evaluated here | natural |
| 5. Actual transport and reward | UNTESTED | owned by muse-groink l60/#500; not re-evaluated here | natural |
| 6. Cleanup and re-entry | UNTESTED | owned by muse-groink l60/#500; not re-evaluated here | natural |

## Remaining work

Watch l52/l53 `dependency-ready.json` and issue checkpoints; when published,
cherry-pick reviewed candidate commits read-only into the audit loop, feed a
real generated run log through both runners, and report the gate-1 verdict
per identity. Fixture adoption (fresh arena, 960x540, starting squad) is N/A
for this tooling-only slice: no runtime claim is made. Tooling-only handoff;
native `null` claim is consistent (no engine change, stdlib checker only).
