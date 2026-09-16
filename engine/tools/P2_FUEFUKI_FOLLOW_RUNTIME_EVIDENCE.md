# Fuefuki follow-locomotion real-GL runtime evidence (#245)

Status: **executed, PASS**. Every `P2_FUEFUKI_FOLLOW_RT_*` marker below came
from an actual real-GL run of `tools/p2_fuefuki_follow_runtime.cpp` against the
retail-derived asset tree and the converted Pikmin 2 room arena. Nothing here is
simulated from the mock-host policy fixtures.

## Scope (what is real, what is not)

Real in this run:

- the frozen P1 host booted with `--experimental-pikmin2-room` on a real
  SDL2/OpenGL window (960×540, centred);
- six real `pikiMgr->birth()` Pikmin placed on the converted room collision,
  three inside the 130-unit whistle ring and three outside;
- the lane-owned `pc_p2_fuefuki_binding.h` seam driving the new
  `pc_p2_fuefuki_follow.h` ActTeki policy: the host sample reads real
  `Piki::mSRT.t` positions and the host drive applies the command to the real
  `Piki` actor (`Piki::setSpeed` plus the labeled `mVolatileVelocity`
  approximation);
- the observed **position change is engine integration**, not a fixture
  write: follower 1 walked 70 → 50 units toward the beetle at the source
  arrival threshold (`FOLLOW_DISTANCE / 2 = 50`).

Not real / not covered:

- no dedicated P1 follow-teki action; the `mVolatileVelocity` impulse is an
  explicit approximation (see `P2_FUEFUKI_FOLLOW.md`);
- the beetle anchor is policy-side (static in the approach phase, scripted
  along -Z in the trail phase); there is no Fuefuki actor or visual/audio
  asset and the beetle velocity blend is pinned to zero, so this proves the
  follower policy against a moving trail, not native beetle locomotion;
- no PIKISTATE_Panic equivalent; this run does not cover release/reclaim
  (covered by `P2_FUEFUKI_RUNTIME_EVIDENCE.md`).

## Provenance

- Native branch `opencode/p2-lane28-fuefuki-follow`, HEAD
  `c3fd1a94ef62c07dc98a5b887d19bd9cdb118b6a` (adds the moving-trail phase; the
  locomotion policy/seam/host slice is `f6982a58`, the runtime fixture
  `f0900f2a`).
- Base `f14c6851473ac1161be56c8b98f4f905232f3635` (`codex/p2-main-review-native`).
- Isolated fixture build (verifies HEAD, Ninja freshness, records git state):

  ```
  py -3.12 scripts/build_pikmin2_fixture.py \
      --build output/lane28-fuefuki-build \
      --source output/native-lane28-fuefuki \
      --fixture output/native-lane28-fuefuki/tools/p2_fuefuki_follow_runtime.cpp \
      --output output/p2-lane28-follow-runtime-04 \
      --expected-native-head c3fd1a94ef62c07dc98a5b887d19bd9cdb118b6a
  # -> {"status": "built", ...}
  ```

- Private build `output/lane28-fuefuki-build`, Ninja Release, MinGW-w64 g++
  16.2.0, JAudio ON; `ninja pikmin_pc -n` reported no work.
- Fixture executable SHA-256
  `1AC01C5359B10F014DCC5B9B455B068A50C16235DE14A050A41FACA4139765B4`.
  Earlier clean-HEAD runs `p2-lane28-follow-runtime-02` (`8AE83711…`, HEAD
  `f0900f2a`) and dirty-worktree `…-03` (`471450F2…`) are superseded; all
  produced the same PASS.

## Staging and run

```
py -3.12 -c "import sys; sys.path.insert(0,'scripts'); from pathlib import Path; from preview_pikmin2_room import prepare; print(prepare(Path('C:/Users/alari/pikmin-local/game/assets'), Path('C:/Users/alari/pikmin-randomizer/output/pikmin2-room105').resolve(), Path('C:/Users/alari/pikmin-randomizer/output/p2-lane28-follow-arena')))"
# -> output/p2-lane28-follow-arena/754d8570d6054b078cfd542ad2078368

cd <run dir>; cp output/p2-lane28-follow-runtime-02/fixture.exe .
./fixture.exe --experimental-pikmin2-room > run.log 2>&1   # exit=0
```

Assets: retail-derived tree at `C:/Users/alari/pikmin-local/game/assets`,
converted room at `output/pikmin2-room105` (gitignored local state; no disc data
committed).

## Marker output (verbatim from run.log)

```
P2_FUEFUKI_FOLLOW_RT_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
P2_FUEFUKI_FOLLOW_RT_READY squad=6 anchor=0,0 ring=130 follow_distance=100 locomotion=actteki_volatile_approx
P2_FUEFUKI_FOLLOW_RT_CLAIM claimed=3 hold=3 start_dist=70.0
P2_FUEFUKI_FOLLOW_RT_MOVE start=70.0 end=48.4 frames=9 moves=60 stops=4 writes=0 real_piki=1
P2_FUEFUKI_FOLLOW_RT_TRAIL anchors_moved=112.5 follower_moved=25.9 dist_to_anchor=99.0 frames=45 moves=51 stops=84 writes=0
PASS FUEFUKI_FOLLOW_RUNTIME
```

(Run-to-run variation in the approach phase is expected: the near-speed
`0.5 * randFloat() + 0.5` and the frame rate both vary. The `end` value always
lands at the source arrival threshold `FOLLOW_DISTANCE/2 = 50`.)

Phase detail:

- **WINDOW** — real 960×540 centred window after settings load.
- **READY** — six real red leaf Pikmin; anchor at the room origin; the run
  declares the volatile-velocity approximation honestly.
- **CLAIM** — the real cast scan claims exactly the 3 in-ring Pikmin; follower
  1 starts 70 units from the anchor (inside the 100-unit follow distance but
  outside the 50-unit arrival threshold).
- **MOVE** — one binding tick per rendered frame: the ActTeki policy emits a
  footprint target (the anchor trail mark), and the host drives the real Piki.
  Follower 1 closed from 70.0 to ~48 units in 9 frames and the policy then
  emitted its arrival stop at the source threshold. 60 move commands and 4 stop
  commands; **zero ownership writes**; held Pikmin stayed in `FreeMode`; the
  three outside-ring Pikmin did not move into the ring.
- **TRAIL** — the anchor then walked 112.5 units along -Z (2.5 units/frame) and
  the follower kept chasing the real footmark trail: it moved a further 25.9
  units and settled at 99.0 units from the beetle — the source
  `FOLLOW_DISTANCE = 100` follow band — with 51 move / 84 stop commands
  (stop/re-target each frame as the trail receded) and still **zero ownership
  writes**. This exercises the footmark ring, `makeTarget` re-targeting and the
  far-speed branch against a moving trail, not just a static approach.

## Remaining gaps

- The approximation should be replaced by a real P1 follow action (provider
  lane 12); this run proves the lane policy and host API produce real motion,
  not that they are source-parity locomotive behaviour (no collision steering,
  no footmark chasing of a moving beetle).
- No moving beetle, visuals, materials, capture/release, or restart coverage in
  this run; those stay open.
