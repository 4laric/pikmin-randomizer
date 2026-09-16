# Admitted nine-identity cohort QA (#530)

Lane `muse-admitted-cohort-qa`, worker `muse-l70`, issue #530.
Implementation owner: Codex through shared account 4laric; Muse contributor.
Session `ses_f57d7060bffeVi4xCtEhd8nM7q`, generation 2,
attempt `85c9bdd57d7e54d8f733a6b35a998f693b4eb71ef5e53464299e61919fee76f3`.
No nested agents; private worktrees only; no ADMIT writes; no allowlist changes.

## Pins (frozen species integration pin after #437)

- Root `C:\Users\alari\pikmin-randomizer\output\qa-root-530`
  at `e72f350ec89321b1b6d321739baa5fb44211614d` (clean) plus the QA commits
  listed below on `codex/throughput-qa-530`.
- Native `C:\Users\alari\pikmin-randomizer\output\qa-native-530`
  at `f05e3162daa83a03c861867ed3dbb942e3afd0b7` (clean, no commits).
- `qa-root-530/native` junction → `qa-native-530` (worktree convention; was
  missing, which failed 2 `NativeContractSyncTests` before any QA edits).
- Executable: exact-pin build `output/dsw/native-wave-build/bin/nectar.exe`,
  SHA-256 `bd662b7df09ae46e0362238f4f9a9f4b1273783cc238343bc3215837fb765d35`,
  build-evidence line `2026-09-15T23:39:39 lane=wave target=pikmin_pc
  native=f05e3162... dirty=no ... ninja: no work to do.` Reused read-only;
  production never modified, no rebuild in shared directories.

## Owned additive files (all new)

- `experimental/pikmin2_admitted_cohort_qa.py` — deterministic QA checker
  (seed manifests, determinism, denied exclusion, install targets,
  save/restart) with a JSON-report CLI.
- `tests/test_pikmin2_admitted_cohort_qa.py` — 12 engine-free tests.
- `docs/PIKMIN2_ADMITTED_COHORT_QA.md` — this report.

## Baseline unit sweep (frozen pin, fresh)

`test_pikmin2_admitted_placement.py`, `test_pikmin2_admission_contract.py`,
`test_pikmin2_admission_seed.py`, `test_pikmin2_enemy_roster.py`,
`test_pikmin2_roster_coverage.py`, `test_pikmin2_muse_placement.py`,
`test_pikmin2_muse_packaging.py`: **88 passed**. (2 placement native-sync
tests failed before the missing `native/` junction was restored; they pass
with the standard worktree layout. No source change was needed.)

## Engine-free QA (fresh, `qa-report.json`)

Representative seeds `qa-cohort-alpha/beta/gamma` against the committed
`docs/PIKMIN2_ADMITTED_PLACEMENT.json`:

| Check | Result |
|---|---|
| Roster admitted set == [23, 44, 54, 57, 59, 60, 61, 62, 78] | PASS |
| Manifest binds exactly the cohort (33 bindings, accepted slot uids, no foreign slots) | PASS x3 |
| Layout validates against admitted set; ENEMY_P2 bootstrap round-trips | PASS x3 |
| Same seed twice: identical bindings + fingerprint (alpha `27e37cfa…`) | PASS x3 |
| Manifest save→reload: byte-identical, same fingerprint, revalidates | PASS x3 |
| Tampered (foreign-source) copy rejected at load | PASS x3 |
| Duplicate binding target rejected | PASS (`invalid or duplicate P2 binding target: '5465461'`) |
| Enum mismatch rejected | PASS |
| Smuggled denied source (30/Queen, fresh target) rejected by admission gate | PASS (`P2 layout binds unadmitted source ids: [30]`) |
| Denied probes (30/41/53) have no lane-04 candidate targets | PASS (fail-closed membership) |
| Family install targets for 23/44/59/60/61/62 | PASS (sarai/dwarf_orange/dweevil) |
| Family install targets for 54/57/78 | **FAIL — concrete defect §D1** |

Evidence: `output/qa-530-run/qa-report.json`
(`cb9c053719f064fb98866caa401bdb3ecd32f899f790e982045292fc577abf46`),
session manifests under `output/qa-530-run/sessions/`.

