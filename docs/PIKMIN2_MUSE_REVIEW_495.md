# Independent review of Muse l55 / #495 — Sokkuri haul evidence and missing Onion receipt boundary

Review lane `muse-review-495` (child issue #514), generation 1, session
`opencode:ses_f57d77bb6ffekDlzMEjJu9W0Sk` (PID 19516, attempt
`35f324d76dc04c759af0bba9e46dd327`, matched before any edit).
Implementation owner: Codex through shared account `4laric`; executing
reviewer Muse Spark 1.3 Contributor. Private review root
`C:\Users\alari\pikmin-randomizer\output\msw\l69-root` at
`d684d47e1a35cfc6e65768a6d3b448041e9aaaae` (clean; this document is the
only owned file: `docs/PIKMIN2_MUSE_REVIEW_495.md`).
Producer sources were read-only throughout: no edits, builds, runtime
launches, merges, receipt/registry writes, or ADMIT grants.

## Producer identity pinned

- Root branch `codex/muse-l55-ground` (worktree
  `output/msw/l55-root`), base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`,
  ordered commits `50f6e89a`, `0fea5ec5`, `ea9ca230`
  (`ea9ca230b8750bac3be11ec5c164c610db3de988`), clean.
- Native branch `codex/muse-l55-ground-native` (worktree
  `output/msw/native-l55`), base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`,
  ordered commits `ecc80b72`, `7ab1262b`, `54e018f7`
  (`54e018f73a5935ac0ff2e9a030cbffa851f3b361`), clean.
- Registry `muse-ground` generation 3, revision 13, state `review_ready`
  via `finish` outcome `review-ready` (no CLI `handoff` submitted —
  `handoff: null`); progress evidence
  `output/muse-wave/l55/run-carry3/capture/native.log` sha256
  `5dd85ff8b9e9c32c411f3119ea091f30781efe2f863761ac81be34d8db380a29`.
- Docs handoff under review:
  `output/msw/l55-root/docs/PIKMIN2_MUSE_GROUND_HANDOFF.md` (slice 2,
  committed as `ea9ca230`).

## Evidence hashes — historical claims vs fresh checks

All hashes below were recomputed fresh by this reviewer (read-only
SHA-256 over producer files); every one matches the claimed value.

| Artifact | Claimed SHA-256 | Fresh check |
|---|---|---|
| `output/muse-wave/l55/run-carry3/capture/native.log` (1049 lines) | `5dd85ff8…d380a29` | MATCH |
| `output/muse-wave/l55/pytest-muse-ground2.log` (12 passed) | `2675629b…e02cf9c4b` | MATCH |
| `output/muse-wave/l55/pytest-muse-ground.log` (10 passed) | `1f9fb0ce…79ff400` | MATCH |
| `output/muse-wave/l55/build-1789515320859273900.log` | `5f2ca00a…481684` | MATCH |
| `output/muse-wave/l55/fixture-carry3/provenance.json` (`built` vs `54e018f7`) | `4de7ae2a…831b17a83` | MATCH |
| `output/muse-wave/l55/fixture-carry3/fixture.exe` | `e2468b5e…4edc135496` | MATCH |
| `output/muse-wave/l55/arena-carry2/6efb254a…/arena.json` | `46de181b…2bf5520b5e` | MATCH (prefix `46de181b945bc9ab`) |

Fresh behavioral re-verification (historical log, new analysis —
no new runtime, no provenance claimed):

- Fresh grep of run-carry3: `P2_SOKKURI_DELIVERY_BIND` log:776,
  `P2_SOKKURI_BIND` log:777, `P2_ENEMY_READY` log:778; seven
  `P2_SOKKURI_DAMAGE` rows 105.0→15.0 (log:797–847);
  `P2_SOKKURI_DEAD … prior_health=15.0` log:851;
  `P2_MUSE_GROUND_CORPSE pellet=1` log:862; zero
  `P2_ORDINARY_P2_RECEIPT`; zero `Extinction`; `Direct boot … 20 reds`
  log:235; `P2_MUSE_GROUND_READY squad=20` log:794; 960×540 centred
  window log:7. All match the handoff §slice-2 citations.
- Fresh validator rerun
  (`experimental.pikmin2_muse_ground.validate` over the historical
  run-carry3 text): `damage_hits=7`, `prior_health=15.0`, 54 carry
  observations (53 with `natural=1`), `max_natural_haul=573.55`,
  `transport_gate=untested`, reason "natural haul movement observed
  (max 573.5 units) but no ordinary onion:p2:79 receipt in log" —
  reproducing the handoff's `identity=1 damage=1 death=1 corpse=1
  receipt=0 carry=0 haul=573.5 transport=untested` exactly.
- Fresh replication check of run-carry2: 124 natural carry rows, max
  haul 564.39 units — consistent with the reported "~563 units".
- Fresh `scripts/check_p2_handoff_gates.py
  docs/PIKMIN2_MUSE_GROUND_HANDOFF.md` from the producer root: exit 0;
  gates 5/6 for both identities `UNTESTED` (ignored), gates 1–4 `PASS`
  preserved.

## Source-scope findings (all with file/line citations)

1. Delivery bridge is family-scoped, no shared files. Native diff
   `ecc80b72` touches only `pc_port/pc_p2_sokkuri.cpp` (adds
   `#include "pc_randomizer.h"` ~line 18, `pc_randomizer_p2_forget_source`
   in `pc_p2_sokkuri_forget` ~line 274, `pc_randomizer_p2_bind_source(…,
   79, …)` + `P2_SOKKURI_DELIVERY_BIND` print in `pc_p2_sokkuri_setup`
   ~lines 412–419) and creates `tools/p2_muse_ground_fixture.cpp`.
   Follow-ups `7ab1262b`/`54e018f7` touch only that fixture (preview
   include, `--experimental-pikmin2-room` entrypoint guard + 960×540
   centred-window block). Root diffs `50f6e89a`/`0fea5ec5`/`ea9ca230`
   touch only `experimental/pikmin2_muse_ground.py`,
   `tests/test_pikmin2_muse_ground.py` (12 tests:
   `test_natural_death_chain_without_receipt_is_untransported`,
   `test_receipt_without_carry_stays_interface_only`,
   `test_receipt_plus_carry_closes_transport`,
   `test_injected_log_never_passes_transport`,
   `test_large_prior_health_fails_small_prior`,
   `test_duplicate_grant_breaks_exactly_once`,
   `test_duplicate_new_zero_keeps_exactly_once`,
   `test_missing_delivery_bind_fails_identity`,
   `test_non_string_rejected`, `test_gate_summary_mentions_transport`,
   `test_haul_observation_without_receipt_stays_untested`,
   `test_small_haul_below_threshold_is_not_evidence`) and
   `docs/PIKMIN2_MUSE_GROUND_HANDOFF.md`. All within the 8 reserved
   files; `pc_p2_elecbug.*` untouched per brief ordering; no roster,
   admission, CMake, seed-default, or shared cargo change; no ADMIT
   writes. Proposed shared-file disposition: **none required — nothing
   outside ownership was modified**.
