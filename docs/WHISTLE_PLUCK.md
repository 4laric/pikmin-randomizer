# Whistle Pluck

Tracked in [#452](https://github.com/4laric/pikmin-randomizer/issues/452).
Implementation owner: Codex through shared GitHub account `4laric`.

Enable **Whistle Pluck** in **F1 → Mods**, return to the main settings panel,
and select **Save**. It is off by default. The persisted setting is
`whistlePluck = 1` in the game's local `pikmin_settings.conf`.

A whistle press plucks the nearest eligible sprout inside the current whistle
circle. Holding continues with at least 80 ms between sprouts. Releasing stops
new plucks; an emergence already started finishes normally. Expanding or moving
the whistle selects from the sprouts currently in reach. There is no queued
list of actors. Range upgrades affect the circle normally.

Sprouts use the native `AutoNuki` self-unbury state and `Kaifuku` animation,
including its keyed dirt effect and pluck sound. Animation completion joins
the calling captain's formation. Base color, leaf/bud/flower maturity and
experimental Purple/White identity are copied from the sprout.

Eligibility uses the native grounded/pluckable sprout states, a strict
horizontal distance inside the whistle radius, and less than 25 units of
vertical separation from the cursor, matching manual plucking's vertical
reach. Pauses, UI overlays, active movies, day end and dead captains reject
new conversions.

Sprouts already count toward the field population. Conversion uses the same
temporary birth allowance as manual plucking; it does not grant additional
Pikmin or expand the limit. Failed allocation leaves the sprout intact.
Successful allocation finishes the sprout's water effect and removes it once.
The native animation owns subsequent movement and formation joining.

The option is a local gameplay setting. It adds no randomizer item, receipt
counter or campaign-save schema. The old dormant PC debug cursor-pluck path is
replaced by this explicit setting and cadence. Manual plucking is unchanged.

## Verification

The private fixture `engine/tools/preview_whistle_pluck.cpp` boots a newly
generated room with 20 Reds in a centered 960×540 window. It injects grounded
sprouts and captain controller input, then exercises the production whistle
state and native emergence animation. Allocation failure and the field-limit
boundary are deliberate fixture parameter changes. This is not a manual
controller or full-campaign playthrough.

Build and runtime evidence is recorded in #452 and the local
`output/whistle-pluck/` directory.


Validation (2026-09-14): private and maintained Release builds passed with
`PIKMIN_NATIVE_JAUDIO=ON`, `PIKMIN_NATIVE_OPTIMIZE=OFF`, and Ninja reporting no
pending work. Native integration: `a95040b66a0ffc9cdbfc649502569a29e66949a7`.
Maintained executable SHA-256:
`464cf858f314cfab496b55baf9c9de22b6da291ec01104525d246b3c77ba96b2`.
Public export contains 1,580 source files; the inherited dirty native baseline
was preserved.

Three fresh fixture runs passed for base colors, Purple and White. They
observed the disabled option through actual whistle input; pause, UI, movie,
dead-captain, radius and height rejection; failed population-gated allocation;
conversion at the field limit; release-to-stop; native emergence completion;
formation joining; preserved identity and all three maturity stages; and
unchanged total population of 24 (20 starting Pikmin plus four injected
sprouts). Observed intervals were 89, 96 and 100 ms respectively. All nine
before/emerging/after captures are 960×540. Window position `(373,263)` on a
`1707×1067` display is centered within rounding.

Final fixture provenance is `built` at
`output/whistle-pluck/fixture-03/provenance.json`; its executable SHA-256 is
`1c7c07c2059fc007d38109134ef1a011d47e88cb0d68c5ffd13cbbe9800d2875`.
Run directories and all staged model/config hashes are recorded in
`output/whistle-pluck/adoption.json`. The earlier fixture-02 gameplay passes
are supplementary only: its settings reload enlarged the window, corrected
in the final fixture.

The existing compiled whistle-tap regression and nine relevant Python tests
(`test_benefits`, `test_pikmin2_preview`, `test_pikmin2_preview_policy`) pass.
Audio uses the fixture's dummy device; audible/controller feel, manual F1
navigation, multi-captain play and full campaign save/re-entry were not tested.
No original assets, live saves or shared Archipelago installation were changed.
