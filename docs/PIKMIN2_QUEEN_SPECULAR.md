# Queen animated specular layer (#399)

Codex implementation owner using shared GitHub account 4laric. This is an
opt-in experimental Empress Bulblax material path, outside Pikipelago v0.1.

## Integration pass

The candidate starts from shared P2 branch `db9467f` and preserves the current
animation, material-binding and actor-lifetime changes. Integrated handoffs:

| Source | Integrated commit | Scope |
|---|---|---|
| `aa876b8` | `f8e7939` | Bulblax six-lane arena, Queen/King actor profiles, runtime harnesses and policy tests |
| `44deb01` | `bbb03ae` | Cleanup checks identify the launched process by PID |
| `6b0fde6` | `0b13784` | Optional King WarCry fixture injection; review additionally rejects trailing input |
| `541bfba` material files | Already present via `ec8dc1d` | Verified identical to the existing material module/tests; unrelated window changes excluded |

Larger incoming snapshots remain separate candidates. These branches contain
family work worth integrating, but also diverge from recent shared engine
exports. Do not replace `engine/` wholesale with their versions.

| Candidate observed | Remaining integration work |
|---|---|
| `kimi/p2-bulblax-import` at `ca3bd8b` | Reconcile broad batch-2/batch-4 exports and associated family gates |
| `opencode/p2-batch1-root` at `9b9dd20` | Reconcile cleanup, re-entry, corpse, framed display and movement work |
| `opencode/p2-batch2-handoff` at `3d30774` | Review BombSarai/Fuefuki/BigTreasure handoff |
| `opencode/p2-batch4-root` at `89103ce` | Review cleanup and reported death blocker |
| `opencode/p2-batch3-visuals` at `10d6f73` | Review movement acceptance delta |

These are inventory observations, not rejection of the families or a new
requirement for owners to wait for engine permission. #186 tracks coordination.

## Source contract

Audited GPVE01 assets, kept local:

- Queen `enemy.bmd`: SHA256 `e4904b223fa388e53092dc67c80a3668782a314b6e7683bd2284f7413cfb4414`.
- `queenchappy_model.btk`: SHA256 `af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae`.
- MAT3 `mat_queen_body` is source material 0, host shape/material 1. The head
  remains host material 0.
- Source stage 0 uses diffuse texture TEX1[2] and **UV1**, with a 2x diffuse
  texture/raster product. The ordinary converter retained UV0, so changing
  only the texture did not recover the correct body mapping.
- Source stage 1 adds TEX1[1] multiplied by raster color channel 1 to the
  previous result. Its texture coordinates are normal-derived and use the
  animated texture matrix. The layer is evaluated in the same draw, not as
  a second transparent geometry pass.
- The BTK has one slot-zero track, duration 30, loop attribute 2 and angle
  shift 1. Its nonrotating SRT uses negative X scale and an animated Y scale.
  `Queen.cpp::doAnimationCullingOff` advances the source material loop at
  30 fps while alive. Native Queen uses a separate phase on its existing
  bounded 30 Hz actor ticks, rather than resetting it when behavior changes.
  Dead actors retain their final phase; pause/UI/movie flags suppress phase
  increments; resetting the actor bank resets the phase.

The exporter verifies both source hashes and the specific material/texgen
contract before conversion. It starts with the existing Bulblax material
profile, appends source UV1 to the host UV0 array, and remaps only body vertex
UV indices. Position, normal, color, material and texture chunks remain
byte-identical during that UV operation. A second application is rejected.
All 54 Queen poses were patched; the full three-species bank still validates
174 MOD files, 8,196,096 bytes. The emitted animation text has SHA256
`8ae29e3e2fb23098021da5719a22e14116ee3af469f515655b5e8acfac32ac0c`.

## Usage

Use locally extracted source assets and an existing sampled Bulblax bank:

```powershell
py -3.12 -m experimental.pikmin2_queen_specular --imported <import-root> --bank <sampled-bank> --output <fresh-specular-bank>
py -3.12 -m experimental.pikmin2_queen_specular_stage --bank <fresh-specular-bank> --assets <private-room-assets> --output <fresh-run> --xyz 300 25 0
```

