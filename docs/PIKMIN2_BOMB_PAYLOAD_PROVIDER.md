# Bomb payload actor provider (lane enemy-bomb-payload-provider, issue #577)

Provider slice for consumer #573 (BombOtakara93 family otakara-joint and
lifetime acceptance). No runtime claims: no gate1/3 closure until a live
fixture proves it. No ADMIT, no ledger writes.

## Reuse survey: why no second divergent Bomb

Inspected in the integrated native tree (read-only; nothing edited):

- P1 host teki roster (`src/plugPikiNakata/tekinakata.cpp` strategy
  table: Frog, Iwagen, Iwagon, Chappy, Swallow, Mizigen, Qurione, Palm,
  Collec, Kinoko, Shell, Napkid, Hollec, Pearl, Rocpe, Chappb, Swallob,
  Frow, Namazu, P2Demon, ...): NO Bomb type exists, so no host manager
  can birth EnemyID_Bomb today.
- Retail P2 `Game::Bomb` (`bomb.cpp`/`bombState.cpp`, `Bomb.h`) cannot run
  on the P1 engine (different Creature/AI/param/cell systems); porting it
  would be a divergent second Bomb, explicitly refused.
- `pc_p2_king_policy.h` `BombPlacement` is a labelled fixture-injection
  struct (`externalBlastTick`), not an actor.
- Lane-22 `pc_p2_bombotakara` carries a numeric `payloadId` stub
  (labelled) with policy-driven detonation.

Conclusion (document branch of reuse-or-document): this provider manages
payload LIFECYCLE records bound to host-verified carrier tokens. The host
births through its own manager and hands the pool the carrier token plus
the `otakara`-joint position; the engine-actor birth seam itself is a
documented follow-on requiring shared-owner review (see §5), not code
here.

## Host API (`native/pc_port/pc_p2_bomb_payload_actor.h`, engine-free)

Generational handles (`slot` + `generation`; generation 0 never issued):
`birth` (fails closed on exhaustion, duplicate live carrier, zero token,
non-finite joint, bad config), `isLive` (Carried only), `followJoint`
(carried only, finite positions), `onPayloadLost` (release without blast;
host kills the carrier per OtakaraBaseState bomb-carry guard),
`onCarrierDeath` (death-trigger detonation), `detonate` (exactly-once;
duplicates suppressed and counted), `hasBlast`/`lastBlast`/`clearBlast`
(query until reset/slot-reuse), `reset` (interruption/reset/re-entry:
retires every handle via epoch advance), plus `phase`/`carrierToken`/
`position` inspection and `activeCount`/`suppressedCount`/`blastCount`.

Detonation records ONE `P2BombSaraiBlastEvent` with pinned retail
defaults (radius 90 fp22, teki 500 fp01, navi/piki 10 fp24, half-height
50 fp02); carrier liveness for attribution resolves at blast time
through the host `P2BombSaraiCarrierFn` (source mCarrier==nullptr
fallback when unconfirmed). Routing stays host-side with the REAL
`p2_bombsarai_route_blast` — reused, never duplicated. The module prints
nothing: no fake log evidence is possible from it.

## Proof (not tokens/prints)

- `native/tools/p2_bomb_payload_actor_test.cpp`: standalone, compiles
  with `-Ipc_port` ONLY plus the shared blast TU, exit 0 with
  `PASS P2_BOMB_PAYLOAD_ACTOR checks=65`: birth/exhaustion/duplicate/
  zero/non-finite refusal; joint follow + rejection; stale-handle and
  recycled-generation after reset; payload-lost (no blast) vs
  carrier-death (detonates); duplicate-detonation suppression with
  exactly-once counting; invalid/forged-handle no-ops; REAL shared
  routing (Teki 500 self-attributed, Piki 10 carrier-attributed,
  out-of-volume excluded) and carrier-unconfirmed self fallback;
  trigger names.
- `tests/test_pikmin2_bomb_payload_provider.py`: 10 passed — contract
  shape, pinned defaults, canonical log agreement, double-detonation /
  missing-attach / unknown-trigger / injected-marker / empty-log
  refusals, suppressed-second-trigger and detach recording. The Python
  validator is consumer-log grammar only; the native test is the proof.

## Consumer contract (#573)

Stage the carrier through the real family generator chain, emit the
grammar in `experimental/pikmin2_bomb_payload_provider.py`
(BIRTH/ATTACH/DETACH/DETONATE/BLAST with the pinned damage fields), and
validate with `provider -- validate`. Any injected marker fails the
verdict. `provider_contract()` reports schema `p2-bomb-payload-actor/1`,
`runtime_claim: False`.

## Shared-hook request (NOT included; needs #169/#186 review)

Real engine-actor birth for EnemyID_Bomb payloads (teki birth path for a
Bomb type) plus any `CMakeLists.txt`, engine registry, `pc_main.cpp`,
generic lifecycle/receiver, or `pc_p2_bombsarai_*` change. This provider
deliberately stops at the lifecycle/policy boundary so integration can
wire it without a divergent Bomb.

## Commits and evidence

- Native branch: provider header/cpp/test (new, engine-free).
- Root branch: provider contract module, tests, this doc (new).
- Standalone test exe + full leased `pikmin_pc` build evidence under the
  lane output directory (hashes pinned at handoff).
