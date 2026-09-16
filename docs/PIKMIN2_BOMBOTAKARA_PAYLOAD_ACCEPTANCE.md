# BombOtakara93 payload provider seam (#573, parent #569)

Implementation owner: Codex through shared GitHub account 4laric; executing
contributor Muse Spark 1.3 (lane enemy-bombotakara93-payload, generation 2).
Prior #501 integrated work is historical context only; this slice adds the
family-owned provider adapter the #501 handoff named as remaining work.

## Scope and verdict

Bounded follow-on: replace the labeled actor-local payload stub with actual
owned Bomb payload birth/otakara-joint attachment lifecycle. Investigation
verdict, recorded honestly: **the provider birth API is absent from this
port**, so gates 1 and 3 stay BLOCKED with the exact artifact named. What
this slice delivers instead (all within reserved files):

- A family-owned provider contract + ownership machine (engine-free,
  strictly tested) that a future Bomb-manager provider plugs into.
- A runtime seam that logs the exact missing-artifact request and stays
  dormant otherwise: no stub relabeled, no fake birth/attach/blast.
- A bounded runtime fixture proving the seam wiring + honest BLOCKED exit.
- An independent acceptance observer that already adjudicates the future
  natural chain (and rejects stub/injection markers as natural today).

## Source anchors (read-only decomp `native/pikmin2-research`, rev 632af9378)

| Behavior | Anchor |
|---|---|
| `initBombOtakara` Bomb birth + otakara-joint capture + mCarrier | `OtakaraBase.cpp:649-677` |
| Carrier dies when payload pointer disappears | `OtakaraBaseState.cpp:761-763,816-819,880-882` |
| Blast volume + owner attribution (carrier vs bomb-self) | `bombState.cpp:159-190` (:167-172 fallback) |
| Delegated damage/earthquake | `BombOtakara.cpp:42-87` |
| stimulateBomb 1.5 s force delay | `OtakaraBase.cpp:699-707` |
| Payload is separate EnemyID_Bomb (36), not a spawnable | family audit |

## Provider gap (exact, verified in-tree)

- The P1-engine port compiles **no Bomb::Mgr and no Bomb enemy actor**;
  `generalEnemyMgr->getEnemyMgr(EnemyID_Bomb)->birth()` has no target.
- The only actor-birth seam, `BTeki::generateTeki(tekiType)`
  (`src/plugPikiNakata/tekibteki.cpp:1112`), births Teki-vehicle types via
  `tekiMgr->newTeki`, and **no TEKI_Bomb vehicle exists** (`include/teki.h`
  vehicle list). A Teki-vehicle "bomb" would be a proxy, which this slice
  refuses to build.
- Lane-20 `P2BombSaraiBomb`/`P2BombSaraiBombPool` is engine-free policy
  (no actor birth); the shared `p2_bombsarai_route_blast` primitive routes
  blasts but births nothing.

## Bounded provider request (for #169 projectiles / #186)

Contract `p2-bomb-payload-provider-1` (`pc_p2_bombotakara_policy.h`,
`p2bombotakara_provider` namespace). Required provider API with source
behavior in parentheses: `birthBomb(carrierGenerator)` (Bomb::Mgr birth +
init), `captureOnJoint(payload, carrier)` (startCapture + mCarrier),
`payloadAlive(payload)` (blast-time liveness), `forcePayloadBomb(payload)`
(1.5 s force path), `killCarrierOnPayloadLoss(payload)` (carrier-death
rule). Family-side `PayloadOwnership` machine enforces single live payload
per carrier, exactly-once detonation, stale-token (Gone) rejection, and
carrier-vs-bomb-self attribution. No shared-generic edits proposed; the
provider owns its manager/FSM, the family owns this adapter.

## Owned files (this slice only)

Native (`output/autofill-native-573`, branch `codex/autofill-native-573`):
- `pc_port/pc_p2_bombotakara_policy.h` — appended provider namespace.
- `pc_port/pc_p2_bombotakara.h` / `.cpp` — provider seam; stub flow untouched.
- `tools/p2_muse_bombotakara_fixture.cpp` — new provider-seam fixture.

