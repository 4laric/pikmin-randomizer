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
first on their own 33 committed targets (six-gate species never use
proxy-only targets), each remaining species takes one unique accepted
target where its terrains match, and species without a target are listed
under `unplaced` (they stay vanilla). There are 49 proxy-tier targets:
the 33 committed ground slots plus a 16-slot proxy-only sibling
(`docs/PIKMIN2_PROXY_PLACEMENT.json`, schema `p2-proxy-placement-v1`):
2 Hope singleton dwarf slots and 14 pack generators (Hope grubs,
Spring dwarfs/grubs, counts 2-3) carrying `pack: true`, member `count`,
`original_teki`, `first_day`, and honest mechanical-only evidence. Pack
binding was proven by a launch probe (2026-09-21, native
`claude/p2-proxy-family` at `ba6832cef`, unmodified product sampler,
Forest of Hope and Distant Spring day 2): all 8 packs live on day 2
bound every member (`P2_BATCH2_BIND` lines per species equal the pack
count), with no `P2_SETUP_SKIP` and no duplicate-generator abort; the
6 day-5/day-16 packs share that native path but were not live in the
probe. Terrain/route stay "unprobed" in the evidence string because the
`P2_PLACEMENT_SLOT ground/route=1` markers the probe emitted were not
folded through `scripts/audit_p2_placement_evidence.py`. 49 stays under
the native 64-binding cap, enforced fail-closed in the sampler.

Pack rule: a pack births 2-5 hosts of the same swapped type, so a large
or dangerous host (Spotty Bulborb 4, Bulbear 32, Fiery Blowhog 15, Puffy
Blowhog 16, Armored Cannon Beetle 17, Snitchbug 11, ...) would multiply
difficulty and crowd the spot. Pack targets therefore admit only
small-host proxy rows (`pack_hosts: [0, 3, 18, 19, 20, 25, 31, 33]` in
the sibling, enforced in `_proxy_accepted_targets`; any other host is
simply ineligible on pack targets, singletons keep the full ground set).
The set is every SAFE host in the host-safety review with no
open-air/pellet/clearance condition beyond landing space (section 4 verdicts
for 18/19/20/25/31/33) plus the proven vanilla small hosts Frog 0 / Chappy 3
(host-safety scope): Chappy 3 /
Chappb 31 (proven dwarf family, same cohort as the dwarf packs),
Kabekui 18/19/20 (self-contained burrowers, same cohort as the grub
packs), Otama 25 (land-capable), Frog 0 / Frow 33 (landing space only).
Excluded with reason: Qurione 6 (ephemeral 5 s floater, not a durable
guard), Collec 8 (needs pellets/waypoints unprobed on these slots),
Napkid 11 / Mar 16 (obligate 60-height fliers; slots carry
`flight_space: false`), Beatle 17 (firing lane + vehicle), and all
large/dangerous hosts. Only 20 of the 50 declared proxy rows are
small-host, so wide pools still leave species `unplaced`; the sampler
places as many distinct eligible species as the rule allows and never
fills a target with a repeat while an eligible unplaced species exists.

## Staging limits

The stager enforces the native sidecar caps fail-closed: at most 100
generator rows in `p2-proxy-actors.txt` and at most 64 species rows in
`p2-proxy-campaign.txt`. Anything past a cap is refused with
`StagingError`, never silently truncated. The per-species 8 MiB pose
budget is enforced at extraction; there is no multi-species total-bytes
guard on the root side (the native per-scene budget is 48 MiB), so watch
the per-stage staged bytes on wide pools.
