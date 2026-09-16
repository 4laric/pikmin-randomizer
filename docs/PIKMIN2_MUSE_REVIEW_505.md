# Independent review: Muse l65 / #505 Honeywisp pushed-source reconciliation and gate N/A (review for #517)

Implementation owner: Codex through shared account `4laric`. Executing reviewer:
Muse Spark 1.3 Contributor through OpenCode (`opencode-go/muse-spark-1.3-contributor`),
lane `muse-review-505`, child issue #517, parent #505.
Review worktree: `C:\Users\alari\pikmin-randomizer\output\msw\l72-root`
at `d684d47e1a35cfc6e65768a6d3b448041e9aaaae` (clean at review time).
No native worktree for this review lane (`native: null`).
No ADMIT granted by this review. No merge, no gameplay change, no native build,
no new runtime run claimed.

## Recommendation: REVISE (minor) then accept as review evidence — do not admit gameplay

The l65 bounded slice is honest and review-ready as **evidence**, with two
source-backed N/A cases I concur with and one openly unfinished gate. It is not
an implementation-ready runtime gate closure: gate 2 (`movement_animation`)
remains `UNTESTED/PARTIAL`, fixture provenance is `rejected` (shared-tooling
limitation), and the registry lane `muse-honeywisp` still reads `blocked`
(gen 2, rev 11) even though `output/muse-wave/l65/finish-gen2.json` records a
`review-ready` outcome file. The integrator should apply the small corrections
below, record an `accept-review` disposition (or require the producer to submit
the recorded outcome through the workflow CLI), and schedule the gate-2
fixture run. Gates 3/5 N/A admission remains an integrator decision.

## Pinned source identities (verified fresh 2026-09-16, UTC)

- Root producer: `output/msw/l65-root`, branch `codex/muse-l65-honeywisp`,
  base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`,
  head `be1463700c002fb52f94d6db2254a0cf607c1581` (single commit ahead of base,
  clean `git status`, present on `origin/codex/muse-l65-honeywisp`).
- Native producer: `output/msw/native-l65`, branch `codex/muse-l65-honeywisp-native`,
  base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`,
  head `8a2db6519a2bd7deb5ea87a2c22f197ad53de0da` (single commit ahead of base,
  clean, branch contains head).
- Root diff (base..head): 3 new files, 508 insertions —
  `docs/PIKMIN2_MUSE_HONEYWISP_HANDOFF.md` (116 lines),
  `experimental/pikmin2_muse_honeywisp.py` (242 lines),
  `tests/test_pikmin2_muse_honeywisp.py` (150 lines).
- Native diff (base..head): 1 new file —
  `tools/p2_muse_honeywisp_fixture.cpp` (140 lines, contains `P2_QURIONE_MUSE_*` markers).
- `native/pc_port/pc_p2_qurione.cpp` / `.h` / `pc_p2_qurione_policy.h`
  intentionally **unchanged** (verified: no diff entries). Correct scoping.
- Decomp anchor cited by producer: `632af93787b9c95b63f0c13be32b161375ce3a96`
  exists in `native/pikmin2-research` (`oops all versions supported and equivalent`).
- Private build executable `output/msw/native-l65-build/bin/nectar.exe` SHA-256
  recomputed fresh: `0125f9785b8aa2c2c95216ccca52564bc77d29fbfa380736fdbc33d1848cffcf`
  — matches handoff `build.executable_sha256`. Historical build log tail shows
  `[616/616] Linking CXX executable bin\nectar.exe` then `ninja: no work to do.`
  (historical evidence, not re-linked by this review).

## Evidence hashes (fresh recomputation vs handoff claims)

- `output/muse-wave/l65/legacy-revalidation.txt` → fresh SHA-256
  `78c549a2cb549a5be46127896b06320ebd32e6912d558fe919bf9f2204b52e0f`
  matches `handoff.evidence.checks.sha256`. Historical artifact (preserved
  lane-15 fix5 logs re-graded); not a fresh run.
- `output/muse-wave/l65/gate-check.txt` → fresh SHA-256
  `bf706d6721f5d43651f3e370b682c06d50ff62fba27a9e75dcd1fef04b74716b`
  matches `handoff.evidence.gate_check.sha256`. Content: gates 1/4/6 accepted
  PASS, gate 2 PARTIAL (non-advancing), gates 3/5 N/A (non-advancing).
- `output/muse-wave/l65/contributor-status.md` → fresh SHA-256
  `12bc83e50bc285af32dd505322f190c4b439ba451fc49a7103bf571c25715cf4`
  matches `output/muse-wave/l65/finish-gen2.json` evidence hash.
- `output/muse-wave/l65/fixture-sustain/provenance.json` → fresh SHA-256
  `66e65ac17d954d834eed851a4fe66d2e3803e052f613fdd0f96a1567eb1a9743`;
  content `status: rejected`, `error: Empty command or unsupported response file`.
  Historical; see finding F3.

