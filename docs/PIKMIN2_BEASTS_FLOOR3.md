# Beasts floor 3 source package (#295)

Follow-up: [navigation interpretation #300](PIKMIN2_BEASTS_NAVIGATION.md) explains
why exact source-height mismatches are not absent ground, and why both directed
graphs already reach every door. Its optional waypoint grounding preserves this
historical default package.

Owner: Codex using shared 4laric account. This independent floor 3 track starts
at root `8b7d480` (#293). It imports actual source treasures and packages the two
source room candidates for engineering work. It does not enable campaign launch.

The GPVE01 revision 0 `forest_1` definition index 2 contains two distinct Hiba
rows: seven placement-type 1 and seven placement-type 8 hazards. HikariKinoko has
a target count of eight. Gates and caps are empty. There is no geyser or clogged
hole; progression must descend to floor 4, whose lifecycle is not implemented here.

| Source treasure | Pokos | Carry strength | Carry slots | Converted MOD SHA256 |
|---|---:|---:|---:|---|
| donutswhite | 230 | 15 | 25 | `2f344dc4dc56619b44f0a0895f7acb4fc198241b9dd8489fd3d089115f2fdf5f` |
| dia_c_green | 150 | 12 | 20 | `39e6a982f7f5d36163a991959ec3ab7a7d505d46d5947a58a1af93d1738a9b60` |

Economy comes directly from the US otakara configuration. Original BMDs, converted
MODs and normalized conversion sidecars are retained. No treasure is spawned,
collected or registered as a receipt by this package.

Both rooms receive capped collision and retain their original route graphs.
`room_block1_3_hiba_tsuchi` has seven grounded source candidates out of 22;
waypoint 6 cannot be reached from waypoints 0–5. `room_north_1_hiba_tsuchi`
has 23 grounded candidates out of 23; waypoint 3 cannot be reached from 0, 1,
2 or 4, and waypoint 4 cannot be reached from 0–3. These are source graph
properties, not repaired or certified carry routes. Elevated/unmatched source
positions remain explicit audit entries; no position is silently relocated.

The two rooms are isolated candidates, not a generated topology. Hiba and
HikariKinoko are omitted. Source spawn records are retained with no selected actor
placements. Materials use the existing explicit approximation and deferred texture
animation policy. There is no native gameplay evidence for this package.

## Reproduction and validation

Run from the private root worktree `output/p2-beasts-floor3-track`:

```powershell
python -m experimental.pikmin2_beasts_floor3 `
  --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' `
  --catalog ../../output/p2-cave-catalog-batch/audit-final/catalog.json `
  --units ../../output/p2-mapcode0-batch/import `
  --output output/floor3-295/new-package
python -m pytest -q tests/test_pikmin2_beasts_floor3.py tests/test_pikmin2_beasts_floor2.py tests/test_pikmin2_beasts_content.py
```

Both actual-disc runs `output/floor3-295/final-a` and `final-b` passed and produced
13 byte-identical files. Manifest SHA256:
`6ea4a790a2d80a1cf5ca142a15341d6fb13087371d8e5a1ef9bd7bc1597dab8d`.
All per-file hashes are recorded locally in `output/floor3-295/verification.json`.
Catalog sources and converted unit source archives are rehashed against the disc;
converted room inputs are checked against their import manifest before staging.
Output directories must be fresh. Disc assets and existing imports remain read-only.

14 tests and 24 subtests passed, including changed catalog roster, conflicting
provenance, changed disc bytes, mutated/unsupported rooms, invalid economy and
preservation of source graph disconnections. No native source, build or shared
save changes were needed. First probes exposed absolute paths in converter
sidecars; those are now normalized, and only the final repeated packages are
the determinism evidence.

Next: resolve source waypoint/placement semantics, assemble a traversable floor,
install source Hiba mechanics and both treasures, then validate actual carrying
and descent with the separately developed persisted handoff path.
