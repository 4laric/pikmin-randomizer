# Independent review: Muse l57 / #497 Fuefuki41 handoff (l70, #515)

Reviewer: Muse Spark 1.3 Contributor, lane `muse-review-497` (worker `muse-l70`),
child issue #515, parent #497. Implementation owner: Codex through shared
account 4laric. Session `ses_f57d7060bffeVi4xCtEhd8nM7q`, PID 32884,
generation 1, revision 2, attempt `ac2e2b88923043caa752a0a08cdcaba3`.
Private review root `C:\Users\alari\pikmin-randomizer\output\msw\l70-root`
at `d684d47e1a35cfc6e65768a6d3b448041e9aaaae` (clean, verified).
No edits to producer worktrees, receipts, registry, gameplay, or ADMIT state.
No native builds, no runtime launches. All producer evidence read-only;
hashes below marked FRESH (recomputed by this review) vs HISTORICAL (as
recorded by the producer).

## Pinned source identities (producer claim vs fresh check)

- Producer handoff root: base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`,
  head `a67bc80569c905cc77bb40f9fcc39a413d2dd5f5`, 8 ordered commits, dirty "".
  FRESH: branch `codex/muse-l57-fuefuki` log shows exactly those 8 commits on
  top of `72a2c450` (`ec53d25b`, `568384c4`, `b5486ee9`, `08bd1819`,
  `d5e78523`, `5ef3ebda`, `579305fb`, `a67bc805`). Order matches
  `handoff.json:177-191`. PASS.
- Producer handoff native: base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`,
  head `499e513c7000da008c041beff4e50f349672e6bb`, 2 commits, dirty "".
  FRESH: branch `codex/muse-l57-fuefuki-native` log shows `a0b559fa` then
  `499e513c` on top of `7b9ecaa6`. Matches `handoff.json:154-163`. PASS.
- Registry lane `muse-fuefuki` (read-only status query): same root/native
  heads, state `blocked`, generation 2, handoff sha `7819c3ea...`. Matches
  disk. PASS.

## Evidence hashes: HISTORICAL claim vs FRESH recomputation

| Artifact | Historical (handoff) | Fresh (this review) | Verdict |
|---|---|---|---|
| `output/muse-wave/l57/handoff.json` | registry `7819c3eac731...` | `7819c3eac731...` (12-char `7819c3eac731`) | MATCH |
| `genesis/native.log` (1079 lines) | `94dadc758b2a...1bdebc` | `94dadc758b2a...` | MATCH |
| `genesis/stage-manifest.json` | `e9cd5ea3ff6a...` | `e9cd5ea3ff6a...` | MATCH |
| `genesis/run-meta.json` | `70dd63d8b50d2...` | `70dd63d8b50d...` | MATCH |
| `checks.log` | `082a5d7957d7c...` | `082a5d7957d7...` | MATCH |
| `adoption.md` | `299be7063bc4...` | `299be7063bc4...` | MATCH |
| `contributor-status.md` | `ec62677a7794...` | `ec62677a7794...` | MATCH |
| `build-1789523181478217400.log` (8 MB) | `744371c12a78...` | `744371c12a782ae99a0a2e1b2dda669041a6e64b9377f2fe8d172c50cce95b8e` | MATCH |
| `native-l57-build/bin/nectar.exe` | `cc607620411d...ad31e93` | `cc607620411ddcbd5b06926fa60a1971cc3249ec34410a09040b0b887ad31e93` | MATCH |
| `l52/dependency-ready.json` | `7f34304b217d...` | `7f34304b217d...` | MATCH |
| `l53/dependency-ready.json` | `6bcb75881051...` | `6bcb75881051...` | MATCH |
| `integration-receipt.json` | (file on disk) | `0a0f1991301f...` | EXISTS but CONTENT INVALID (see §4) |
| `export-evidence.json` | receipt cites `23e22c3d8d2f...` | `23e22c3d8d2f...` | HASH MATCHES, CONTENT WRONG LINEAGE (see §4) |
| `integration-validations.log` | receipt cites `af2b529eece3...` | `af2b529eece3...` | HASH MATCHES, CONTENT INSUFFICIENT (see §4) |