## Fresh checks by this reviewer (vs historical evidence)

Fresh (2026-09-16, read-only; no producer files modified, no builds, no runtime):
- Recomputed the four SHA-256 hashes above; recomputed executable hash.
- Verified git ancestry/branches/remotes/clean status for both producer worktrees.
- Verified decomp commit `632af937` resolves.
- Ran `py -3.12 -m pytest tests/test_pikmin2_muse_honeywisp.py -q` in
  `output/msw/l65-root` (read-only execution): **16 passed** — matches
  `checks-honeywisp.txt` (`16 passed in 0.10s`) and handoff `tests` claim.
- Ran `py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_HONEYWISP_HANDOFF.md`
  in `output/msw/l65-root`: exit 0, output identical to `gate-check.txt`.
- Grep-verified every load-bearing source citation against
  `native/pikmin2-research` (details below).

Historical (taken as-is, not re-executed): leased private build log
(`build-1789516923523624500.log`, 8086400 bytes), lane-15 fix5 arena logs under
`output/dsw/l15-out/arena-runs/4eb9093898ff4d8a9e73110675683570/`
(`drop-run.log`, `qurione-run.log`, `cleanup6-run.log`), fixture syntax log
(`syntax_check.log`, rc 0 with shared-header warnings only), provenance
`rejected` record.

## Source-citation verification (all concur, one path correction)

- F1 — Gate 3 N/A (`attacks_receivers`), CONCUR. `Qurione.cpp:136-144`
  `Obj::flyCollisionCallBack` is the only creature callback: Piki contact in
  `QURIONE_Move` transits to `QURIONE_Drop` and returns true, else false. There
  is no damage/health write on this path, and the wisp is `EB_Untargetable` +
  `EB_Invulnerable` (`Qurione.cpp:52-53` per handoff; callback body verified
  verbatim). Contact-trigger observed in preserved `drop-run.log:769` is
  supporting observation, not an attack. N/A keeps the ledger from demanding a
  receiver that cannot exist.
- F2 — Gate 5 N/A (`transport_reward`), CONCUR. `EB_LeaveCarcass` disabled on
  Qurione (`Qurione.cpp:57` region verified: `disableEvent(0, EB_LeaveCarcass)`)
  and on the Egg (`egg.cpp:38` region: `disableEvent(0, EB_LeaveCarcass)`);
  `mDropGroup = EDG_None` verified in `Qurione.cpp`. `Obj::attachItem`
  (`Qurione.cpp:284-296` region) births `EnemyTypeID_Egg` and captures to the
  `water` joint; `dropItem()` endCaptures once and nulls `mEgg`. `Egg::genItem`
  (`egg.cpp:243-289+`) verified: random table rolls only Single/Double nectar,
  Mitites, Spicy, Bitter — pellet branches (`egg.cpp:294-306`) require
  `mForcedDropType` (`egg.cpp:277-279`), which defaults to 0
  (verified in `include/Game/Entities/Egg.h`, `Parms()` constructor:
  `mForcedDropType = 0`). Nectar births as `HONEY_Y` field items
  (`egg.cpp:308-336` verified), absorbed in place, never `ACT_Transport`.
  Real DoubleNectar in preserved `drop-run.log:773-775` is supporting
  observation. No lane-06 receipt can exist for this chain, so N/A is the
  correct ledger disposition, pending integrator admission.
- F3 — Fixture provenance `rejected`, HONEST BUT STALE-HEAD. The rejection
  (`Empty command or unsupported response file` — Release link uses
  `@CMakeFiles\pikmin_pc.rsp` LTO response file) is a shared-tooling limitation
  correctly routed to #491, and the fixture file itself is syntax-valid
  (syntax-check rc 0) and present (140 lines, `P2_QURIONE_MUSE_*` markers).
  Correction: `provenance.json` `expected_native_head` is the **base**
  `7b9ecaa6...` with `observed_source.status: ?? tools/p2_muse_honeywisp_fixture.cpp`
  (recorded pre-commit); it does not certify the committed head `8a2db651...`.
  Integrator must not read it as fixture-source certification. Actual evidence
  for the fixture is syntax-check + private build green, not provenance.
- F4 — Gate 2 (`movement_animation`) PARTIAL/UNTESTED, HONEST. Preserved
  `qurione-run.log:793-797` shows one full appear→move→disappear→stay cycle
  (3 distinct Move positions, dz=161.2, 0 NaN); re-appear stalls without a
  nearby squad. The handoff aggregates across logs fairly (drop-run shows only
  1 Move position; cleanup6 shows 3 positions dz=159.3), and per-log UNTESTED
  rows in `legacy-revalidation.txt` must not be mistaken for full coverage.
  The new sustained-flight fixture (sight-ring squad parking: inside SIGHT 200,
  outside HIT_RADIUS 30) is a reasonable closure vehicle but **not yet run** —
  correctly recorded `UNTESTED`, `fixture_adoption: deferred`.
