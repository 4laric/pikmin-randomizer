# Muse contributor 59: BombSarai58 correlated natural generated birth (l59, #499)

Implementation owner: Codex through shared GitHub account 4laric; executing
contributor Muse Spark 1.3 through OpenCode. Parent #244; wave #491.
Generation 2 (resume attempt `e957cdabf4314bd6a63e10ab7aeee341`); generation-1
observer work preserved and extended, never redone.
Root worktree `output/msw/l59-root` (`codex/muse-l59-bombsarai`);
native worktree `output/msw/native-l59` (`codex/muse-l59-bombsarai-native`).
Legacy lane-27 claim, family projectile/FSM, and shared placement files were
read-only except for the reviewed dependency cherry-picks listed below;
nothing else outside the four reserved files was touched. No ADMIT writes,
no allowlist edits.

## Scope delivered

Gate1 (`identity_spawn`) for source ID 58 closed through the actual
generated placement and source resolve: a live engine `GenObjectTeki::birth`
resolved source 58 on the accepted candidate slot uid through the seed
bridge, bound it through the reviewed muse-placement native path, and the
same generator drove the lane-27 carrier binding (READY/SUPPLY/Release plus
a natural squad kill). The additive observer
(`experimental/pikmin2_muse_bombsarai.py::validate_generated_birth`) reuses
the cherry-picked `experimental/pikmin2_muse_placement.observe_identity`
(never forked) and adds only the bind-generator/teki-vehicle cross-check.

## Reviewed dependency consumption (exact source order, zero conflicts)

Root branch `codex/muse-l59-bombsarai` (base `72a2c450`), oldest first:

