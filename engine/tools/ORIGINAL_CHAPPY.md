Original Chappy provider (#1240)
===============================

`pc_p2_original_chappy_test` checks the provider contract with a controlled
engine. `pikmin_ci_fixture_original_chappy` checks real original source-row
birth, actual Chappy FSM registration, 180 engine updates, cleanup and a second
activation. These checks do not establish natural combat, delivery or SAVE.

Stage a new private imported tutorial course using the current overlay with
20 live Pikmin. Preload TEKI_Swallow (4), its ordinary corpse config and number
pellets before admission. Stage the actual `p2-chappy-bank.txt` Red Bulborb
species row and all authored clips/converted meshes; an AP actor roster is not
needed. Keep private legal assets and runtime output under ignored output.

Run the native diagnostic through `scripts/run_pikmin2_fixture.py` with
`--arg=--experimental-pikmin2-surface --arg=tutorial`, a fresh staged run directory,
timeout 60 and marker `PASS P2_ORIGINAL_CHAPPY_RUNTIME`. Record exact native pin,
executable SHA256, no-work result and observed 960x540 centered window. Its
catalog contains only the literal tutorial/nonloop/5-29.txt#1 Red Bulborb row;
this is not whole-course admission. The diagnostic fingerprint is fixture-only.

For a human encounter, add `--manual-encounter` to the fixture invocation.
The actor appears at its authored XZ (-1172.299316,1737.217407), facing300
degrees, on actual installed terrain. No fixture writes its health or actions.

1. Confirm 20 live Pikmin and the centered 960x540 window. Approach the sleeping
   Red Bulborb on the upper route using ordinary captain controls.
2. Wake it through a normal Pikmin attack. Observe its P2 wake, chase, bite,
   swallow and flick clips. Observe captain/Pikmin damage from the actual attack.
3. Defeat it with ordinary attacks; wait through its death animation. Record the
   original source UID/token in the log and any number drops. Drop probability
   is 0.7; absence in one encounter is valid. Verify exactly one natural corpse.
4. Use ordinary Pikmin carry to the actual Red Onion. Record population change
   and corpse removal. Leave/re-enter through the consumer's real course path
   and verify original four-day respawn rules there.

SAVE/fresh-process resume belongs to the campaign consumer and requires its
actual tested save path. This provider diagnostic does not implement that path.
