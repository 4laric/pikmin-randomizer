# Groink burst: runtime consumer for the integrated shell-strike bridge (lane 21, #208)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4.1-flash), 2026-09-14. This advances the parked Groink stack
by giving the **already-integrated** Groink shell-strike bridge
(`pc_port/pc_p2_groink_hit.{h,cpp}`, `pc_port/pc_p2_groink_strike.{h,cpp}`, with
the capacity-correct `P2GroinkStrikeTracker`) a runtime consumer in real GL.

## What it adds

Private native candidate `opencode/p2-groink-burst` (base draft
`5f33a9e6e8f618394c5d78cfb1cc1201a754c1b6`, head
`1a7702fbfb165203667bc4f7bc0e79c98e970287`, worktree
`output/native-groink-burst`). Two ordered commits:

- `d4fe5f98` compiles the parked Groink policy/arena/target/volley stack into
  `pikmin_pc`: `pc_p2_groink.cpp`, `pc_p2_groink_arena.{h,cpp}`,
  `pc_p2_groink_attack.{h,cpp}`, `pc_p2_groink_clock.h`, `pc_p2_groink_events.h`,
  `pc_p2_groink_map_trace.{h,cpp}`, `pc_p2_groink_target.{h,cpp}`,
  `pc_p2_groink_volley.{h,cpp}` (all byte-identical to the parked copies, no
  source edits needed against the current draft), plus seven pure-policy CTests.
  The integrated `_hit`/`_strike` bridge and its tracker are preserved unchanged.
- `1a7702fb` makes the runtime fixture honour `PIKMIN_P2_ROOM_WINDOW=WxH` (the
  shared 960x540 room-window override; `pc_window_init` does not read it).

`tools/p2_groink_target_runtime.cpp` is revived as the private fixture. It no
longer `#include`s the Groink `.cpp` implementations directly (they are now in
`PC_PORT_SOURCES`); it includes only headers and links them from the product
objects, avoiding duplicate definitions. It drives each terminal shell through
`p2_groink_apply_strike(proxy, strike, candidate)` (with the shared
`P2GroinkStrikeTracker` dedup) into the integrated
`P2ProjectileReceiverRegistry`.

## Build

- Product `pikmin_pc`: `output/native-groink-burst-build`, `bin/nectar.exe`
  sha256 `2B3359977C720BD2B7C03FF6913426D7B967488F8A3A24049A3635794E3B5047`;
  `ninja -n` -> `ninja: no work to do.` The larger current draft makes Ninja
  link through `CMakeFiles/pikmin_pc.rsp`.
- Fixture: `output/groink-burst-fixture-build.py` (private; the maintained
  `scripts/build_pikmin2_fixture.py` rejects `@response-file` link commands and
  links through a rewritten response file instead). `output/groink-burst-fixture-02/fixture.exe`
  sha256 `511B410E572E7AFB7CD58D8AB012415BF7455AAACE76657CB770B06A3179343C`.
- All eight standalone tests compile with `-Wall -Wextra -Werror` and exit 0.

## Real-GL evidence

Run `output/groink-burst-run-01` (960x540, hidden window, `SDL_AUDIODRIVER=dummy`,
room `room_4x4a_4_conc`, `assets`/`save` junctioned to
`output/groink-runtime-sessions/0d2aa8c8fb084839b6616aef201fa614`); log copy in
`output/groink-burst-session-01` (stdout sha256 `438CD921…432FAB`, stderr
sha256 `ECCEC60B…5E426E09`). Exit via `std::_Exit(0)` after PASS. Markers:

```
P2_GROINK_ARENA_READY model=groink_attack.mod visual_muzzle_alignment=unvalidated shellmarker=debug fixed_heading=owner_yaw_only no_ai=1 no_damage=1
P2_GROINK_ATTACK_FIRE tick=42 frame=26.0 cycle=0 emitted=3
P2_GROINK_STRIKE_PLACEMENT fixture_pinned=1 reason=terminal_sweep_midpoint
P2_GROINK_RECEIVER_HIT token=2385837346720 kind=Bomb damage=10.000 health=15.000
P2_GROINK_RECEIVER_HIT token=2385837346720 kind=Bomb damage=10.000 health=5.000
P2_GROINK_RECEIVER_HIT token=2385837346720 kind=Bomb damage=10.000 health=0.000
P2_GROINK_RECEIVER_DEAD token=2385837346720
P2_GROINK_FLIGHT_SWEEP_PASS steps=90 hits=0 wind=0
P2_GROINK_STRIKE_PASS hits=6 deaths=1 health_start=25.000 health_end=0.000 placement=fixture_pinned
PASS GROINK_VOLLEY_RUNTIME
```

## PROVEN / NOT-PROVEN

**PROVEN** — the integrated bridge and tracker link into `pikmin_pc`; a real-GL
run drives shell sweeps through `p2_groink_apply_strike` into the integrated
`P2ProjectileReceiverRegistry`; Bomb strikes remove exactly the classifier's
10 damage per hit (25 -> 15 -> 5 -> 0) and the death marker fires exactly once;
the once-per-shell/target dedup (capacity-correct tracker) holds.

**NOT-PROVEN** — the six receiver hits use a fixture-pinned Navi placement at
the terminal sweep midpoint, not natural pursuit; the in-flight moving sweep
runs every tick (90 steps) but yields no natural moving hit (`hits=0 wind=0`).
Real MiniHoudai actor registration/locomotion stays blocked on the shared
`teki.h`/`tekimgr.cpp`/`gameCoreSection.cpp` hook. The seam's
`P2_PROJECTILE_RECEIVER_HIT`/`_DEAD` strings are emitted only by the
projectiles-arena consumer, not by this Groink fixture, whose receiver markers
are `P2_GROINK_RECEIVER_HIT`/`_DEAD`. Wind impulse still has no receiver
representation.

No maintained checkout or shared build was modified; native origin/upstream was
not pushed.
