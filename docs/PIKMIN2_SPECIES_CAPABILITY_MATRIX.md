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
  emitter or its damage routing (lane 10, #170). The port still lacks
  `InteractDenki`/`InteractGas` classes, so electricity and gas cannot yet be
  exercised at runtime.
- Live Bulbmin identity is wired (`Piki::mP2Bulbmin`, `pc_p2_species`/
  `pc_p2_make_bulbmin`), but nothing spawns Bulbmin yet, so the matrix is
  compile-backed rather than runtime-proven. Cave persistence needs a versioned
  schema bump (see [PIKMIN2_BULBMIN_CONTRACT.md](PIKMIN2_BULBMIN_CONTRACT.md)).
