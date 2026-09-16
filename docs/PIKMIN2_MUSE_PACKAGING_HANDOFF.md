# Muse packaging lane (l53, #493) — candidate content packaging handoff

Parent wave #491; family/dependency parent #442; integration #437/#186.
Implementation owner: Codex through shared account 4laric. Executing
contributor: Muse Spark 1.3 through OpenCode
(`opencode/muse-spark-1.3-contributor-free`), lane `muse-packaging` (l53).

## Scope

Extend the existing family install binding to stage hash-verified
assets/sidecars for the four candidate identities whose only missing gate is
`identity_spawn` — Fuefuki (41), Kurage (57), BombSarai (58), MiniHoudai
(78) — using family installers as-is. Candidate-only generated-session
command plus negative tests for missing/wrong identity, cache replay and
generator-binding disagreement. Placement contract coordinated with
muse-placement (l52/#492): the seed's `p2_layout` bindings
`{"target", "source_id", "enum_name"}` plus `actor_bindings` mapping every
`target` token to its int native generator id (the lane 03/04 `ENEMY_P2`
seam). No admission writes, no allowlist edits, no resolve-marker fakes;
honest local candidate staging only.

## Source IDs and files owned

- `experimental/pikmin2_family_install.py` — added the missing
  `58`/`bombsarai` identity mapping so source 58 reuses the existing
  shared-contract `pikmin2_bombsarai_install` module as-is; added the
  `MUSE_CANDIDATE_IDS` note documenting that 41/57/78 intentionally stay
  unmapped here (no shared-signature installer exists) and stage through the
  candidate sidecar path. Family installers untouched.
- `experimental/pikmin2_muse_packaging.py` — new candidate-only staging
  module (`stage_candidates`, `verify_staging`, CLI `main`).
- `tests/test_pikmin2_muse_packaging.py` — new (12 tests).
- `docs/PIKMIN2_MUSE_PACKAGING_HANDOFF.md` — this file.
- `native/tools/p2_muse_packaging_fixture.cpp` — new standalone
  staging-verification fixture (receipt/sidecar/binding checks, no gameplay
  injection).

## Ordered commits

- **Root** branch `codex/muse-l53-packaging`, base
  `72a2c450d7b9040545de4a440c2c32e2173ea6fa`, clean except this handoff
  doc (committed next):
  1. `3131b76dc14a867cc5d32c31d242a95eaf91fdee` — muse-packaging:
     candidate-only staging for 41/57/58/78 with 58 family binding (#493)
- **Native** branch `codex/muse-l53-packaging-native`, base
  `7b9ecaa668fd55332073446cdbdaf6424b209ea7`, clean:
  1. `a959336d0ffc8012aa5eeff1bc9a18cac4950994` — muse-packaging:
     standalone candidate staging verification fixture (#493)

## Staging design (what was built)

- Candidate-only gate: every binding must name one of 41/57/58/78 with
  source-id/enum agreement; any non-candidate identity fails
  closed with `StagingError`.
- Source 58 delegates to `family_install.install_layout` as-is (manifest
  policy `P2_BOMBSARAI_IMPORT_1`, disc/pose hash checks stay authoritative
  in that installer). Sources 41/57/78 stage hash-verified sidecars: a
  validated `<content_root>/<Enum>/identity.json` copy plus a canonical
  `p2-candidate-<enum>-actors.txt` (`<header> <count>` + one generator per
  line). Aggregate receipt `p2-muse-packaging-receipt.json` records
  `candidate_only: true`, `admission: 'none'`, plan digest and per-file
  SHA-256.
- Cache replay mirrors the family binding (`cache_dir/p2muse-<digest>`);
  replay never re-reads sources. A matching run receipt replays with
  `cached=True`. Duplicate generator ids across the candidate set are
  refused (one actor per native generator).
- Native fixture verifies the staged run: receipt marker fields, sidecar
  presence/shape, and every expected `Target=generator` binding present in
  the staged sidecars. Markers `P2_MUSE_PACKAGING_RECEIPT_OK`,
  `P2_MUSE_PACKAGING_SIDECAR_OK`, `P2_MUSE_PACKAGING_BINDING_OK`,
  `P2_MUSE_PACKAGING_OK`; failures print `FAIL P2_MUSE_PACKAGING <reason>`.

## Verification evidence

- Focused tests: `py -3.12 -m pytest tests/test_pikmin2_muse_packaging.py -q`
  → **12 passed** (positive 4-candidate staging, missing/wrong identity,
  generator disagreement, missing/duplicate actor binding, non-candidate
  rejection, cache replay without sources, receipt replay, conflicting
  receipt, CLI entrypoint).
- Regression: `tests/test_pikmin2_family_install.py`,
  `tests/test_pikmin2_install_binding.py`,
  `tests/test_pikmin2_bombsarai_install.py` → **59 passed**.
- E2E staging via the candidate command against synthetic content:
  `output/muse-wave/l53/demo/demo-run`, plan digest
  `9e28bc62137f0caa0a645b8403f36f8695b51c7285a992a14d96e80df10721bb`.
- Fixture run:
  `output/muse-wave/l53/fixture-standalone/p2_muse_packaging_fixture.exe`
  against the demo run → all four `SIDECAR_OK`, all four `BINDING_OK`,
  `P2_MUSE_PACKAGING_OK`; wrong-digest negative exits 1 with
  `FAIL P2_MUSE_PACKAGING`. Log:
  `output/muse-wave/l53/demo/fixture-output.log`.
- Private native build (leased runner): configure + `pikmin_pc` build +
  `ninja -n` dry run exit 0; executable SHA-256
  `41f7006167bd941cdec0e102d0dedd46ea2bec4f971f7c487d7d7d623bb09b31`.
  Build log: `output/muse-wave/l53/build-1789515549965065100.log`.
- Standalone fixture compile (leased runner): g++ exit 0; log
  `output/muse-wave/l53/build-1789516835551075600.log`.
- Provenance-builder limitation (exact defect, not a code failure):
  `scripts/build_pikmin2_fixture.py` rejects with
  `Empty command or unsupported response file` because the private build
  tree carries no `CMakeFiles/pikmin_pc.rsp` link response file after the
  build (none exists anywhere under `native-l53-build`), so the link
  command `g++.exe ... @CMakeFiles\pikmin_pc.rsp -o bin\nectar.exe` cannot
  be parsed. Logs:
  `output/muse-wave/l53/build-1789515685817764900.log` (relative fixture
  path form) and `output/muse-wave/l53/build-1789515713219025300.log`
  (absolute path form). The fixture is therefore verified via the
  direct standalone compile above; the integrator can rebuild it through
  the provenance path once the response-file gap is fixed. No runtime
  PASS is claimed from this.

## Gate tables (tooling honesty: no natural gameplay claims)

### Source ID: 41 Fuefuki

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | packaging stages hash-verified candidate sidecar only; natural generated birth needs l52 placement slot + gate observer (l57/#497); demo receipt output/muse-wave/l53/demo/demo-run/p2-muse-packaging-receipt.json | unobserved |
| 2. Movement and animation | UNTESTED | no runtime run in this slice; see l28 family evidence | unobserved |
| 3. Attacks and receivers | UNTESTED | no runtime run in this slice; see l28 family evidence | unobserved |
| 4. Death and corpse | UNTESTED | no runtime run in this slice; see l28 family evidence | unobserved |
| 5. Transport and reward | UNTESTED | no runtime run in this slice; see l28 family evidence | unobserved |
| 6. Cleanup and re-entry | UNTESTED | no runtime run in this slice; see l28 family evidence | unobserved |

### Source ID: 57 Kurage

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | packaging stages hash-verified candidate sidecar only; natural generated birth needs l52 placement slot + gate observer (l58/#498); demo receipt output/muse-wave/l53/demo/demo-run/p2-muse-packaging-receipt.json | unobserved |
| 2. Movement and animation | UNTESTED | no runtime run in this slice; see l29 family evidence | unobserved |
| 3. Attacks and receivers | UNTESTED | no runtime run in this slice; see l29 family evidence | unobserved |
| 4. Death and corpse | UNTESTED | no runtime run in this slice; see l29 family evidence | unobserved |
| 5. Transport and reward | UNTESTED | no runtime run in this slice; see l29 family evidence | unobserved |
| 6. Cleanup and re-entry | UNTESTED | no runtime run in this slice; see l29 family evidence | unobserved |

### Source ID: 58 BombSarai

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | BombSarai content installs through the family installer as-is (manifest hash-verified); natural generated birth needs l52 placement slot + gate observer (l59/#499); demo receipt output/muse-wave/l53/demo/demo-run/p2-muse-packaging-receipt.json | unobserved |
| 2. Movement and animation | UNTESTED | no runtime run in this slice; see l27 family evidence | unobserved |
| 3. Attacks and receivers | UNTESTED | no runtime run in this slice; see l27 family evidence | unobserved |
| 4. Death and corpse | UNTESTED | no runtime run in this slice; see l27 family evidence | unobserved |
| 5. Transport and reward | UNTESTED | no runtime run in this slice; see l27 family evidence | unobserved |
| 6. Cleanup and re-entry | UNTESTED | no runtime run in this slice; see l27 family evidence | unobserved |

### Source ID: 78 MiniHoudai

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | packaging stages hash-verified candidate sidecar only; natural generated birth needs l52 placement slot + gate observer (l60/#500); demo receipt output/muse-wave/l53/demo/demo-run/p2-muse-packaging-receipt.json | unobserved |
| 2. Movement and animation | UNTESTED | no runtime run in this slice; see l21 family evidence | unobserved |
| 3. Attacks and receivers | UNTESTED | no runtime run in this slice; see l21 family evidence | unobserved |
| 4. Death and corpse | UNTESTED | no runtime run in this slice; see l21 family evidence | unobserved |
| 5. Transport and reward | UNTESTED | no runtime run in this slice; see l21 family evidence | unobserved |
| 6. Cleanup and re-entry | UNTESTED | no runtime run in this slice; see l21 family evidence | unobserved |

## Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_PACKAGING_HANDOFF.md
(EXIT=0 expected: no PASS rows claimed)
```

## Remaining work / consumers

- l52 muse-placement: consume the staged contract (layout bindings +
  actor generators) for one defensible slot per identity; fail closed on
  unsupported terrain/routes.
- l57–l60 gate observers: correlate the same real generated
  slot/generator across placement, source-id resolve and actor binding
  markers for the natural gate-1 run.
- Provenance-builder response-file gap (above) if a replacement-main
  fixture build is required before integration.
- No ADMIT writes in this slice; authorization to improve lanes is not a
  request to flip admission flags.
