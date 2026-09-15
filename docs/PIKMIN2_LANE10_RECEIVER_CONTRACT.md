# Lane 10 receiver-side contract for family emitters (#408)

Lane 10 owns the damage/elemental/attack receiver layer. This is the contract an
elemental **family emitter** consumes to deliver its element to a live Pikmin.
The emitter side is `pc_port/pc_p2_hazard_emitter.h` (`p2_emitter_accepts`); the
receiver side is this table. Every receiver routes immunity through the lane-11
species matrix (`pc_port/pc_p2_species_policy.h`), so an emitter and its receiver
cannot disagree about who is immune.

## Receiver table (what to stimulate, and what happens)

| Element | Construct and stimulate | Immunity gate (species matrix) | Reaction state | Receiver log |
|---|---|---|---|---|
| **Fire** (`P2HazardFire`) | `piki->stimulate(InteractFire(owner, damage))` | `p2_species_immune(species, P2HazardFire)` — Red, Bulbmin immune | `startFire()` -> `PIKISTATE_Fired` (P1); death timer `mPanicTime` (p55) | none (P1 path) |
| **Water** (`P2HazardWater`) | `piki->stimulate(InteractBubble(owner, damage))` | `p2_species_immune(species, P2HazardWater)` — Blue, Bulbmin immune | `PIKISTATE_Bubble` (P1; decomp uses `PIKISTATE_Panic`+`PIKIPANIC_Water`) | none (P1 path) |
| **Gas** (`P2HazardGas`) | `piki->stimulate(InteractGas(owner, damage))` | `p2_hazard_reaction(species, P2HazardGas, piki->gasInvicible())` — White, Bulbmin immune; `gasInvicible()` also rejects | `PIKISTATE_Panic` (gas) -> `PIKISTATE_Dying` | `P2_RECV_GAS` (debug build only — see below) |
| **Electric** (`P2HazardElectric`) | `piki->stimulate(InteractDenki(owner, force, &dir))` | `p2_hazard_reaction(species, P2HazardElectric, ...)` — Yellow, Bulbmin immune | `PIKISTATE_DenkiDying` (0.3s) -> `PIKISTATE_Dead` | `P2_RECV_DENKI` (debug build only — see below) |
| **Bomb** | not a Pikmin receiver — `BombOtakara` delegates to its carried `EnemyID_Bomb` payload (lane 20 blast contract) | n/a | n/a | n/a |

> `P2_RECV_GAS`/`P2_RECV_DENKI` are emitted with the `PRINT` macro
> (`src/plugPikiKando/interactBattle.cpp:246,280`), which is routed to the in-game console (sysCon) via _Print under PIKI_PC_PORT (include/DebugLog.h:64-65, :13-29), not to the stdout capture in a
> Release/GL build (`include/DebugLog.h:68` — the `#else` branch defines `PRINT`
> empty). The hiba run7 log has 7 `P2_HIBA_GAS_HIT` + 1 `P2_HIBA_DENKI_HIT` and
> **zero** `P2_RECV_*` lines. The **family emitter** must therefore log its own
> accepted/immune markers (the `P2_*_HIT`/`P2_*_IMMUNE` lines below), not rely on
> the receiver's debug-only `P2_RECV_*`.

Constructor signatures (`include/Interactions.h`):

- `InteractFire(Creature* owner, f32 damage)`
- `InteractBubble(Creature* owner, f32 damage)`
- `InteractGas(Creature* owner, f32 damage)`
- `InteractDenki(Creature* owner, f32 force, Vector3f* direction)`

Implementation: `src/plugPikiKando/interactBattle.cpp`. The gas/electric receivers
were `__attribute__((used))` for LTO retention when nothing referenced them; the
ElecBug/GasHiba/ElecHiba emitters now reference them, so that markers are
documented as defensive only.

## Species immunity matrix (`pc_port/pc_p2_species_policy.h`)

| Species | Fire | Water/Bubble | Electric/Denki | Gas |
|---|---|---|---|---|
| Blue (0) | - | immune | - | - |
| Red (1) | immune | - | - | - |
| Yellow (2) | - | - | immune | - |
| Purple (3) | - | - | - | - |
| White (4) | - | - | - | immune |
| Bulbmin (5) | immune | immune | immune | immune |

`p2_species_immune(species, hazard)` is the query. Electric and gas additionally
go through `p2_hazard_reaction(species, hazard, gasInvincible)` (which applies the
gas-invincible gate and returns the reaction target), because the P2 Denki/Gas
receivers differ from the P1 Fire/Bubble receivers.

## Family consumer notes

- **Lane 14 ElecBug (source 28)** — already integrated. Its discharge sweep
  selects the nearest shockable Pikmin with
  `p2_emitter_accepts(pc_p2_species(p), P2HazardElectric, p->gasInvicible())` and
  delivers `piki->stimulate(InteractDenki(teki, 1.0f, &dir))`
  (`pc_port/pc_p2_elecbug.cpp:665`), logging `P2_ELECBUG_DENKI` (accepted+sweep
  target state, :667) and `P2_ELECBUG_IMMUNE` (Yellow/Bulbmin in sweep, :222,:226).
  This is the reference natural-emitter pattern.
- **Lane 22 Otakara (elemental dweevils 59-62; BombOtakara 93 is not bound)** —
  the second integrated consumer, `pc_port/pc_p2_otakara.cpp`. On the OtakaraBase
  Flick attack event type 3 (source `attack1` frame 35), `doDischarge` (:216)
  resolves the species element through the engine receivers: `dweevilAccepts`
  (:204-214) routes Fire/Water through `p2_species_immune(...)`, Gas through
  `p2_emitter_accepts(... P2HazardGas ...)` (:210) and Denki through
  `p2_emitter_accepts(... P2HazardElectric ...)` (:211); then it
  `stimulate(InteractFire/Bubble/Gas/Denki)` (:238/:241/:244/:248) and logs
  `P2_OTAKARA_DISCHARGE_IMMUNE` (:229) / `P2_OTAKARA_DISCHARGE_HIT` (:255) and the
  per-cycle summary `P2_OTAKARA_DISCHARGE` (:264). The item-carry (5..10) and
  Bomb-carry (11..13) states are source-backed N/A (no treasure/Bomb staged).
- **Fixed hazards (Hiba 20 / GasHiba 21 / ElecHiba 22)** — `pc_port/pc_p2_hiba.cpp`
  `emitScan` is the worked example: it routes each hazard's stimulus through
  `p2_emitter_accepts(...)` and delivers `InteractFire`/`InteractGas`/
  `InteractDenki`, logging `P2_HIBA_FIRE/GAS/DENKI_HIT|PASS` and a species-tagged
  `P2_HIBA_GAS/DENKI_LETHAL` (fire-immune Red witness).

## What a family emitter must log (for the lane-10 gate)

For the receiver side to be provable as natural (not injected), the family
emitter must deliver the element through its own FSM/volume to a live Pikmin and
log, per delivery: the target species + the receiver's accept/reject and the
resulting Pikmin state; and, for immunity, one marker per rejected immune species
in volume. These emitter-owned markers are the ONLY reliable signal in a GL
build, because the receiver's own `P2_RECV_*` lines are `PRINT` (compiled out —
see the note above). The ElecBug `P2_ELECBUG_*`, Otakara
`P2_OTAKARA_DISCHARGE_*`, and Hiba `P2_HIBA_*` logs are the model.