The stage command verifies the animation and model hashes before creating an
output directory. It creates a private asset overlay, a no-larvae `f_01`
Queen actor profile and `p2-queen-specular.txt`. The latter enables the native
layer; absent sidecars retain the old drawing path. The native loader rejects
wrong track identities and wrong diffuse texture bindings. The staging
manifest records installed model hashes. It is an accidental-corruption
check, not an authenticity signature for an attacker-controlled manifest.

Launch a matching private native build from the fresh run directory with
`--experimental-pikmin2-room`. Preview-specific companion configuration, such
as a cargo-pod profile, must be supplied by the chosen room fixture. The
stage does not copy saves or patch a player package. Do not edit junctioned
or hardlinked source assets inside the overlay.

`p2material::drawSpecular` is a bounded shared helper. It accepts the known
single-stage, single-texture UV0 diffuse base and a nonrotating normal-map
SRT, temporarily substitutes the two-stage material, draws the whole Shape
once, then restores texture/texgen/TEV pointers, display list and lighting
flags. It invalidates the renderer material cache around the draw, including
exception unwinding. Its `enabled=false` control keeps the same doubled
diffuse base so a comparison isolates the specular contribution.

## Validation and limits

Focused Python/native tests cover UV1 remapping with/without vertex colors,
byte-preserved geometry, malformed topology, repeated conversion refusal,
source and staged-file hash failures, existing-output preservation, the real
native TEV helper, diffuse-only mode, unsupported layouts, nonfinite samples,
and normal/exception restoration. Imported Queen/King/arena policy tests
also pass. Native production and exact fixture provenance are recorded below.

The private `scripts/pikmin2_queen_specular_fixture.cpp` loads the actual
converted Queen and source-derived BTK. It draws diffuse-only, phase 0,
phase 10, phase 0 again, and diffuse-only again within the same frame.
Both replays must match byte-for-byte. Captures were visually inspected.
Its controlled light7 is deliberate: the fixture executes after the HUD's
lighting setup. The initial comparison without that light had no visible
specular contribution. This does not establish retail lighting parity or
that every host room's lighting will produce equally visible highlights.

Remaining fidelity work: Queen's third source color stage, source-specific
lighting/attenuation, full source alpha-stage parity, moving-camera and
combat visual sign-off, and other graphics backends. This is not BRK/BTP,
general arbitrary TEV import or a change to the default converter. It does
not close the broader Queen/King gameplay umbrellas.

### Final candidate evidence

Native commit `fc60edce976ea52efd45f36f073017db915e4e41` (following
`49b06eff`) builds with `cmake --build build-timing --target pikmin_pc -j6`.
Production executable SHA256:
`385c94ec4478d68c861d3815beaeeeb676589f9029974b6a109c261c96bf0e394`.
Existing Dolphin header and serialized-LTO warnings remain.

Final fixture SHA256:
`68c0df5338e8cdc956a80b8c6bc240ca5fc41df62606fc88042709987228c321`.
Built with `scripts.build_pikmin2_fixture` against that exact native HEAD;
provenance and dependency snapshots are in private `output/queen399/fixture-final`.
Native actor setup accepted the prepared bank and the renderer completed the
comparison with 695067 visible channels, 242772 specular-contribution channels
and 336607 channels changed between source phases 0 and 10. Both phase-zero
and diffuse-only replays were byte-identical. Captures and the final log are
in `output/queen399/run`; rendered pixel counts depend on the fixture camera.
The captured ordinary scene also proves actor setup/draw runs with the sidecar,
but is not gameplay or whole-scene material sign-off.

`pytest tests -q -rs` with MinGW on PATH: **1389 passed, 23 skipped,
1049 subtests passed**. Skips require local asset outputs or Windows symlink
privileges. Focused material, UV, actor and arena tests: **42 passed,
379 subtests passed**. The later native binding/pause guard was additionally
production-built and exercised by the final real-bank fixture startup.