2. Missing-receipt boundary is correctly drawn, not a gap in the
   analysis. The handoff states gate 5 UNTESTED because the preview
   room runs without a randomizer session, so
   `pc_randomizer_p2_corpse_delivered` correctly returns false
   (handoff lines 75–77, 187, 222–228). The haul stall at ~573 units
   is reported as route exhaustion in a cargo-free (Onion-less) arena
   (handoff lines 71–73, 214–218), not a defect. Both carry runs
   exiting before the fixture terminal line with cause unestablished
   is recorded honestly (handoff lines 83–88, 229–233). No
   Transport/kill/credit injection exists in the fixture path these
   runs exercised.
3. Gate 1–4 citations are shorthand but resolvable. Rows of the form
   "docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2
   native.log:782" (handoff lines 183–186, 196–199) cite the lane-14
   handoff's embedded rows, which in turn reference
   `output/dsw/l14-out/natural-run2/…/capture/native.log:<line>` /
   `elecbug-run4a` equivalents. Fresh check: the lane-14 doc (772
   lines) contains `natural-run2` ×7, `elecbug-run4a` ×7 and the exact
   `native.log:<line>` refs 782, 801, 826, 904, 807, 820, 867, 1082.
   The lane-14 logs themselves are historical evidence cited
   read-only, not re-run or relabelled — acceptable, but the
   integrator should know gates 1–4 rest on lane-14 provenance, not on
   l55 runtime.
