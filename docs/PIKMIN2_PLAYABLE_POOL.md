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
| 23 | Sarai | sarai |
| 79 | Sokkuri | sokkuri |
| 2 | Chappy | chappy |
| 33 | FireChappy | chappy |
| 35 | KumaChappy | chappy |
| 43 | YellowChappy | chappy |
| 53 | KingChappy | chappy |
| 67 | LeafChappy | chappy |
| 76 | KumaKochappy | chappy |
| 12 | UjiA | uji |
| 13 | UjiB | uji |
| 14 | Tobi | uji |
| 28 | ElecBug | elecbug |
| 94 | DangoMushi | dangomushi |
| 68 | TamagoMushi | tamago |
| 17 | Frog | frog |
| 18 | MaroFrog | frog |
| 24 | Tank | tank |
| 75 | Kabuto | kabuto |
| 56 | Damagumo | long_legs |
| 63 | Jigumo | aquatic |
| 69 | BigFoot | long_legs |
| 34 | SnakeCrow | snagret |
| 70 | SnakeWhole | snagret |
| 65 | Imomushi | ground_inverts |
| 71 | UmiMushi | aquatic |
| 101 | UmiMushiBlind | aquatic |
| 25 | Wtank | tank |
| 15 | Armor | armor |
| 78 | MiniHoudai | minihoudai |
| 38 | PanModoki | breadbug |

The installer table (`experimental/pikmin2_family_install.py`
`IDENTITY_FAMILY`) can already stage more species (1 Kochappy, 45 Snow,
9 Kogane, 57 Kurage, 58 BombSarai, plus 26 Catfish,
27 Tadpole, 84 Hana, 93 BombOtakara, 66 Houdai, 97 FminiHoudai).
Staging is not admission: those species stay out of the table until their
campaign evidence lands.

Separate from this pool, the proxy tier (`docs/PIKMIN2_PROXY_TIER.md`)
stages Pikmin 2 models over Pikmin 1 enemy behaviour. Proxy species are
never P2 identities and never enter this table.

## Owner decisions, 2026-09-28 (#888)

- **Roster follows admission exactly.** The roster evidence, the admitted
  placement document and this table name the same species. `tests/test_p2_pool_roster_sync.py`
  checks equality, not subset. A bare `--p2-enemies` seed (no `--p2-species`)
  must generate.
- **Pulled for now:** 9 Kogane (see the no-check rule below) and 57 Kurage.
  The campaign Kurage runs on the P1 Frog host AI, because its P2 FSM is env-gated.
- **78 MiniHoudai (Gatling Groink): admitted.** Its Windows OWN campaign run
  (#888 §4A) and the shell visuals (#892) are in. The source FSM fights, the
  Groink dies naturally, is carried, and delivers `onion:p2:78:3`. The owner
  eye-checked the facing and the shell effects. Carcass revival and the
  body charge/smoke effects are not ported yet.
- **38 PanModoki (Breadbug): admitted (#898).** The source FSM runs it in the
  campaign. Pikmin and the captain never target it (in retail it is only a
  living thing while bittered), and thrown Pikmin landing on it press it. It
  steals carcasses, tugs them against the carriers and hauls them home to hide.
  A carcass it takes home is spared at the nest, so its check is never lost.
  It dies to six presses (or container damage when it is sucked off its cargo
  at the Onion), is carried and delivers `onion:p2:38:3`.
- **The pool may outgrow the placement slots (#893).** A seed then samples it:
  under the default density every target gets a distinct species, and the
  species that did not fit are listed as `unplaced` in the layout
  (`sampled-v1`). With 37 species on 35 slots, a given seed may leave out any
  one pool species. A pool that fits keeps the legacy fill unchanged.
- **Unkillable enemies carry no Archipelago check.** 9 Kogane, 10 Wealthy,
  11 Fart and 16 Qurione are invulnerable in P2 source and leave no carcass, so
  a kill, carry and Onion check is unreachable. They are `excluded` in the roster
  evidence, never enter this table, and are dropped from every proxy tier
  (`randomizer.p2_proxy.NO_CHECK_SOURCE_IDS`). A proxy host would only fake the death.
- **Bosses belong in the pool.** Eight P2 bosses are already here (34, 53, 56,
  69, 70, 71, 94, 101). The remaining bosses 30 Queen, 40 Giant Breadbug,
  66 Houdai, 73 Titan Dweevil and 99 Waterwraith are in scope under the same
  admission bar. Per-boss arena feasibility is the work, not a policy question.

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
   state, forced transport, or synthetic markers do not count. Owner ruling
   2026-09-25: bot-driven power-mode runs (larger squad, damage multiplier)
   count, provided each claim keys on the species' own generator token.

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
py -3.12 -m randomizer run <seed-manifest.json> --exe <path-to-nectar.exe> --p2-content <p2-content> --p2-actors <p2-actors.json> --session-dir <short-dir> --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets
```

`--exe` is required to actually launch the game: `randomizer run` stages the
P2 content and prints `PIKMIN_P2_BOUND: ...` regardless, but the native
process is only spawned when `--exe` is given (`randomizer/runner.py`, the
`if exe:` block gating `subprocess.Popen`). Without it the command exits 0
having staged everything and launched nothing, which looks like success.

Keep session paths short: Windows' 260-char limit makes `.mod` loads fail in
deep directories.

## Starting squad in future campaign packages (#882)

Campaign staging excludes explicitly labelled `campaign red pikmin` harness
records from the private Forest of Hope generator. Some local input assets
contain twenty such actors beyond the landing wall, duplicating the twenty
starters the production game already holds in the starting Onion. Withdraw the
intended squad normally from the Onion. Retail Pikmin and other generators are
preserved byte-for-byte; shared asset inputs are never rewritten. Fresh staging
and model-cache replay both apply this correction. Standalone fixture staging
retains its intentional squad.

This source fix is for future packages. The existing `output/p2play` delivery,
its running game, AP progress and saves were not patched or migrated.
