# Seed-bound second captain

Issue #1080 adds an explicit generation option for the existing single-player
captain-switching implementation. Use `randomizer generate --p2-enemies
--p2-second-captain` or `generate(..., p2_enemies=True,
p2_second_captain=True)`. Both solo and AP manifests support the option.
Archipelago YAML exposes the same default-off option:

```yaml
Pikmin Randomizer:
  p2_enemy_randomizer: true
  p2_second_captain: true
```

Enabling the captain option without `p2_enemy_randomizer` fails generation.
It adds no items or progression requirements and does not change cooperative
multiplayer. Generated slot data and the exported manifest carry the same
captain setting and fingerprint.

The default is false. False and omission produce the same legacy manifest.
Opt-in adds the true-only `p2_second_captain` field and the
`p2-second-captain-v1` capability after existing capabilities. The manifest
fingerprint therefore separates sessions with different captain settings.
Non-boolean values and opt-in without P2 enemy generation are rejected.

`NativeRun` emits `CAPTAINS 2` immediately before `END`, following `PURPLE 1`
when Purple is enabled. Journal recovery removes only the exact captain trailer
for an opted-in manifest; missing, malformed, duplicated, reordered or foreign
captain directives fail closed. Existing persisted sessions cannot silently
change their manifest fingerprint.

The paired native parser consumes this seed setting in ordinary randomizer
mode. Generated sessions without it remain single-captain even if the process
environment contains the standalone preview opt-in. Standalone previews retain
their existing environment switch. `combined_captain` remains a separate option
that bundles movement/plucking upgrades.

Validation here covers generation, validation, bootstrap construction and
Python journal recovery. It does not establish native day-save restoration of
both captains, cave transitions, captain health/squad persistence, or full
campaign completion. Native capability handshake and runtime evidence must be
recorded against the paired native producer separately.
