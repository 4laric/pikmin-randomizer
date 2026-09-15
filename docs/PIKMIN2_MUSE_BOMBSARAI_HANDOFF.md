# Muse contributor 59: BombSarai58 correlated natural generated birth (l59, #499)

Implementation owner: Codex through shared GitHub account 4laric; executing
contributor Muse Spark 1.3 through OpenCode. Parent #244; wave #491.
Root worktree `output/msw/l59-root` (`codex/muse-l59-bombsarai`);
native worktree `output/msw/native-l59` (`codex/muse-l59-bombsarai-native`).
Legacy lane-27 claim, family projectile/FSM, and shared placement files were
read-only; nothing outside the four reserved files was touched.

## Scope delivered (independent slice)

Additive gate1 observer plus negative tests against the existing lane-27
correlated marker contract. The observer
(`experimental/pikmin2_muse_bombsarai.py`) layers placement/source
correlation on top of the lane-27 teki validator (reused read-only, never
forked): READY/SUPPLY binding generators must equal the candidate
generated-placement generator, and the placement source resolve must be 58.
A P1 Napkid birth without a matching source-58 placement resolve reports
`placement-pending` and never correlates.

Placement (#492) and packaging (#493) candidate commits are still pending
(no `dependency-ready.json` in `output/muse-wave/l52` or `output/muse-wave/l53`
at handoff time), so gate1 stays BLOCKED on reviewed dependency artifacts.
Gates 2-6 are UNTESTED in this contributor scope; lane-27's accepted
movement/combat/death/reward/re-entry evidence is preserved read-only and is
not relabeled here.

## Ordered commits

Root branch `codex/muse-l59-bombsarai` (base `72a2c450`):

1. observer + tests + handoff for correlated generated birth (#499)

Native branch `codex/muse-l59-bombsarai-native` (base `7b9ecaa6`):

1. engine-free gate1 correlation stub + standalone self-check (#499)

Dirty state at handoff: none on either branch (reserved files only).

## Files owned / interfaces touched

- `experimental/pikmin2_muse_bombsarai.py` — new correlated-birth observer.
- `tests/test_pikmin2_muse_bombsarai.py` — 10 observer tests, all pass.
- `docs/PIKMIN2_MUSE_BOMBSARAI_HANDOFF.md` — this file.
- `native/tools/p2_muse_bombsarai_fixture.cpp` — engine-free correlation stub,
  not wired into CMakeLists.txt, never linked into production.

No shared semantics changed. No ADMIT writes, no allowlist edits.

## Tests run

- `py -3.12 -m pytest tests/test_pikmin2_muse_bombsarai.py -q` → 10 passed
  (empty log, correlated dict/text placement, Napkid-without-placement
  refusal, generator/source mismatch, supply-missing, throw-without-ready,
  malformed placement).
- Standalone native contract probe (`-Wall -Wextra -Werror`) → build exit 0,
  `contract=muse-bombsarai-gate1-v1 vehicle=11 failures=0`.
- Observer self-check against the real lane-27 historical runtime log
  `output/dsw/l27-out/bombsarai-teki-run-fix2.log` (read-only, 1272 lines):
  with an assumed matching placement record
  `{source_id: 58, generator: 270001}` it reports `correlated` (READY/SUPPLY
  generator 270001, 5 blasts, Release, dead=True, corpse=False); without a
  placement record it reports `placement-pending`. The assumed placement
  record is a self-check input, not gate1 evidence: no reviewed placement
  candidate exists yet.

## Six-gate evidence (Source ID: 58 BombSarai)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED (placement/packaging candidates pending) | tests/test_pikmin2_muse_bombsarai.py experimental/pikmin2_muse_bombsarai.py output/muse-wave/l59/gate1-probe.exe | natural (observer logic unit-verified; no runtime PASS claimed) |
| 2. Autonomous movement and animation | UNTESTED (lane-27 pinned-arena evidence read-only, not relabeled) | output/deepseek-wave/handoffs/l27.md | injected (lane-27 pinned carrier; see l27 handoff) |
| 3. Attacks and receivers | UNTESTED (lane-27 InteractBomb evidence read-only, not relabeled) | output/deepseek-wave/handoffs/l27.md | injected (lane-27 carrier/receivers; see l27 handoff) |
| 4. Death and corpse | UNTESTED (natural-kill branch read-only, not relabeled) | output/deepseek-wave/handoffs/l27.md | injected (see l27 handoff fix2 notes) |
| 5. Actual transport and reward | UNTESTED (no corpse receipt observed in this scope) | output/deepseek-wave/handoffs/l27.md | injected (carry stall documented in l27 handoff) |
| 6. Cleanup and re-entry | UNTESTED (single-session scope) | output/deepseek-wave/handoffs/l27.md | injected (not exercised here) |

## Remaining blockers (named providers)

- `output/muse-wave/l52/dependency-ready.json` (muse-placement #492):
  candidate legal-slot profile + native binding path for source 58.
- `output/muse-wave/l53/dependency-ready.json` (muse-packaging #493):
  candidate generated-session staging for source 58.
- On arrival: cherry-pick reviewed candidate commits into the private
  worktrees (preserving this slice), re-run the observer against a fresh
  generated-session log, and promote gate1 only on a real correlated
  placement + source-resolve + binding marker chain.
