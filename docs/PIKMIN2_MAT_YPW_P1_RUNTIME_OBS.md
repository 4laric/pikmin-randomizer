# ch_MAT_yellow_purple_white P1 runtime observation (issue #552)

Lane `p2-challenge-ch-mat-ypw-p1-runtime-obs`. Owner: Codex through shared
account `4laric`. Root-only tooling plus a supervised runtime run; no native
authorship (existing fixtures/runners reused read-only, never edited or
re-owned), no engine/family/shared edits, no ADMIT, no ledger writes. Issue
#552 stays OPEN.

## Stage facts (canonical baseline + hash-verified disc decode)

- `ch_MAT_yellow_purple_white`, 1 floor, 230.0 s within 700.0 s legacy,
  sprays 0 bitter / 2 spicy, `ui_index` 19, roster 30+15+15 = 60.
- Disc `user/Mukki/mapunits/caveinfo/ch_MAT_yellow_purple_white.txt`
  (1143 bytes, sha256
  `f6359e35e4fc27c5ef428ad3666cf419d2b93dc5a5877ba52fc8df0dc5ea94ae`):
  pool `1_MAT_tower2_toy.txt`, enemies `FminiHoudai_key`,
  `ElecBug_wadou_kaichin` x2 rows, `GasHiba`; treasures `kumakibori`,
  `bell_blue`, `yoyo_red`, `diamond_blue`; 0 gates; caps `TamagoMushi`, `Egg`.

## Provider contract (this lane)

`experimental/pikmin2_mat_ypw_p1_runtime_obs.py`:

- Reuses the done P1 content lane read-only (manifest validation +
  run-layout staging verbatim; P0 adapter loaded by path, never forked).
- `render_sidecar` emits strict `P2_CHALLENGE_CONTENT_1` from the real
  decoded tokens (row counts, never observed instances) plus
  `render_generate_manifest` with matching spawn intents; malformed input
  fails closed.
- `stage_fresh_run` writes the P1 layout + sidecar + manifest + run config
  into a fresh run dir with SHA-256 records; refuses non-fresh dirs.
- `read_run_log` parses runtime marker logs with a strict verdict (all
  required markers present, no fail/captain-down/duplicate tokens, no
  injected markers); `guard_record` hashes canonical
  `scripts/p2_fixture_captain_guard.h` read-only and fails closed on drift
  (pinned `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`;
  absent from this lane pinned root base, recorded as a pin gap).

## Runtime evidence

Recorded in `output/workflow/autofill/planning-shards/challenge-1/prepared/mat-ypw-obs-output/`:
leased private `pikmin_pc` build (exe hash + `ninja: no work to do.`),
private fixture link (provenance `built`), guard self/negative tests,
headed run log with ordered markers, and the run-result verdict. The
six-gate handoff below claims gates solely on observed evidence.

## Six-gate disposition

(To be recorded after the run: each gate PASS / FAIL / BLOCKED / UNTESTED /
source-backed N/A with the exact observed marker or the explicit reason.
No playability claim beyond observed evidence.)
