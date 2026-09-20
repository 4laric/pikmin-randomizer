# P2 playable pool: admission bar and how to add a species

The playable pool is the set of P2 enemy species a player can actually meet in
a Pikmin 1 randomizer seed with P2 enemies. It is defined as the evidence
table `P2_PLAYABLE_POOL` in `randomizer/seed.py`; `PLAYABLE_P2_SPECIES` is
derived from it (`tuple(row["source_id"] for row in P2_PLAYABLE_POOL)`) so
every existing caller keeps working. Today the pool is:

| source_id | enum_name | family |
|---|---|---|
| 44 | BlueKochappy | dwarf_orange |
| 54 | Miulin | mamuta |
| 59 | FireOtakara | dweevil |
| 60 | WaterOtakara | dweevil |
| 61 | GasOtakara | dweevil |
| 62 | ElecOtakara | dweevil |

The installer table (`experimental/pikmin2_family_install.py`
`IDENTITY_FAMILY`) can already stage more species (1 Kochappy, 45 Snow,
9 Kogane, 23 Sarai, 57 Kurage, 58 BombSarai, 78 MiniHoudai, 79 Sokkuri).
Staging is not admission: those species stay out of the table until their
campaign evidence lands.

## Admission bar

A species is admitted when all three hold:

1. **Family installer.** An entry in `IDENTITY_FAMILY` mapping the source id
   to a family installer, so `install_layout` can stage it into a session.
2. **Bridge-mode campaign setup.** A native campaign binding for the species
   (host type via `pc_port/pc_p2_campaign_policy.h`, model binding via the
   `campaignWanted` path in `pc_p2_batch2.cpp`), so the campaign path can
   actually run it.
3. **Campaign evidence.** A real run showing the species boots and behaves in
   a campaign or campaign-like native session: spawn, movement/animation,
   combat interaction, natural death, corpse. The table row cites what was
   run and where the log lives (`evidence.run` / `evidence.log`); injected
   state, forced transport, or synthetic markers do not count.

## How to add a species

1. Produce the campaign evidence in a lane that owns the species (natural
   gameplay; keep the native log and record its location and hash).
2. Add one row to `P2_PLAYABLE_POOL` with `source_id`, `enum_name`,
   `family`, and `evidence` (`run`, `log`, `installer` — all non-empty).
   Do not touch `PLAYABLE_P2_SPECIES`; it derives from the table.
3. Run `py -3.12 -m pytest tests/test_p2_playable_pool.py
   scripts/test_p2_apworld.py` (from the repo root; `scripts/test_p2_apworld.py`
   takes `--ap`/`--archive`). `tests/test_p2_playable_pool.py` asserts every
   row carries non-empty evidence and that the derived tuple still matches.
4. Update this file's table above.

## Play commands

Generate a playable-pool seed and stage a session (see
`docs/PIKMIN2_PLAY_P2_SEED.md` for the full ISO-to-session walkthrough):

```powershell
py -3.12 -m randomizer generate --seed <name> --p2-enemies --p2-species playable --output <seed-manifest.json>
py -3.12 scripts/p2_prepare_content.py --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --out <p2-content> --seed-manifest <seed-manifest.json> --actors-out <p2-actors.json>
py -3.12 -m randomizer run <seed-manifest.json> --p2-content <p2-content> --p2-actors <p2-actors.json> --session-dir <short-dir> --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets
```

Keep session paths short: Windows' 260-char limit makes `.mod` loads fail in
deep directories.
