# P2 content staging (#442)

Lane 05 first slice: a reusable, family-agnostic orchestrator that installs a
versioned content manifest into a generated session's run tree. It is the generic
consumer of family extractors, not a replacement for them: family owners keep
their extractors, and lane 09 owns generic conversion. No network and no retail
assets are used or committed.

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

## Validation

```powershell
py -3.12 -m pytest tests/test_pikmin2_staging.py -q
```

Covers happy-path staging plus receipt, cached replay no-op, missing source, wrong
source hash, interrupted-staging detection/repair, path traversal, duplicate
id/destination, malformed schema/manifest and deterministic receipt/digest. All
sources are synthetic temp files.

## Limitations

- One source per entry; `sha256` is both source and destination digest. Multi-file
  merge records would need a schema bump.
- Staging is fail-fast per manifest but not transactional across entries; on a
  mid-run source change it stops without corrupting any completed destination.
- Destination is not enforced to live under `output/`; callers select the ignored
  run directory. Tests use temporary directories.
- The orchestrator does not extract, convert or validate asset contents; it only
  verifies hashes and installs bytes. Family extractors and lane 09's converter
  remain the producers.
