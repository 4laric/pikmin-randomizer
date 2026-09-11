# Bomb-yellow throw selection (#67)

The shared preferred selection now distinguishes four classes: the existing three color IDs and a fourth class for yellow Pikmin holding a bomb. D-pad Left/Right skips classes without an alive, Normal, throwable squad member in the existing 200-unit radius. Simultaneous directions remain a no-op. Mouse-wheel color selection uses the same classes so it cannot overwrite the D-pad bomb preference.

Next-throw preview and both grab-selection paths filter by the same class. Held swaps use the existing D-pad routine; no bomb ownership, drop, fuse or throw behavior is changed. When a class is exhausted, selection retains the existing fallback behavior.

The live selection fixture uses two yellow squad Pikmin and a temporary held-creature sentinel (hasBomb is the engine's isHolding check), without advancing game AI while that sentinel exists. It checks both directions, preference persistence through findNextThrowPiki, simultaneous cancellation and an empty bomb group. This is selection coverage, not a live bomb-fuse/held-throw gameplay test. Physical controller and real bomb swap/throw acceptance remain open.

Build with tools/verify_bomb_selection_windows.py --build BUILD --output FIXTURE, then run scripts/test_bomb_selection_native.py from the randomizer root with --exe, --assets and a fresh private --output.