4. Minor presentation notes (non-blocking): the ordered-commits table
   (handoff lines 95–102) lists the third root row as "(this handoff)"
   without printing `ea9ca230` — the hash is confirmed via registry
   (`ea9ca230b8750bac3be11ec5c164c610db3de988`) and branch log; and
   "53 natural carry rows" vs the validator's "54 observations" is
   consistent (53 `natural=1` + 1 `natural=0` first row at tick 420),
   not a discrepancy.

## Review recommendation: REVISE-AND-CONTINUE (do not close gates)

- **Accept** the slice-2 natural-haul observation as honest, hash-bound
  carry evidence: 7-hit natural drain 105→15, combat-culminated death
  (`prior_health=15.0`), corpse pellet, and ~573-unit free-Pikmin haul
  with no injection markers and no extinction. The validator's
  honesty contract (receipt + carry required for transport PASS) held
  in the fresh rerun.
- **Do not** treat `transport_reward` or `cleanup_reentry` as closed
  for either identity. The producer likewise leaves them UNTESTED; no
  CLI handoff was submitted and none should be until the receipt
  slice lands. No ADMIT implication exists.
- **Do not** integrate anything on the basis of this docs handoff
  alone; there is no registry handoff object to accept (`handoff:
  null`) and no shared-file change to dispose.

## Exact remaining work for the existing integrator / producer

1. Exactly-once `onion:p2:79` receipt via the real ordinary Onion
   endpoint in a randomizer-enabled session (hauled Sokkuri corpse →
   `GoalItem::suckMe` → `pc_randomizer_p2_corpse_delivered` with the
   family bind from `ecc80b72`): capture `P2_ORDINARY_P2_RECEIPT …
   id=onion:p2:79:<n> … new=1` plus a duplicate-delivery `new=0`
   across restart, together with natural-carry markers in the same
   run, then submit the CLI handoff for gates 5. No new shared hook
   is expected unless that run exposes a real receiver/route defect
   (then a focused request to #491).
2. Full natural scene re-entry stays a lifetime-lane concern
   (#397/07); keep gate 6 UNTESTED — generator re-bind / fixture
   forget must not be presented as scene re-entry.
3. ElecBug28 delivery/re-entry only after the Sokkuri receipt slice
   (brief ordering); its modules remain untouched.
4. Diagnose or explicitly bound the early session exit (both carry
   runs ended before the fixture `observed>9000` terminal line with
   no extinction/FAIL marker) before relying on terminal-line PASS
   semantics in the next slice.

## Review provenance

- Review root commit: recorded at commit time on branch
  `codex/muse-l69-review-495` (base `d684d47e`); review path
  `docs/PIKMIN2_MUSE_REVIEW_495.md` with SHA-256 recorded in the
  finish evidence and issue #514 comment.
- Fresh checks performed by this review: hash recomputation of all
  seven artifacts above; marker/line grep of run-carry3; validator
  rerun; run-carry2 replication grep; arena.json hash; gate-checker
  rerun; `git show --stat`/log ancestry in both producer worktrees;
  registry `status` read. Historical evidence reused without
  re-execution: l55 builds, fixture runs, pytest runs, and all
  lane-14 gate 1–4 runtime.
