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
`p2-pod.txt` text the native reader parses), `parse_cargo_profile(...)`,
`load_pod_package(...)`/`find_pod_package(...)`, `treasure_record(...)`/
`append_treasure_record(...)` and `stage_cargo(...)`; `enable_cargo(...)` and
`prepare(..., cargo=...)` are extended.

A "Pod asset package" is the disc-derived trio `p2-pod.txt`, `pod.mod` and
`treasure.mod` produced once by `experimental.pikmin2_pod.extract` (or
`pikmin2_beasts_content`) and cached under `output/`. The already-converted
package for this lane is `output/pikmin2-pod111/import-01` (`dia_a_red 180 15
25` / `Kochappy 2`, hashes in `provenance.json`); it is not committed.

`prepare(..., cargo=dict(pod_package=<dir>[, position=<xyz>]))`:
1. loads/hashes the package and stages `treasure.mod` + `pod.mod` into
   `assets/dataDir/courses/pikmin2room/`;
2. appends the single `pr05` treasure actor (reserved generator `221004`) to the
   staged `chal0/default.gen`;
3. removes `p2-cargo-free.txt` and writes `p2-pod.txt` via `enable_cargo`, which
   now also verifies `pod.mod`.

Every stage fails closed before mutation when the package is unavailable, a
model hash mismatches, a second `pr05` actor is present, or the arena is not
cargo-free. Unit tests cover the profile round-trip, package loading/fail-closed,
record append/duplicate guards, and the Pod validators.

End-to-end source staging was exercised headlessly (no GL) at
`output/mamuta-pod-stage-smoke-01/<run>`: `p2-pod.txt` present,
`p2-cargo-free.txt` removed, the generator holds 8 records including the `pr05`
actor at generator `221004`, and `arena.json` records
`gates.pod_cargo=staged`.

## Pod observation fixtures (compile-only)

`scripts/pikmin2_mamuta_pod_fixture.inc` (unassisted) and
`scripts/pikmin2_mamuta_pod_assisted_fixture.inc` (explicitly labelled
`assisted=1`) reuse `experimental/pikmin2_mamuta_natural_runtime.build(...,
fixture=...)`. Both wait for `pc_p2_preview_ready()`, assert the staged `pr05`
actor and zero starting Pokos, drive the natural captain approach, then observe
kill/corpse/carry and the Pod receipt
(`P2_POD_RECEIPT id=corpse:...mamuta:221001`). The unassisted fixture never
forces pickup; the assisted variant assigns the native `Transport` action after
a grace period and is never reported as natural.

`scripts/pikmin2_mamuta_pod_native.py` stages the Pod arena and validates the
Pod markers (`validate(...)` classifies `pod_ready`, kill, corpse, natural /
assisted carry and `pod_receipt`).

Both fixtures were compiled and linked privately against the approved native
head `a54f4af2` (no GL run):

| fixture | dir | fixture.exe sha256 |
| --- | --- | --- |
| unassisted | `output/mamuta-pod-fixture-natural-01` | `30C36E92882C8B154605D7AAE9147812EFFA9D1BB3CB5C1582E1BA411453A1F4` |
| assisted | `output/mamuta-pod-fixture-assisted-01` | `90D18D244BC31FA2FF2ACDB0BF6037C104531E727BA46AD681FA69F291BED0F7` |

`ninja -n` on `output/native-mamuta-pod-build` -> `ninja: no work to do.`;
`pikmin_pc` = `bin/nectar.exe` sha256
`6C49DC33591C13F279014D49098651875CC116F9805E1E59321C8E116461515D` (unchanged,
no native code added by this batch).

## Tests

`py -3.12 -m pytest tests/test_pikmin2_mamuta_cargo.py
tests/test_pikmin2_mamuta_natural.py tests/test_pikmin2_mamuta_rules.py
tests/test_pikmin2_mamuta_pod.py -q` -> 32 passed; the wider lane family
(`..._assets/_install/_runtime/_native`) -> 65 passed + 24 subtests. The Pod
staging tests are asset-independent and skip nothing; `prepare`-with-assets
tests skip only when the local user assets/import are absent.

## Remaining (not claimed here)

- **Runtime GL acceptance.** No display is available; nothing above is a
  runtime PASS. The fixtures compile/link and the staging is proven, but the
  Pod receipt has not been observed in the engine.
- **Natural vs assisted carry.** Whether idle P1-proxy Pikmin pick up the `tkmu`
  carcass unaided in a Pod arena is unmeasured; the assisted variant exists and
  is labelled.
- **Day/floor reset, save-load, Piklopedia** remain open from the natural doc.

## Exact human GL acceptance commands (not run here)

```powershell
# natural (unassisted) Pod observation:
py -3.12 -m scripts.pikmin2_mamuta_pod_native --assets <assets> --imported <imported> `
  --exe output/mamuta-pod-fixture-natural-01/fixture.exe `
  --output output/mamuta-pod-accept-natural --pod-package output/pikmin2-pod111/import-01

# observed log must contain:
#   P2_POD_READY treasure=dia_a_red ...
#   P2_MAMUTA_POD_RESULT ...
#   P2_POD_RECEIPT id=corpse:...mamuta:221001 value=2 ...   <-- gate 5
#   PASS P2_MAMUTA_POD_RUNTIME observe approach receipt reset
```

Assisted (must be labelled assisted, never natural):

```powershell
py -3.12 -m scripts.pikmin2_mamuta_pod_native --assets <assets> --imported <imported> `
  --exe output/mamuta-pod-fixture-assisted-01/fixture.exe `
  --output output/mamuta-pod-accept-assisted --pod-package output/pikmin2-pod111/import-01 `
  --assisted
```

Gate 5 closes only when the natural run emits the `mamuta:221001` receipt (or
the assisted run does, reported as assisted).

## Provenance

Native candidate `opencode/p2-mamuta-pod` (local-only, not pushed), base
`f14c6851473ac1161be56c8b98f4f905232f3635`, head
`a54f4af24286e264b1baf00ca80509f7ec6814ac`; worktree `output/native-mamuta-pod`.
Patch: `native-candidates/mamuta-pod/0001-*.patch`; metadata in
`native-candidates/mamuta-pod/provenance.json`. Root worktree
`output/mamuta-pod-root` on `opencode/p2-mamuta-pod-root`. Native
origin/upstream not pushed. No maintained checkout or shared build modified.

