# Native repeat-visit fixture (#114 / #132)

`scripts/test_pikmin2_surface_repeat_native.py` runs the repeated manual host
against seven actual native processes: entrance, cave floor1, floor2, entrance,
floor1, floor2, final entrance. It uses one SurfaceLedger and the existing
SurfaceRunner. The separately compiled normal repeat App is retained with its
hash; native process execution uses the explicitly instrumented fixture binary.

The private fixture includes an extracted copy of the real manual App body.
`build_apps` reads its source up to the unique `main` definition and records the
source/executable hashes and complete link recipes. No manual input/checkpoint
logic is replaced: an SDL F6 event is injected into its event filter, while a
private linker wrapper answers the confirmation dialog. The App performs its
usual native checkpoint and actual-position write. These are injected events,
not physical keyboard/controller acceptance or Kimi's independent manual QA.

The fixture explicitly removes enemies, changes captain position, injects a
first-visit casualty/maturity/health change and10 Purple identities, then calls
native delivery hooks. Second-visit delivery repeats the same cargo identities;
both within-process and across-visit balances must not increase again. It changes
health to50% on the second visit. Every native process checks restored species,
maturity, count, health and receipt balance against its entry files. Surface
processes also check the saved source position within one unit of native settling.
The final surface exits automatically after inspection.

Expected final state:19 survivors including10 Purples,50% captain health, and the
same cumulative receipt total after both visits. The host must have revision8 and
remain at the source surface. This is native restoration/receipt/transition
evidence; it does not validate combat, Purple conversion gameplay, hauling AI,
physical input, full-world saves, or native surface water.

Use a fresh output directory. The timeout is bounded to1–300 seconds per exact
fixture process. Each run logs its injected actions; a missing F6 or confirmation
marker fails the harness. Both executable hashes are captured before execution.
Build only against a parent-confirmed stable object set; private fixture/App
linking must not race a shared native rebuild. The helper reads the exact current
production object list from `build.ninja` so newly added engine modules are not
omitted by an older fixture recipe. It replaces only the main object and redirects
the import-library output into the private build directory. One unchanged settings
source is also compiled privately with `-fno-lto`: otherwise production LTO inlines
the menu-state setter and bypasses the separate App's linker wrapper. Verify actual
callers to `__wrap_pc_window_set_settings_menu_open` in the linked normal App.

## Observed run

`output/p2-lifecycle-batch/native-repeat-02/result.json` passed all seven processes
against native156cbefa objects and the integrated surface identity checks. Exits
were42 six times, then0; final ledger revision8 contains19 survivors/10 Purples,
health0.5 and480 Pokos. Both visits ended at480, with no duplicate cumulative credit.
The final source position was saved exactly as(-200,80,1160); native position after
30 walking frames was(-199.813248,80,1160.71484), within the existing one-unit
settling allowance. Each surface log contains expected/actual coordinates.

The earlier `native-repeat-01` reached the correct final party/health/receipt state
but failed the stricter position observation after90 frames. The final fixture
uses the same30-frame restoration window as the preceding surface fixture;
subsequent body/collision movement is not a promise of stationary coordinates.

Normal repeat App: `output/p2-lifecycle-batch/repeat-runtime-build-03/manual.exe`,
SHA256 `859ac665d33929eec7bfd8807d564be46bcafbe56e279851c2cbf9ff21633367`.
Fixture SHA256 `60c2a7fb6cad02c479d80d6b2c9a024896976ba2c9c9653f6a0d73960e094ee2`.
The result captures both paths/hashes before execution. Private recipes, source
hashes and build logs are adjacent to the executables. No production binary or
player save was replaced. No physical-input or normal-gameplay claim is made.
