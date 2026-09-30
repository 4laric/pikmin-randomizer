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
