# Machine-readable provenance for production-binary acceptance runs (#615)

`scripts/build_pikmin2_fixture.py` emits hash-pinned `provenance.json`
only for replacement-main fixture builds. Production-binary acceptance
runs had no equivalent: every runtime handoff hand-rolled these bindings
into prose. `scripts/pikmin2_provenance_run.py` (new, additive, light)
closes the gap. It never builds, never runs a game, grants no admission
and makes no gameplay PASS claim.

## Usage

```powershell
py -3.12 scripts/pikmin2_provenance_run.py --native <worktree> `
  --expected-head <full-sha> --build-dir <dir> --exe <path> `
  --arena <dir> --log <native.log> --output <provenance.json>
```

The recorder verifies every input first and fails closed (non-zero exit,
`ValueError`) on missing files, a dirty native tree, head mismatch, or
unreadable inputs. Only top-level arena files are hashed; subdirectories
such as `assets/` or `capture/` are recorded by name so overlay junctions
are never traversed.

## Handoff evidence mapping

| Provenance field | Handoff evidence slot |
|---|---|
| `native.observed_head` + `dirty: ""` | root/native source record (`head`, clean) |
| `build.directory` | build `directory` (must sit under ignored `output/`) |
| `build.executable.sha256` | build `executable` evidence |
| `arena.arena_json_sha256` + `arena.files` | fixture-adoption `fresh_arena` / `assets_config` |
| `log.sha256` (+ `lines`) | gate citations + adoption `window`/`live_squad` |
| `created_utc` + `tool` | reproducibility stamp |

`self_check(record)` validates the shape read-only and is the right
entry point for auditors and for the unit suite.

## Verification

`tests/test_pikmin2_provenance_run.py`: 7 tests pass (happy-path
round trip, dirty-tree / wrong-head / missing-input fail-closed, CLI
write, required-key rejection, read-only real prior log shape check).
No shared file was modified; builder helpers are reused by import.