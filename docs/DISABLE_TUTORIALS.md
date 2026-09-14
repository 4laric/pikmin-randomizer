# Disable Tutorials (#465)

Open **F1 > Mods > Disable Tutorials**, set **On**, then return and select **Save**. On is the default in this fork for new installations and config files missing the key. Explicit saved Off choices are preserved; resetting defaults enables it again. The option uses the normal pending/apply/cancel settings behavior.

When On, suppresses the nectar/flower, bomb explanation, 100-Pikmin limit, blocked carry-route, pluck/dismiss and HUD explanation popups. Their gameplay and discovery bookkeeping still run. Story, ship parts, recovery, extinction/day-end, and ending screens remain active. Turning it Off restores future tutorial triggers; tutorials already recorded as seen do not replay automatically.

For automated fixtures, write `disableTutorials = 1` in that run directory's `pikmin_settings.conf`, and ensure the fixture calls the normal settings loader. This is a runtime preference, not a seed/save field. Old executables need rebuilding. No existing run configuration was modified automatically.

Implementation owner: Codex through shared GitHub account 4laric. Native 5c9ba209 based on cc4f6205, clean. Replaces unconditional nectar suppression from #463 with the setting. The text dispatch uses an explicit six-ID allowlist before allocating a tutorial or activating its overlay, and performs the associated movie skip used by normal dismissal.

Initial implementation validation (before the default-On follow-up): full P2 production build PASS, Release/Ninja/MinGW, JAudio/IPO ON, private output/native-nectar-qol-build. Final ninja -n: no work to do. Executable SHA-256 8F8C6C8206FAF4BD3C15A1220DF9EFDCCC893BD77D0A334F2A451B2E432321C7. Exported 1996 files with only the intended six files changed/added. Compiled regression against both P2 and main settings implementations PASS: default/legacy config, pending isolation, saved On/Off round trips and all IDs -1..160 including progression exclusions. No interactive menu or in-game popup runtime acceptance claimed.

Regression source: engine/pc_port/tests/tutorial_settings_test.cpp. Compile with assertions enabled, the engine pc_types.h forced include, SDL_MAIN_HANDLED, MinGW -O2 -flto and the engine include/pc_port and SDL2 include directories. Run only in an empty private output directory: the test writes pikmin_settings.conf there. LTO strips unused renderer/input code; the only stub is the default keybinding table. Full compile and test logs are in common-root output/tutorial-settings-test; production log is output/disable-tutorials-build.log.

Default-On follow-up: native 156e372f. Compiled actual-settings regression PASS for initial defaults, missing-key config, pending isolation, explicit saved Off, saved On, reset-to-defaults, and unchanged tutorial policy. No full executable rebuild for this two-initializer change; the executable hash above belongs to the earlier default-Off build.
