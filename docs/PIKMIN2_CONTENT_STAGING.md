# P2 content staging (#442)

Lane 05 first slice: a reusable, family-agnostic orchestrator that installs a
versioned content manifest into a generated session's run tree. It is the generic
consumer of family extractors, not a replacement for them: family owners keep
their extractors, and lane 09 owns generic conversion. No network and no retail
assets are used or committed.

Lane 05 second slice adds an offline preflight (`verify_manifest`) and a
read-only dry-run (`plan`) plus strict manifest I/O/construction helpers, so a
caller can validate and plan an install before any destination is created.

Module: `experimental/pikmin2_staging.py`
Tests: `tests/test_pikmin2_staging.py`

## Manifest contract

A manifest is a JSON object (or an equivalent mapping) with an explicit schema and
version:

```json
{
  "schema": 1,
  "version": 3,
  "entries": [
    {"id": "snow_bulborb_model", "kind": "model",
     "source": "import/SnowBulborb/snow.mod",
     "destination": "courses/pikmin2room/snow.mod",
     "sha256": "<64 hex characters>"}
  ]
}
```

- `schema` must equal `1`; any other value is rejected.
- `version` is a positive integer identifying the content revision.
- `entries` is an ordered list. Order is preserved in the receipt and digest.
- `id` is a unique non-empty logical asset id.
- `kind` is one of `model`, `texture`, `anim`, `config`, `sidecar`.
- `source` is one source path per entry, absolute or relative to `base`.
- `destination` is a relative path under the run directory. Absolute paths,
  backslash/drive/UNC forms, `..` escapes, and `.staging` temp names are rejected.
- `sha256` is the lowercase-normalized hex digest of both the source and the
  staged bytes.

Duplicate ids and duplicate destinations are rejected. `load_manifest(path)` reads
and validates JSON; `validate_manifest(mapping)` normalizes a mapping in place-free
fashion (returns a fresh dict). Unknown schema, bad version, bad shape, unsupported
kind, bad digest and unsafe destinations raise `ValueError` with the offending id
or value.

An optional string `notes` field is preserved by validation when present.

## Manifest I/O and construction

- `load_manifest(path)` reads strict JSON and validates it; malformed JSON raises
  `ValueError`.
- `dump_manifest(manifest, path)` validates, then writes canonical
  (2-space indented, LF-terminated) JSON and returns the validated mapping. It
  creates the parent directory but never touches a destination tree.
- `build_manifest(version, entries, notes='')` wraps an explicit list of entry
  dicts into a validated manifest. The filesystem is never scanned for assets;
  callers supply every entry. Duplicate ids/destinations, unsupported kinds,
  malformed entries and non-string notes are rejected by `validate_manifest`.

`load_manifest(dump_manifest(m, p)) == validate_manifest(m)` is a strict
round-trip.

## Preflight and dry-run

`verify_manifest(manifest, base=None) -> report`

Offline preflight. Validates the manifest (malformed input still raises
`ValueError`), then checks that every source exists and its bytes hash to the
declared `sha256`. It reads only sources and never consults or creates any
destination. The report is deterministic:

```json
{
  "schema": 1,
  "version": 3,
  "ok": true,
  "entries": [
    {"id": "...", "destination": "...", "source": "...",
     "sha256": "...", "found_sha256": "..." | null,
     "status": "ok|missing_source|hash_mismatch"}
  ],
  "summary": {"entries": 1, "ok": 1, "missing_source": 0, "hash_mismatch": 0}
}
```

`plan(manifest, destination, base=None) -> report`

Read-only dry-run against `destination`. For each entry it reports the action
staging would take:

- `stage` — no destination file present.
- `skip` — an identical destination (same `sha256`) already exists.
- `conflict` — a destination exists with a different hash or is not a regular
  file.

Each row also carries `planned_temp` (the temp name the atomic write will use,
`<name>.<pid>.<index>.staging`) and `interrupted_temp`/`interrupted_temps` for any
leftover `*.staging` temp matching the target. The report includes the full
`interrupted` list under the destination and `ok` is true only when no entry
conflicts. `plan` never creates, rewrites or removes anything.

## Staging behavior

`stage(manifest, destination, base=None, receipt_path=None) -> receipt`

1. Resolve every source before creating the destination; a missing source or a
   hash mismatch raises `StagingError` naming the exact entry id and leaves no
   partial tree.
2. Create the destination and remove leftover `*.staging` temp files.
3. Per entry: a destination whose bytes already match `sha256` is cached and never
   rewritten. A destination with a wrong hash is repaired. A missing destination
   is staged. Writes go to a temp file in the destination directory and
   `os.replace` into place, so an interrupted run can never leave a half-written
   destination.
