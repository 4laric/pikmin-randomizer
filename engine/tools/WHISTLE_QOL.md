# Responsive whistle and worker protection (#65)

The PC whistle recruits from its first frame and continuously while held. It begins 35% of the way from the configured minimum radius to the maximum, reaching the existing maximum after 0.6 seconds. AP whistle-range upgrades scale both the recruitment radius and visible circle. The full radius is initialized and retained instead of reading an uninitialized sustained radius.

Short calls protect every mode except Free/Formation. At 0.6 seconds of continuous hold, workers become eligible for ordinary recall; releasing never grants worker interruption. Existing eligibility rules still apply. Drowning, knockdown and fire rescue bypass worker protection. Other programmatic callers retain the original default worker-recall behavior.

The isolated real-game fixture checks all protected mode tags, immediate idle recruitment, held worker recall, out-of-range rejection and timing/radius boundaries. It links actual Navi/Piki code; the mode-tag checks do not simulate every task's work animation or physical gamepad input. Physical whistle feel, sustained effects, task-specific cleanup and moving-cursor acceptance remain playtest checks.

Build the completed Windows game first, then run tools/verify_whistle_windows.py --build BUILD --output FIXTURE. From the randomizer root run scripts/test_whistle_native.py --exe FIXTURE/preview_whistle.exe --assets ASSETS --output FRESH_PRIVATE_SESSION. The fixture is a separate test main and is not linked into production.
