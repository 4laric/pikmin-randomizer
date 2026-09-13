# Tank visual proxy handoff

Child #202, parent #170, integration #186. Codex owner under shared 4laric.
Root integrates source; this lane made no shared native/converter/build edits.
Root source at handoff: `dd390c51d1201f1c09d0fae2575b6800b316759e`.

Owned new root files:

- `experimental/pikmin2_tank_install.py`
- `experimental/pikmin2_tank_arena.py`
- `tests/test_pikmin2_tank_install.py`
- This document.

Native source is an isolated review patch only under
`output/p2-lifecycle-batch/tank-proxy-patch/`: `pc_p2_tank.cpp`,
`pc_p2_tank.h`, `pc_p2_tank_phase.h`. The compiled test executable in that
directory is local evidence, not source for export.

## Explicit behavior split

Tank's opted-in actor remains a **P1 Fiery Blowhog**, native `TEKI_Tank` 15.
Only supported live visual motions change. P1 health, targeting, fire emission,
damage, collision, death/corpse, hauling and rewards remain authoritative.

Wtank is a **static noninteractive display**, not a creature. It has no native
actor, collision, AI, health, attack or receiver. The installer requires an
explicit `noninteractive=True` placement; config, manifest and native logs
call this out. No blue-textured fire attacker is created. Typed Bubble
receivers and water-panic behavior remain required for playable Wtank.

## Installer and arena

`install(profile, manifest_sha256, run, ids, water=None)` binds an explicitly
supplied source-manifest hash, checks variant IDs/receiver identities, all
pose hashes, exact clip/sample ordering and source event-frame coverage.
It validates actual generator IDs/type 15, finite water placement, private
stage/model paths, resource budgets and all conflicts before writing. Config
bytes are UTF-8/LF; overwrite is refused. Optional water absent means no water
display model/config row. No source assets are committed.

The original P1 Impact Site arena preserves every course file byte-for-byte,
including collision/routes. Added generator IDs 186151 (proxy) and 186152
(ordinary control) have full XYZ (-150,30,1850) and (150,30,1550), with zero
offsets and explicit single deterministic births. Static display 186153 is at
(300,30,1800), yaw 0. All three were absent from maintained root/native ID
searches and are reserved in the issue. The source generator is checked again
against all three before staging. These are engineering placements, not P2
source placements; actual native ground alignment is still untested.

Actual staging passed at
`output/p2-lifecycle-batch/tank-arena-02/394fd5b25a8342a0a29f2f6ffd845719`.
It installed 27 fire pose models plus one static water model. Config SHA256:
`f5df6513e0ae10f8bf892723140510ac9252ad3f94763162e8fb039509ba98b7`.
Source import is the #195 final `tank-assets-05` manifest.

## Native mapping and requested root hooks

The P1 counterpart's `src/plugPikiYamashita/TAItank.cpp:385–402` explicitly uses
Move1, Attack, Flick, WaitAct1 and WaitAct2. These map to the identically named
P2 source clips. Wait1, Move2, Type1, unknown motions and dead/corpse actors
decline the delegate and retain native visuals. This conservative fallback
can visibly switch to the P1 model; it is intentional until those motions have
a reviewed correspondence. No velocity-based animation guess is used.

The source frame is the clamped native counter divided by native last frame,
scaled to source last frame; the nearest baked source sample is selected.
Native loop wrap, pause and animation reset therefore determine visual timing.
No wall clock or gameplay event execution is added. This is normalized native
motion timing, not an assertion that P1/P2 event timings match exactly.

Root-owned integration, after reviewing the isolated source:

1. Add the family cpp to CMake. Call `pc_p2_tank_setup()` once after opted-in
   stage Teki birth, inside the existing asset heap context. Absent profile
   returns without registration or model loading.
2. Add `pc_p2_tank_draw(actor,gfx,view)` to the existing live draw delegate;
   return true consumes that draw. Do not add it to corpse rendering.
3. Call `pc_p2_tank_reset()` at the same stage/init teardown boundary as the
   other family modules; call `pc_p2_tank_forget(actor)` before pointer reuse.
4. Call `pc_p2_tank_draw_water(gfx)` at the existing world-overlay location.
   It sets perspective/material/depth and multiplies source SRT by camera
   look-at, matching the bounded Breadbug display precedent. It draws source
   waitact2 frame 0 only; no animation or actor update hook exists for water.

No shared ID allocation, save, collision, receiver or reward hook is needed.
Native parser rejects unresolved/duplicate/non-Tank bindings and malformed
samples/config; shape loading validates resource structure and byte budgets.
It does not replace the installer's source-hash checks. Models use gameflow
heap ownership; reset clears references, not independent frees. Texture
attachments are per pose in this small first module; mixed-roster memory and
render performance must be measured before scaling.

## Validation

Ten Python tests pass across source import and installer. They cover hash
mismatch, conflicting IDs/type, noninteractive water opt-in, nonfinite pose,
exact config bytes, tampering before writes and overwrite refusal. Actual
private staging validates original map preservation and model installation.

Isolated `pc_p2_tank.cpp` syntax-only compilation passed against native headers;
log: `output/p2-lifecycle-batch/tank-proxy-syntax.log`. The actual native phase
helper compiled and executed assertions for mapping, repeated paused frame,
counter reset, endpoint clamping and invalid observations. No shared build ran.

Native cpp SHA256:
`81c6639c8094398b3a49822f7cb1485b1cabb73a1f2d85ab77219556c5c0b9e4`.
Native runtime acceptance remains **pending**: fresh integrated build must
verify exact birth XYZ, live fire appearance/counter mapping, ordinary control,
water static visibility, reset/forget, then natural P1 combat/corpse behavior.
This handoff is not evidence that either full P2 enemy is playable or complete.