4. Write the receipt next to the destination as
   `<destination>-staging-receipt.json` unless `receipt_path` overrides it.

Re-running over an identical staged tree is a cached replay: no destination file
is rewritten and the staged digest is unchanged. `base` defaults to the manifest
file's directory for a path input, otherwise the current directory.

## Receipt contract

```json
{
  "schema": 1,
  "manifest_version": 3,
  "staged_digest": "<sha256 over ordered id/destination/sha256>",
  "entries": [
    {"id": "...", "kind": "model", "source_sha256": "...",
     "destination": "...", "staged": true, "status": "staged|cached|repaired"}
  ],
  "summary": {"entries": 1, "staged": 1, "cached": 0, "repaired": 0, "cleaned_temp": 0}
}
```

`staged_digest` is deterministic for a manifest regardless of run or cache state.
The receipt is machine-readable and is not part of the staged set.

## Command line

The module exposes a small argparse entry point over a manifest path and an
optional destination:

```powershell
py -3.12 -m experimental.pikmin2_staging verify MANIFEST [--base DIR]
py -3.12 -m experimental.pikmin2_staging plan   MANIFEST DESTINATION [--base DIR]
py -3.12 -m experimental.pikmin2_staging stage  MANIFEST DESTINATION [--base DIR] [--receipt PATH]
```

`verify` and `plan` print the JSON report and exit non-zero when `ok` is false;
`stage` prints the receipt. `--base` overrides the source base directory (it
defaults to the manifest file's directory).

## Generated-session launcher/cache integration

`stage_session_content(manifest, session_dir, base=None, cache_dir=None)` is the
launcher-facing entry point. Content is installed under
`<session_dir>/content`, so a revisit or process restart reuses it without a
manual copy step. Staging runs before any native process starts: a missing/wrong
source, unsafe destination or corrupt cache raises `StagingError` and nothing
launches.

With `cache_dir`, the verified tree is kept under
`<cache_dir>/<version>-<staged_digest>/`, with its receipt as the completeness
marker. A later session whose manifest has the same version/content digest
materializes from the cache without reading the sources again; a corrupt cached
entry fails closed instead of installing bad bytes.

The launcher consumes it through the ordinary session command:

```powershell
py -3.12 -m randomizer run MANIFEST --session-dir DIR --exe EXE --assets ASSETS \
    --content-manifest content-manifest.json [--content-cache CACHE]
```

`randomizer.runner._launch` invokes `stage_session_content` before `Popen`; the
`--content-cache` path is optional and off for legacy runs. Family extractors
still produce the manifest; the launcher only installs verified bytes.

## Validation

```powershell
py -3.12 -m pytest tests/test_pikmin2_staging.py tests/test_pikmin2_session_staging.py -q   # 26 passed
```

Covers happy-path staging plus receipt, cached replay no-op, missing source, wrong
source hash, interrupted-staging detection/repair, path traversal, duplicate
id/destination, malformed schema/manifest and deterministic receipt/digest. The
second slice adds verify success/missing-source/hash-mismatch, plan
stage/skip/conflict, plan read-only-ness and interrupted-temp reporting, manifest
JSON round-trip and `build_manifest` construction/duplicate rejection. All
sources are synthetic temp files.

## Limitations

- One source per entry; `sha256` is both source and destination digest. Multi-file
  merge records would need a schema bump.
- `verify_manifest` and `plan` are point-in-time: a source or destination can
  change between a successful preflight and the actual `stage`. `stage` re-checks
  every source hash before writing, so a later mismatch still fails closed.
- `planned_temp` reports the naming scheme with the current process id and entry
  index; `stage` uses a monotonic counter for the sequence component, so the exact
  name may differ while sharing the prefix/suffix.
- `verify_manifest` reports at the manifest level only; it does not enforce a
  destination base or any run-tree boundary.
- Staging is fail-fast per manifest but not transactional across entries; on a
  mid-run source change it stops without corrupting any completed destination.
- Destination is not enforced to live under `output/`; callers select the ignored
  run directory. Tests use temporary directories.
- The orchestrator does not extract, convert or validate asset contents; it only
  verifies hashes and installs bytes. Family extractors and lane 09's converter
  remain the producers.
- The session destination (`<session_dir>/content`) is installed and receipted,
  but no native overlay consumer reads it yet; layered native consumption is a
  lane 01/09 integration boundary. No family extractor is wired into the launcher
  in this slice.
