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
| 73 | BigTreasure | bigtreasure |
| 32 | Demon | demon |
| 38 | PanModoki | breadbug |
| 41 | Fuefuki | fuefuki |
| 58 | BombSarai | bombsarai |
| 26 | Catfish | aquatic |
| 27 | Tadpole | aquatic |
| 84 | Hana | ground_inverts |
| 93 | BombOtakara | dweevil |

The installer table (`experimental/pikmin2_family_install.py`
`IDENTITY_FAMILY`) can already stage more species (1 Kochappy, 45 Snow,
9 Kogane, 57 Kurage, 66 Houdai, 97 FminiHoudai).
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
- **58 BombSarai (Careening Dirigibug): admitted (#244).** The source FSM
  hovers, supplies and drops its bomb, and the blast kills Pikmin as in P2.
  Latched and grounded, it dies naturally, is carried, and delivers
  `onion:p2:58:3` (bot runs v1 normal squad and v2p power mode). P2 sounds and
  balloon/supply effects are not ported; poses are rigid samples per clip.
- **41 Fuefuki (Antenna Beetle): admitted (#245, 2026-09-29).** Its OWN
  campaign port runs the source FSM on a P1 Chappy teki with its AI suppressed. The beetle
  whistles followers away, is pressed into Struggle by a thrown Pikmin, dies
  naturally, is carried and delivers its Onion receipt on Distant Spring,
  on Forest Navel (a natural seed, no rebind) and on Forest of Hope. Its
  owner-death Panic followers come back to a captain whistle. A P1 safety
  guard keeps its Land/Walk targets on ground routed to home: before the
  guard, run d4 stranded the corpse on a ledge behind a closed waypoint. The
  whistle ring is a P1 ground-band stand-in, not the retail effect.
- **38 PanModoki (Breadbug): admitted (#898).** The source FSM runs it in the
  campaign. Pikmin and the captain never target it (in retail it is only a
  living thing while bittered), and thrown Pikmin landing on it press it. It
  steals carcasses, tugs them against the carriers and hauls them home to hide.
  A carcass it takes home is spared at the nest, so its check is never lost.
  It dies to six presses (or container damage when it is sucked off its cargo
  at the Onion), is carried and delivers `onion:p2:38:3` (three bot runs on the
  pinned exe, z2/z3/z6). Eating a plain pellet (retail `endCarry`) is untested
  at runtime. Pikmin still holding the cargo when it hides are killed, as in
  retail; this needs an owner eye-check. Binding is shown on Distant Spring and
  Forest of Hope; no Impact Site slot opens before day 8, so none was run.
- **The pool may outgrow the placement slots (#893).** A seed then samples it:
  under the default density every target gets a distinct species, and the
  species that did not fit are listed as `unplaced` in the layout
  (`sampled-v1`). With 41 species on 35 slots, a given seed may leave out any
  four ordinary pool species: the arena bosses (94, 73; #899, #246) are placed in
  boss arenas outside the ordinary slots, so 39 ordinary species share 35
  ordinary slots. A pool that fits keeps the legacy fill unchanged.
- **26 Catfish (Water Dumple), 27 Tadpole (Wogpole), 84 Hana (Creeping
  Chrysanthemum), 93 BombOtakara (Volatile Dweevil): admitted (#964).** Each
  runs its transcribed source FSM in the campaign, dies naturally, is carried as
  its dead corpse and delivers `onion:p2:<id>:3` on its own generator token
  (bot power mode, then a day-cycle run: alive at two sunsets, rebound each new
  day, killed and delivered on day 4). The kill runs used a land slot: the
  aquatics have no water plane, and the bot could not reach the water-slot
  packs, so a fight on the real water slots is unobserved. The Catfish and
  Wogpole take water-cohort slots only (their lane-04 profile); Hana takes
  ground slots; the Volatile Dweevil the same ground slots as 59-62. Details,
  fixes and open items: `docs/PIKMIN2_WAVE3_MECHANICS.md`.
- **32 Demon (Bumbling Snitchbug): admitted (#215).** It rides the Sarai host
  with its own retail profile and bank. It grabs the captain, flies, drops him
  (10 damage), is knocked down by Pikmin weight, dies naturally, is carried as
  the Demon carcass and delivers `onion:p2:32:3` on its own generator. Known
  accommodations: the Chappy anchor's collision stands in for the body, gravity
  is assumed, the corpse carry config is the P1 host's, and a captain flick is
  a plain release.
- **Unkillable enemies carry no Archipelago check.** 9 Kogane, 10 Wealthy,
  11 Fart and 16 Qurione are invulnerable in P2 source and leave no carcass, so
  a kill, carry and Onion check is unreachable. They are `excluded` in the roster
  evidence, never enter this table, and are dropped from every proxy tier
  (`randomizer.p2_proxy.NO_CHECK_SOURCE_IDS`). A proxy host would only fake the death.
- **Bosses belong in the pool.** Nine P2 bosses are already here (34, 53, 56,
  69, 70, 71, 73, 94, 101). The remaining bosses 30 Queen, 40 Giant Breadbug,
  66 Houdai and 99 Waterwraith are in scope under the same admission bar.
  Per-boss arena feasibility is the work, not a policy question.

## Owner rulings, 2026-09-29 (#246, #899)

- **Boss arenas.** P2 bosses are placed only in designated P1 boss arenas,
  replacing the P1 boss there (`randomizer/p2_boss_arenas.py`). The pool's
  arena bosses are 94 Crawbster and 73 Titan Dweevil; the most-constrained
  boss is seated first, so the Titan (footprint 250) takes the Impact Goolix
  arena (clear 275) and the Crawbster the Hope snagret pit.
- **73 BigTreasure (Titan Dweevil): admitted.** The source BigTreasure FSM runs
  as its own campaign actor with the retail collision tree: Pikmin knock the
  four weapons off by hitting each weapon's own part, the body takes damage
  only after the last drop, and it dies naturally. A carryable corpse is the
  reward (ruling #1; the source Titan leaves none) and delivers
  `onion:p2:73:0` on its own generator token (bot power-mode run e7 and
  repeats, plus a day 11-15 re-entry run rc2, #246). Its gas stays lethal to every P1 colour (ruling #2). The
  knocked-off weapons and Louie are not carryable pellets yet.

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