## Gate-1 claim assessment (fresh log read, no new runtime)

FRESH read of `genesis/native.log` (1079 lines total, matches claim):

- Line 8: `[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)`.
- Line 14: `Experimental preview window set to 960x540 windowed and centered`.
- Line 590: `P2_SEED_RESOLVE source_id=41 target=1254096625 original_type=11 ...`.
- Line 591: `P2_GENERATED_PLACEMENT source_id=41 target=1254096625 generator=245001 bound=1`.
- Line 592: `P2_PLACEMENT_SLOT generator=245001 slot=1254096625 actor=11 xyz=1 terrain=ground route=1 ...`.
- Line 736: `P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=245001 type=11 follow_locomotion=actteki_volatile_approx`.
- Lines 994/1019: `P2_FUEFUKI_TEKI_FREE_RECRUIT count=20 carriers=0 squad=20` (live squad of 20, twice).
- `stage-manifest.json`: `accepted_slot 1254096625`, `generator_file_id 245001`,
  binding `{target 1254096625, source_id 41, Fuefuki}`, bootstrap
  `ENEMY_P2 1 a019a3ef...902 1 1254096625 41`. Consistent with the log triple.

Source-ancestry spot check (fresh read of the pinned retail research checkout,
read-only): `native/pikmin2-research/src/plugProjectNishimuraU/Fuefuki.cpp:163-185`
defines `Obj::pressCallBack` and `Obj::hipdropCallBack`, each transiting to
`FUEFUKI_Struggle` when `mCanStruggle`; `FuefukiState.cpp:154-156` arms
`mCanStruggle = true` at `KEYEVENT_3`. The handoff `source_mapping` citation
(`Fuefuki.cpp:163-185`, `FuefukiState.cpp:154-156`, P1 bridge note) is accurate.
The observer contract in `experimental/pikmin2_muse_fuefuki.py` (fail-closed:
uid equality, generator equality, mapped slot, `terrain=ground`, `xyz=1`,
`route=1`) matches the cited log fields.

Finding G1: gate-1 `identity_spawn` PASS (natural, triple-correlated uid
1254096625 / generator 245001) is SOUND and FRESHLY corroborated from the
hashed log. Preserve it; do not relaunch the lane to re-earn it.

## Owned files (4, additive, in-scope)

`experimental/pikmin2_muse_fuefuki.py`, `tests/test_pikmin2_muse_fuefuki.py`,
`docs/PIKMIN2_MUSE_FUEFUKI_HANDOFF.md`,
`native/tools/p2_muse_fuefuki_fixture.cpp`. Commits `ec53d25b` + `568384c4` +
`a0b559fa` (native) are single-purpose and additive. No overlap with other
lanes' owned files. No ADMIT/allowlist/default changes. ACCEPT as-is.

## Shared-file dispositions (11 files outside l57 ownership — the core of this review)

Changed-but-not-owned in `handoff.json:21-37` = 7 placement files + 4
packaging files. FRESH blob comparison (producer head vs l57 cherry-pick):

- Root, placement (`b5486ee9` vs l52 head `bd97334a`): `randomizer/p2_placement_catalog.py`,
  `experimental/pikmin2_muse_placement.py`, `tests/test_pikmin2_muse_placement.py`,
  `docs/PIKMIN2_MUSE_PLACEMENT_HANDOFF.md` — all four byte-IDENTICAL (25,898 / 3,839 / 9,638 / 9,082 bytes).
