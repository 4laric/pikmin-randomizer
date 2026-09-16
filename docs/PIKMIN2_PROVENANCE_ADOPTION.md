# Production-run provenance adoption (issue #615)

Read-only review. Implementation owner: Codex through shared account `4laric`;
executing worker muse-l62 (generation 2). The integrated recorder
(`scripts/pikmin2_provenance_run.py`, present in the wave-root and
p2-main-review trees) had zero documented consumers: every runtime handoff
hand-rolled provenance into prose. This lane ran it read-only against two
published runtime handoff artifact sets and publishes a reusable checker any
family lane can use. No runtime, no build, no shared edits, no gate flips, no
ADMIT. All six runtime gates UNTESTED; no acceptance claimed.

## 1. Live verification (read-only recorder runs)

| Consumer | Native head (clean) | Exe | Log | Result |
|---|---|---|---|---|
| armor15 run2 | `0a32249a` | `ae666fb4?` (fixture) | `8ccbb58b?` | validates end to end |
| l62 run4 | `b024c88c` | `7e451858?` (fixture) | `52d1ad8c?` | validates end to end |

Both exe/log hashes match the hashes already recorded in those lanes'
handoff evidence, so the recorder reproduces hand-rolled provenance exactly.
Records:
`output/workflow/autofill/planning-shards/provider-runtime-fixtures/prepared/provenance-adoption-output/armor15-provenance.json`
and `l62-provenance.json`.

Staged-vs-natural labelling: **both consumers exercised replacement-main
fixture executables, not production binaries.** The recorder binds whatever
exe it is given; the "production-run" name overclaims. Callers must label the
exe kind themselves (see gaps).

## 2. Recorder output -> handoff evidence mapping

`experimental/pikmin2_provenance_adoption_check.py::map_to_handoff_evidence`
implements this mechanically:

| Recorder field | Handoff evidence key | Notes |
|---|---|---|
| `build.executable.path/sha256` | `exe` | drop-in for the fixture/production exe entry |
| `log.path/sha256` | `nativelog` | drop-in for the run-log entry |
| `arena.files.<name>` | `arena:<name>` | per-file entries (arena.json, configs, validation JSON) |
| whole record | `provenance` | new evidence key lanes should add |

`check_record` cross-checks native head/dirty, exe sha256, log sha256 and the
arena directory against caller expectations and fails closed on mismatch.

## 3. Remaining adoption gaps (exact)

1. **Exe kind is unlabelled.** The record has no `replacement_main` boolean
   or fixture-build linkage (`expected_native_head` of the fixture provenance
   is not cross-checked). A consumer must state staged vs production itself.
2. **Arena bytes are partial.** Only top-level files are hashed; `assets/`
   and `capture/` subdirs are names-only (junction safety), so the actual
   stage bytes ride on `arena.json` alone.
3. **No build record.** Build commands, `ninja -n` dry-run result, and exe
   rebuild identity are absent; the record pins the exe file, not how it was
   produced.
4. **No startup evidence.** Window size/centring, live squad, and
   no-extinction markers stay in the log prose; the recorder does not extract
   or assert them.
5. **Timestamps are wall-clock** (`created_utc`), not gameplay time.
6. **Consumer migration is per family.** Each lane must adopt the checker and
   add the `provenance` evidence key; no lane has done so yet (this review
   changes no lane).

## 4. Reusable artifacts (this lane, new files only)

- `experimental/pikmin2_provenance_adoption_check.py` ? `run_recorder`,
  `load_provenance`, `check_record`, `map_to_handoff_evidence`, `certify`
  (stdlib only; shells out to a caller-chosen recorder root).
- `tests/test_pikmin2_provenance_adoption_check.py` ? 6 tests + 7 subtests
  (malformed records, hash mismatches, missing fields, mapping, plus live
  checks against both provenance files above, skipped if absent).
- This doc.
