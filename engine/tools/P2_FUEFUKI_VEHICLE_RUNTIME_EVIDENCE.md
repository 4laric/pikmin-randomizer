# Fuefuki real-vehicle natural claim — runtime evidence (#245)

Status: **executed, PASS**. `tools/p2_fuefuki_vehicle_runtime.cpp` ran on a real
SDL2/OpenGL window inside the cargo-free practice arena, where the Napkid 11
placement vehicle births through the real generator and `pc_p2_hardlanes` binds
it. This is the first run where the lane FSM reached `Whisle`, claimed real
Pikmin, and the follow locomotion moved them — on a native actor, not the
fixture's own binding.

## Provenance

- Native branch `opencode/p2-lane28-fuefuki-follow`, HEAD
  `c531ca7b1dc2baa24f5e3bb0fb5af9c8b450046a`.
- Private build `output/lane28-fuefuki-build`, Ninja Release, MinGW-w64 g++
  16.2.0, JAudio ON; `ninja pikmin_pc -n` => no work.
- Fixture `output/p2-lane28-vehicle-runtime-04/fixture.exe`, SHA-256
  `3054B35020FE4224F2D94706B52EDEC4C8C4721EC4D97084878C77AE6506DF08`
  (supersedes `…-03` `170FAA3D…`).
- Run dir `output/p2-fuefuki-arena-real3/556113df…` (arena `p2-cargo-free.txt`,
  `p2-fuefuki-teki.txt`, overlaid pose bank + motion table).

## Marker output (verbatim)

```
P2_FUEFUKI_VEHICLE_RT_WINDOW size=960x540 centered=1
P2_HARDLANES_READY family=Fuefuki vehicle=Napkid gen=245001 type=11 follow_locomotion=actteki_volatile_approx
P2_HARDLANES_READY family=Fuefuki visual=1 clips=8
P2_HARDLANES_READY family=Fuefuki motion=1 clips=10
P2_FUEFUKI_VEHICLE_RT_READY vehicle=-150.0,38.2,1849.9 state=2
P2_FUEFUKI_VEHICLE_RT_STAGE frames=30 state=2 held=0
...
P2_FUEFUKI_VEHICLE_RT_STAGE frames=300 state=4 held=0
P2_FUEFUKI_VEHICLE_RT_STAGE frames=330 state=7 held=0
P2_FUEFUKI_VEHICLE_RT_CLAIM state=7 held=2 frames=339
P2_FUEFUKI_VEHICLE_RT_MOVE held=2 moved=14.9 frames=2 state=7
P2_FUEFUKI_VEHICLE_RT_KILL health=0
P2_FUEFUKI_VEHICLE_RT_DEATH state=0 held=0 frames=22
PASS FUEFUKI_VEHICLE_RUNTIME
```

Phase detail:

- The fixture moves the captain 400+ units away and places six staged Pikmin in
  the 60..130 unit annulus around the vehicle, so the hardlane probe reports no
  intruder and the FSM can leave `Land`.
- FSM progression: `Land(2) -> Jump(3) -> Stay(1) -> Land(2) -> Wait(4) ->
  Whisle(7)`. Reaching `Wait` needed the separate motion-state clip mapping
  (below); before it the Land state was fed the looping `wait.bca` and stalled.
- At frame 335 (state 7, casting) the real whistle claimed **2** Pikmin
  (`held=2`).
- The follow locomotion then moved the claimed Pikmin (flick + volatile-velocity
  drive) — real motion on the real vehicle.
- Defeat: the fixture zeroes the vehicle's health; the FSM routes to `Dead(0)`
  and the owner-death release detaches every follower. `P2_FUEFUKI_VEHICLE_RT_KILL`
  then `..._RT_DEATH state=0 held=0` confirm `held` drops 2 → 0 on the real
  vehicle within the same run.

## Fix that unblocked it

`pc_p2_fuefuki_visual_clip_for_state` maps `Land -> wait` because `landing` has
no converted geometry. The motion feed must instead use the real `landing.bca`,
so `p2_fuefuki_motion_clip_for_state` was added and the hardlane driver uses it;
the visual keeps the wait pose. Without this, `Land` was fed a looping clip and
never delivered its END, so the FSM never advanced past `Land`.

## Honest limits

- The vehicle is **Napkid 11**, not enemy 41 (`native_identity` BLOCKED).
- The FSM is fed by the converted motion event table, not source skeletal
  Beetle animation (#128).
- The move distance combines the beetle's Jump flick with the labeled
  `mVolatileVelocity` follow drive; follower count was small (2). Owner-death
  follower release is covered, but the carcass/reward path, real combat
  receivers and persistence are not.
- Whistle effect ring/audio and retail material fidelity remain open.