## Bounded private startup (fresh, exact-pin exe, current fixture)

Staging `output/qa-530-run/stage_cohort_startup.py` (uncommitted runtime):
fresh arena via current `preview_pikmin2_room.prepare` (20-red overlay),
`bootstrap.txt` = real qa-cohort-alpha ENEMY_P2 line (33 admitted bindings),
run dir `output/qa-530-run/startup/abd29156b7d14ff084d595b9581fec2a`.
Launch: exact-pin exe, `--experimental-pikmin2-room --randomizer-seed
bootstrap.txt`, cwd = run dir, `PIKMIN_P2_ROOM_WINDOW=960x540`,
`SDL_AUDIODRIVER=dummy`, 90 s bound (timed out as expected for a live room;
no stray process remains).

`native.log` (809 lines, `305aba4a6505280a039301f7bb2457d692045ea7ee9c4b080b0d9f752bbc7a4c`):

- 960x540 centred window: PASS (lines 8, 14).
- Live starting squad: PASS (`P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20`,
  line 247); no extinction markers in 809 lines.
- Admitted bootstrap consumed without failure: the process lived the full
  window (a roster/version mismatch aborts immediately — see negative
  control). No per-identity birth markers: this arena carries no appended
  admitted generators and no family sidecars, so nothing bound had a spawn
  vehicle here. Startup/load scope only; NOT combat/birth acceptance.

Negative control: same staging with a zeroed roster revision
(`bootstrap-bad.txt`) exits fast with `[Pikmin Randomizer] incompatible P2
enemy roster or protocol version` (`native-bad.err`,
`b7627936848b28b950394da2580847536c14996e9fcdf5a24805bf646d9a4fe7`).
The bridge-only seed path is active at this pin and fails closed.

## Defect D1 (concrete, reproducible): admitted 54/57/78 have no family installer

`experimental/pikmin2_family_install.py::resolve_family` raises `ValueError:
no family installer` for admitted 54 (Miulin), 57 (Kurage), 78 (MiniHoudai).
The candidate-only muse-packaging sidecar path (`MUSE_CANDIDATE_IDS =
{41, 57, 58, 78}`) covers 57/78 as candidates but not 54 at all. Repro:

```
cd output/qa-root-530
py -m pytest tests/test_pikmin2_admitted_cohort_qa.py -q  # pins the gap
py -c "from experimental.pikmin2_family_install import resolve_family;
       resolve_family(54)"  # ValueError
```

Seed/load/save paths all pass, so this bites at content-staging time
(`install_layout`/`install_family`), not at seed time. Requested
disposition: species integrator either adds the three family installers
(or explicit candidate-sidecar coverage for 54) or records an accepted
limitation that 54/57/78 content cannot be staged yet. This QA's files do
not touch the installer; shared-review scope, never silently approved.

## Queen context (read-only, not duplicated)

- `output/muse-wave/l56/contributor-status.md` + `review-verdict.json`:
  Queen30 gate-5 transport verified as a natural mechanism with explicit
  carrier/reward/proxy caveats; no new GL rerun (candidate sidecar +
  shared-hook edits were out of that slice's scope).
- `output/deepseek-wave/handoffs/l24.md`: lane-24 Bulblax natural-combat
  slice (different identity, no overlap with this cohort QA).
- Source-30 carrier/reward approximation is explicitly not parity; cave
  item-5 QA belongs to muse-cave51 and was not duplicated here.

## Limitations (honest)

- Startup checks prove seed loading, window, squad and fail-closed
  behavior — not per-identity births, combat, death, transport or rewards.
- Runtime births for admitted IDs need per-identity vehicles/sidecars plus
  the D1 installer gap closed; not attempted here.
- Queen30 transport relies on #529's combined-candidate validation, not on
  this slice.

## Disposition requested

Engine-free cohort paths: PASS (evidence above). One concrete defect (D1)
for the species integrator. No ADMIT changes. Proposed: integrator resolves
D1 (installers or accepted limitation), then treats this QA as supporting
evidence for the admitted nine; no lane relaunch needed.
