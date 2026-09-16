# Fuefuki native vehicle (Napkid 11) — arena staging (#245)

Status: **RESOLVED for binding/draw** (2026-09-14). The lane binds and draws on a
real Napkid 11 placement vehicle in the P1 practice arena, via the **cargo-free**
preview mode. What remains open is *native Fuefuki identity* (enemy 41) — the
Napkid is still only a placement vehicle.

## Resolution

`pc_p2_preview_setup` validates `p2ValidatePreviewCargo(cargoFree, hasCargoConfig,
hasTreasure)`: without a treasure generator it aborts ("treasure generator
missing"). The practice arena has no treasure generator, but the supported
**cargo-free** config (`p2-cargo-free.txt` containing `P2_CARGO_FREE_1`) makes
the validation pass. `experimental/pikmin2_fuefuki_arena.py` now writes that
config into the run directory.

Running `nectar.exe --experimental-pikmin2-room` in that arena with the converted
pose bank overlaid produced:

```
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_HARDLANES_READY family=Fuefuki vehicle=Napkid follow_locomotion=actteki_volatile_approx
P2_FUEFUKI_VISUAL_READY clips=8
P2_HARDLANES_READY family=Fuefuki visual=1 clips=8
[Pikipelago] P2_ROOM_CARGO_FREE_READY cargo=0 repairs=1
P2_FUEFUKI_VISUAL_DRAW clip=wait pose=0 x=-150.0 y=30.0 z=1850.0
P2_FUEFUKI_FSM state=2 clip=wait
```

The draw position `(-150, 30, 1850)` is exactly the arena's Napkid placement, so
the visual is anchored on the real vehicle. The run stayed stable for 40 s
(manually stopped; the game has no self-exit).

The binding is **generator-scoped** through an optional `p2-fuefuki-teki.txt`
(`P2_FUEFUKI_TEKI_1 <generator> <type>`, the Kurage/Onikurage private-adapter
pattern): with the arena's `245001 11` the receipt reads
`family=Fuefuki vehicle=Napkid gen=245001 type=11`, so the lane actor binds the
exact placement row rather than "the first Napkid". The arena script writes this
config. This is still a *placement vehicle* (Napkid 11), not enemy 41.

## What was tried before (kept for the record)

1. **Arena without cargo-free** — stalled at `P2 preview: treasure generator
   missing`; never reached the hardlane setup.
2. **Direct `tekiMgr->newTeki(TEKI_Napkid)`** — `hasType==1` and a type-11 `Teki`
   is returned, but a hand-initialised instance (`mPersonality` pos/nest,
   `reset()`, `startAI(0)`) access-violated on the next frame. Not needed once
   the generator path runs.

## Still open

- **Native Fuefuki identity (41):** the vehicle is Napkid 11; `native_identity`
  stays BLOCKED.
- **FSM progression:** now driven from the converted motion event table
  (`pc_p2_fuefuki_motion` + `p2retail::Player`): on the real vehicle the FSM
  cycles `Land -> Jump -> Stay -> Land` with matching visual clips
  (`state=2 clip=wait`, `state=3 clip=jump`, `state=1 clip=jump`). It does not
  reach `Walk/Turn/Whisle` in the arena because a nearby captain triggers the
  source jump-away (intruder) behaviour. The source Beetle animation bank
  (#128) remains the eventual feed, but the table is enough for the state
  machine.
- Whistle effect ring, audio; the arena does not itself stage the converted pose
  bank (overlay `p2-fuefuki-visual.txt` + mods to see it).
- **Material upload:** fixed. Every sampled pose is its own Shape with its own
  texture instances; the visual previously attached only pose 0, so later poses
  drew transparent (`[PC GX Warning] ... nunca se subió`). Attaching all poses
  dropped the warning count from the 8-report cap to **0**. Retail material
  *fidelity* (approximate converter materials) is still provider 09 work.
