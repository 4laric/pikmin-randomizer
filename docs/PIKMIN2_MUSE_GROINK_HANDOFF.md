# MiniHoudai78 correlated natural generated birth — lane muse-groink handoff (l60, #500)

Implementation owner: Codex through shared GitHub account `4laric`. Executing
contributor: Muse Spark 1.3 through OpenCode
(`opencode/muse-spark-1.3-contributor-free`), lane `muse-groink`.
Parent #198; wave #491; existing integration #437/#186. Attempt
`6f58cdebe6104a8598cb33464f9393e6`, ownership generation 1.

Scope: close gate 1 for mobile MiniHoudai78 via an actual legal generated
encounter, including the projectile corridor/helper contract. Observer plus
negative tests; placement/packaging coordination. Pedestal FminiHoudai97 is
out of scope; existing Groink modules are untouched; legacy l21 is
claim-held and read-only (inspected, never edited). Accepted
movement/combat/death/reward/reentry evidence is preserved below as history,
not relabeled as a new combined run.

## Source audit (read-only research rev 632af93787b9c95b63f0c13be32b161375ce3a96)

- MiniHoudai=78: source role, spawnable, use_own_id, day_end_max 4,
  BDT_Normal, no child birth (`docs/PIKMIN2_ENEMY_ROSTER.json`). Mobile
  Gatling Groink; `MiniHoudai::Obj` is inherited by fixed and roaming
  groinks (`docs/PIKMIN2_CANNON_GROINK_AUDIT.md`).
- FminiHoudai=97: distinct source identity sharing the bank; no dedicated
  module yet. Not touched by this lane.
- Projectile corridor/helper contract: MiniHoudaiShotGun pool of up to 3
  shells, radius-10 swept sphere, gravity 20, `InteractBomb` to Navi/Pikmin
  and 100 to Teki, reclaimed by `doUpdateCommon`
  (`docs/PIKMIN2_CANNON_GROINK_AUDIT.md`). No spawnable helper birth exists,
  so the contract is the volley/sweep/strike marker chain, not a helper
  spawn.
- Gap: live bind markers `P2_GROINK_CARCASS_READY/BECOME generator=<g>`
  carry no source_id. Gate 1 needs the correlated triple on one generator:
  `P2_SEED_RESOLVE source_id=78 target=<uid>` +
  `P2_PLACEMENT_SLOT generator=<g> slot=<uid>` (same uid) +
  READY/BECOME on `<g>`, with `P2_GROINK_ATTACK_FIRE` plus a sweep/strike
  PASS as firing-variant support. Full analysis:
  `output/muse-wave/l60/findings.md`.

## New work (this lane, additive only)