- F5 — Preserved gates 1/4/6 PASS, NO OVERCLAIM. Identity BIND
  (generator 203001, source_id 16), Drop→Dead fly-away, and same-wisp second
  appearance (one BIND, 2 appears, single FORGET, generator continuity) are
  re-graded from preserved logs with the new observer and explicitly labeled
  as re-validated history, never as fresh runs. Generator-continuity
  distinguisher (same-wisp re-appear vs new-actor re-entry) is the right
  criterion and is evidenced in `cleanup6-run.log:782,800`.
- F6 — Citation path imprecision (minor revise). Handoff `source_mapping` and
  text cite `Egg.h` / `Egg.h:124` without the full include path; the verified
  file is `include/Game/Entities/Egg.h`. Also `source_mapping.evidence` lists
  only the three `.cpp` files, omitting the Egg header that carries the
  `mForcedDropType = 0` default. Request the producer (or integrator edit) to
  record the full path `include/Game/Entities/Egg.h` in the mapping.
- F7 — Handoff envelope honesty notes. `handoff.json` `kind: review`,
  `fixture_adoption.status: deferred`, `movement_animation.status: UNTESTED`,
  `shared_reviews: []`, `remaining_work` listing the gate-2 run, the LTO
  limitation, and N/A-as-integrator-decision — all consistent with the
  `contributor-status.md` REVIEW-READY outcome. `slice_acceptance` all PASS is
  about slice delivery/regression/scoping, not gameplay admission; the
  `gate_check` N/A/PARTIAL rows are intentionally non-advancing. Do not promote
  this artifact as an `implementation-ready` runtime handoff.

## Proposed shared-file dispositions

- None. No shared files were touched: root diff adds 3 reserved files only;
  native diff adds 1 reserved fixture only; owned-file lists match the
  reservation (`native/pc_port/pc_p2_qurione.*`, `experimental/…`,
  `tests/…`, `docs/…`, `native/tools/…`). `shared_reviews: []` is correct.
- Keep `native/pc_port/pc_p2_qurione.*` unchanged (fix5 code verified, no
  defect reproduced). No Egg or shared-host changes needed; handoff notes
  consumer use of lane-20 `P2Egg` policy is already integrated — accepted
  without further action.
- Route the LTO response-file builder limitation to #491 (possibly l67
  fixturetools scope); it is not a producer defect.

## Exact remaining work for the existing integrator

1. Apply/record the F6 citation correction (full path
   `include/Game/Entities/Egg.h` in `source_mapping.evidence`) and acknowledge
   the F3 provenance staleness (`expected_native_head` = base, not head) in
   the integration record.
2. Reconcile registry state: `muse-honeywisp` reads `blocked` gen 2 rev 11
   while `output/muse-wave/l65/finish-gen2.json` holds a `review-ready` outcome
   (evidence `contributor-status.md` SHA-256 `12bc83e5…`). Record
   `accept-review` for the reviewed slice or require the producer to submit the
   outcome through `pikmin2_workflow.py finish`; do not silently edit submitted
   evidence.
3. Schedule exactly one fresh GL run of the committed fixture
   `output/msw/native-l65:tools/p2_muse_honeywisp_fixture.cpp`
   (@ `8a2db651…`) to close gate 2: sustained Move displacement across ≥2
   re-appeared cycles with 0 NaN, sight-ring squad staging documented, fresh
   arena + 960×540 adoption record at run time. No source change expected.
4. Decide gates 3/5 N/A admission explicitly (concur recommended on the source
   case above); record the decision in the roster/allowlist through the normal
   admission path. This review grants no ADMIT and flips no flags.
5. Do not merge gameplay on this artifact alone; gate 2 is still open and
   fixture provenance remains `rejected` pending the #491 tooling fix.

## Review provenance

- Review root commit (this document): recorded at commit time below.
- Review path: `docs/PIKMIN2_MUSE_REVIEW_505.md` in
  `C:\Users\alari\pikmin-randomizer\output\msw\l72-root`,
  branch `codex/muse-l72-review-505`; SHA-256 recorded at commit/finish time.
- Producer evidencegrader: `experimental/pikmin2_muse_honeywisp.py`
  (schema `p2-muse-honeywisp-v1`) — 16 hermetic tests fresh-passed by this
  reviewer read-only; historical log grades reproduced.
- Registry: single canonical DB `output/workflow/registry.sqlite3` read-only
  for producer state (`muse-honeywisp: blocked/2/11`, `muse-review-505:
  running/1/2` at review time); no producer receipts/registry modified.
