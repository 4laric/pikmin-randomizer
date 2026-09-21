# P2 proxy tier: declaration, evidence, and generation

A proxy species is a Pikmin 2 model with sampled animations staged over a
real Pikmin 1 host enemy type. What runs in the game is P1 behaviour and
combat (movement, attacks, damage, death, corpse) with a P2 appearance.
A proxy species is not a P2 identity: it is never recorded in
`experimental/pikmin2_enemy_roster.py`,
`docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json`, or `P2_PLAYABLE_POOL`, and it
never passes through the six-gate admission those files gate. The roster
contract is untouched by this tier; proxy rows only declare how a species
is extracted and staged.

## Declaring a species

One JSON file per species: `randomizer/p2_proxy/<source_id>_<Enum>.json`,
validated fail-closed by `randomizer/p2_proxy.load_rows()`.

Required fields: `schema` (1), `source_id` (int), `enum_name` (must match
the roster entry for that source id), `host_teki` (a safe Pikmin 1 vehicle
type; placeholders 26-29/34 and the other non-free-standing types are
refused), `pose_limit` (2..8 sampled poses per clip; a `None` limit in a
direct `extract_proxy` call takes this value).

Optional fields:

* `terrains` (default `["ground"]`): slot terrains the species may be
  placed on, from `ground`/`water`/`mixed`/`air`. Placement intersects
  these with the slot terrains of the accepted-placement document; today
  all committed slots are `ground`. `26_Catfish` and `27_Tadpole` accept
  `["ground", "water"]` because their hosts (TEKI_Namazu, TEKI_Otama) are
  land-capable; everything else stays on the default.
* `asset_dir` / `param_dir`: disc directory / parameter prefix when they
  are not the enum name / lowercase enum name.
* `clips` (`{canonical_output: source_stem}`): alias a registry clip stem
  to a native clip name when the species' `enemyanimmgr.txt` lacks the
  canonical stem.
* `param_files` (`{metadata_filename: prefix}`): per-file parameter
  prefixes for split families.
* `missing_normals` (only `"compute"`): opt-in converter normal policy,
  passed to the model decode exactly like the admitted bulblax
  extractor's `POLICIES` (`docs/PIKMIN2_NORMAL_POLICY.md`). Needed when a
  shape references no normal attribute (KingChappy shape 0). Recorded in
  `proxy.json`.
* `evidence`: probe evidence block (see below). Rows carrying a valid
  block form the `proven` tier; every declared row forms `declared`.

## Evidence bar

A proxy species is proven when a campaign probe shows all three in one
native log: the campaign `table` binds it, the seed `bind`s it to a
generator, and it is `drawn` live. Evidence is recorded with:

```powershell
py -3.12 scripts/p2_proxy_record_evidence.py --result <probe result.json> --native-commit <hex> [--rows-dir randomizer/p2_proxy]
```

The result carries `log`, `log_sha256` (re-verified against the file on
disk; mismatch refuses the run), `table` (non-empty), `bound_species`,
`drawn_live`, `expected`, `skips`, `fatal` (must be empty), `ok` (must be
true) and `exe_sha256`. Each expected species that is bound, drawn, in a
non-empty table, with no fatal and no skip naming it, gets an `evidence`
block (`run` = probe name, `log`, `log_sha256`, `native_commit`,
`recorded` = today, `markers` all true). A species that is bound but not
drawn is not recorded. Anything else is refused with a reason; the script
is idempotent and touches no other row field.

## Generation CLI

```powershell
py -3.12 -m randomizer generate --seed <name> --p2-enemies --p2-proxy-tier declared --p2-species full --output <seed.json>
py -3.12 scripts/p2_prepare_content.py --iso "<iso>" --out <content> --seed-manifest <seed.json> --actors-out <actors.json>
```

`--p2-proxy-tier {proven,declared}` opts in; `--p2-species full` means
the playable six plus the tier's species. `declared` is for private probe
runs only. `p2_prepare_content` extracts every proxy id the manifest's
`p2_layout` bindings bind (no manual `extract_proxy` call); manifests
without proxy bindings extract exactly the default list. An
already-extracted species directory stays an error (same convention as
the non-proxy extractors); the message names the directory.

## Placement rule

Proxy placement uses the `sampled-v1` density policy
(`experimental/pikmin2_seed_bridge.py`): playable species are assigned
first, each remaining species takes one unique accepted target where its
terrains match, and species without a target are listed under `unplaced`
(they stay vanilla). Today there are 33 ground slots, so a 50-species
declared pool leaves most species `unplaced` on any given seed.

## Staging limits

The stager enforces the native sidecar caps fail-closed: at most 100
generator rows in `p2-proxy-actors.txt` and at most 64 species rows in
`p2-proxy-campaign.txt`. Anything past a cap is refused with
`StagingError`, never silently truncated. The per-species 8 MiB pose
budget is enforced at extraction; there is no multi-species total-bytes
guard on the root side (the native per-scene budget is 48 MiB), so watch
the per-stage staged bytes on wide pools.
