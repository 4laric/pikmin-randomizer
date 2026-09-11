# Cutscene skipping (#59)

Press Start (Enter on the default keyboard mapping) during an in-engine cinematic to finish it. This includes previously blocked landing, discovery and end-of-day cinematics, in standalone randomizer and ordinary PC play. A newly queued cinematic requires its own press. Text prompts and results/save screens retain their normal confirmation controls.

Skipping advances through scene events over successive updates. Notify and Action keys still use the ordinary dispatch path; scene actors are initialized, drawn near their final frame, and cleaned up normally. The movie queue and end callbacks remain intact. Existing non-player skip commands and the opening/video skip handlers retain their previous behavior.

Validation:
- `python tools/verify_cutscene_windows.py --build PATH --output PATH` links to actual game objects. Watched/skipped Notify event parity across 30/60/120 Hz, partial playback including the last scene tick, repeated requests, author-blocked scenes and looping scenes; final scene frames and teardown visited. 42 cases pass.
- `ctest --test-dir PATH -R pc_bbft --output-on-failure`: normal and background input gates pass, including Start edges in ordinary play.
- `--live` builds the isolated live fixture. With private schema-5 bootstraps, real landing movies 41, 42 and 43 skip and return to 60 stable gameplay frames. Extracted assets are not modified or distributed.
- Asset audit: 125 scene cuts, all forward/nonzero; at most eight keys in one cut. Exhaustive gameplay acceptance of every discovery, ending and day-end sequence remains separate from these checks.
- Production build: Release, JAudio ON, test hooks OFF.
