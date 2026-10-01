# Private App settings guard and drift observations (#114 / #135)

The separate manual App observes `pc_window_set_settings_menu_open` through a
linker wrapper. Production LTO can inline that setter into settings and bypass
the wrapper, leaving the App's F6 guard unaware of an open menu. The private build
fix compiles unchanged `pc_port/settings/pc_settings.cpp` with `-fno-lto` and
substitutes only that private object. Production source/objects remain unchanged.

`scripts/pikmin2_settings_fixture.cpp` includes the actual manual App body. Its
keyboard-state wrapper injects an F1 edge into the real settings implementation,
which opens the menu and invokes the real menu-state callback. The fixture verifies
both the App's observed flag and `pc_settings_consume_game_input()` being true.
It injects F6, waits five frames, and requires no dialog, queued descent or transfer.
Another real F1 edge closes the menu; the next F6 must show one confirmation and
produce the native transfer and actual-position file. Only the confirmation answer
is automated. This is runtime input injection, not physical keyboard/controller QA.

## Runtime evidence

`output/p2-lifecycle-batch/settings-regression-01/result.json` passed:

- Real settings menu opened and consumed game input.
- Open-menu F6 produced zero dialogs/transfers over five frames.
- Closing with F1 allowed one F6 confirmation and native exit42.
- The transferred20-Pikmin party and full captain health were unchanged.

The fixture linked46 privately copied/hashed native156cbefa objects/libraries;
`output/p2-lifecycle-batch/settings-runtime/snapshot.json` records the exact inputs.
It did not race or change the shared production build. The fixture hash is
`0ea25cc266ac31b4e71b87000c47c4b2566abae4b0d1264b171b3c096a6f66b0`.

The fixed normal App remains
`output/p2-lifecycle-batch/repeat-runtime-build-03/manual.exe`, SHA256
`859ac665d33929eec7bfd8807d564be46bcafbe56e279851c2cbf9ff21633367`.
This runtime result supplements the earlier objdump proof of actual wrapper callers.

## Separate90-frame drift investigation

No actor position, fixture timing or tolerance was changed for these observations.
Using the final19-Pikmin/10-Purple snapshot at(-200,80,1160), the fixture zeroed
keyboard and gamepad buttons/axes and measured frames1,30,60 and90. All three fresh
runs were stationary throughout those observation windows:

| Run | Distance from saved position at every observed frame |
| --- | ---: |
| Initial observation |0.326654 units |
| Repeat2 |0.202206 units |
| Repeat3 |0.135515 units |

Ground height stayed80. The first run reported collision activity and a nearest
Pikmin14.70 units away, with both body radii8.5; the Pod was outside their combined
captain/Pod radii. These small initial offsets are consistent with startup body
separation. `Creature::respondColl` applies separation through volatile velocity
(`native/src/plugPikiKando/creatureCollision.cpp`), which `Creature::update` applies
and clears (`creature.cpp`). Standing Pikmin are not excluded by `Navi::ignoreAtari`
(`navi.cpp`). The measurements do not isolate a specific collision pair.

The earlier larger90-frame offset was **not reproduced** under controlled input.
Its exact cause remains unproven: uncontrolled input or different startup contact
conditions could explain it. No drift fix or broader stationary-position guarantee
is claimed. The earlier failed observation remains retained; thresholds were not
relaxed. Repeat measurements are in `settings-regression-01/drift-repeats.json`,
with full force/nearest-actor diagnostics in each native log.
