# P2 Archipelago playtest integration (#439)

Implementation owner: Codex through shared account 4laric.

The AP option `p2_enemy_randomizer: true` now consumes `p2_placement`, a complete
lane-04 p2-placement-v1 mapping in the player YAML. It is passed unchanged to the
existing admission/placement validator. Missing, malformed and denied placement
fail generation. Keep P1 enemy shuffle modes off when enabling P2.

The .apworld bundles a pinned roster/evidence snapshot and the seed/placement
modules under its own package. It needs neither a repository checkout nor global
randomizer/experimental imports. Rebuild the package when admission changes.
No game assets are included. The bundled roster is read-only generation input.

Build and verify:

```
py -3.12 scripts/build_apworld.py --output output/pikmin_randomizer.apworld
py -3.12 scripts/test_p2_apworld.py --ap C:/Users/alari/Archipelago --archive output/pikmin_randomizer.apworld
```

The isolated integration test uses explicitly synthetic placement to check AP
fill, deterministic generation, missing/denied input rejection and saved-manifest
roundtrip. It does NOT establish gameplay placement acceptance.

Native P2 launch requires the existing --content-manifest or --p2-content route;
a bare seed can no longer start an unstaged native process. The content route
must cover seed identities; actor bindings and reviewed source assets remain
required as documented in PIKMIN2_CONTENT_STAGING.md.

## Current species-line validation

Rebased onto the actual species delivery line 3a33cbdefd5e4057eef9fb0d824cce4510ddab05,
not the integrator's older l74 working checkout. That line already supports a
default admitted placement document; an omitted AP placement uses its packaged
snapshot. Explicit placement still goes through normal validation.

Actual Generate.main + Main.main produced AP seed 90474384339549028366, player
Alari, with server multidata, spoiler and player manifest. It contains all 11
admitted IDs [9,23,44,54,57,59,60,61,62,78,79], 33 bindings, Forest/Red start,
capacity 50 and Emperor goal. Local output: output/p2-ap-playtest (canonical root).
The isolated package test uses the real bundled placement document and a cwd
outside the source tree; synthetic placement is used only as a denial fixture.

## Native runtime work still required

Generation is not a verified playable campaign. The species native source's
pc_p2_generated_placement.cpp still restricts Kurage57 and MiniHoudai78 to fixed
UIDs; the generated manifest can assign multiple copies to other targets. Their
native sidecar parsers accept only one actor. Kogane setup aborts when a configured
actor is absent, incompatible with a sidecar spanning different campaign areas.
The full-pool runtime adapter/content chain and production-native campaign launch
remain unverified. Do not distribute this as a working game launcher or grant
ADMIT from the AP fill result. StartServer.cmd only starts the local AP server.
