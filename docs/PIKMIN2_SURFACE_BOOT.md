# Bounded retail tutorial boot (#738)

The native `--experimental-pikmin2-surface tutorial` flag selects exactly one
registered `stages/p2_tutorial.ini` with stage ID 0. Unknown keys, duplicate flags,
room/challenge flags, AP bootstraps and explicit/inherited BBFT ports are refused.
The save root is disposable, stored Pikmin are cleared, and the private stage
must provide the current twenty-red field squad. Production startup defaults to
a centred 960×540 window after loading settings.

Stage with `python -m scripts.stage_pikmin2_surface_boot --assets <P1 assets>
--bundle <tutorial source bundle> --identity <receipt SHA256> --output <fresh output>`.
The source bundle is verified before conversion. Collision uses unchanged whole
source faces around the Emergence entrance and the existing physical engineering
boundary. Source water is retained and every declared local walking probe is dry.
The render model includes the whole retail course with approximate static materials.
Only the bounded entrance has supported collision; this is not a complete Valley
level. Routes, generator schedules, native water, full-course nonmanifold topology,
campaign progression and saves remain future work.

`native/tools/p2_surface_boot_fixture.cpp` observes real stage loading, twenty
live Pikmin, source ground height and engine movement traces. It checks a centred
960×540 window and the fixture captain guard on every active frame. Setting
`P2_SURFACE_FORCE_CAPTAIN_DOWN=1` produces exit 86 without a successful marker.
The `P2_SURFACE_BOOT` marker records selection only; acceptance additionally
requires `PASS P2_SURFACE_BOOT_RUNTIME` in a fresh guarded run. Engine traces
are bounded movement evidence, not natural player traversal or campaign sign-off.

Native dispatch refusal tests require `P2_SURFACE_EXE` to name the current pinned
private executable. Missing/duplicate stage registration is independently exercised
with private negative arenas. Keep assets, converted maps, fixture executables,
save roots and acceptance logs under ignored `output/`.
