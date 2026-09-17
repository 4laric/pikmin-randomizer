# P2 player seed launch package (#643)

Lane p2-player-seed-launch-package, generation 2. Owner: Codex through
shared account 4laric. This is a TOOLING provider: a snapshot-matched
validator, a fail-closed preflight, and a checked launcher generator for the
existing unmodified seed output/seeds/p2-monsters-20260916/seed.json. No
ADMIT, no ledger writes, no P1-proxy substitution, no fake launch.

## Seed pin (preserved, never modified)

- Seed p2-monsters-20260916, slot Player1, schema 9, snapshot
  e72f350ec89321b1b6d321739baa5fb44211614d.
- Admitted pin exactly {23,44,54,57,59,60,61,62,78} (33 p2 bindings);
  ledger rows 9/79 refused; whole-cohort placement pin preserved.
- Seed SHA-256 82cc2376c7b5a8f5cc8757007b18b840666b1d5f3f4b0708dda135031cb127a2
  (matches generation-info.json).

## What was built (owned files)

- experimental/pikmin2_player_package.py: snapshot validator (pin
  enforcement, 9/79 refusal), per-identity asset/binding audit against real
  installer/asset/native modules, fail-closed preflight, and gated
  Play.cmd/launch.py writers (written ONLY on a passing preflight).
- scripts/package_p2_player_seed.py: CLI (--check default; --write
  gated).
- 	ests/test_pikmin2_player_package.py: 10 focused tests (schema mismatch,
  refused/outside/incomplete pin, sidecar-only flag, missing
  installer/assets/native, exe requirement, refuse-without-write,
  full-provision success). All pass.
- This file.
- output/seeds/p2-monsters-20260916/Play.cmd + launch.py: NOT generated
  (preflight fails, correctly; see gaps). They are owned reserved paths for
  the passing run only.

## Real preflight result (fail-closed, correct)

ok=false, exit 1, seed valid, nothing written, no P1 launch. Exact gaps:
1. 57 Kurage: sidecar-only identity (muse_packaging stages sidecars, no
   full asset installation).
2. 78 MiniHoudai: sidecar-only identity (muse_packaging stages sidecars, no
   full asset installation).
3. 
o native executable provided (no matching e72f350e-pinned binary;
   native trees are read-only references here).

The other seven identities (23,44,54,59,60,61,62) pass installer, asset and
native-host presence checks.

## Exact gap + owned follow-on (no launch claimed)

Campaign-native support is missing beyond packaging. Owned follow-ons (for
the integrator/coordinator to dispatch, not this lane):
1. Full Kurage57 asset installer + native binding (family scope).
2. Full MiniHoudai78 asset installer + native binding (family scope).
3. Leased private native build pinned to the seed snapshot with executable
   hash + dry-run, then a passing preflight and the generated Play.cmd.
Until then, no player launch succeeds and none is claimed.

## Checks

- py -3.12 -m pytest tests/test_pikmin2_player_package.py -q -> 10 passed.
- Real preflight -> ok=false with the 3 gaps above, exit 1, seed untouched.
