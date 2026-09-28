# Play a P2 seed: ISO to staged session

Single step from the P2 retail ISO to what `randomizer run --p2-content
--p2-actors` needs. All commands run from the repo root. Never commit game
assets or anything extracted from the ISO; generated content stays under
`output/reduced/rd-p2ap-content/` (untracked).

## 1. Generate a playable-pool seed

Playable = species the launcher can run today: 44 BlueKochappy, 54 Mamuta,
59-62 Otakara (`randomizer/seed.py` `PLAYABLE_P2_SPECIES`).

```powershell
py -3.12 -m randomizer generate --seed rd-p2ap-content-playable `
  --p2-enemies --p2-species playable `
  --output output/reduced/rd-p2ap-content/seed-manifest.json
```

This writes a manifest whose `p2_layout.bindings` are `{target, source_id,
enum_name}` entries over the committed accepted-placement document
(`docs/PIKMIN2_ADMITTED_PLACEMENT.json`); targets are slot-uid tokens
(`randomizer/p2_placement_catalog.py`).

## 2. Prepare the identity-keyed content root + actor bindings

```powershell
py -3.12 scripts/p2_prepare_content.py `
  --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" `
  --out output/reduced/rd-p2ap-content/p2-content `
  --seed-manifest output/reduced/rd-p2ap-content/seed-manifest.json `
  --actors-out output/reduced/rd-p2ap-content/p2-actors.json
```

What it does (existing per-family extractors are reused, never rewritten):

* 44 BlueKochappy: `pikmin2_dwarf_orange_profile.extract` +
  `pikmin2_dwarf_orange_bank.build` -> `<out>/BlueKochappy/{bank,profile}/`.
* 54 Miulin: `pikmin2_mamuta_assets.extract` -> `<out>/Miulin/` directly.
* 59-62 Otakara: `pikmin2_dweevil_assets.extract` once, then the full import
  tree (`dweevils.json` + species banks) under each of `<out>/FireOtakara`,
  `WaterOtakara`, `GasOtakara`, `ElecOtakara`, because the shared-contract
  dweevil installer validates the whole five-species manifest per install.
* 23 Sarai: `pikmin2_sarai_assets.extract` for the source poses, then the
  validator-required `sarai-attack-mouths.txt` is derived from that extraction
  (mouth joints + pose files + sha256; see `sarai-mouths-provenance.json`).
* Ids with no family installer (9 Kogane, 57 Kurage, 78 MiniHoudai,
  79 Sokkuri) are reported as skipped in `<out>/prepared.json`, never
  fabricated.

Actor bindings map every `p2_layout` binding target to its native generator
id, deterministically: `generator_id = int(target)` (targets are unique
slot uids fitting uint32, so the mapping is bijective).

## 3. Stage the session (writes `p2-binding-receipt.json`)

```powershell
py -3.12 -m randomizer run output/reduced/rd-p2ap-content/seed-manifest.json `
  --p2-content output/reduced/rd-p2ap-content/p2-content `
  --p2-actors output/reduced/rd-p2ap-content/p2-actors.json `
  --session-dir output/reduced/rd-p2ap-content/session `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets
```

Without `--exe` this stages only: `install_layout` writes the per-family
sidecars and models into `session/runs/<token>/` plus
`p2-binding-receipt.json`, then the runner waits for a native process, so
stop it once the receipt is written (there is no headless native mode; do
not pass `--exe` expecting a windowless launch).

## Known blocker (2026-09-19, lane rd-p2ap-content)

Staging a full playable seed (33 bindings over 6 species) currently fails
before any receipt is written:

```
ValueError: Refusing existing/conflicting dweevil installation
```

`experimental/pikmin2_family_install.py::install_layout` calls the family
installer once per binding with a single actor, but the dwarf_orange, mamuta
and batch2 (dweevil) installers refuse a second install into the same run
(only the Sarai adapter accumulates). Every real seed repeats families, so
no full seed can stage until that shared layer groups installs by family or
the installers accumulate like Sarai. Single-binding installs of this lane's
real ISO-extracted content (44, 54, 59, 23) each stage cleanly, so the content
root itself is valid; the defect is in the shared binding layer, owned by the
integration lead (#186). See `output/reduced/rd-p2ap-content/staged-run.md`.
