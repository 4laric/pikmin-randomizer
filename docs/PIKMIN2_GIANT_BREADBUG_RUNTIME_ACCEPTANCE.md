# Giant/nest native display runtime acceptance (#229)

Codex completed this bounded display acceptance using the actual integrated
native module. It does not establish Giant enemy gameplay.

## Results

All four separate native runs exited 0: Giant wait, Giant move, nest, and
missing-profile control. Each enabled run loaded and drew, captured two poses,
reset, captured the absent model, reloaded and captured the restored model.
Disabled mode produced neither setup nor draw markers. Native assertions kept
Teki count 0, cargo count 0 and repairs 1 through setup/draw/reset/reload.
No Pod/cargo receipt was created. These assertions are display isolation,
not save/campaign or enemy combat acceptance.

I inspected lossless captures: Giant face/body visible in wait and move,
leaf-covered nest visible, Giant absent after reset, and Giant visible again
after reload. The original ship dust and foliage remain in the scene and can
partly obscure background objects. No shape rescaling was applied.

Display ID 229001, XYZ (103.058197, 30, 1906.487915), yaw 0, scale 1 was
recorded identically in each enabled run. This was an explicit engineering
placement relative to the captain, projected onto actual P1 Impact Site
collision. It is not a source-generated P2 placement. Twenty ordinary Reds
were added to the original start to avoid extinction blocking; no Teki or
cargo generator was added. Original course bytes were hash-checked unchanged.

The private fixture includes the established tutorial A-pulse shim, movie
skip and frozen captain controller. The model samples animate by display
clock; there is no AI/collision/contest, and the walking pose stays in place.
Reset/reload here calls the actual module APIs within one process; a full
scene transition/save reload remains untested. Small-Breadbug source/config
was untouched; a live small-Breadbug coexistence test was not added.

## Provenance and artifacts

All paths below are relative to `C:/Users/alari/pikmin-randomizer/output/p2-root-integration`.

- Fixture: `output/p2-giant-breadbug-runtime/fixture01/build/fixture.exe`
- SHA256: `443244756335b222c71e0373fd320bcd094d0a38e885ae43dc935efa04f1e8b9`
- Build provenance: adjacent `provenance.json`, copied `link-inputs`, compile/link logs.
- Native HEAD: `7faa64475176658af85e2f558858c6d660cd4d20`.
- Source snapshot records inherited tracked changes in creatureCollision.cpp
  and goalItem.cpp, diff SHA256
  `7c5baccf4deb14218bb8690dc795a9a6a0c629e3bf2d2f3b9eec501a6bb957ad`,
  plus untracked research source. This is not a clean-HEAD binary claim.
- Runtime report: `output/p2-giant-breadbug-runtime/validation01/result.json`.
- Per-run directories contain native.log, stage provenance and four PPM/PNG
  captures: giant-pose-a, giant-pose-b, giant-reset, giant-reload.
- Existing GX depth-texture 0x11/GXCopyTex-stub warning occurred in all four
  modes, including disabled, before these displays loaded. No warning-free
  engine or material parity claim.

New code: `experimental/pikmin2_giant_breadbug_runtime.py`; new tests:
`tests/test_pikmin2_giant_breadbug_runtime.py`. Four runtime/staging tests pass;
combined with the previous native-parser/installer suites, 10 tests pass.
No shared native source, shared build or existing save was modified.

## Fixed local Kimi launch paths

Use these local scripts; they create a fresh disposable stage each launch:

- `output/p2-giant-breadbug-runtime/kimi/Play-wait.cmd`
- `output/p2-giant-breadbug-runtime/kimi/Play-move.cmd`
- `output/p2-giant-breadbug-runtime/kimi/Play-nest.cmd`

The display resets briefly during the automated check, then reloads and stays
open. Close the game window to exit. Window/title and terminal explicitly
say noninteractive. The Python `play` command uses the same proven stage and
fixture as acceptance plus a keep-open marker; the batch-file launch itself
has not been separately driven by UI automation. It uses local legal assets,
Python 3.12 and MinGW runtime DLLs and is not a redistributable release bundle.
`kimi/handoff.json` records exact paths and executable hash. Kimi manual QA
remains separate from these developer fixture passes.

Giant actor registration, Purple-only press, cargo contests, owner-linked
nest storage/recovery/save behavior and animated texture-matrix fidelity
remain the gates listed in PIKMIN2_GIANT_BREADBUG_NATIVE_BINDING.md.
