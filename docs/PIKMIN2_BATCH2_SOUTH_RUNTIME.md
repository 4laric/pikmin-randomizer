# Batch-2 visuals (south) — native display runtime evidence (#352, #353, #312)

Batch 4 ([docs/PIKMIN2_FAMILY_BATCHES.md](PIKMIN2_FAMILY_BATCHES.md)) drove the
south families through the native display step with a real-GL room fixture:
Waterwraith/Tyre (#352, parent #175), Flora/Candypops (#353, parent #171) and
Long Legs (#312, parent #173).

## Integration fixes required first

The batch-2 native registration was never runtime-tested (see
[PIKMIN2_BATCH2_NATIVE_REGISTRATION.md](PIKMIN2_BATCH2_NATIVE_REGISTRATION.md))
and aborted on first contact with real install output. Three fixes:

1. `pc_p2_batch2.cpp` / `pc_p2_long_legs.cpp` `parseActors` compared an 8-char
   suffix against the 9-char `_ACTORS_1`, so **every** family aborted with
   `P2_BATCH2 invalid actor config`. Now `compare(size - 9, 9, "_ACTORS_1")`
   (the same fix batch 1 applied to `pc_p2_batch3.cpp`).
2. `pc_p2_batch2.cpp` `parseBank` rejected `poses 0`, but the canonical install
   writers emit zero-pose ("unsupported") clips (e.g. Flora Pelplant /
   HikariKinoko). Now `poses < 0`, matching `pc_p2_batch3.cpp`.
3. `experimental/pikmin2_batch2_core.py` `prepare()` called the default
   `install(cfg, imported, run, actors)` with three arguments, so the
   Waterwraith/Flora/Dweevil/Ground/Cannon arena CLIs raised
   `TypeError: install() missing 1 required positional argument: 'actors'`.
   The default installer/verifier are now bound to `cfg`; the bespoke Long Legs
   three-argument installer is unchanged.

## Fixture

Built with `engine/tools/verify_p2_room_windows.py` against the isolated
batch-4 native build (`output/tracks/p2-batch4-root/native/build-batch4`,
Ninja Release, `PIKMIN_NATIVE_JAUDIO=ON`, `495/495` + incremental relink).

- `output/p2-batch4-fixture/preview_p2_room.exe` SHA-256
  `BFE84C3EADE36B4A4AC7C5B42455CB22E94EB63AA4972A397F90056748506A1F`
- Production `nectar.exe` SHA-256
  `23FF55634FBE8027DCE79A3A1FDE585BE32C27289DA753745092E6FE2F54D7AC`

Run per family from a private arena run dir with
`preview_p2_room.exe --experimental-pikmin2-room` (real GL; audio dummy). Raw
logs: `output/p2-batch4-runtime/<family>/<run-uuid>/native.log`.

## Results

| Family | `native_identity` (`*_BIND`) | `*_DRAW` | Bank |
|---|---|---|---|
| Waterwraith | PASS 352001 BlackMan, 352002 Tyre | PASS `key=waterwraith\|BlackMan clip=kagebozu_wait` | 2 species, 1319520 B |
| Flora | PASS 353001-353006 six Candypops | PASS `key=flora\|RedPom clip=wait` | 6 species, 2084544 B |
| Long Legs | PASS 312001 Houdai, 312002 BigFoot | PASS `species=Houdai pose=bind` | 2 species, 218816 B, `pose_bank=0` |

Raw lines:

```
P2_BATCH2_BIND generator=352001 key=waterwraith|BlackMan visual_only=1 native_fsm=unimplemented
P2_BATCH2_BIND generator=352002 key=waterwraith|Tyre visual_only=1 native_fsm=unimplemented
P2_BATCH2_BANK total_mod_bytes=1319520 species=2
P2_BATCH2_DRAW corpse=0 key=waterwraith|BlackMan clip=kagebozu_wait
P2_BATCH2_BIND generator=353001 key=flora|BluePom visual_only=1 native_fsm=unimplemented
... 353002 RedPom, 353003 YellowPom, 353004 BlackPom, 353005 WhitePom, 353006 RandPom ...
P2_BATCH2_BANK total_mod_bytes=2084544 species=6
P2_BATCH2_DRAW corpse=0 key=flora|RedPom clip=wait
P2_BATCH2_BANK total_mod_bytes=0 species=0
P2_LONG_LEGS_BIND generator=312001 species=Houdai pose=bind visual_only=1 native_fsm=unimplemented
P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind visual_only=1 native_fsm=unimplemented
P2_LONG_LEGS_BANK total_mod_bytes=218816 species=2 pose_bank=0
P2_LONG_LEGS_DRAW corpse=0 species=Houdai pose=bind
```

The Long Legs run's `P2_BATCH2_BANK ... species=0` confirms the batch-2 unit is
a clean no-op when its configs are absent (ordinary play unaffected).

## Gate status

- `native_identity`: **PASS** for all three families (bind confirmed from the
  `*_BIND` log line, per the pipeline rule that screenshots are not identity).
- Pose selection / draw path: **PASS** (live `*_DRAW` frame captured once per
  run).
- `spawn_exact_xyz`, `control_undisturbed`, `reload`: **UNTESTED** (no
  effective-XYZ probe in this fixture).
- `natural_AI`, `combat`, `death_corpse`, `carrier_recovery` and the
  family-specific extras (`boss_phases`, `tyre_roll_crush`,
  `purple_vulnerability`, shared Pom base, pellet-to-Pom, Pelplant receptor,
  sprout birth, `ik_leg_stability`, `foot_crush`, `houdai_gun_callback`,
  `skeletal_playback`): **BLOCKED** — not implemented; this is a visual-only P1
  proxy anchor, not source behavior.

## Limitations

One actor per draw line is logged (the `logged[]` latch). The fixture ran the
default room-preview camera; effective world XYZ and camera-only observation
are not captured. No generated assets, logs or saves are committed.
