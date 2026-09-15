# Groink shell interaction policy (#205)

Codex hard lane; base a32709de, successor to the source-event runtime.
Source: projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96,
MiniHoudaiShotGun.cpp:148-247 and include/Vector3.h normalise specialization.

The pure classifier returns at most one Bomb/Wind command per supplied living
candidate. It preserves the strict swept-prism boundaries, unconditional
terminal suppression for geometry-qualified candidates, source species rules,
owner exclusion for enemies, damage values and knockback vectors. Zero sweep
length suppresses all interactions. A vertical sweep retains the source zero
cross-product basis; it is deliberately not replaced with a capsule.

Host contract:

- Supply shell-step start/end after movement and terminal ground correction,
  already shifted down 10 units. Apply on moving steps, including the final
  step before recycling. Terminal includes owner-range expiration, not only
  floor/wall collision; invalid trace failure must never become a blast.
- Enumerate source-compatible cell candidates with sphere center at the sweep
  midpoint and radius sweep length plus terminalRadius (source attackHitAngle).
  The classifier does not perform this broad phase. Its vertical-degeneracy
  test intentionally bypasses candidate selection and is not world-hit proof.
- Map Captain, actual Pikmin, other Piki, Enemy and Other explicitly. Supply
  alive status, owner identity and enemy cell radius from current valid actors.
- Dispatch returned commands through appropriate receivers while preserving
  owner attribution. Do not treat classification as accepted damage. Pointer
  lifetime, rejection, immunity, repeated hits and cleanup belong to the host.

Finite inputs are bounded to absolute 1e6; radii, damage and cell radius must
be nonnegative. Zero radii preserve the source strict comparisons. Invalid
input returns valid=false with no command.
These are adapter limits, not additional claims about retail parameter ranges.
Float sqrt/normalization is a portable approximation of the original math.

Validation command (MinGW bin on PATH):

```
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_groink_hit_test.cpp pc_port/pc_p2_groink_hit.cpp -o ../groink-hit-test-01/test.exe
```

Tests cover strict prism/radial boundaries, species and owner filtering,
terminal suppression, zero-motion and zero-normalization cases, wind falloff,
fixed enemy damage, centerline knockback and nonfinite rejection. This is
synthetic source-policy evidence only. Live receiver damage, autonomous
targeting, death/corpse/revival and lifecycle remain open.

Next bounded target slice: MiniHoudai.cpp:492-530 chooses the first qualifying
cell candidate in a strict muzzle-relative corridor (vertical <200, lateral
<25, forward >1 and <searchDistance). Preserve source cell ordering; do not
substitute nearest distance. Attack END transitions additionally require home,
territory, searched target and path snapshots. The nearest-target helper's
candidate tie order is unresolved in the current source checkout.
