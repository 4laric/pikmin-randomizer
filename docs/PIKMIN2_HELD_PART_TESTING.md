# Held ship part: acceptance testing (#901, #924)

Test-only tooling for proving that a P2 occupant of a P1 ship-part holder
drops its part, that the bot delivers it, and that the vanilla Archipelago
check fires. None of this is reachable in normal play.

## Seed-generated takeover

`randomizer/p2_held_parts.py` lists the holder slots. A slot whose
`held_part_transfer` flag is true is accepted for compatible identities and
bound by the seed's own held-part layer (`p2_layout.held_parts.placed`), with
its own RNG stream, after the ordinary layout. Boss arenas
(`randomizer/p2_boss_arenas.py`) use the same flag: the P2 boss born in the
arena holds the P1 boss's part.

Emperor stays protected (it carries the goal). The Puffstool arena may take a
P2 occupant, but its bestiary check is not re-keyed here (#905).

A flag is set only with a campaign run that shows ASSIGN, HOLD, DROP, carry and
the vanilla ship CHECK for a seed-generated binding.

## Arena teleport hook (native, TEST-ONLY)

Some arenas sit behind bomb walls or a pit rim the autoplay bot cannot route
past. `PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT="x,z"` moves the captain and every
free Pikmin to that ground point once, when the squad is out (80 Pikmin in
power mode, 20 otherwise), and logs
`AUTOPLAY_TELEPORT x=.. y=.. z=.. moved=N TEST-ONLY`.

- It requires `PIKMIN_RANDOMIZER_AUTOPLAY=1`. With the autoplay gate closed the
  variable is ignored (`p2_autoplay_test`: `teleport/inert_without_gate`).
- It never changes generators, walls or the seed. Only positions move.
- The `run` command of `held_part_run.py` passes the environment through.

Arena points used so far (world x,z, arena centre in brackets):

| arena | teleport | centre |
|---|---|---|
| hope_snagret_part | `-460,3620` | -460, 3708.6 |
| spring_cannon_beetle | `-450,-830` | -450.9, -941.4 |

## Driver

`output/claude-orch/p2-held-part/held_part_run.py plan|run|score` (see its
docstring). Useful flags: `--held-target UID --held-species N` searches seeds
whose own held-part layer binds that slot; `--arena A --species N` searches
seeds whose arena sampling places N in arena A; `--power 10` for the bot's
damage multiplier; `--stop-on-check REGEX`.

Two more autoplay-gated switches, both logged and inert otherwise:

- `PIKMIN_RANDOMIZER_AUTOPLAY_TELEPORT_TO_PART=1`: a dropped ship part whose
  crew stays short for 20 s (it fell where the squad cannot walk) gets the
  captain and free Pikmin moved beside it once
  (`AUTOPLAY_TELEPORT_TO_PART`). The carry is still done by the Pikmin.
- `PIKMIN_RANDOMIZER_AUTOPLAY_NEXT_DAY=1`: taps A whenever no captain exists
  after the first stage. It does not get past the day-end save screen (see
  below), so it is not enough for a next-day run.

## Evidence (issue #924)

Native log sha256 for each run. Executables are staged under
`output/claude-orch/p2-held-part/bin-*`.

| run | what | result |
|---|---|---|
| f1 | seed-generated binding of the Puffy Blowhog holder to BlueKochappy 44, no hand binding | ASSIGN via=slot, DROP via=die, CHECK 5 Interstellar Radio (vanilla index). `25bf4de17c568997a69cbf27dd0418e2874f6ce2efce6d6708921015d8ec2782` |
| g8 | Hope Snagret part arena (`hope_snagret_part`), P2 own-FSM occupant, teleport | ASSIGN via=arena, DROP part=uf06, CHECK 9 Geiger Counter (vanilla index). `c2389cd96d82daeea68df75de74463bb8c76b989c5e67e35e47625b39bdcfa1a` |
| h2 | Navel Breadbug holder bound to 44 (seed-generated), teleport | ASSIGN via=slot, DROP part=un09, carried, CHECK 23 Space Float (vanilla index). `db81a9ba019110618a09a9ec6be57fbbda8bfac9c4a35df120d2e7e4edb6dae0` |
| b1, b2 | Beady Long Legs arena, occupant 44 | ASSIGN, DROP part=uf03, 26-31 carriers hauling; the day ended first (`UFO_PART_CACHE_SAVE part=uf03`). No CHECK. |
| k3 | Cannon Beetle arena, occupant 44 | ASSIGN, DROP part=ust1, crew 29 of 30 short. No CHECK. |
| p1 | Puffstool arena, occupant 44 | ASSIGN via=slot, DROP part=uf09, crew 8 of 30. No CHECK. |

Flags: `hope_snagret_part` is true. The Breadbug holder is proven but stays
false because the Navel Breadbug is the only Breadbug spawn, so a takeover
strands the Breadbug bestiary check until #905 re-keys it (un09 stays
protected pending #905). Beady Long Legs, Cannon Beetle and Puffstool arenas
now have `held_part_transfer` true per the owner ruling (#901) and the merged
#955 placement document. Delivery for those three is still unproven by bot
runs (b1, k3 and p1 above ended on squad size or day length before a CHECK).
Emperor stays protected.

Not reachable with the current bot, so not run: the next-day load half of a
dropped part (the day-end save screen does not advance under scripted A),
vanilla regressions for the Snagret and Beady Long Legs arenas (they are P1
bosses, not `BTeki`, so the bot cannot target them), the Cannon Beetle vanilla
holder (a UI overlay held the run after the teleport), and two-peer lockstep
(the netplay branch is not in `fork/main`).

