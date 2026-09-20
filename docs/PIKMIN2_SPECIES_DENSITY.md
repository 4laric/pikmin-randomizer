# P2 species-density policy (#838, wired by #841)

`resolve_placement_layout` in `experimental/pikmin2_seed_bridge.py` binds lane-04
accepted placement targets to the admitted lane-02 identities. This document
defines the versioned density policy that decides *how many* compatible targets a
selection replaces, and records how `randomizer/seed.py` and the product CLI
expose it.

## The problem

The original resolver guaranteed each selected species at least one binding and
then filled **every** remaining accepted target. With `p2_species=[23]` the
committed accepted-placement document exposes 33 compatible Hope targets, so all
33 became Sarai — the eight overlapping capture territories reported in #838.
That is correct for "replace the whole compatible set", but it is the wrong
default for a narrow one-species validation, which only needs one Sarai.

## Versioned policies

The policy is stored on the layout as the `density` key so a loaded manifest is
rederived/rejected against the same rule it was generated with:

| token | meaning |
|---|---|
| `all-targets-v1` | Legacy default. Every selected species is covered and **every** accepted compatible target is bound. |
| `bounded-coverage-v1` | Binds the minimum number of targets that gives **every** selected species at least one binding; unassigned compatible targets stay vanilla (unbound). |

`resolve_placement_layout(..., density=None)` is the legacy default and is
byte-for-byte unchanged. A layout with **no** `density` key (an existing saved
seed) is treated as `all-targets-v1` and still validates. An unknown token is
rejected, so a tampered manifest fails closed instead of re-rolling.

### Invariants (both policies)

- Every selected species appears at least once; if two identities can only share
  one accepted target the resolver raises rather than silently dropping one.
- A target is only ever bound to an identity the document **accepts** for it;
  bounded mode never widens accepted-placement constraints.
- The result is a pure, deterministic function of
  `(seed, slot, document, species, density)` on the `sha256-counter-v1` RNG. The
  bounded policy reuses the legacy coverage roll stream, so its one-per-species
  role assignment is stable for the same inputs.
- No species is special-cased; nothing about Sarai is hardcoded.

## API

```python
from experimental.pikmin2_seed_bridge import (
    DENSITY_BOUNDED, DENSITY_LEGACY, resolve_placement_layout)

layout = resolve_placement_layout(
    seed, slot, placement_document, roster,
    species=sorted(selected_source_ids),   # optional subset
    density=DENSITY_BOUNDED,               # optional; default None == legacy
)
layout["density"]            # -> "bounded-coverage-v1"
layout["bindings"]           # one per selected species under bounded coverage
```

`resolve_layout` (the explicit-cohort diagnostic path) takes the same `density`
keyword: bounded mode binds the first `len(cohort)` ordered targets, legacy mode
fills all of them.

The native `ENEMY_P2` bootstrap line carries only the bindings, so it cannot
carry the policy. `parse_bootstrap(text, roster, density=layout["density"])`
preserves an explicit policy; without the keyword it reconstructs a legacy
layout.

## Product API and CLI wiring (#841)

`randomizer/seed.py` now exposes the policy as an explicit, optional keyword and
forwards it into the existing resolver call:

```python
from randomizer.seed import generate

manifest = generate(
    "seed-a",
    p2_enemies=True,
    p2_species=[23],              # optional subset
    p2_density="bounded-coverage-v1",
)
manifest["p2_layout"]["density"]  # -> "bounded-coverage-v1"
```

- `p2_density=None` is the default and reproduces the legacy all-target fill
  byte-for-byte, so existing seeds keep their fingerprints.
- The token is validated through the bridge's `validate_density`; an unknown
  token fails closed before any layout work.
- `p2_density` requires `p2_enemies`, exactly like `p2_species`.

The `python -m randomizer generate` CLI surfaces the same value as
`--p2-density {all-targets-v1,bounded-coverage-v1}`; omitting it keeps the legacy
default. Exposing the option from the AP YAML layer
(`apworld/pikmin_randomizer/options.py`) is a separate product decision and is not
part of this slice.

## Tests

`tests/test_p2_species_density.py` pins, against the committed accepted-placement
document and the real roster:

- the eight-Sarai all-target case (`species=[23]` binds all 33 accepted targets),
- the unchanged legacy default and its exact admitted-cohort multiset,
- bounded coverage for one and many species (`species=[23]` binds exactly one),
- insufficient-unique-target fail-closed behaviour,
- unknown-policy rejection and `p2_species` subset selection,
- manifest/bootstrap round trips preserving the stored `density`,
- absence of the `density` key on a legacy manifest remaining valid.

`tests/test_p2_density_seed_wiring.py` covers the product wiring:

- `generate(..., p2_density=...)` forwards the policy and stores it on `p2_layout`,
- the default equals an explicit `all-targets-v1` and keeps the pinned legacy and
  P2-legacy seed fingerprints,
- one- and multi-species bounded coverage through the product API,
- manifest JSON round trips, tampered-policy rejection and the legacy manifest
  with no `density` key still validating,
- the `--p2-density` CLI flag for a bounded and a default-legacy seed, plus
  rejection of an unknown token.
