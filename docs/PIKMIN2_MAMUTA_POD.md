# Mamuta carcass Pod receipt (lane 19, #168 / #221)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4.1-flash), 2026-09-14. Extends
[PIKMIN2_MAMUTA_NATURAL.md](PIKMIN2_MAMUTA_NATURAL.md), whose gate 5 (natural
corpse pickup -> transport/reward) was recorded BLOCKED/UNPROVEN.

## Why gate 5 could not close

The natural arena is staged **cargo-free**: `experimental/pikmin2_mamuta_arena.py`
always writes `p2-cargo-free.txt`, and the fixture asserts
`pc_p2_preview_cargo_free_ready()`. A cargo-free preview has no Pod
(`pc_p2_preview.cpp`), so there is no reward endpoint for the Mamuta carcass.

Even with a Pod, the preview credits only Chappy corpses:
`pc_p2_preview_rebind_corpses` registers `TEKI_Chappy` actors, and
`pc_p2_preview_deliver` aborts on any unregistered pellet ("Unregistered P2 pod
cargo"). `pc_p2_preview_deliver` already routes family corpses through
`pc_p2_sheargrub_receipt`, but there was no Mamuta equivalent.

## What this adds

`pc_p2_mamuta_receipt(PelletView*, unsigned& generator)` in
`pc_port/pc_p2_mamuta.{h,cpp}` resolves a Mamuta carcass pellet (the bound
actor's own `PelletView`) to its generator. `pc_p2_preview_deliver` now routes it
before the corpse-registry fallback, crediting
`corpse:<prefix>mamuta:<generator>` with the Pod's configured `corpseValue`. This
mirrors the existing sheargrub family receipt and changes no other cargo/reward
path; Chappy behavior is untouched.

## Build evidence

Private Ninja Release/MinGW JAudio-ON build `output/native-mamuta-pod-build`:
`pikmin_pc` links `bin/nectar.exe` sha256
`6C49DC33591C13F279014D49098651875CC116F9805E1E59321C8E116461515D`; `ninja -n`
-> no work to do.

## Cargo staging helper (root)

`experimental/pikmin2_mamuta_rules.py` gains `cargo_profile(...)` (the exact
`p2-pod.txt` text the native reader parses) and `enable_cargo(run, ...)`, which
switches a cargo-free staged arena to a Pod: it requires the arena to still be
cargo-free and a matching staged
`assets/dataDir/courses/pikmin2room/treasure.mod`, writes `p2-pod.txt`, and
removes `p2-cargo-free.txt`. `prepare(..., cargo=...)` calls it and records the
result in `arena.json`. Bad ids/economy, a missing/mismatched treasure model, an
already-converted arena or an existing Pod config all fail closed.

Tests `tests/test_pikmin2_mamuta_cargo.py` cover the profile text and every
guard (5 passed); the lane suite `test_pikmin2_mamuta_{natural,rules,cargo}.py`
is green (20 passed).

## Remaining (not claimed here)

- **Treasure actor + converted model.** `enable_cargo` needs a staged
  `treasure.mod` and a `pr05` treasure actor in the stage gen (the preview
  aborts with 'treasure generator missing'/'converted treasure missing'
  otherwise, and `p2ValidatePreviewCargo` requires a treasure when not
  cargo-free). No such actor is staged by the lane yet.
- **Natural vs assisted carry.** Whether idle P1 Pikmin pick up the `tkmu`
  carcass unaided in a Pod arena is unmeasured; an assisted-transport variant may
  be required.
- **Day/floor reset, save-load, Piklopedia** remain open from the natural doc.

## Provenance

Native candidate `opencode/p2-mamuta-pod` (local-only, not pushed), base
`f14c6851473ac1161be56c8b98f4f905232f3635`, head
`a54f4af24286e264b1baf00ca80509f7ec6814ac`; worktree `output/native-mamuta-pod`.
Patch: `native-candidates/mamuta-pod/0001-*.patch`; metadata in
`native-candidates/mamuta-pod/provenance.json`. Native origin/upstream not
pushed. No maintained checkout or shared build modified.
