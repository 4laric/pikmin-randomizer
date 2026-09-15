# Jellyfloat expansion (OniKurage + Kurage ingestion) and mixed-scene baseline

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407); Jellyfloat
[#243](https://github.com/4laric/pikmin-randomizer/issues/243). Three parallel
slices integrated into the species lane branch `opencode/p2-species-native`
(`8641da60`). Owner: Codex via shared `4laric`.

## OniKurage (Greater Spotted Jellyfloat, EnemyID 72)

Shared-base variant of the integrated Kurage slice; the Kurage FSM/policy is
reused and extended.

- New `pc_port/pc_p2_onikurage_fsm.h`, `pc_p2_onikurage_mouth.{h,cpp}`,
  `pc_p2_onikurage_teki.{h,cpp}`, `pc_p2_onikurage_teki_policy.h`; `tools/`
  docs (`P2_ONIKURAGE.md`) and tests.
- Adds the source `Drop` state (falling; finish when ground distance < 25,
  vertical velocity positive, or timer > 3 s; END → Dead/Land) and two mouth
  slots (Pikmin suction + captain capture via an `InteractSarai` policy
  approximation), with Flick/Bomb release decisions.
- Standalone: `p2_onikurage_fsm_test PASS checks=22`, `p2_onikurage_mouth_test
  checks=27`, teki-policy test PASS; shared Kurage tests unchanged (35+35).
- Runtime PASS: `output/onikurage-auto-runtime-01` — `P2_KURAGE_WINDOW … centered=1`,
  `red=20`, `P2_ONIKURAGE_TEKI_READY generator=201001 variant=Greater
  mouth_slots=2`, `P2_ONIKURAGE_AUTO_BIND_PASS` (log `7D3F38DD…CF7C47`).
- Open: live captain capture against a real `Navi`, OniKurage material fidelity,
  full Drop motion under the host clock beyond the bound actor.

## Kurage ingestion lifecycle (#243)

- New `pc_port/pc_p2_kurage_ingestion.h` — the full `PikiSuikomiState`
  lifecycle (admission → mouth → stomach → shrink → terminal), composing the
  existing digestion controller; `pc_p2_kurage_receiver.cpp` now owns it.
- Standalone PASS (admission, mouth/stomach capture, 16 s `mKurageKillTime`,
  bitter and health pauses, 0.5 s shrink, owner-death eject, cleanup).
- Runtime PASS: `output/kurage-ingestion-runtime-01` —
  `P2_KURAGE_INGESTION_PASS admit=1 mouth_travel=1 stomach_attach=1 kill_time=16
  shrink=0.5 bitter_pause=1 health_pause=1 owner_death_cleanup=1 shrink_death=1`
  and `PASS KURAGE_RUNTIME receiver_ingestion`; fixture
  `output/kurage-ingestion-fixture-01` (fixture SHA-256 `DDD813FB…02E133`),
  960×540 centred with `red=20`.
- Open: live captain release (OniKurage-only `flickStickNavi`), tube/string leg
  (Kurage-inapplicable), material/opacity.

## Mixed-scene baseline (fan-out requirement)

- Root harness `experimental/pikmin2_mixed_scene_behavior.py` + test stages
  **13 actors = 12 implemented species + 1 control** in one private run:
  ground (Armor, ElecBug, Imomushi, TamagoMushi, Sokkuri, Hana), flying (Mar,
  Hanachirashi) and aquatic (Catfish, Tadpole, Jigumo, UmiMushi).
- Run: `output/p2-mixed-scene/6086c9897a0e4325b94f4fed0653437f`
  (`mixed-scene-validation.json` `97583C3C…3017C`); exe
  `92F29D22…26AC87`; 960×540.
- Measurements: pose-bank bytes **4,883,616** (within a proposed 8 MiB);
  tracked texture peak **64 MiB** (at a proposed 64 MiB); **mean frame time
  33.45 ms**, slowest window mean 33.93 ms — **the proposed 60 fps (16.7 ms)
  budget is not met** at 12 species in this fixture room. This is a real,
  honest baseline for integration review, not a production FPS claim.
- Excluded: snagret (the mixed import path had no converted `snagret.json`
  poses) and the batch-2 visual-only families (no implemented source FSM).
- Proposed budgets (labelled `proposed_not_accepted`):
  `total_pose_bank_bytes_max ≤ 8 MiB`, `target_mean_frame_ms_max ≤ 16.7`,
  `slowest_window_mean_ms_max ≤ 20.0`, `tracked_texture_peak_mib_max ≤ 64`.

## Coordination

- These slices build on the shared Kurage host edits that modify
  `creature.cpp`/`piki.cpp`/`gameCoreSection.cpp`/`pc_window.*`, which still need
  focused #186 review before the maintained build/export.
- The mixed-scene frame-time result should set the density budget conversation
  with integration before scaling species counts.
