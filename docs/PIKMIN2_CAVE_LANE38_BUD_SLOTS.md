# Lane 38 handoff — cave Candypop bud slot class

Lane 38 / owner-session opencode deepseek-v4.1-flash / parent #468 + lane issue #477.
Slice: **BUD SLOTS** (seeded bud placement + N exposure + the never-behind-its-own-type constraint test).

## Concrete slot class / routine addressed; missing model piece

Fourth slot class of the frozen cave model: **seeded Candypop bud slots**. Before
this lane, `buds` existed only as schema rows in lane 34 (#473) with no place to
*place* them, no conversion count exposed to the logic consumer, and no
generation-time constraint check. Lane 38 adds:

- native `p2cavebud` placement policy: `validatePlacement` enforces the
  never-behind-its-own-type rule at generation time (the floor generator
  retries on a non-empty report, acceptance item 6), and
  `requirementSatisfied` exposes `N` as `colour OR (bud before segment AND
  pikmin_count >= N)`;
- root-side `experimental/pikmin2_cave_buds.py`: the same rule/model plus
  `from_floor_table`, an adapter that consumes lane 34's seeded table and
  re-checks it independently;
- the strict `P2_CAVE_BUD_1` sidecar contract so the seeded table can be fed to
  the native generator.

Not attempted (correctly out of scope): Candypop conversion/refund behavior
(lane 23) and Purple/White capabilities (lane 11).

## Root base/head; native base/head; dirty state; ordered commits

- Root base `fba8d5eb0767950f56486bd2738598eb99a4645d` on `deepseek/p2-l38`.
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` on
  `deepseek/p2-l38-native`.
- Ordered commits (both trees clean after each):
  1. native `9e8fa943fb273e0c8e21dc53137fdab9981f0722` — `lane38: cave
     candypop bud slot placement policy + one-consumer test (#477)` (adds
     `pc_port/pc_p2_cave_bud_policy.h`, `tools/test_p2_cave_bud_policy.cpp`,
     one-line CMake test-target hook).
  2. root `da7e8aa6` — `lane38: candypop bud slot model, lane-34 table
     adapter, N exposure (#477)` (`experimental/pikmin2_cave_buds.py`,
     `tests/test_pikmin2_cave_buds.py`).
  3. the handoff commit containing this file.
- Native working tree: `pc_port/pc_p2_cave_bud_policy.h` line endings normalise
  LF->CRLF on the next git touch (warning only, no content change).

## Owned files; generator hooks and provider/consumer agreements

Owned (new): native `pc_port/pc_p2_cave_bud_policy.h`,
`tools/test_p2_cave_bud_policy.cpp`; root
`experimental/pikmin2_cave_buds.py`, `tests/test_pikmin2_cave_buds.py`.

Shared-file hook (small, separately committed, labelled): `CMakeLists.txt` adds
`cave_bud_policy` to the existing `foreach(policy IN ITEMS …)` engine-free test
list. One consumer: `tools/test_p2_cave_bud_policy.cpp`. No engine header, no
generator routine (`gameCaveInfo`, unit/gate/item placement, `pc_p2_cave.*`),
and no lane-23/11 file was touched.

Provider/consumer agreements:
- **Provider (34):** `buds[] = {slot_id, index, segment, species, count}` and
  chokes as `{after_segment, before_segment, hazard}`. `from_floor_table`
  consumes exactly this shape; `HAZARD_SPECIES` (water->blue, elec->yellow,
  fire->red, poison->white) is mirrored locally because lane 34's module is not
  importable in every consumer worktree.
- **Consumer (39):** call `bud_key_available(segment, required_type, buds,
  pikmin_count, available_types=…)`; requirements must be in the same species
  space as the buds (translate a hazard with `HAZARD_SPECIES` first). `N` is
  read from the table, never hardcoded.
- **Consumer (35):** feed the seeded `P2_CAVE_BUD_1` table plus the floor gate
  bitmask (colour space 0 blue, 1 red, 2 yellow, 3 purple, 4 white) to
  `p2cavebud::validatePlacement`; a non-empty report means the floor must
  retry rather than ship a bud behind its own colour.

## What is already integrated; what is actually new

Integrated/reused: lane 34's schema, `derive_floor_table`, `table_digest`,
`HAZARD_SPECIES` and its forest_1 fixture; lane 23's `p2pom::IpTtlBudget` (=5)
is reused as the default `N`; lane 11's colour space (`speciesColour`) is the
bud/gate colour space.

New: the placement policy and constraint enforcement, the `N` exposure
predicate, the `P2_CAVE_BUD_1` sidecar, the lane-34 table adapter, and both
focused test suites.

## Build evidence line (native commit, exe SHA-256, ninja -n)

Recorded in `output/dsw/l38-build-evidence.txt` (last line):

```
2026-09-15T13:04:18 lane=l38 target=p2_cave_bud_policy_test native=9e8fa943fb273e0c8e21dc53137fdab9981f0722 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l38-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l38-build\p2_cave_bud_policy_test.exe sha256=b3153d7f2a5ef5b1f2dc50b47d4b892c31440d22cc6a5f6b269caa913d783b2d ninja_n="ninja: no work to do." seconds=0
```

Run with MinGW on PATH (`C:\msys64\mingw64\bin`):

```
PASS P2_CAVE_BUD_POLICY
```

No real-GL fixture was run: this is an engine-free policy test, not a runtime
scene (no `pc_p2_cave.*`/`nectar.exe` change).

## Fixture/seed used; observed generation evidence with exact paths

Root tests use `tests/test_pikmin2_cave_buds.py` fixtures, including a literal
of the lane-34 table shape (`lane34_table`) with a water choke and a white/blue
bud. All 18 tests pass.

Cross-lane consumer evidence (private, uncommitted) generated by
`output/dsw/l38-out/bud_consumer_report.py`, which loads lane 34's real
`derive_floor_table` from `output/dsw/l34-root` and lane 38's adapter/sidecar:

- Seed `"1"`, `forest_1` floor 1, pool `1_units_cent3_tsuchi.txt`, 2 chokes
  (water after segment 0, elec after segment 1), seeded bud
  `(segment 0, white, N=5)`.
- `validate_buds` re-check: `[]` (no violation).
- `bud_key_available` at 5 Pikmin: `seg1:white == seg2:white == seg3:white ==
  true`, every other colour/segment `false`; with fewer than 5 Pikmin the white
  key is `false`.
- Re-run with the same seed: identical buds and identical digest.
- Output: `output/dsw/l38-out/bud_consumer_seed1.json`; digest
  `2fee25ff6fd0be8c283d6b04605c3119fd1876120dac92245a6c79102df0ebdf`.

This is **model-level, injected-seed** evidence: lane 34's derived table is
passed through lane 38's consumer. It is **not** a live cave generated by the
engine's own generator, and it is never reported as a generation PASS.

## Acceptance contract 1–6 results (injected vs natural)

1. **Generation invariant** — native policy proves placement + the
   never-behind-its-own-type constraint deterministically; the root adapter
   re-checks a lane-34 table. Structural/injected, **not** a live-generation
   claim (the PC port has no P2 cave generator yet — see limitations).
2. **Seed determinism** — PASS host-side: same seed -> same seeded buds and
   digest (`rerun_same_buds: true`, identical `rerun_digest`); seeds 1/2 differ
   in bud segment/colour, seeds 0/3/4/5 seed no bud.
3. **Re-roll invariance** — same-seed re-derivation reproduces the bud table
   and `requirements` (lane 34's test + lane 38 `rerun_same_buds`). Native
   re-entry persistence is **not** demonstrated; depends on lane 35.
4. **Reachability** — the constraint rule guarantees a seeded bud is never
   behind its own colour; `requirementSatisfied` refuses a bud at/after the
   gated segment. Ambient-vs-alcove enforcement stays lane 37.
5. **End-to-end loop** — not attempted; owned by lane 40.
6. **Failure handling** — `validatePlacement` returns violations for any table
   that seeds a bud behind its own colour (and for duplicates/bad N/out of
   range), so the generator retries. Native retry loop is lane 35; the
   predicate and report are demonstrated here.

Injected vs natural: native/root policy is natural deterministic logic; the
seed-1 consumer report and the lane-34 fixture are **injected fixtures**
(`generated: false` in the report's provenance), never a generation PASS.

## Re-roll / restart / cross-seed result (or named remaining dependency)

Cross-seed shown (seeds 0–5: only 1 and 2 seed a bud, at different
segments/colours). Same-seed host re-derivation is stable. Real engine
re-roll/restart is not run because no native cave generator/unit-selection
routine exists to hook (named dependency: lane 35's unit-pool partition and
phased trunk growth, then lane 40's end-to-end spike).

## Known limitations; next consumer; ONE exact reproduction command

Limitations: the PC port has **no P2 cave generator** (root and native engine
worktrees carry only the `pc_p2_cave.*` entry/checkpoint stub and lane 23's
sidecar Candypop actor); the P2 generator itself lives read-only in
`native/pikmin2-research` (`RandMapMgr`/`MapUnitGenerator`/`RandMapUnit`). The
native policy is therefore a placement/constraint routine ready to be called by
lane 35's generator, verified entry-to-entry in an engine-free test, not an
in-engine placement. Buds are single-colour Pikmin keys; the colour space and
`N` are fixed by lane 23/34. No multi-bud-per-segment support beyond the
duplicate rejection.

Next consumer: lane 39 (AP logic reads `bud_key_available`), then lane 35
(native generator calls `validatePlacement`).

Reproduction (from the root worktree):

```
py -3.12 -m pytest tests/test_pikmin2_cave_buds.py -q
```

## Subagent usage

Three subagents were delegated in one staggered batch per the brief:

1. `explore` **source audit** — used, with its central finding verified by me:
   the PC port has **no** P2 cave generator (`gameCaveInfo`/unit selection/item
   and gate placement absent; only the `pc_p2_cave` entry/checkpoint stub), and
   the nearest seam is lane 23's `P2_POM_1` sidecar. This re-scoped the lane
   from "hook the generator" to "add the placement policy the generator will
   call" and shaped the `P2_CAVE_BUD_1` contract. Corrected one implication:
   its candidate insertion into `pc_p2_pom.cpp` would cross lane 23's ownership,
   so I kept the policy in a new lane-38 file instead.
2. `explore` **candidate inventory** — used as-is; confirmed no prior
   bud-slot/choke/segment vocabulary and named lane 34's `buds[]`/`count` and
   lane 39's consumption as the provider/consumer contract.
3. `general` **tests/scaffold** — used, then extended. It produced a green
   14-test `experimental/pikmin2_cave_buds.py` + `tests/test_pikmin2_cave_buds.py`
   (correct, non-tautological violation/key cases, no lane path leaks). I added
   `HAZARD_SPECIES`, `from_floor_table` and 4 lane-34 adapter tests (14 -> 18)
   and did the native policy myself. Estimated saving ~30–40 min of read-heavy
   audit/test scaffolding; cost ~10 min reviewing the model for a parallel
   definition (fixed by making the adapter explicit).
