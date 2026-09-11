# Day-end skip regression (#63)

The results screen uses looping cinematic backgrounds. Player skipping previously finished those backgrounds, causing DayOverModeState to advance from the results phase into the ending phases and eventually return to title without saving.

GameMovieInterface now vetoes player skip requests while ordinary/challenge/final results or a memory-card dialog is open. Internal UI completion commands retain their existing skip behavior. DayOverModeState also refuses automatic phase advancement while ordinary/challenge results or memory-card UI owns the transition. Sunset, takeoff and other cinematics remain skippable.

Validation on Windows Release (JAudio ON, test hooks OFF):

- Actual day-end fixture boots Hope day 2, forces sunset, repeatedly requests cinematic skips, holds results for 120 frames, then presses A through results/save. It reaches the next-day map transition and creates a 155,648-byte private card data file.
- Baseline using b705642e's actual GameMovieInterface/DayOverModeState fails with `background skip advanced into ending phases` after opening results, reproducing the user's report.
- Fixed fixture passes: `results/save completed; next-day map requested`.
- All 42 existing actual CinematicPlayer cases still pass.
- Final player build includes the separately validated #62 quick-release grab fix. No player save/session files are edited by this work.

Commands (MinGW64 on PATH):

```
python tools/verify_cutscene_windows.py --build BUILD --output OUTPUT --dayend
python tools/run_dayend_skip.py OUTPUT
```

The run wrapper uses a fresh private schema-5 test bootstrap, dummy audio and hidden game window. Its local asset path must match your extracted files. `--baseline` on the build wrapper reconstructs the old native source through git, for the pre-fix comparison; it requires the native development history. The fixture links the actual day-end implementation into the test executable; it is not included in production.

This covers ordinary day-end in Hope; it is not exhaustive gameplay acceptance of every final ending or challenge-mode save path.
