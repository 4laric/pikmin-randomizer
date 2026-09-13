# Breadbug lane batch 2: install + arena (#220)

Follows batch 1 (#213, commit `fa025f5`). Implementation owner: Codex on shared
4laric. No native hook wiring was changed; the Giant/nest native display need
is flagged below and in issue #220. Parallel lanes (beetles #219, Mamuta #221)
were not touched.

## Install

New `experimental/pikmin2_breadbug_lane_install.py`:

- `prepare(lane_import, profile)` — stages hash-verified MODs from the
  `breadbug-lane-03` extraction: Breadbug wait/move sampled poses, Giant
  Breadbug wait/move **weighted** sampled poses (`lane_ootake_*.mod`), and the
  nest (`lane_nest_nest.mod`). Every staged model passes a structural MOD
  check (chunk walk, required chunks, nonzero geometry). The profile refuses
  any import where alias 39 or helper 83 is marked spawnable.
- `install(profile, run)` — copies into the private run's
  `assets/dataDir/courses/pikmin2room/`, refuses overwrites, re-reads and
  re-verifies every installed byte, and writes `breadbug-lane-install.json`
  with per-file SHA-256 and geometry counts.
- `verify_installation(run)` — re-verifies an existing install (tamper check).
- Reproducibility: two independent real private runs
  (`output/p2-lifecycle-batch/breadbug-lane-install-01/{a,b}`) installed 21
  files with identical manifests (`install-report.json`,
  profile SHA-256 `e32a67d9…c2061d`). The lane extractor now also emits a
  schema-1 `breadbugs.json` compatibility view so the established
  visual/cargo pipeline consumes lane imports directly; `breadbug-lane-03`
  `.mod` payloads are byte-identical to `breadbug-lane-01`.

## Arena gates (native runtime, frozen fixture executables)

Profile `breadbug-lane-visual-01` and bank `breadbug-lane-cargo-bank-01` were
regenerated from the lane-03 import. Assets: local P1 asset copy; original
practice map/collision/routes preserved byte-for-byte by the arena prepare.

| Gate | Fixture exe (SHA-256 prefix) | Result | Evidence |
|---|---|---|---|
| Spawn identity/XYZ + natural movement + reset | actor `3ab9be48…` | **PASS** — generator 186081, native type 8, birth (−150,30,1850), max displacement 289.5, 291 moving frames, post-reset draw decline | `breadbug-lane-actor-native-01/result.json` |
| Cargo grab/drag/nest approach/release | cargo `e79d7a45…` | **PASS** — grabbed, 196 held frames, 137.4 displacement, 95.8 nest progress, released, live visual | `breadbug-lane-cargo-native-01/result.json` |
| Cargo visual bank vs baseline + injected pause | cargo-anim `ad22547f…` | **PASS** — baseline and bank runs both complete; bank shows render states [5,6,8] (Back/Hide phases); 59 unchanged-counter pause checks | `breadbug-lane-cargo-animation-native-01/result.json` |
| Visual display wait/move/nest + disabled fallback | visual `d837eced…` | **PASS** — all four modes, PPM captures recorded | `breadbug-lane-visual-native-01` |

Scope labels unchanged: these are P1 Collec-proxy gameplay with P2 source
visuals; no P2 FSM/keyevent execution is claimed.

## Giant Breadbug / nest gate status

- Giant native arena gates (spawn, Purple-only press, boss flag, contest):
  **BLOCKED** — the native visual delegate (`native/pc_port/pc_p2_breadbug_visual.cpp`)
  is hardcoded to small wait/move/nest model names, and there is no Giant actor
  hook. Hook request flagged in issue #220; lane-side weighted models are staged
  and structurally verified (`lane_ootake_*.mod`) but not yet natively rendered.
- Nest linking, cargo contest arbitration, defeat and treasure recovery at P2
  semantics: covered at source-reference level by batch-1 tests
  (`tests/test_pikmin2_breadbug_lane.py`); native P2-FSM acceptance remains
  BLOCKED pending the same hook track. P1-proxy nest-approach and release are
  natively observed (cargo gate above).

## Tests

New `tests/test_pikmin2_breadbug_lane_install.py` (5 tests): MOD verifier
valid/truncated/trailing, synthetic install + double-install reproducibility +
verify, overwrite refusal, tamper detection, spawnable-helper rejection, and
real lane-03 install (Giant ≥6 poses, nest staged, reproducible, verified).
Extended `tests/test_pikmin2_breadbug_lane.py` extraction tests now also cover
the compatibility view via lane-03. Full suite result recorded in the issue
comment.

## Remaining open

- Native Giant display/actor hook (requested, native track owns wiring).
- Giant texture-matrix animation fidelity (currently static approximation).
- P2 FSM cargo/digest/recover port; day-save nest treasure persistence.
- Kimi fixed-bundle QA of the new installs.
