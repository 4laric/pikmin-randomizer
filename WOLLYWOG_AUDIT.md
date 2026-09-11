# Wollywog cohort candidate audit (#44)

Implementation owner: Codex using shared account 4laric. This is an audit tranche;
the cohort is not enabled in seeds. Source review and loaded parameter comparison
do not establish physical compatibility.

Regenerate evidence from an existing asset directory:

```powershell
python scripts/audit_wollywog_cohort.py <assets> --output output/wollywog44-audit.json
```

Repeat with `--check` to verify identical evidence. The report fingerprints the
parameter, model, collision, animation and key files, and records the unchanged
campaign catalog hash. It does not copy asset payloads into the repository.

## Findings

`TEKI_Frog` is type 0 (Yellow Wollywog); `TEKI_Frow` is type 33 (Wollywog).
Both are registered with `TaiOtimotiStrategy` in `tekinakata.cpp`, with separate
parameter and sound classes. `TAI/Otimoti.h` defines 21 integer and 62 float
parameters. The installed version-11 files contain 368 bytes, decoded according
to `TekiParameters::read` and `ParaMultiParameters::read`, not constructor defaults.

| Loaded parameter | Yellow Wollywog | Wollywog |
| --- | ---: | ---: |
| Health | 2000 | 1800 |
| Scale | 1 | 1 |
| Walk / run speed | 30 / 190 | 30 / 190 |
| Collision radius | 24 | 24 |
| Corpse radius / height | 20 / 10 | 20 / 10 |
| Attackable range | 240 | 240 |
| Flight height | 100 | 100 |
| Drop velocity | 100 | 100 |
| AI culling type | 0 | 0 |

Matching configured radii do not prove matching model footprints or jump clearance.
The strategy includes water-specific behavior; dry and submerged routes require
separate observation. Both leave corpses. Pellet-manager carrier counts and seed
yields remain to be decoded; corpse radius is not carrying weight.

## Generator candidates

All eleven active records are point spawns with one body and persistence flags 5.
Seven pass the structural candidate filter:

- Forest Navel: `2/0-29.gen@852`, `@1059`, `@1266`, `@1473`; original type 33,
  respawn interval 5, available throughout campaign days 2–29.
- Distant Spring: `3/init.gen@3872`, `@4079`, `@8618`; original type 0,
  respawn interval 5. The last uses fixed-count `aton` rather than `1one`.

Four Spring records (`3/init.gen@2880`, `@3087`, `@3294`, `@3501`) have special
personality parameter -1. Keep them pinned. No active Wollywog record has a named
pellet ID. Candidate personality payloads retain pellet counts 1–2, chance about
0.7 and zero nectar; drop randomization is a separate track (#47).

Proposed source policy, pending implementation: require both species in each
area's early renewable candidate slots and preserve protected sources. Assign
before AP fill and derive bestiary access from the saved choices. Keep conservative
Blue/carry requirements until actual return routes support loosening them.

## Remaining acceptance before enabling

1. Decode corpse carry requirements/yields and verify existing farming assumptions.
2. Exercise replacement loading, birth, combat, jumping, camera culling and death
   at every candidate anchor; observe terrain depth and corpse return paths.
3. Verify survivor restore and respawn with the owned generator identity.
4. Add versioned seed/bootstrap capability, native assignments and source logic;
   preserve old seed identity and reject incompatible assets.
5. Run all-check solo/AP fills, remote-Blue cases and physical Onion deliveries.

Shearwig/ground swaps, density changes and boss adapters remain separate cohorts.