Root branch `codex/muse-l60-groink` (base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`):

- `experimental/pikmin2_muse_groink.py` — pure observer: `correlated_birth`
  (resolve/slot/bind/corridor join), `pedestal_confusion` (97-claim
  rejection), `muse_contract` (headless fixture join), plus flip-safe
  helpers. No lane paths, no assets.
- `tests/test_pikmin2_muse_groink.py` — 12 tests, all passing:
  full-log PASS, resolve strip, slot-uid disagreement, Frog-only bind,
  READY-without-BECOME, corridor fire/sweep required, corridor-alone
  refusal, pedestal-97 rejection, muse-contract positive/negative.

Native branch `codex/muse-l60-groink-native` (base
`7b9ecaa668fd55332073446cdbdaf6424b209ea7`):

- `native/tools/p2_muse_groink_fixture.cpp` (new file only) — headless
  marker-contract fixture. Parses `p2-groink-teki.txt` with the REAL
  `p2groink::read`, joins `p2-placement-slots.txt` and
  `p2-muse-groink-resolve.txt` (fail-closed on source != 78, generator or
  slot disagreement), then drives a REAL `P2GroinkCarcass` become/step to
  `RequestBirth`. Emits `P2_MUSE_GROINK_*` markers; `PASS` exit 0 /
  `FAIL ... reason=<...>` exit 1. No family/placement/shared module is
  modified.

## Build evidence

- Private configure+build via the wave leased runner at native
  `7b9ecaa668fd55332073446cdbdaf6424b209ea7` (dirty:
  `?? tools/p2_muse_groink_fixture.cpp` only):
  `output/muse-wave/l60/build-1789515298629135900.log`, 616 targets,
  `bin/nectar.exe` sha256
  `f8da35687defacfa860af9ecbbd0451e2a7b47ba74d455ff81ef972b9a541d95`,
  `ninja -n` -> `ninja: no work to do.`
- Fixture (`scripts/build_pikmin2_fixture.py` from this worktree — the
  maintained copy predates #437 response-file expansion and rejects the
  current link line; same leased wrapper, same provenance schema;
  expected native head `7b9ecaa668fd55332073446cdbdaf6424b209ea7`,
  `provenance.json` status `built`) ->
  `output/msw/l60-fixture-02/fixture.exe` sha256
  `770a715603d12196bfdc186d597f6faf908e2445b4ec9e965568ba7d1d330859`.
- Headless runs (raw-byte logs, UTF-8):
  - `output/msw/l60-run-01/native.log` sha256
    `0b5070af361a9d340252550b56a815d7c10a7bd5bd85666d9711d0061e2324cd`
    (exit 0): SIDECAR/SLOT/RESOLVE/BIRTH_POLICY + `PASS
    MUSE_GROINK_CORRELATED`; root observer `muse_contract` =
    all-True (contract evidence, labeled injected/headless, never
    gameplay).
  - `output/msw/l60-run-02/native.log` (exit 1,
    `FAIL ... reason=slot_disagree`): slot-uid disagreement fails closed.
  - `output/msw/l60-run-03/native.log` (exit 1,
    `FAIL ... reason=resolve_source`): pedestal-97 resolve fails closed.
- Focused regression: `py -3.12 -m pytest
  tests/test_pikmin2_muse_groink.py -q` -> 12 passed.
- No real-GL runtime acceptance was attempted: no live generated encounter
  exists yet (see BLOCKED gate 1). Fixture window/squad adoption is N/A
  for this headless slice; no runtime PASS is claimed from it.

## Gate table

- Source ID: 78 `MiniHoudai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | output/muse-wave/l60/findings.md correlated-triple definition; output/msw/l60-run-01/native.log PASS MUSE_GROINK_CORRELATED (headless contract only); live encounter pending muse-placement l52 slot profile + native bind case 78 (#492) and muse-packaging l53 staged assets/session command (#493) | injected (contract); natural pending |
| 2. Autonomous movement and animation | PASS | output/dsw/l21-out/run-groink-live/native.log:1269,:1305,:1319,:1566 P2_GROINK_MOVE (position + source-FSM state + clip + phase; travel 0 -> 84.377 over 600 ticks) | natural (preserved l21 slice5; not a new run) |
| 3. Attacks and receivers | PASS | output/dsw/l21-out/run-groink-live/native.log:1313 P2_FROG_LAND radius=23.0 pikmin=3 behavior=source and :1314 P2_GROINK_TARGET_HIT health=30.0->20.0 state=22->33 alive=1->1 (and :1455 health=10.0->0.0 alive=1->0) | natural (preserved l21 slice5; not a new run) |
| 4. Death and corpse | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1277 P2_FROG_DEAD and :1279 P2_GROINK_CARCASS_BECOME (natural free-mode squad kill) | natural (preserved l21 slice4; not a new run) |
| 5. Actual transport and reward | PASS | output/dsw/l21-out/run-carcass-transport3/native.log:1378 P2_POD_RECEIPT id=corpse:groink:201001 value=2 new=1 pokos=2 seeds=0 | natural (preserved l21 slice4; not a new run) |
| 6. Cleanup and re-entry | PASS | output/dsw/l21-out/run-groink-reentry/native.log:1340 P2_GROINK_TEKI_FORGET bound=1 remaining=0 and :1345 P2_GROINK_TEKI_RESET bound_before=1 bound_after=0 and :1348 P2_GROINK_REENTRY stale_bound=0 rebound=1 | natural (preserved l21 slice6; not a new run) |

Gates 2-6 reuse the exact l21 citations already transcribed into the roster
ledger; this lane ran no new gameplay and advances none of them. No ADMIT
write; no allowlist change; deny-by-default tests untouched.

## Dependency record (exact)

- `muse-placement` (l52, #492): no `dependency-ready.json` yet. Needed:
  candidate legal-slot profile covering MiniHoudai78 (one defensible slot),
  and the narrow generated native binding path (`pc_p2_generated_placement`
  case 78 — today it handles 23/59-62 only; that file is l52-owned and was
  not touched here). Consumer contract: the same slot uid must appear in
  `P2_PLACEMENT_SLOT` and the seed `P2_SEED_RESOLVE source_id=78` target.
- `muse-packaging` (l53, #493): no `dependency-ready.json` yet. Needed:
  hash-verified MiniHoudai assets/sidecars staged for the candidate slot
  and a candidate-only generated-session command producing the natural
  encounter this observer validates.
- When both land, this lane will consume the reviewed candidate commits
  (cherry-pick with base/order recorded, own work preserved), stage the
  natural run, and update gate 1 with real `native.log:line` citations or
  an exact defect.

## Remaining work

Gate 1 natural closure on the live encounter; shell-corridor markers from
the same run (ATTACK_FIRE + sweep/strike) to complete the firing-variant
support; then a reviewable ADMISSION CANDIDATE handoff through the CLI.