Root (`output/autofill-root-573`, branch `codex/autofill-573`):
- `experimental/pikmin2_bombotakara_payload_acceptance.py` — observer CLI.
- `tests/test_pikmin2_bombotakara_payload_acceptance.py` — 10 tests.
- `docs/PIKMIN2_BOMBOTAKARA_PAYLOAD_ACCEPTANCE.md` — this file.

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_bombotakara_payload_acceptance.py -q`
  -> 10 passed (9 observer boundary cases + strict MinGW
  `-Wall -Wextra -Werror` compile-and-run of the ownership machine).
- Lane-22 otakara suites rerun to prove no family regression (see checkpoint
  evidence).

## Six-gate table (Source ID 93 `BombOtakara`)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | No Bomb::Mgr birth in port; seam logs `P2_BOMBOTAKARA_PROVIDER_REQUEST missing=no_bomb_mgr_birth` (run log, this slice) | natural (honest absence) |
| 2. Autonomous movement and animation | PASS (natural, prior) | lane-22 fix4 log (see #501 handoff, preserved) | natural |
| 3. Attacks and receivers | BLOCKED | Same provider gap; stub blast explicitly not counted (observer rejects unlinked BLAST) | natural (honest absence) |
| 4. Death and corpse | PASS (natural, prior) | lane-22 fix4 log (preserved) | natural |
| 5. Actual transport and reward | PASS (natural, prior) | lane-22 fix4 log (preserved) | natural |
| 6. Cleanup and re-entry | PASS (natural, prior) | lane-22 fix4 log (preserved) | natural |

No new runtime PASS is claimed. Prior PASS rows are preserved, not re-run.

## Bounded runtime record (this slice, honest BLOCKED)

Run `output/workflow/autofill/enemy-bombotakara93-payload/run-573/bombotakara573/c808437200ee4a689515723ffa9471d5/native.log`
(exit 0, 907 lines; fixture `fixture-build/fixture.exe` provenance `built`,
native `302106dd`, exe `cc4dc858`):

- :722 `P2_MUSE_BOMBOTAKARA573_BASELINE red=8 blue=0` — live starting squad.
- :723 `P2_MUSE_BOMBOTAKARA573_WINDOW width=960 height=540 centered_call=1`
  plus SDL `960x540` init — fixture-entrypoint baseline (replacement main
  does not run pc_main window setup; see fanout custom-fixture note).
- :725-726 census: exactly one Teki, generator 349005 type 3 — the staged
  family generator record born a real Chappy-vehicle actor.
- :727 `P2_MUSE_BOMBOTAKARA573_BIND_REFUSED ... reason=dynamic_bridge_59_62_only`
  — second exact blocker (`bind_dynamic` admits 59-62 only; #186 review).
- :729-730 `P2_BOMBOTAKARA_PROVIDER_REQUEST ... missing=no_bomb_mgr_birth`
  + `P2_BOMBOTAKARA_PROVIDER_ABSENT ... state=awaiting_birth` — first blocker.
- :733 squad holds red=8 (no extinction); :908 honest BLOCKED exit,
  requests=1 live_payloads=0. Zero stub/injection markers in all 907 lines.
- Earlier iteration lesson (recorded): the `iket` template births Teki, the
  `ikip` template births Pikmin — the first staging used ikip and censused
  nothing; the batch-2 actors-file path aborts without converted poses, so
  the dispatcher-mirrored dynamic bind is used instead.

The independent observer reports `VERDICT BLOCKED no_bomb_mgr_birth` on
this log (exit 2 by design), with gates 1/3 unlinked and zero
exactly-once/stale violations.

## Remaining work (proposed next bounded scope)

Port (or provider-wrap) the Bomb enemy manager + birth path under #169
with #186 review, then rerun the 573 fixture: the seam already observes
born/captured/detonated/released/gone provider events, and the observer
already adjudicates the full provider-linked chain. Family adapter needs
no further change for that run.
