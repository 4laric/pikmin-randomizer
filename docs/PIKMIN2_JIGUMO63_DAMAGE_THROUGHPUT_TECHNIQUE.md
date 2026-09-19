# Jigumo63 damage-throughput technique (#729, unblocks #374 gate 4)

Read-only technique slice: the EAT receiver works (9 bites / 7 eats, #689); the kill
fails on throughput (HP floor 380). No family/shared change, no runtime, no ADMIT.

## Measured baseline (pass1, #374 death-run1)

117 genuine throws drain HP 500.0 -> 380.0 (~1.03 per throw); 9 bites, 7 eats, 1 flick;
squad 20 -> 0; timeout with 0 DEAD; captain-down guard exit 86 taints the run.

## Break-even inequality

A kill needs strictly more than 500/20 = 25 HP drained per Pikmin lost. Pass1 measured
120/7 ~= 17.1 -> fails. Any passing run must beat 25 with a live captain and zero
injections; the adapter enforces this as a strict gate.

## Technique (stimulus-only; #689: no shared edit needed)

1. Latch-first sustained blows instead of throw impacts: keep thrown Pikmin re-latching
   inside the 200-unit bite sweep (ATTACK key event 2 / frame 26 capture zone) so damage
   comes from blows, not ~1-HP impacts.
2. EAT-rate bound: keep non-attacking Pikmin out of the sweep so the bite rate stays
   below pass1 9-per-117; re-latch promptly after each flick (radius 25, shake 100).
3. Anchors: LIFE 500.0 (`pc_p2_jigumo.cpp:88`), bite keys (`:489,496-499`), swallow keys
   (`:266-273,553-555,601-603`), flick (`:100-102,189-199,562-569`), Dead on mHealth<=0
   (`:425`); source part rule (`jigumo.cpp:325`, port accepts while alive).

## Validation plan for the observer

Same fixture + arena, latch-first stimulus; assert natural DEAD + corpse/disappearance,
ratio strictly above 25, zero captain-down, zero injections; fail closed otherwise.

## Verification

`py -3.12 -m pytest tests/test_pikmin2_jigumo63_damage_throughput_technique.py -q` -> 10 passed.