- Root, packaging (`08bd1819` vs l53 `3131b76d`; `d5e78523` vs l53 `f82171d4`):
  `experimental/pikmin2_family_install.py`, `experimental/pikmin2_muse_packaging.py`,
  `tests/test_pikmin2_muse_packaging.py`, `docs/PIKMIN2_MUSE_PACKAGING_HANDOFF.md` —
  all four byte-IDENTICAL (28,348 / 18,386 / 8,618 / 10,481 bytes).
- Native (`499e513c` vs l52-native `4765885b`):
  `native/pc_port/pc_p2_generated_placement.cpp`,
  `native/pc_port/pc_p2_generated_placement.h`,
  `native/tools/p2_muse_placement_fixture.cpp` — all three byte-IDENTICAL
  (4,351 / 2,828 / 3,050 bytes). The only delta on the native branch is the
  owned `p2_muse_fuefuki_fixture.cpp` addition.

Producer state (read-only registry): `muse-placement` and `muse-packaging`
are both `done` with reconciled integrations (`cbb4d1e3`/`612fd2d2` and
`4ba13b4e`/`4e736413`). The 11 `shared_reviews` entries in the l57 handoff
are `status: requested` — i.e. correctly flagged as pending integrator
approval, not silently self-approved.

Finding S1: all 11 shared-file consumptions are verbatim cherry-picks, zero
conflicts, zero drift. Proposed disposition: APPROVE all 11 for ingestion
alongside the l57 slice (no content re-review needed; producer lanes are
already integrated). The integrator's approval action is still required to
clear `pending_reviews`; this review does not substitute for it.

## Receipt defect (the blocking issue — precise correction proposal)

`output/muse-wave/l57/integration-receipt.json` (HISTORICAL, producer-written)
is INVALID AT THE SOURCE and must NOT be submitted to `workflow receipt` /
`integrate`:

- Records `root_commit 339b17b52db174c6904552a9f0ea65bc7686e718` and
  `native_commit 48219915d84e6ab68801655df0adbf2fa49fe1b1` in worktrees
  `output/dsw/wave-root` and `output/dsw/native-wave`, which do not exist and
  do not match the handoff (`a67bc805` / `499e513c` in
  `output/msw/l57-root` / `output/msw/native-l57`).
- `export-evidence.json` (hash-correct, content-wrong) records the same wrong
  lineage: `native_commit 48219915`, `root_export_commit d17efa0f`, build dir
  `output/dsw/native-wave-build`, exe `.../dsw/native-wave-build/bin/nectar.exe`.
- `integration-validations.log` (hash-correct) is a 3-line summary asserting a
  wave build PASS and pytest counts; it is not a re-runnable validation record
  tied to the handoff heads.

Finding R1 (BLOCKING): reject the current receipt. Proposed corrected record
for the integrator's receipt-generation slice (to be produced by the existing
integrator, not this review lane):

```json
{"key": "muse-fuefuki", "generation": 2,
 "root_worktree": "output/msw/l57-root",
 "native_worktree": "output/msw/native-l57",
 "record": {"root_commit": "a67bc80569c905cc77bb40f9fcc39a413d2dd5f5",
 "native_commit": "499e513c7000da008c041beff4e50f349672e6bb",
 "native_dirty": "",
 "export_evidence": "<fresh export evidence path under output/muse-wave/l57/>",
 "export_sha256": "<fresh>",
 "validation_path": "<fresh validation log under output/muse-wave/l57/>",
 "validation_sha256": "<fresh>"}}
```

The fresh export/validation must be generated from those exact heads and
worktrees (maintained export + focused test run), then submitted through the
canonical `receipt`/`integrate` path. Do NOT edit the existing receipt file in
place; write new evidence files and a new receipt.

## Gates 2–6 and other historical claims (explicitly not fresh-tested)

- The handoff marks gates 2–6 `UNTESTED` with detail "Preserved accepted PASS
  under claim-held legacy l28". That labeling is HONEST (no upgrade of
  unrelated evidence), but the underlying "accepted PASS" is HISTORICAL and
  was NOT verified by this review (legacy l28 worktrees are claim-held; I
  confirmed only that `output/deepseek-wave/handoffs/l28.md` exists, 42,395
  bytes, Fuefuki scope, without auditing its gate evidence).
