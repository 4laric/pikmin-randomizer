# P2 Bulbmin leader/dependent contract (lane 11, #131)

Lane 11 of [PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md),
parent [#131](https://github.com/4laric/pikmin-randomizer/issues/131) (with
Purple #113/#393 and White #395). Implementation owner: Codex through the shared
`4laric` account; executing session: opencode
(`opencode-go/deepseek-v4.1-flash`), recorded separately per AGENTS.md.

Native candidate: branch `opencode/p2-lanes-1012` @ `8219bf17`, base
`f9e139d8`. Header-only contract, no engine behavior changed, no shared checkout
touched. Patch bundle: `native-candidates/lanes-1012/`.

## Why this slice

Purple (`pc_p2_purple*`) and White (`pc_p2_white*`, `pc_p2_white_poison*`)
already exist, and the white/poison/purple policy tests pass (26 passed). The
remaining five-species gap in this lane was Bulbmin: there was no module for its
leader/dependent ownership or cave-only lifecycle. `Piki.h` reserves species
`Bulbmin = 5`, which the current `pc_p2_species` adapter cannot represent.

## Source basis

`native/pikmin2-research` (US GPVE01 revision 0):

| Concern | Anchor |
|---|---|
| species id | `include/Game/Piki.h:54` `Bulbmin = 5` |
| mother Bulbmin | `include/Game/Entities/LeafChappy.h:7` "(Mother) Bulbmin (LeafChappy)" |
| dependent births | `LeafChappy.cpp:131–152` `birthChildren()`: 10 `pikiMgr->birth()`, `initArg.mLeader = this` |
| wild flag / model | `piki.cpp:155–156` `changeShape(Bulbmin)` + `FPFLAGS_IsWildBulbmin` |
| not a Pikmin | `piki.cpp:231,250–251,788–789`; `pikiMgr.cpp:134` `isTekiFollowAI()` |
| whistle recruitment | `interactPiki.cpp:178–179` resets `IsWildBulbmin` |
| elemental immunity | `interactPiki.cpp:347,453,511,543` (Denki/Fire/Bubble/Gas) |
| cave persistence | `pikiMgr.cpp:722–723,762` exit drops all; descend keeps only `isPikmin()` |

## Interface

`native/pc_port/pc_p2_bulbmin_policy.h` (header-only, no engine includes):

- `P2BulbminFlock` — shared scene ledger `bulbmin id -> {mother epoch, phase}`,
  wild/recruited counts, `releaseWild`, `applyTransition`.
- `P2BulbminLeader` — one per LeafChappy mother:
  - `birth(motherEpoch, id)` — source ten-dependent bound, no duplicates
  - `whistle(motherEpoch, id)` — wild -> recruited in place, `detachFromLeader`
  - `leaderDied(motherEpoch)` — releases only wild dependents
  - `cancel()` — teardown release
- `p2_bulbmin_hazard_immune()` — true in both phases.

## Invariants (enforced by the policy test)

1. One mother owns a dependent; a dependent is never born twice.
2. Recruitment converts one body in place; no duplication or destruction.
3. Mother death releases wild dependents; whistled team members keep their
   captain ownership and survive.
4. Floor descent keeps only whistled Bulbmin; cave exit removes them all.
5. Wild Bulbmin never count toward the Pikmin total.

## Evidence

```text
g++ -std=c++17 -Wall -Wextra -I pc_port tools/test_p2_bulbmin_policy.cpp -o test_p2_bulbmin_policy.exe
PASS P2_BULBMIN_POLICY
```

Native commit `14e8fb92`; executable SHA-256
`9818AF2F5B7CC06DE59504DAFE2571DC0CAF74EA34E1A7D5FFD6F40852A6361A`.
Policy/contract test (engine-double), not a live arena run.

## Companion slice: species hazard capability matrix

`native/pc_port/pc_p2_species_policy.h` (same branch) exposes the receiving
lane-10 capability table for Blue/Red/Yellow/Purple/White/Bulbmin plus the
species-only Purple impact and White poison attacks, source-anchored in
`interactPiki.cpp` (`Denki :347`, `Fire :453`, `Bubble :511`, `Gas :543`). See
[PIKMIN2_SPECIES_CAPABILITY_MATRIX.md](PIKMIN2_SPECIES_CAPABILITY_MATRIX.md).

## Engine bridge (lane 11)

Native commit `9f9d0783` (base `5a0cb4ee`), branch `opencode/p2-sub-bulbmin`,
worktree `output/native-sub-bulbmin`. This is the first module that calls the
`P2BulbminFlock` / `P2BulbminLeader` contract from engine code.

Owned files:

- `native/pc_port/pc_p2_bulbmin.h` — config struct/parser and the engine-free
  `P2BulbminBridge` core, plus the live `pc_p2_bulbmin_*` entrypoints.
- `native/pc_port/pc_p2_bulbmin.cpp` — the live bridge: config opt-in, Piki
  pointer→ledger id map, and the captain reassignment at whistle time.
- `native/tools/test_p2_bulbmin_bridge.cpp` — standalone parser/policy test.
- Additive: one source line in `CMakeLists.txt`, one include and one
  `pc_p2_bulbmin_setup()` call in `pc_port/pc_p2_preview.cpp`, and an
  epoch-qualified `P2BulbminFlock::remove` in `pc_p2_bulbmin_policy.h`.

Config, opt-in only (no file and no env value ⇒ inert no-op):

```text
P2_BULBMIN_1 <mother_epoch> <dependents>
```

`mother_epoch` is a nonzero decimal id for the LeafChappy instance; `dependents`
is bounded by the source ten. Read from `p2-bulbmin.txt`, or from
`PIKMIN_P2_BULBMIN` (a bare positive epoch is accepted as shorthand). Malformed
or missing configuration aborts, matching the other family bridges.

API: `pc_p2_bulbmin_setup/reset/forget`,
`pc_p2_bulbmin_birth(Piki*)`, `pc_p2_bulbmin_whistle(Piki*)`,
`pc_p2_bulbmin_birth_dependent(Creature*, const Vector3f&, float, int)`,
`pc_p2_bulbmin_transition(P2BulbminCaveTransition)`, and
`pc_p2_bulbmin_bind_captain_table(P2CaptainOwnershipTable*)`. Whistle hands the
recruited body to a bound captain table; with no table it still converts the
body in place.

Evidence:

```text
g++ -std=c++17 -Wall -Wextra -Werror -I pc_port tools/test_p2_bulbmin_bridge.cpp -o test_p2_bulbmin_bridge.exe
PASS P2_BULBMIN_BRIDGE
```

Private build `output/native-sub-bulbmin-build` (Ninja, Release, JAudio ON)
linked `[66/66] Linking CXX executable bin\nectar.exe`; `ninja -n pikmin_pc` →
`no work to do`; `nectar.exe` SHA-256
`853814608B4329FF39E003EEE1BA0A783545D895777B0796981F574008ED48A4`.

This is a build/engine-double gate plus the tested policy wiring. **No live
Bulbmin actor was spawned or observed.** `pc_p2_bulbmin_birth_dependent` compiles
against `pikiMgr->birth()` but has no caller: there is no Mother Bulbmin
(LeafChappy/KumaChappy) actor module in the port and no generator registration,
so the birth path and the `piki_kochappy` model binding stay blocked (see the
audit below).

## Family/asset blockers (audited)

- No `LeafChappy`/`KumaChappy` port module exists. `pc_p2_kochappy.*` is the
  Chappy family's *Kochappy* (Dwarf Red Bulborb) visual/stun bridge, not the
  Mother Bulbmin; the only `TEKI_Chappy` handling is in `pc_p2_preview.cpp:172`
  and the kochappy/kogane/snow/sheapgrub registration lists.
- No spawner/generator or `enemyInfo` registration path for a Mother Bulbmin;
  `pc_p2_bulbmin_birth_dependent` therefore has no caller.
- No live captain adapter: `pc_p2_captain_policy.h` is still header-only, so
  `pc_p2_bulbmin_bind_captain_table` has no table to bind at runtime.
- No `piki_kochappy` model binding; `pc_p2_make_bulbmin` writes colour only
  (`pc_p2_species.cpp:59-68`).

## Integration and remaining work

- Identity wiring landed on the same branch (commit `0a735f7e`): `Piki` and
  `PikiHeadItem` carry `mP2Bulbmin`, `pc_p2_species` recognizes it (rejecting a
  doubly-flagged Piki), `pc_p2_set_species` accepts species 5, and
  `pc_p2_make_bulbmin` / `pc_p2_is_bulbmin` are available. Build evidence:
  private `output/native-lanes-1012-build` (Ninja, Release, JAudio ON) linked
  `[520/520] bin/nectar.exe`; `ninja -n pikmin_pc` -> "no work to do";
  `nectar.exe` SHA-256 `7AB7305B6B36C35C4F34E53CCD110FCE391815488FC287797E5F44FFB4C99115`.
  This is a build/compile gate, not a runtime gate — nothing spawns Bulbmin
  yet.
- `pc_p2_cave.cpp` still accepts species 0-4. Carrying Bulbmin through a cave
  checkpoint needs a versioned schema bump (schema 3), not a widened schema 2,
  so old readers do not silently reinterpret IDs.
- The recruited dependent must be handed to the captain/ownership table
  (see [PIKMIN2_CAPTAIN_SQUAD_CONTRACT.md](PIKMIN2_CAPTAIN_SQUAD_CONTRACT.md))
  and the mother's bullet-lifecycle cleanup to lane 07.
- Live Mother Bulbmin actor registration, `piki_kochappy` model binding, birth
  and whistle hooks, and an arena run remain unscheduled family work (LeafChappy
  is a KumaChappy descendant).
