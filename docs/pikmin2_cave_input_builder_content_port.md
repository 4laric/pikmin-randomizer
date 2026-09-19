# Cave input builder content port (provider-cave-input-builder-content-port, #642)

Cross-line provider port. Implementation owner: Codex through shared account
4laric. Root-only lane; no native work, no builds, no runtime, no ADMIT.

## Why

The shared cave runtime input builder
`experimental/pikmin2_cave_runtime_inputs.py` (with
`tests/test_pikmin2_cave_runtime_inputs.py`) is owned by
`cave-guarded-runtime-fixture` (#642, done) and exists ONLY on the species
wave line. It is absent from the content line, so content P1 lanes cannot
stage their guarded boot input packages without forking shared code.

This lane owns ONLY three new additive files and re-derives the exact
landable change as a self-contained packet. The two shared files stay owned
by `cave-guarded-runtime-fixture` (#642); nothing here edits them.

Owned files (this lane):

- `docs/PIKMIN2_CAVE_INPUT_BUILDER_CONTENT_PORT.md` (this file)
- `experimental/pikmin2_cave_input_builder_content_port.py`
- `tests/test_pikmin2_cave_input_builder_content_port.py`

## Canonical-line absence (verified)

`git -C C:/Users/alari/pikmin-randomizer cat-file -e <ref>:experimental/pikmin2_cave_runtime_inputs.py`
fails for both content pins:

- `b0d2c08c1ccb8c67f23946241b4b67dcb9ae9f53` ("preview: no-cargo fixture
  build/run helper with guard checks (#695)") -> ABSENT
- `36b86839` -> ABSENT

## Producer bytes (reviewed #642, species line)

Producer lane `cave-guarded-runtime-fixture` (#642, done gen 2 rev 7),
worktree `output/workflow/runtime-prerequisites-v2/cave-guarded-runtime-fixture/root`:

- base `07e2126ff8c6dacd610958bcba117f3048dbd870`
- commits `94770bc7626bac4c8d941908b6873f3e13b5928c`,
  `74f5a099038149b36c49ff8cb7d699533b41f997` (head, clean)

| shared file | git blob | file sha256 |
|---|---|---|
| `experimental/pikmin2_cave_runtime_inputs.py` | `b9fa6c994bf5650b4b334f2428259739be90de1e` | `f44fcfd1e59fe7b0c69249eae68cd54ba95eb0d2b9de624b0f97206e60d3fc77` |
| `tests/test_pikmin2_cave_runtime_inputs.py` | `a221b7559ed82e531c5268229c0c699b6be3f1d7` | `81e96100e83e1e56969915b8404c29a8fdb40c6afa92bf36b4bdc644d110bd7f` |

`experimental/pikmin2_cave_input_builder_content_port.py` carries these exact
bytes (byte-identical, re-verified at write time) plus the blob/file hashes,
the content base, and the downstream refs. Stdlib only; never imports the
shared module and never writes shared paths.

## Landable patch (for the integrator, under #642 ownership)

Apply the two carried files byte-identical as NEW files on the content line,
then verify with `git hash-object`:

- `experimental/pikmin2_cave_runtime_inputs.py` must hash to blob
  `b9fa6c994bf5650b4b334f2428259739be90de1e`
- `tests/test_pikmin2_cave_runtime_inputs.py` must hash to blob
  `a221b7559ed82e531c5268229c0c699b6be3f1d7`

`emit --out <dir>` writes `packet.json` plus `packet-files/` copies for the
integrator to diff. `verify --self` checks the carried bytes;
`verify --producer-root <dir>` checks an on-disk producer checkout. Any
mismatch exits non-zero with `REFUSED reason=...`.

## Downstream consumers

| consumer lane | issue | cave preset |
|---|---|---|
| `shard-caves-forest-forest1-p1` (blocked gen 12) | #154 | forest1 |
| `shard-caves-yakushima-yakushima4-p1` (blocked gen 12) | #161 | yakushima4 |
| `p2-cave-tutorial_1-p1-runtime` (done gen 6) | #114 | tutorial1 (preset policy; tutorial1 uses its own lane inputs) |

The #642 presets cover forest1/yakushima4 floor-1 harness inputs with
schema-valid placeholders; each consumer substitutes P0-derived manifests.

## Acceptance evidence

- `tests/test_pikmin2_cave_input_builder_content_port.py`: **12 passed**
  (carried-byte/hash match, self-verify, unknown/empty/non-bytes/tampered
  refusals, producer-tree populated/missing/tampered, emit round-trip,
  CLI emit/verify/self/verify-root/bad-args). Hermetic; stdlib only.
- CLI: `verify --self` -> `SELF_PASS files=2` (exit 0);
  `verify --producer-root <#642 worktree>` -> `PRODUCER_PASS` (exit 0);
  `emit --out` -> `PACKET_EMITTED ... downstream=154,161,114` (exit 0).
- All six runtime gates UNTESTED. No build, no runtime run, no shared/native
  edits, no manifest write, no ADMIT. Captain safety #632 N/A
  (planning/tooling-only turn; the packet records no observed ticks).