# Independent review: Muse l59 / #499 BombSarai58 gate1 handoff (l71, #516)

Reviewer: paid `opencode-go/muse-spark-1.3-contributor`, lane `muse-review-499`,
generation 1, session `ses_f57d6904affeWrCM05FygL1axj` (attempt
`4e53726fa0544ac48add328296e8bbb9`, matches `session-ready.json` rev 2).
Implementation owner: Codex through shared account `4laric`.
Review root: `output/msw/l71-root` at `d684d47e1a35cfc6e65768a6d3b448041e9aaaae`
(branch `codex/muse-l71-review-499`, clean at review time).
Scope: shared-file review + receipt-correction proposal for the existing l59
handoff. No merge, no registry/receipt edits, no native build, no runtime
launch, no gameplay change, no ADMIT. Producer worktrees
(`output/msw/l59-root`, `output/msw/native-l59`) were read-only
(`git log/show/diff` + file reads only).

## Producer pin (verified read-only in producer worktrees)

- Root branch `codex/muse-l59-bombsarai`, base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`,
  head `4e9235e224dbd585f38073e5874b940d2f02a580`, clean. Ordered commits:
  `4ec1a475` (authored observer/tests), `ca3484c3` (cherry-pick #492 `bd97334a`),
  `0ec57fca` (cherry-pick #493 `3131b76d`), `553f75da` (cherry-pick #493 `f82171d4`),
  `04e2a06d` (authored gen-2 validation), `4e9235e2` (handoff doc).
- Native branch `codex/muse-l59-bombsarai-native`, base
  `7b9ecaa668fd55332073446cdbdaf6424b209ea7`, head
  `cb760b27f065e976417b390c9835990cfd1e9994`, clean. Ordered commits:
  `63a87c10` (authored stub), `795cdc8b` (cherry-pick #492 `4765885b`),
  `cb760b27` (authored probe v2).
- Registry `muse-bombsarai` (read-only `status`): gen 2, rev 12, state `blocked`;
  recorded root/native heads match the pins above. Handoff evidence
  `output/muse-wave/l59/handoff.json` sha256
  `176e81fd02fa8616c00b141b603cbd7562c988a6b811e0fc8f52e81777bc9034`.
- `validate-handoff` (read-only, current tool): `reviewable:true`,
  `gameplay_accepted:false`, `slice_passed:true`; 11 `pending_reviews` (all
  shared files, `status:requested`); outstanding gates `attacks_receivers`,
  `cleanup_reentry`, `death_corpse`, `movement_animation`, `transport_reward`
  (only `identity_spawn` PASS).

## Evidence hashes: declared vs fresh recomputation

All recomputed locally in this review (fresh checks); historical values are the
handoff-declared ones. Every file below matched its declaration.

| Artifact | sha256 (declared = recomputed) |
|---|---|
| `output/muse-wave/l59/handoff.json` | `176e81fd02fa8616c00b141b603cbd7562c988a6b811e0fc8f52e81777bc9034` |
| `output/muse-wave/l59/adoption-gen2.md` | `082cb597df480a62a0be127f3fe5eb56ab5bba43f0a0e23ff3c098e05ef9d447` |
| `output/muse-wave/l59/arena/92b1f898ecce42be8555481f28b33080/native.log` (1268 lines) | `58a926ce3ec90fed420a291b0a7fd5c1fe59016b3643e306858c20cf05ff9e3f` |
| `output/muse-wave/l59/build-1789523566253639500.log` | `17b035f4f8792dcba37bc0e135469110cee9aeb5891675fae7c30eb124917dac` |
| `output/muse-wave/l59/checks-gen2.log` (UTF-16; tail: 127 passed) | `cec041d2989f8c91995f8881d86400b95d575dce7b7d5685e3fec4576b8057ac` |
| `output/msw/native-l59-build/bin/nectar.exe` | `5ded849191a9d2e566d023610134191dbbf70a79ef608ef584a6667e5ad615dd` |
| `output/msw/l59-root/docs/PIKMIN2_MUSE_BOMBSARAI_HANDOFF.md` | `568b1bd7735fcf3ccb1c74e4059c24d2c33583a6126cb729016915c2390814a7` |
| `output/muse-wave/l52/dependency-ready.json` | `7f34304b217d21bd35b73ce4174d24fbeffa69f69b2d4bdbde49404ed928e98b` |
| `output/muse-wave/l53/dependency-ready.json` | `6bcb75881051913b53111bed2afe2c77b2c08eaa1dd6255ed140f2f540068c3a` |
| `output/muse-wave/l59/integration-validations.log` | `d29c91dfe5a01f9366b6f88cba42da4de843bcd5dda7860abc9e3c2fd1c32b3d` |
| `output/muse-wave/l59/export-evidence.json` | `966e5a1a6ea90095dda512bcda2c955ae5272ab980a0bc4a8c59bc67bf0ee848` |

Fresh spot check of the cited runtime markers (read-only read of the recorded
`native.log`; line numbers 1-indexed): `:14` 960x540 centered window, `:247`
`red=20`, `:585` `P2_SEED_RESOLVE source_id=58 target=1787125272`, `:586`
`P2_GENERATED_PLACEMENT ... generator=270001 bound=1`, `:722` TEKI_READY,
`:765` TEKI_SUPPLY, `:783` JOINT_FOLLOW, `:795` PROBE nearest=0.101 squad=20,
`:936` MOVE Release, `:1000` TEKI_DEAD, `:1001` `P2_FUEFUKI_TEKI_DEAD` watcher
line (as disclosed). The gate1 correlation claim (resolve + bound=1 on accepted
slot 1787125272 + READY/SUPPLY on generator 270001) is consistent with the
recorded log. The `checks-gen2.log` tail (127 passed; gate1 accepted PASS,
gates 2/4 descriptive PARTIAL, 3/5/6 UNTESTED) matches the handoff's honest
no-PASS-beyond-gate1 posture. No new runtime was launched for this review.

## Findings

1. Gate1 evidence is sound and honestly scoped. `handoff.json` claims PASS only
   for `identity_spawn` (method `natural`, evidence `arena`); the other five
   gates are `UNTESTED` with explicit family-seam retention
   (`output/muse-wave/l59/handoff.json`: `gates`, `remaining_work`). Source
   mapping cites `enemyInfo.h:117`, `generalEnemyMgr.cpp:406-407`,
   `genEnemy.cpp:558`, `BombSaraiState.cpp:19-35`, `BombSarai.cpp:263-294`,
   `bombState.cpp:159-190` via `docs/PIKMIN2_BOMBSARAI_AUDIT.md`; those lines
   were not re-audited here (out of scope) but the runtime correlation legs
   were verified against the recorded log as above.
2. Shared-file consumption is verbatim (fresh `git diff` checks, read-only).
   `bd97334a` vs `ca3484c3`, `3131b76d` vs `0ec57fca`, `f82171d4` vs `553f75da`,
   and native `4765885b` vs `795cdc8b` all differ only by pre-existing
   l59-authored files; the 11 shared files are byte-identical to the reviewed
   candidates. Producer diff base-to-head touches exactly 15 files: the 4 owned
   files plus the 11 pending-review shared files (root 11 files / +1980,
   native 4 files / +404/-1). Disposition proposal per file is in the table
   below; all remain `requested` so only the integrator (with #492/#493
   owners) can approve.
3. Receipt defect (correction proposal — the blocking issue). Recorded
   `output/muse-wave/l59/integration-receipt.json` pins `root_commit
   e7049cb1683337dbdc6db6c02f4d705d3c31f685` / `native_commit
   a2ae0513ebff44bb0450d48b4ef124b14527b5e8` in worktrees
   `output/dsw/wave-root` + `output/dsw/native-wave`, and
   `export-evidence.json` cites `output/dsw/native-wave-build` with exe
   `a7e0977a...`. None of these match the producer pins (`4e9235e2` /
   `cb760b27` in `output/msw/l59-root` + `output/msw/native-l59`). The
   registry `next_action` already records this receipt as invalid and names
   the correction. The integrator must NOT integrate `e7049cb1`/`a2ae0513`
   for this lane.
4. Minor doc-vs-handoff label mismatch. `docs/PIKMIN2_MUSE_BOMBSARAI_HANDOFF.md`
   six-gate table (lines 137-142) marks gates 2 and 4 `PARTIAL` while
   `handoff.json` classifies them `UNTESTED` (no PASS claimed in either).
   Recommend aligning the doc wording to `UNTESTED` (keeping the descriptive
   FSM/kill observations) so the table cannot be misread as partial credit.
5. Adoption record is complete for gate1: fresh private arena
   `92b1f898ecce42be8555481f28b33080`, overlay reds=20 + 960x540 observed live,
   exe `5ded8491...` identical across both leased builds, staged-vs-observed
   ~40 u position caveat disclosed, corpse receipt/re-entry explicitly left
   open. No ADMIT writes, no allowlist edits, no shared-hook edits.

## Proposed shared-file dispositions (integrator approval required)

| File | Source | Disposition |
|---|---|---|
| `experimental/pikmin2_muse_placement.py` | #492 `bd97334a`, verbatim | approve consumption |
| `tests/test_pikmin2_muse_placement.py` | #492 `bd97334a`, verbatim | approve consumption |
| `docs/PIKMIN2_MUSE_PLACEMENT_HANDOFF.md` | #492 `bd97334a`, verbatim | approve consumption |
| `randomizer/p2_placement_catalog.py` | #492 `bd97334a`, verbatim | approve consumption |
| `native/pc_port/pc_p2_generated_placement.cpp` | #492 `4765885b`, verbatim, built+exercised | approve consumption |
| `native/pc_port/pc_p2_generated_placement.h` | #492 `4765885b`, verbatim | approve consumption |
| `native/tools/p2_muse_placement_fixture.cpp` | #492 `4765885b`, verbatim, unwired | approve consumption |
| `experimental/pikmin2_family_install.py` | #493 `3131b76d`, verbatim (58 bombsarai binding reused as-is) | approve consumption |
| `experimental/pikmin2_muse_packaging.py` | #493 `3131b76d`, verbatim | approve consumption |
| `tests/test_pikmin2_muse_packaging.py` | #493 `3131b76d`, verbatim | approve consumption |
| `docs/PIKMIN2_MUSE_PACKAGING_HANDOFF.md` | #493 `f82171d4`, verbatim | approve consumption |

## Proposed corrected receipt (integrator to write, not this review)

- `root_commit`: `4e9235e224dbd585f38073e5874b940d2f02a580` (`dirty: ""`,
  `root_worktree: output/msw/l59-root`).
- `native_commit`: `cb760b27f065e976417b390c9835990cfd1e9994` (`native_dirty:
  ""`, `native_worktree: output/msw/native-l59`).
- Regenerate export evidence from the maintained export at those heads (the
  current `export-evidence.json` describes `output/dsw` state, not this
  handoff) and re-run the validation log, then record fresh
  `export_sha256`/`validation_sha256`.
- Then `accept-review` for `muse-bombsarai` gen 2; keep family gates 3/5/6,
  corpse receipt, and re-entry with lane 27 / providers #408/#128.

## Recommendation

REVISE (conditional accept): the gate1 correlated-birth evidence and the
verbatim shared-file consumption are accepted as reviewed; DO NOT integrate
until (a) the 11 shared reviews are approved with #492/#493 owners, (b) the
corrected receipt + fresh export/validation evidence above replace the invalid
`e7049cb1`/`a2ae0513` receipt, and (c) the gate 2/4 `PARTIAL` wording is
aligned to `UNTESTED`. No ADMIT: gameplay acceptance remains with the existing
integrator and the family seam.

## Exact remaining integrator actions

1. Approve (or reject with reason) the 11 shared-file consumptions listed
   above, coordinating #492/#493 owners; they are verbatim but still
   `requested`.
2. Write the corrected receipt per the proposal (heads `4e9235e2`/`cb760b27`,
   `output/msw` worktrees, fresh export + validation hashes); discard the
   `e7049cb1`/`a2ae0513` `output/dsw` receipt for this lane.
3. `accept-review` for `muse-bombsarai` gen 2 through the controller/CLI, then
   run the normal integration sequence.
4. Align handoff-doc gates 2/4 wording to `UNTESTED` (descriptive observations
   retained) or record acceptance of the current wording.
5. Leave gates 3/5/6, corpse receipt, and re-entry to lane 27 / providers;
   l59 correctly does not take them over.

## Review provenance

- Review lane `muse-review-499`, issue #516, gen 1, rev 2 at write time; evidence
  dir `output/workflow/paid-scale/l71`.
- This document: `docs/PIKMIN2_MUSE_REVIEW_499.md` in `output/msw/l71-root`
  (sole owned file; only file edited).
- Historical evidence (producer logs, commits, registry handoff record) vs
  fresh checks (hash recomputation, log line reads, `validate-handoff`,
  `git diff` ancestry checks, registry `status` read) are labeled as such
  above. No producer file, receipt, registry entry, or gameplay state was
  modified.
