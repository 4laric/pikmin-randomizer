# Upstream GL specular changes vs actual P2 materials (#128, #399, #429)

Engine/toolchain lane (09), Codex through shared account `4laric`. Scope:
integrate the upstream GL specular fixes and validate them against actual P2
material paths; list the real-bank failures that remain.

## Integration

The two upstream commits were **not** ancestors of the maintained native tip
`f9e139d8` (`codex/pikmin2-room-preview`) nor of `opencode/p2-integration-128`.
They live on `upstream/main` (and `codex/p2-main-review-native`). They are now
cherry-picked onto the lane branch `opencode/p2-lanes789-native`:

| Commit | Subject | File |
|---|---|---|
| `01b15dea` | `gl: GX_AF_SPEC es 0, no 2, y el especular es un cociente` | `pc_port/gl/pc_gfx.cpp` |
| `413f9251` | `gl: implementar GXInitSpecularDir de verdad` | `pc_port/gl/pc_gfx.cpp` |

Candidate lane HEAD for these two commits `eb7c911a`; base `f9e139d8` (the
lane branch later carries the #397 rebind candidates to `b185ff89`).
Integration of GL/shared renderer changes is owned by lane 01 and needs #186
review.

### What the fixes correct

- `GXAttnFn` is `0=SPEC, 1=SPOT, 2=NONE`. The vertex shader tested
  `uChan1AttnFn == 2` for the specular branch, so a specular channel
  (`GX_AF_SPEC == 0`) never entered it and COLOR1 fell through the diffuse path
  (double-counting / saturating specular materials). It now tests `== 0` and
  evaluates specular as the ratio of two `N.H` quadratics, the angle
  coefficients over the distance coefficients (`pc_gfx.cpp:1372-1395`).
- `pc_gfx_init_specular_dir` was a copy of the diffuse direction setter. It now
  writes the hardware half-vector `normalize(-n + (0,0,1))` into `ldir` and the
  direction scaled by `1024*1024` into `lpos` (`pc_gfx.cpp:3770-3800`).

### Why this reaches P2 materials

`decode_xf_attn_fn(control)` maps the XF channel control to
`bit9 ? GX_AF_SPOT : GX_AF_SPEC` (`pc_gfx.cpp:478-482`), and the host uploads
the specular half-vector/`a[]` coefficients for channel 1 when
`attnFn == GX_AF_SPEC` (`pc_gfx.cpp:6146`). Any converted P2 material that
emits a specular COLOR1 channel now takes the corrected branch. The primary P2
consumer is the opt-in Empress Bulblax path (`#399`,
`p2material::drawSpecular`), which builds a two-stage diffuse+normal/specular
material; the upstream commit message records the Onions as the other obvious
beneficiary.

## Validation performed

- Cherry-picks apply cleanly; production build
  `output/tracks/p2-lanes789/native-build` links
  `bin\nectar.exe` with `ninja -n` -> `no work to do`.
- Offline converter/material suites on the lane root branch (base
  `opencode/p2-integration-128` @ `74afca7`, MinGW on PATH):
  - `tests/test_pikmin2_animation_clock.py`, `test_pikmin2_convert_billboard.py`,
    `test_pikmin2_convert_normals.py`, `test_pikmin2_flora_assets.py`
    -> **62 passed**.
  - `tests/test_pikmin2_bulblax_material.py`, `test_pikmin2_frog_material_compare.py`,
    `test_pikmin2_frog_material_profile.py`,
    `test_pikmin2_qurione_material_audit.py`,
    `test_pikmin2_qurione_material_patch.py` -> **26 passed**.
- Real-GL smoke (flora lifecycle arena, adapter `Intel(R) Graphics`, GL 3.3,
  `TEV specialisation: on`): the engine carrying both specular fixes rendered a
  960x540 scene to `PASS P2_LIFECYCLE_RUNTIME`, exit 0, with no GL error. This
  proves the fixed renderer runs, **not** that a specular highlight changed.
- **PASS — measured on the real Queen material (A/B).** The two upstream
  commits were applied to the #422 integration native line, which already
  carries the P2 material/queen modules, and the #399 fixture was run against
  the same staged assets and camera on both renderers.

  | Run | Native | `visible` | `animated` | `specular` |
  |---|---|---:|---:|---:|
  | BASE (pre-fix) | `0ab3ea12` | 694380 | 336266 | 242347 |
  | FIXED | `0ab3ea12` + `01b15dea` + `413f9251` | 695384 | 320703 | 260655 |

  Both `PASS QUEEN_SPECULAR_RENDER` with `replay_equal=1`; the only changed
  input is the upstream GL specular code, so the specular contribution and the
  animated-channel delta are attributable to it (a stronger highlight and a
  smaller broad wash, matching the ratio-lobe correction).

  Setup:
  - Native branches `opencode/p2-lanes789-queen-native` @ `d4bc8dbc`
    (fixed; `bin\nectar.exe` `255E0C7D…`) and `queen-native-base` @ `0ab3ea12`
    (`C1B95F06…`); fixtures `C58B44A0…` / `9BFEC5B8…`.
  - Bank prepared from the real source (`output/bulblax-run1` +
    `output/bulblax-bank2-run2`; source hashes `e4904b22…`/`af0dde01…`);
    `p2-queen-specular.txt` SHA-256
    `8AE29E3E2FB23098021DA5719A22E14116EE3AF469F515655B5E8ACFAC32AC0C` matches
    the #399 doc exactly.
  - Room assets are the room-preview overlay specified by
    `docs/PIKMIN2_ROOM_PREVIEW.md`:
    `output/pikmin2-room-preview/25e03db572bd40bab335332dd03d212f/assets`
    (its `default.gen` carries the `50rp` treasure so `pc_p2_preview_ready()`
    stabilises; the family-arena assets use `p2-cargo-free.txt` and do not).
  - Run `output/tracks/p2-lanes789/queen-specular-run-03`, 960x540
    (`[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)`),
    logs `native-fixed.log` / `native-base.log`, both exit 0.

  Repro (the stage's `--assets` is an existing room-preview `assets` dir, not a
  family arena):

  ```powershell
  py -3.12 -m experimental.pikmin2_queen_specular --imported output/bulblax-run1 `
      --bank output/bulblax-bank2-run2 --output <fresh-specular-bank>
  py -3.12 -m experimental.pikmin2_queen_specular_stage --bank <fresh-specular-bank> `
      --assets output/pikmin2-room-preview/<run>/assets --output <fresh-run> --xyz 300 25 0
  # then launch the fixture built from scripts/pikmin2_queen_specular_fixture.cpp
  ```

## Remaining real-bank failures

These are source/converter gaps; the GL specular fix neither causes nor closes
them. Each is a converter/profile/design item, not a shader bug.

| Bank | Status | Remaining failure |
|---|---|---|
| Queen `enemy.bmd` | Two-stage diffuse+specular opt-in present (#399/#416) | Source color stage 3, source-specific lighting/attenuation, full alpha-stage parity, moving-camera/combat sign-off. The #416 static envmap rewrite must not be stacked on the #399 prepared bank. |
| Frog / MaroFrog | Native identity/motion pass; materials unlit | Generic converter emits lighting control `0/0x1800` with no Color1 specular attenuation and omits the 2x TEV scale + additive stage; register color 204 lost. `collections` the GL fix cannot help because no specular channel is emitted. Needs the audited diffuse+specular material profile. |
| Qurione (Honeywisp) | Opt-in TEV register/alpha patch exists (#207) | Source two-material expression `clamp(2*C0*lit_RASC)`; export emits white register and scale1. Runtime compare was INCONCLUSIVE (actor out of view). Needs a camera-framed fixed-flight fixture. |
| Tank / Wtank | Diagnosed | Matching body-channel loss; owned by the Tank lane. |
| HikariKinoko | Static billboard fallback only (#429) | Native camera-facing billboard orientation absent; static fallback is a labeled approximation. |
| Snow and other P1 proxies | Unchanged | P1 material/lighting; not a P2 source-material claim. |

## Non-claims

No gameplay/visual fidelity pass is claimed. The GL fix is a renderer-correctness
change; converted banks that omit lighting/specular stages remain unconverted at
the source level. Third source stages, source lighting and camera-facing
billboards remain distinct capabilities owned with the converter (#128).
Nothing was pushed to native origin and `native/build-randomizer` was not used.
