# Provider: Bomb::Mgr birth seam for EnemyID_Bomb payloads (#616)

Implementation owner: Codex through shared GitHub account `4laric`.
Executing worker: Muse Spark 1.3 (session `ses_f588f4eb3ffeo17sLakvD7MPiS`).
Consumer #573 (BombOtakara93 payload) is blocked on exactly this slice;
provider #577 (payload lifecycle API, done) explicitly excluded the birth seam.

## What was delivered

The SINGLE port Bomb::Mgr (`native/pc_port/pc_p2_bomb_mgr_birth.h/.cpp`), which
owns one #577 `P2BombPayloadPool` as its lifecycle engine and adds the birth
seam: carrier registration, natural birth of tracked Bomb entities
(source_id=36) bound to LIVE host carriers, joint follow, carrier-gone release
without blast, exactly-once detonation routed through the REAL
`p2_bombsarai_route_blast`, unregistered-ID rejection, reset/re-entry with
stale-handle retirement. Nothing duplicates the pool, the blast policy, or
lane-22's numeric payloadId stub (which this manager replaces with live
bomb-actor records).

## Source anchors (read-only decomp @632af937)

- `Game::Bomb::Mgr` is an `EnemyMgrBase` with `getEnemyTypeID() ==
  EnemyID_Bomb` (36) whose `birth()` delegates to the base manager birth
  (`src/plugProjectMorimuraU/bombMgr.cpp:10-35`; `include/Game/Entities/Bomb.h:82-85`).
- `Bomb::Obj::onInit` disables `EB_LeaveCarcass` (`bomb.cpp`): bombs leave no
  corpse and are never hauled ? gate 5 is source-backed N/A.
- Otakara capture/kill-carrier contract (`OtakaraBase.cpp:649-677`,
  `OtakaraBaseState.cpp:761-763,816-819,880-882`); payload delegation
  (`BombOtakara.cpp:42-87`); blast volume/attribution (`bombState.cpp:140-198`).

## Host facts (why a port manager, not a host TEKI type)

P1 `TEKI_TypeCount == 35` (`include/teki.h:139`): no `TEKI_Bomb` exists, so no
host manager can birth a Bomb body. The port Bomb::Mgr therefore births real
tracked Bomb entities bound to live host carrier actors at the otakara-joint
position (actor position as joint approximation ? documented adaptation).
Every `P2_BOMB_MGR_*` marker is printed from a production manager path.

## Prerequisite

#577 integrated by cherry-pick `d9ca3b08` as native `3aad911e`
(`pc_p2_bomb_payload_actor.h/.cpp`, `tools/p2_bomb_payload_actor_test.cpp`).
No payload-API code is reimplemented here.

## Files (exact ownership)

- `native/pc_port/pc_p2_bomb_mgr_birth.h` ? manager + host-seam declarations.
- `native/pc_port/pc_p2_bomb_mgr_birth.cpp` ? Section 1 engine-free core
  (always) + Section 2 host binding (excluded by
  `P2_BOMB_MGR_BIRTH_NO_HOST` for the standalone build).
- `native/tools/p2_bomb_mgr_birth_test.cpp` ? dual mode: standalone unit test
  (`-DP2_BOMB_MGR_BIRTH_UNITTEST`) and replacement-main live fixture.
- `experimental/pikmin2_bomb_mgr_birth_provider.py` ? marker validator.
- `tests/test_pikmin2_bomb_mgr_birth_provider.py` ? 15 hermetic tests.
- `docs/PIKMIN2_BOMB_MGR_BIRTH_PROVIDER.md` ? this file.

## Shared-hook contract (requested via #186, not edited here)

`tekibteki.cpp` `BTeki::update` block: add `pc_p2_bomb_mgr_birth_update(this);`
beside the other family updates. `pc_p2_teki_lifetime.cpp`: add
`pc_p2_bomb_mgr_birth_forget(actor);` to `pc_p2_forget_teki` and
`pc_p2_bomb_mgr_birth_reset();` to `pc_p2_reset_all_teki`. All three entries
are no-ops for unregistered actors. The replacement-main fixture drives the
same entry points directly, so the live run does not depend on this contract
landing first.

## Six-gate table (provider scope)

- Source ID: 36 `Bomb`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | fixture live log: `P2_BOMB_MGR_BIRTH ... source_id=36` | natural (manager birth on live carrier) |
| 2. Autonomous movement and animation | UNTESTED | joint follow observed; bombs do not self-move | natural (follow only) |
| 3. Attacks and receivers | UNTESTED | routing proven engine-free via real `p2_bombsarai_route_blast`; live hits are #573 scope | natural (standalone) |
| 4. Death and corpse | UNTESTED | carrier-gone release proven standalone; no live Bomb death | natural (standalone) |
| 5. Actual transport and reward | N/A (source: no carcass, detonation only) | `bomb.cpp` `Obj::onInit` disables `EB_LeaveCarcass` | natural (source-backed) |
| 6. Cleanup and re-entry | PASS (natural) | fixture live log: `RESET` + same-carrier `REBIRTH` | natural (manager re-entry) |

## Validation

- Standalone: `P2_BOMB_MGR_UNITTEST checks=49 failures=0` (birth, rejection,
  duplicate/exhaustion, follow, carrier-gone, exactly-once detonation +
  routing, reset/stale-handle retirement, rebirth, death-trigger attribution).
- Python: 15/15 hermetic marker tests.
- Live fixture: birth/follow/reset/rebirth with captain-guard adoption;
  evidence in the child issue with pinned commits, exe hash and provenance.
- Captain safety #632: fixture embeds the canonical 3-signal guard verbatim
  (scripts hash recorded in the handoff); captain parked out of blast reach;
  protected observation is labelled and claims no captain damage.

## Remaining work (consumer scope, not this provider)

Live blast-routing hits and BombOtakara93 end-to-end belong to #573 once it
consumes this seam. No ADMIT. Issue #616 stays OPEN until the seam is
integrated.
