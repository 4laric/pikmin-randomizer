# P2 species hazard capability matrix (lane 11, #131/#395)

Lane 11 of [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md).
This is the "species capability definitions from 11" that lane 10 (receivers)
consumes. Implementation owner: Codex through the shared `4laric` account;
executing session: opencode (`opencode-go/deepseek-v4.1-flash`).

Native candidate: branch `opencode/p2-lanes-1012` @ `14e8fb92` (base
`f9e139d8`); header `native/pc_port/pc_p2_species_policy.h`, test
`native/tools/test_p2_species_policy.cpp`; patch bundle
`native-candidates/lanes-1012/`.

## Matrix

Source: `native/pikmin2-research/src/plugProjectKandoU/interactPiki.cpp`.
`actPiki` rejects the hazard when the Pikmin kind is not the immune color(s).

| Species | Fire | Water/Bubble | Electric/Denki | Gas | Attack capability |
|---|---|---|---|---|---|
| Blue | - | immune | - | - | - |
| Red | immune | - | - | - | - |
| Yellow | - | - | immune | - | - |
| Purple | - | - | - | - | impact (#393) |
| White | - | - | - | immune | poison (#395) |
| Bulbmin | immune | immune | immune | immune | - |

Anchors: `InteractDenki::actPiki` `:334`/`:347` (`Yellow`, `Bulbmin`);
`InteractFire::actPiki` `:445`/`:453` (`Red`, `Bulbmin`);
`InteractBubble::actPiki` `:503`/`:511` (`Blue`, `Bulbmin`);
`InteractGas::actPiki` `:531`/`:543` (`White`, `Bulbmin`). Purple has no
elemental immunity. `P2SpeciesBulbmin = 5` was added to
`pc_p2_species.h` (source `Piki.h:54`).

## Interface

```cpp
#include "pc_p2_species_policy.h"
P2SpeciesCapability c = p2_species_capability(P2SpeciesWhite); // c.poisonAttack
bool immune = p2_species_immune(P2SpeciesBulbmin, P2HazardGas); // true
```

Unknown species and out-of-range hazards return `valid=false` / `false`; they
never default to an immunity.

## Evidence

```text
g++ -std=c++17 -Wall -Wextra -I pc_port tools/test_p2_species_policy.cpp -o test_p2_species_policy.exe
PASS P2_SPECIES_POLICY
```

Executable SHA-256
`B0485CA31FE9E35D8C3289A79D0DA35ABDB085B95A934B1B9056C0ECF8F56D2B`.
Policy test (engine-double).

## Limits

- This is the receiver-side immunity definition, not the enemy-side hazard
  emitter or its damage routing (lane 10, #170). `InteractDenki`/`InteractGas`
  receiver classes now exist on the port (see
  [PIKMIN2_RECEIVER_PATHS.md](PIKMIN2_RECEIVER_PATHS.md) §7); the gas/denki
  enemy emitters (`GasHiba`, `ElecHiba`, `GasOtakara`, `ElecOtakara`) remain
  family-lane work, so electricity/gas are compile-backed, not runtime-proven.
- Live Bulbmin identity is wired (`Piki::mP2Bulbmin`, `pc_p2_species`/
  `pc_p2_make_bulbmin`), but nothing spawns Bulbmin yet, so the matrix is
  compile-backed rather than runtime-proven. Cave persistence needs a versioned
  schema bump (see [PIKMIN2_BULBMIN_CONTRACT.md](PIKMIN2_BULBMIN_CONTRACT.md)).

## Receiver integration

The generic Pikmin fire/bubble receivers consume this matrix
(`src/plugPikiKando/interactBattle.cpp`): `InteractFire::actPiki` and
`InteractBubble::actPiki` call
`p2_species_immune(pc_p2_species(piki), P2HazardFire/P2HazardWater)`. See
[PIKMIN2_RECEIVER_PATHS.md](PIKMIN2_RECEIVER_PATHS.md) §6. Electricity and gas
still have no port receiver, so those columns are definition-only until
`InteractDenki`/`InteractGas` land (#170).

## Versioned species / compartment schema

`native/pc_port/pc_p2_species_schema.h` satisfies the #395 storage requirement
and matches the cave wire numbering: v1 = Blue/Red/Yellow/Purple, v2 = + White,
v3 = + Bulbmin (`p2_schema_max_species`, `p2_schema_required_for_species`,
`p2_schema_supports`, `p2_schema_validate`, `p2_schema_total`). An unknown
version is rejected, a nonzero count of a species newer than the reader version
is rejected, and negative counts are rejected.

`pc_p2_cave.cpp` is wired to it: it accepts `P2_CAVE_ENTRY_3`, validates restore
and runtime species through `p2_schema_supports(checkpointSchema, ...)`, restores
Bulbmin with `pc_p2_make_bulbmin`, and the writer emits
`max(checkpointSchema, p2_schema_required_for_species(...))` so it never labels a
payload with a schema that cannot carry its species. Existing schema 1/2
behavior is unchanged (schema 1 already allowed Purple). Private build:
`[2/2] Linking CXX executable bin\nectar.exe` (exit 0), `nectar.exe` SHA-256
`57FFA6844D4B237DAA49FBC0529976C21657EDFE9387F2F4EF893249C741BB1C`;
`tools/test_p2_species_schema.cpp` -> `PASS P2_SPECIES_SCHEMA`. The exact
compartment wire format is still to be agreed with #131/#132.
