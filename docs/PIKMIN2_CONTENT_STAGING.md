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

An optional string `notes` field is preserved by validation when present. An
optional `identities` field is a non-empty, unique list of lane-02 P2 source IDs
that the content serves; the launcher requires it to cover the seed's bound
identities before staging.

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

`stage_session_content(manifest, destination, base=None, cache_dir=None,
required_identities=None, retail_assets=None)` is the launcher-facing entry point.

- **Identity validation:** `required_identities` are the seed's `p2_layout` source
  IDs; the manifest must declare an `identities` list covering them or staging
  raises `StagingError`. Content is thus validated against the identities it serves.
- **Native asset connection:** with `retail_assets`, the destination is the run's
  private asset tree (`<run>/assets`) and the content is applied as a room overlay
  — untouched directories stay junctions to the retail root, untouched files are
  hardlinked, and only the manifest files are materialized — so native asset
  lookup reads the content tree. `randomizer.runner._launch` uses this path and
  skips the plain retail junction.
- **Content cache:** without `retail_assets` (or via the module API) content is
  installed under `<destination>/content` with an optional `cache_dir`, and later
  runs materialize from the cache without reading sources again.

Staging runs before any native process starts, so a missing/wrong source, an
uncovered identity or a corrupt cache raises `StagingError` and nothing launches.
The cache path is per-file atomic (no half-written file) with a resumable partial
tree; the overlay path refuses an existing destination and verifies every source
first.

The launcher consumes it through the ordinary session command:

```powershell
py -3.12 -m randomizer run MANIFEST --session-dir DIR --exe EXE --assets ASSETS \
    --content-manifest content-manifest.json
```

Family extractors still produce the manifest; the launcher only installs verified
bytes. This is a launcher-level connection proven with synthetic retail inputs;
ordinary in-game acceptance still requires a real content manifest and a native
gameplay run.

## Consuming existing family installers

`experimental.pikmin2_family_install` is the lane 05 consumer of family-owned
installers. `FAMILY_MODULES` registers the families whose installer already has
the shared `install(source, run, actors) -> receipt` shape (aquatic, bombsarai,
cannon_projectile, dweevil, flora, flying, frog, ground_inverts, long_legs,
mamuta, sheargrub, snagret, waterwraith); bespoke-signature families need an
adapter. It does not convert or extract assets.

`install_family(name, source, run, actors, retail_assets=None)` prepares the run's
private model destination (`<run>/assets/dataDir/courses/pikmin2room`) via the same
overlay scheme, calls the family installer, and writes a lane 05 receipt. The
launcher consumes it:

```powershell
py -3.12 -m randomizer run MANIFEST --session-dir DIR --assets ASSETS \
    --family-install frog --family-source BANK --family-actor 201001:Frog
```

`--family-install` and `--content-manifest` are mutually exclusive for now because
each owns the private asset tree. Family conversion/registration stays with the
family lanes and lane 01; this module only sequences installers.

## Identity-to-runtime binding (bespoke-family adapters)

`experimental.pikmin2_family_install` also binds a seed's `p2_layout` identities
to family installers so a generated session stages its content without per-family
manual flags.

- `ADAPTERS` registers bespoke-signature family installers wrapped to the shared
  `install(source, run, actors)` shape. Each adapter may expose a
  `validate(source)` pre-flight hook run before any destination write. The first
  adapter is `dwarf_orange`, consuming `pikmin2_dwarf_orange_install.install` from
  an identity content dir laid out as `<source>/bank` + `<source>/profile`.
- `resolve_family(identity)` maps a source id or enum name to a family key. It is
  intentionally narrow: only identities whose family already has an installer are
  registered, and anything else raises `ValueError` instead of silently binding a
  P1 analogue. With the first adapter this is `44` / `BlueKochappy` →
  `dwarf_orange` (Dwarf Orange Bulborb).