1. `4ec1a475` — gen-1 observer + tests + handoff (#499, authored).
2. `ca3484c3` — cherry-pick `bd97334a` muse-placement candidate (#492).
3. `0ec57fca` — cherry-pick `3131b76d` muse-packaging staging (#493).
4. `553f75da` — cherry-pick `f82171d4` muse-packaging handoff (#493).
5. `04e2a06d` — gen-2 log-derived validation over the #492 contract (#499,
   authored; 8 new tests).

Ancestry was inspected first (`merge-base --is-ancestor` = absent for all
four); no commit was replayed and the broad wave was not merged.
Packaging has no native commit (root-only slice, per its dependency-ready
record), so only one native cherry-pick exists.

Native branch `codex/muse-l59-bombsarai-native` (base `7b9ecaa6`):

1. `63a87c10` — engine-free gate1 stub (#499, authored).
2. `795cdc8b` — cherry-pick `4765885b` placement bind path (#492).
3. `cb760b27` — gate1 probe v2 over real markers (#499, authored).

Dirty state: clean on both branches. No shared-hook edit was required:
the runtime used the production binary as-is; both fixture files stay
unwired (the placement fixture's shared-hook request is recorded in its
own header by l52).

## Files owned / interfaces touched (reserved only, plus dependencies)

- `experimental/pikmin2_muse_bombsarai.py` — new `validate_generated_birth`.
- `tests/test_pikmin2_muse_bombsarai.py` — 18 tests (10 gen-1 + 8 gen-2).
- `docs/PIKMIN2_MUSE_BOMBSARAI_HANDOFF.md` — this file.
- `native/tools/p2_muse_bombsarai_fixture.cpp` — contract v2 probe.

## Build evidence (leased runner, common queue)

- Configure+build: `output/muse-wave/l59/build-1789523096464364900.log`
  (sha256 `e2bfdcf904640b696a76a44a950b07cf23bd964ce1318ce4850bc670eff4c182`),
  native `795cdc8b`, clean, 616/616 linked, `ninja: no work to do.`.
- Final-head rebuild: `output/muse-wave/l59/build-1789523566253639500.log`
  (sha256 `17b035f4f8792dcba37bc0e135469110cee9aeb5891675fae7c30eb124917dac`),
  native `cb760b27`, clean, `ninja: no work to do.`.
- Executable `output/msw/native-l59-build/bin/nectar.exe` sha256
  `5ded849191a9d2e566d023610134191dbbf70a79ef608ef584a6667e5ad615dd`
  (identical across both builds; the v2 stub is unwired so the binary is
  bit-identical — the exact binary that produced the runtime log).
- Standalone contract probe (`-Wall -Wextra -Werror`):
  `contract=muse-bombsarai-gate1-v2 vehicle=11 failures=0`
  (`output/muse-wave/l59/gate1-probe.exe`).

## Fixture baseline adoption (fresh private arena, current overlay)

- Child issue / lane / owner: #499 / muse-bombsarai / Codex via 4laric.
- Root `04e2a06d` clean / overlay `scripts/preview_pikmin2_room.py`
  (`ensure_pikmin_squad`, reds=20 default); native `cb760b27` clean /
  worktree `output/msw/native-l59` / build `output/msw/native-l59-build`.
- Squad change present (20-red default squad in staged `default.gen`,
  verified live at `native.log:247`); window change present by ancestry
  (`pc_main.cpp` 960x540 + `pc_window_center`) and observed at
  `native.log:14`.
- Fresh arena: ISO `C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso`
  (the brief's `output/pikmin2-runtime` ISO path does not exist on this
  host) extracted to `output/muse-wave/l59/extract105`, converted to
  `output/muse-wave/l59/room105` (`render.mod` 73472 B, `room.mod` 80367 B,
  `treasure.mod` 22048 B, matching sibling-lane sizes), staged with the
  current overlay to run
  `output/muse-wave/l59/arena/92b1f898ecce42be8555481f28b33080` (20 red
  Pikmin records verified in `default.gen`, plus the appended Napkid
  vehicle record id 270001 type 11).
- Run command (private launch, MinGW on PATH):
  `nectar.exe --experimental-pikmin2-room --randomizer-seed seed58.txt`
  with `PIKMIN_P2_ROOM_WINDOW=960x540`, `SDL_AUDIODRIVER=dummy`,
  cwd = run dir; 120 s, killed after timeout; log
  `output/muse-wave/l59/arena/92b1f898ecce42be8555481f28b33080/native.log`
  (1268 lines, sha256
  `58a926ce3ec90fed420a291b0a7fd5c1fe59016b3643e306858c20cf05ff9e3f`).
- Window observed 960x540 windowed and centered (`native.log:14`); live
  starting squad red=20 (`native.log:247`); no extinction marker in the
  log; 6 PROBE lines hold squad=20 with nearest down to 0.101.
- Result: PASS for gate1 (correlated natural generated birth, see table).
  Staged-vs-observed birth position differs by ~40 u (staged (-90, 10),
  birth (-122.3, -22.9)); identity is unaffected — the full generator
  chain agrees — but the append-coordinate mapping is recorded as
  imprecise, not production evidence.

## Natural vs injected (honest method label)

Staged setup (injected): the Napkid vehicle record appended to the staged
`.gen`, its staged position, the three sidecars, and the candidate seed
bootstrap. Natural engine behavior under test: the `GenObjectTeki::birth`
itself, the seed-bridge resolve to source 58 on the accepted slot, the
`bound=1` placement bind, the carrier FSM (Wait/Supply/Release states on
the live actor), and the squad's engagement and kill (nearest 0.101,
DEAD). Gate1's PASS rests on the natural legs; the vehicle is a placement
carrier, not a P2-identity claim. A companion `P2_FUEFUKI_TEKI_DEAD` line
for the same generator (line 1001) is the known hardlane watcher (it does
not move the vehicle); bombsarai evidence is unaffected.

## Tests run

- `tests/test_pikmin2_muse_bombsarai.py` + `test_pikmin2_muse_placement.py`
  + `test_pikmin2_bombsarai_teki_log.py` → 56 passed.
- Observer on the real runtime log: `validate_generated_birth` →
  `correlated` (all six legs true; resolve/bind/placement uids all
  1787125272; generators both 270001).
- `scripts/check_p2_handoff_gates.py` on this file → exit 0.

## Six-gate evidence (Source ID: 58 BombSarai)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/muse-wave/l59/arena/92b1f898ecce42be8555481f28b33080/native.log:585 (P2_SEED_RESOLVE source_id=58 target=1787125272) native.log:586 (P2_GENERATED_PLACEMENT bound=1 generator=270001) native.log:722 (TEKI_READY) native.log:765 (TEKI_SUPPLY) | natural (live genteki birth through seed bridge + bind path; staged Napkid carrier record/sidecars labeled above) |
| 2. Autonomous movement and animation | PARTIAL (grounded vehicle; FSM Wait/Supply/Release on live actor, JOINT_FOLLOW travel_xz=0.193) | output/muse-wave/l59/arena/92b1f898ecce42be8555481f28b33080/native.log:783 native.log:936 | natural FSM states on injected-grounded vehicle (lane-27 seam, not relabeled) |
| 3. Attacks and receivers | UNTESTED (no BLAST in this run; lane-27 InteractBomb evidence read-only) | output/deepseek-wave/handoffs/l27.md | injected (not exercised here) |
| 4. Death and corpse | PARTIAL (natural squad kill DEAD at line 1000 after contact nearest=0.101; corpse receipt untested, no pod staged) | output/muse-wave/l59/arena/92b1f898ecce42be8555481f28b33080/native.log:1000 native.log:795 | natural kill; receipt untested |
| 5. Actual transport and reward | UNTESTED (no pod staged, no P2_POD_RECEIPT) | output/deepseek-wave/handoffs/l27.md | injected (carry stall documented in l27 handoff) |
| 6. Cleanup and re-entry | UNTESTED (single session) | output/deepseek-wave/handoffs/l27.md | injected (not exercised here) |

## Remaining work (named, out of scope)

- Gates 3/5/6 and the corpse-receipt half of gate 4 stay with the family
  seam (lane 27 / providers #408, #128); this lane does not take them over.
- No shared-hook request: production binary sufficed as-is.
