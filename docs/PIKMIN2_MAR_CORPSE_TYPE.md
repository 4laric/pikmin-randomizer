# Mar family corpse-type fix (#772)

Lane `mar-family-corpse-type-native`, issue #772. Owner: Codex through shared
account `4laric`. Bounded engine slice: the exact missing input behind the
#716 gen-3 failing check (becomePellet binds no pellet: no corpse). Owns one
shared engine file plus four new files. No ADMIT, no ledger writes.

## Fix (one line, owned shared file)

`native/src/plugPikiYamashita/TAImar.cpp`, in
`TAImarParameters::TAImarParameters()` next to the `setI(TPI_SpawnType, ...)`
block:
`multiP->setI(TPI_CorpseType, TEKICORPSE_LeaveCorpse);`
This mirrors the established sibling-family pattern (taichappy, taicollec,
taikinoko, tainapkid, taiotimoti) and routes the family death path
(`BTeki::dieSoon`, `getParameterI(TPI_CorpseType) == TEKICORPSE_LeaveCorpse`)
into `becomePellet` on natural Mar death. No other family semantics change.
No CMakeLists change (GLOB covers the source). #186 shared review REQUIRED
before any shared-line landing.

## Probe (no actor, no HP, no injection)

The guarded fixture instantiates the REAL `TAImarParameters` and reads back
`TPI_CorpseType` through the engine accessor, then evaluates the exact
dieSoon predicate. Markers prove the value equals LeaveCorpse and the pellet
path is bound. Captain safety #632 adopted (guard sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
self-test + negative test); captain parked; no blanket invincibility.

## Producer contract (engine_change, satisfied on landing terms)

- Callsites: `native/src/plugPikiYamashita/TAImar.cpp::TAImarParameters`
  (one-line param; existing death-path callsite `BTeki::dieSoon` identified,
  unchanged).
- Build membership: GLOB-covered source (verified — no CMake edit exists to
  make); standalone probe fixture links outside membership.
- Consumers: mar-corpse-emission-native (#716 — closes its exact gen-3
  failing check: becomePellet binds no pellet) via the probe command (expect
  corpse-type + bound markers or an exact blocker); shard-enemies-2-mar29
  -observer (#375 transport_reward) downstream.
- Deliverable: LeaveCorpse active + pellet path bound with receipt markers,
  or an exact blocker.

## Gates (honest)

Probe-level proof only; engine-actor death, haul physics, and gameplay gates
stay UNTESTED. No playability claim. #716-owned port files untouched.