- `install_layout(run, layout, content_root, actor_bindings=None,
  retail_assets=None, cache_dir=None)` stages every binding in a `p2_layout`.
  `content_root` is identity-keyed (`<root>/<enum_name>`); `actor_bindings` maps
  every `target` token to its int native generator id (the runtime seam owned by
  lane 03/04 + native `ENEMY_P2`). Each binding is validated — identity
  resolution, source-id/enum-name agreement, source presence, the family
  `validate(source)` pre-flight and the actor binding — before the destination is
  created, so an unknown identity, source-id/enum disagreement, missing/wrong
  source or missing actor binding raises `StagingError` and leaves nothing behind.
  A matching on-disk `p2-binding-receipt.json` (no `cache_dir`) or a session-level
  cache marker (with `cache_dir`) is a cached replay that is reused without
  re-reading sources, materializing the staged content into the new run;
  a conflicting/partial tree fails closed.

The launcher consumes it through identity-keyed flags:

```powershell
py -3.12 -m randomizer run MANIFEST --session-dir DIR --exe EXE --assets ASSETS \
    --p2-content content-root --p2-actors actors.json   # {target: generator_id}
```

`--p2-content` is mutually exclusive with `--content-manifest` and
`--family-install`, since each owns the private asset tree. Staging runs before
any native process, so a bad identity/source/binding raises and nothing launches.
The launcher keeps a session-level content cache at
`<session>/p2-content-cache`, so a relaunch of the same seed/session materializes
the staged content into a fresh `runs/<token>` without re-reading sources and
reports `cached=True`.

## Validation

```powershell
py -3.12 -m pytest tests/test_pikmin2_staging.py tests/test_pikmin2_session_staging.py -q   # 26 passed
py -3.12 -m pytest tests/test_pikmin2_family_install.py tests/test_pikmin2_install_binding.py -q
py -3.12 scripts/test_p2_generated_session.py <build>/pc_randomizer_probe.exe                 # generate -> bootstrap -> native parser -> stage/cache
py -3.12 scripts/probe_p2_install_binding.py --output output/dsw/l05-out                      # install_layout -> real adapter -> session-cache replay
```

`scripts/test_p2_generated_session.py` is the combined lanes 02/03/05 product-path
probe: it generates a manifest through the real admission-gated generator, lets
`NativeRun` emit the real `ENEMY_P2` bootstrap, parses it with the native probe,
then stages and cache-replays a synthetic content manifest into the same session.

Covers happy-path staging plus receipt, cached replay no-op, missing source, wrong
source hash, interrupted-staging detection/repair, path traversal, duplicate
id/destination, malformed schema/manifest and deterministic receipt/digest. The
second slice adds verify success/missing-source/hash-mismatch, plan
stage/skip/conflict, plan read-only-ness and interrupted-temp reporting, manifest
JSON round-trip and `build_manifest` construction/duplicate rejection. The binding
slice adds `resolve_family` mapping/rejection, `install_layout` fresh install,
identity-keyed content resolution, cached replay, and fail-closed unknown
identity/missing source/missing actor binding/partial/stale cases plus an
end-to-end generated-seed launch. All sources are synthetic temp files.

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
- The run-local destination (`<run>/content`) is installed, receipted and bound to
  the seed's P2 identities, but no native overlay consumer reads it yet; layered
  native consumption is the remaining lane 01/09 integration boundary.
- The binding layer has one registered adapter so far (`dwarf_orange` for
  `BlueKochappy`/44); Snow/Kochappy and every other bespoke family need their own
  adapter before they resolve through `install_layout`. `actor_bindings` (target →
  native generator id) is supplied by the caller because the runtime generator id
  is resolved by lane 03/04 + native `ENEMY_P2`, not by this lane.
- The session-level family-install cache is keyed by the binding plan (bindings +
  actor map), not by the family bank's bytes; changing a family's content under
  the same binding plan requires clearing `<session>/p2-content-cache` to avoid a
  stale replay. The family installer's own receipt still records the bank/profile
  hashes for diagnosis.

