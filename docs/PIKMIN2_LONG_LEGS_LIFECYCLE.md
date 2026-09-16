# Long Legs natural encounter + death/corpse/cleanup/re-entry (#173 / #312)

Lane 26 bounded slice. Implementation owner: Codex via shared account `4laric`.
Executing session: DeepSeek (lane 26, private root worktree), 2026-09-14.

Follow-on to [PIKMIN2_LONG_LEGS_POLICY.md](PIKMIN2_LONG_LEGS_POLICY.md) (the
engine-free FSM) and [PIKMIN2_LONG_LEGS_HOST.md](PIKMIN2_LONG_LEGS_HOST.md) (the
round-trip host). This slice regenerates the family arena from the P2 disc and
runs the combined natural-encounter + lifecycle acceptance that the host slice
left open.

## Why this slice

The host mapped engine death -> `killed` and health decrease -> `damageTaken`,
and applied landing foot-crush as an `InteractFlick`, but its runtime smoke saw
`CRUSH=0` (the squad never stood inside the 60-unit foot radius) and reused a
stale arena because the `long-legs-family.json`/`.bmd` bank was not present.
The lane ledger's primary next action is *acceptance*: prove the source FSM's
landing/stomp attack reaches a live receiver, then carry a real death through
the policy death output, proxy corpse handoff and module cleanup/re-entry.

## What changed

### Native (`pc_port/pc_p2_long_legs.cpp`, additive only)

- `P2_LONG_LEGS_DAMAGE species=.. generator=.. health=.. prior=..` — an
  incremental, still-positive health decrease is live Pikmin attack damage,
  distinguished from a fixture-injected jump to zero.
- `P2_LONG_LEGS_DEAD species=.. generator=.. health=0 prior_health=..` — the
  death marker now carries `prior_health` so a naturally-fought death (health
  drained by combat) is distinguishable from injected `mHealth=0`.

No shared file (teki.h / tekibteki.cpp / tekimgr.cpp / CMake) changed: the host
was already registered and hooked. `pc_p2_long_legs_count()` /
`pc_p2_long_legs_registered()` / `pc_p2_long_legs_forget()` already existed.

### Root

- `experimental/pikmin2_long_legs_assets.py` — recovered the family asset
  extractor (was only on `codex/p2-longlegs-family`); decodes Houdai/BigFoot
  `model.szs` from the disc into `enemy.bmd` bind meshes + `long-legs-family.json`.
- `experimental/pikmin2_long_legs_lifecycle.py` — the combined acceptance
  harness: stages a fresh arena with BigFoot placed under the starting squad,
  converts the bind poses to `.mod`, builds a private replacement-main fixture,
  drives natural combat then (fallback, labelled) lethal injection, and
  validates the whole death -> corpse -> forget -> re-entry chain.
- `tests/test_pikmin2_long_legs_lifecycle.py` — 21 tests (synthetic-log validate
  contract + GL-free fixture-builder smoke).

## Behaviour staged

BigFoot (69, Raging Long Legs) is placed at `(-104, 30, 1816)`, the centre of
the 20-red overlay squad (`ensure_pikmin_squad` grid), so its wake radius (75)
and landing foot-crush radius (60) both cover the squad; Houdai (66, Man-at-Legs)
stays at `(120, 30, 1850)` so the gunless-no-press schedule runs without crush
interference. The fixture assigns the squad to attack BigFoot through the real
Pikmin Attack action, so `P2_LONG_LEGS_DAMAGE` is natural combat (the health is
drained by Pikmin, not written by the fixture).

## Six-gate status (natural vs injected labelled)

| Gate | Status | Evidence |
|---|---|---|
| 1. Exact identity and spawn | PASS | `P2_LONG_LEGS_BIND` for 312001/312002, `native_fsm=implemented`, exact spawn XYZ |
| 2. Autonomous movement and animation | PARTIAL (bind-pose) | FSM `Land/Wait/Flick(/Shot)` schedule observed; no IK translation or skeletal playback |
| 3. Attacks and receivers | natural | `P2_LONG_LEGS_DAMAGE` (real Pikmin attack damage) + `P2_LONG_LEGS_CRUSH pikmin>=1` (landing InteractFlick reaches live squad) |
| 4. Death and corpse | source intent PASS / proxy corpse | `P2_LONG_LEGS_BIRTH count=30` (BigFoot source death children) + `P2_LONG_LEGS_DEAD prior_health`; `P2_LL_CORPSE` pellet is the P1 Chappy proxy corpse, not a source carcass |
| 5. Actual transport and reward | UNTESTED | cargo-free arena; Mitite children (lane 14) and held-treasure drop (lane 06) are only logged as intents |
| 6. Cleanup and re-entry | PASS | `pc_p2_long_legs_forget` -> count 0; generator `init` + `pc_p2_long_legs_setup` -> fresh bound, stale gone, count 2 |

Injected lethal step (if natural combat does not close the kill in-window) is
explicitly labelled `P2_LL_INJECT .. not_natural_combat=1`; a natural BigFoot
death also records `P2_LL_NATURAL_DEATH bigfoot=1`.

## Remaining blockers

1. **IK body / foot positions** — the port has no IKSystemMgr, so Walk cannot
   move the body and the stomp is collapsed to a centre circle. (lane 08/09, #312)
2. **Actual Mitite births and held-treasure drop** — lane 14 / 06 objects; only
   policy intents are logged.
3. **Man-at-Legs shells** — `fireShell` is logged, not consumed; lane 20.
4. **Stuck-Pikmin damage rule** — host/collision side (US build: only a stuck
   Pikmin damages the body).

This is a natural-encounter + lifecycle acceptance increment, not whole-family
completion and not randomizer admission.
