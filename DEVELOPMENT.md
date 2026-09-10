# Standalone milestone: local implementation

The native port now has a separate `--randomizer-seed` adapter and a Python solo/AP runner. No BBFT conductor or shared AP installation link is required. Physical parts are still at their original positions: the native adapter deliberately rejects relocation manifests until the slot/carry audit is complete.

## Implemented

- Strict versioned manifest with separate native part IDs, permanent location IDs and reward IDs; standalone game identity `Pikmin Randomizer`.
- Thirty checks (28 parts and two Onion discoveries), 25 repair rewards and five color/area unlocks. Victory requires 25 received repairs, not physical part count. This fixes the specification's initial item-count mismatch.
- Deterministic solo reward fill with backtracking and conservative inherited color/area rules.
- Packaged standalone AP world with identical check requirements and an exported `.pikmin.json` manifest. AP rewards are authoritative; local collection does not immediately award its remote reward.
- Version/capability handshake through private file IPC; per-run token, per-manifest fingerprint, native check journal, atomic runner saves, AP receipt overlap validation and exclusive session writer lock.
- Recovery of complete native check records after runner interruption. Native stale-heartbeat hold and normal foreground/input gates remain active.
- Independent day-two Forest of Hope boot with twenty reds and received Yellow/Blue/area unlocks. No BBFT shared tools or travel controls.
- Engine calendar repeats day 29 to retain safe bounds in the original 30-entry diary tables. Standalone disables vanilla ending authority; repair progress/victory appears in the native window title and log. This is not a new ending cutscene.

## Important current limits

Full native campaign resume is not implemented. Relaunching restores check/reward history but starts a fresh day-two native campaign and starter population. Do not treat this as save/resume sign-off: day/area/squad persistence and extinction recovery remain issue #6. Day-29 sunset behavior needs physical testing. New placement routes are not validated, no parts are relocated, and expansion types/treasures/caves are not implemented.

## Build

Configured build directory: `native/build-randomizer`, MinGW GCC 16.2, CMake/Ninja, matching SDL2, native JAudio, CPU-specific optimization disabled. Executable: `native/build-randomizer/bin/nectar.exe`. Matching SDL2.dll and libwinpthread-1.dll are beside it. The compiler/bin tools must be on PATH for rebuilding and running the small test executables.

```powershell
cmake --build native/build-randomizer --target pikmin_pc pc_randomizer_probe pc_bbft_test jaudio_bbft_test -j 6
python -m unittest discover -s tests -v
python scripts/test_native_protocol.py native/build-randomizer/pc_randomizer_probe.exe
python scripts/build_apworld.py
python scripts/test_apworld.py C:/Users/alari/Archipelago
```

The AP test reads that source installation and loads our packaged world in its own process; it does not install a world or change a link.

## Solo launch

Run from this repository root. Use a fresh output filename for each generation; generation refuses to overwrite an existing manifest.

```powershell
python -m randomizer generate --seed first-pikmin --output output/first-pikmin.json
python -m randomizer validate output/first-pikmin.json
python -m randomizer run output/first-pikmin.json --session-dir output/first-pikmin-session --exe native/build-randomizer/bin/nectar.exe --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets
```

The assets argument points to existing extracted files containing `dataDir/stages/`. The runner makes a directory junction into a new private runtime folder; saves/logs/settings stay in that folder. It does not copy or write original assets. Close the game to end the runner. AP mode requires `websockets` (tested with 13.1); solo does not.

## AP launch

Build `output/pikmin_randomizer.apworld` and install it into a separate AP setup, generate a `Pikmin Randomizer` slot, and use that generation's exported `.pikmin.json`. Do not manufacture an unrelated AP-mode manifest: the client must match the generated slot's manifest and fingerprint. Launch as above with `--server localhost:38281`. Optional server password comes from `PIKMIN_AP_PASSWORD`. AP authentication validates room/team/slot identity and waits for received-item synchronization before releasing native gameplay.

## Evidence

- 11 Python contract/session/protocol tests pass; includes 100 solo seeds, duplicates, corrupted manifests, replay conflicts, crash-journal recovery and fake AP server handshake/check/goal exchanges.
- 100 actual AP single-slot fills and one two-slot fill pass with the packaged world: `output/apworld-tests.log`.
- Three inherited BBFT/audio CTest regressions pass.
- Compiled native protocol probe passes opt-out, handshake, durable duplicate suppression, incompatible version/placement/state, mixed BBFT/standalone rejection and single-use-run checks.
- Hidden, silent native startup passes rendered Forest of Hope, twenty field reds, received color stocks, area unlocks, repair goal and zero invented checks: `output/native-startup-1.log` and its linked native log. This uses synthetic AP receipts to exercise native item handling; it is not a real AP server end-to-end gameplay run.
- Full native build passes. Initial build exposed an inherited missing `bbft_checked` test stub; adding that fake-transport function fixed the test link.

Physical part carrying, full-seed solo/AP completion, day rollover and exact campaign resume remain open acceptance work. Planning/issues: https://github.com/4laric/pikmin-randomizer/issues/1 .
