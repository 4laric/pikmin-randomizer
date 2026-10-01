# Kurage57 death/transport/re-entry observer (#768)

Lane `shard-enemies-4-kurage-death-transport-observer`, issue #768. Owner:
Codex through shared account `4laric`. Bounded observer for Kurage57 death,
transport and re-entry, following the #753 designated-paths approach on
disjoint paths (no #498 duplication) and consuming the done #498
natural-birth handoff read-only. Owns only the observer, its tests, this doc
and the guarded fixture. No family/shared edits, no ledger writes, no ADMIT.

## Consumed pins (read-only)

- #498 `muse-kurage` gen 5 (gate-1 baseline): handoff
  `output/muse-wave/l58/handoff.json` (`dbc835c4...`).
- #753 designation gen 2: handoff
  `output/workflow/autofill/prerequisites/kurage-observer-paths-discovery/out/handoff.json`
  (`56e1c210f...`). Note: #753 designated `kurage57_observer` filenames; this
  lane owns the `kurage_death_transport` filenames from its bound brief —
  still disjoint from all four #498 files, so the zero-overlap principle
  holds.
- Real lifecycle: `P2KurageCapturePolicy` (`pc_port/pc_p2_kurage.{h,cpp}`),
  engine-free by design; compiled into the fixture TU, never edited.
- Captain guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`,
  recorded in every acceptance record. CAPTAIN_DOWN exits BLOCKED and can
  never substantiate a PASS. Captain parked far outside attack reach; no
  blanket invincibility; no fake guard provider.

## Observation design

A live Kurage57 actor (ID 57, Greater variant, killTime 16.0) plus a starting
squad of ten is staged. Two passes run the real policy: capture five across
two waves with digestion ticks between (three digested at stomach >= 16.0),
then natural death releasing the survivors plus one hauled corpse. Pass 1
emits the FRESH transport receipt; pass 2 (re-entry after reset) replays the
identical accounting with doublecount=0 and matched=1. Fresh private arena
per run; centred 960x540 window; active observation loop.

## Producer contract (runtime_check, satisfied)

- Callsites: `native/tools/p2_kurage_death_transport_fixture.cpp::main`
  (verification entry; existing engine callsites identified, none changed).
- Build membership: the fixture TU (verification scope; unity-compiled
  policy, no CMake change).
- Consumers: this lane's verification command (run fixture + reader; expect
  markers or an exact blocker). Downstream Kurage family admission pending
  (no live lane; recorded, not claimed).
- Deliverable: policy-level death/corpse + transport + re-entry proof with
  receipt markers, or an exact blocker.

## Gate outcomes (honest labels)

- Gates PASS only on genuinely observed evidence with an uninterrupted run.
  Policy-level observation cannot exercise engine actors, combat, haul
  physics, or reentry; nothing is inferred. Protected observation is labelled
  as such where it occurs and never proves captain damage.

## Not observed / not claimed

No engine world/arena boot, attacks, transports beyond the hauled corpse
receipt, timers, scoring, or retry semantics. No playability claim.

## Remaining scope (not this lane)

Engine-actor Kurage57 death in a real scenario boot; later Kurage content and
persistence. Downstream: Kurage family admission.