- Finding H1: the integrator must decide ledger ingestion of the gate-1 PASS
  only; gates 2–6 must NOT enter the ledger as PASS on the strength of this
  handoff. They remain whatever l28 established, subject to the integrator's
  own l28 evidence check.
- The 4 `test_pikmin2_admitted_placement.py` failures attributed to
  pre-existing Mamuta-54 ingestion at wave base, and the `admit-check 41 still
  <gate>:injected` line (41 correctly still denied — no ADMIT granted), are
  HISTORICAL producer statements. This review ran no test suites (per brief:
  no builds/runtime) and neither confirms nor refutes the failure attribution;
  the additive-only diff claim (+1757/-0, no roster/admission inputs) is
  consistent with the cherry-pick identity findings above but was not
  independently diffed file-by-file here.
- `run-meta.json`: `timed_out: true, exit_code: 1` with `window 960x540` is
  consistent with a 90 s live-room window terminated by timeout, not a crash;
  HISTORICAL framing accepted, no fresh runtime to confirm.

## Review recommendation: CONDITIONAL ACCEPT (revise receipt, then integrate)

- ACCEPT: gate-1 natural PASS evidence for Fuefuki 41 (fresh hash + log
  corroboration); all 4 owned files; all 11 shared-file cherry-picks
  (verbatim, producer lanes integrated) — approve the 11 `pending_reviews`
  for ingestion.
- REVISE (blocking, integrator-owned): discard the `output/dsw`-lineage
  receipt/export/validation; regenerate them from `a67bc805` /
  `499e513c` in the `output/msw` worktrees with fresh hashes; submit via the
  canonical receipt path. Do not relaunch l57; do not re-earn gate 1.
- Ledger: ingest gate-1 PASS only. Gates 2–6 stay UNTESTED in this slice;
  any PASS standing comes from l28 evidence under its own review, not from
  this handoff. No ADMIT for 41 (admission allowlists untouched — correct).

## Exact remaining work for the existing integrator

1. `accept-review`-adjacent approval of the 11 shared files listed in §S1
   (clears `pending_reviews` in registry handoff result).
2. Receipt-generation slice: fresh export from the handoff heads plus a
   re-runnable validation log (pytest suites + gate checker + hash pins),
   written as NEW files under `output/muse-wave/l57/`; new
   `integration-receipt.json` per §R1 (never edit the old one in place).
3. `integrate` the `muse-fuefuki` lane (gen 2) with the corrected record;
   ledger ingests gate-1 PASS only; confirm 41 remains non-admitted.
4. Optional: verify the 4 pre-existing `admitted_placement` failures against
   base `72a2c450` during the validation run, so the integration record
   carries a fresh (not historical) statement.

## Review provenance

- Review root commit: `d684d47e1a35cfc6e65768a6d3b448041e9aaaae` + this
  document (`docs/PIKMIN2_MUSE_REVIEW_497.md`) committed on
  `codex/muse-l70-review-497`. Review path/hash recorded in the #515 issue
  update and the `finish review-ready` evidence for generation 1.
- Fresh checks performed: recomputed SHA-256 of 10 evidence files; `git log`
  ancestry of both producer branches; byte-level cherry-pick identity of all
  11 shared files; line-level read of `native.log` (window/squad/triple/
  bind markers); retail `Fuefuki.cpp`/`FuefukiState.cpp` citation check;
  registry read-only status of `muse-fuefuki`, `muse-placement`,
  `muse-packaging`, `muse-review-497`.
- Not performed (per brief): no merges, no receipt/registry writes for the
  producer, no native builds, no runtime launches, no gameplay claims, no
  ADMIT grant, no test-suite execution.
