# P2 Challenge framework contract (#136)

Owner: Codex through shared account `4laric`. Lane
`p2-challenge-framework-contract` (tooling, generation 2). This is the
missing framework contract that challenge-0/1/2/3 planners consume; it
authorizes no runtime, gameplay, or ADMIT.

## Source anchors (all read-only, verified this slice)

- Stage table: `user/Matoba/challenge/stages.txt` (GPVE01 rev 0, 18875 bytes,
  30 stages, all version 4). KFes variant `user/Matoba/challenge/kfes-stages.txt`
  exists but is out of scope (not the retail default).
- Struct: `Game::ChallengeGame::StageData` (`native/pikmin2-research/.../ChallengeGame.h`);
  reader `vsStageData.cpp` (`StageData::read`); loader
  `vsGameSection.cpp:434` (`loadChallengeStageList`).
- Colors: `EPikiKind` Blue=0, Red=1, Yellow=2, Purple=3, White=4, Bulbmin=5,
  Carrot=6; happa Leaf=0, Bud=1, Flower=2 (`Piki.h`).
- Consumers: title spray/time display + `setDopeCount` (`vsGS_Title.cpp`),
  per-floor extensions (`vsGS_Game.cpp:72`), scoring/result
  (`vsGS_Result.cpp`), stage count (`vsGS_Title.cpp:74`).

## Machine-readable schema

`experimental/pikmin2_challenge_framework_contract.py`:

- `parse_stage_table(text)`: decodes the v4 table into 30 stage dicts
  (`cave_id`, `cave_path`, `floors`, 7x3 `roster`, `legacy_time`,
  bitter/spicy starts, `treasure_count_field`, `ui_index`, `floor_seconds`);
  fail-closed on version/count/truncation/trailing-data errors.
- `read_stage_table(iso_path)`: reads + hashes the table from a local disc.
- `cross_check_inventory(stages, inventory)`: reports drift vs
  `docs/PIKMIN2_CONTENT_INVENTORY.json` (never edits it). **Current result:
  0 mismatches across all 30 stages** - the inventory baseline is exact.
- `compute_score(pokos, time_left, pikmin_left)`: `pokos*10 + timeLeft +
  pikminLeft*10` (`CH_SCORE_POKO_MULTIPLIER/PIKMIN_MULTIPLIER = 10`).
- `framework_providers()` / `first_slice_spec()`: provider split and
  smallest-slice inputs below.

## Supported vs unsupported semantics

Supported by source (engine code exists): stage table decode; squad/spray
application points (`PikiContainer`, `setDopeCount`); countdown + per-floor
extensions; hole descent (`goNextFloor`, provider #129); scoring/highscore/
clear/perfect/pink-flower/unlock computation; separate 1P/2P highscore slots.

Unsupported (no port evidence - do not claim): 1P Challenge host mode
(stage select, squad spawn, timer HUD, result flow); 2P co-op simulation
(dual captains/camera; engine scene files exist, behavior unported);
per-stage completion predicate (key/treasure/exit rules;
`treasure_count_field` semantics unproven); unlock persistence wiring
(#132); KFes variant.

## Existing providers vs missing behavior (#129/#130/#131)

- Existing: cave generation/holes/seams (#129); enemy/family actors,
  receivers, parms, banks (#130/#131); day/save persistence incl. challenge
  flags/highscores (#132); treasure ledger (#140); per-stage caveinfo decode
  + closure, 30/30 P0 complete (challenge-0/1/2/3 planners).
- Missing (this contract enables, does not implement): the Challenge host
  mode, result screen, 2P simulation, and key-completion rules above.

## First implementation slice + ownership

`first_slice_spec()`: 1P single-floor timed stage with score - e.g.
`ch_MUKI_bombing` (1 floor, 255 s) or `ch_NARI_01kusachi` (1 floor, 180 s):
apply squad/sprays, enforce countdown + extension, descend/exit via #129,
end distinctly on timeout/extinction/give-up/captain-down, compute score per
`compute_score`. Owners: host mode = new framework lane (to dispatch);
generation/holes #129; actors #130/#131; saves/unlocks #132; treasure #140;
stage content = challenge-0/1/2/3 planners (P0 complete). Consumer
acceptance: squad/sprays/timers match the decoded entry exactly; distinct end
states observed; score reproduces on observed counts.

## Evidence

- `tests/test_pikmin2_challenge_framework_contract.py`: 7 passed (synthetic
  decode, malformed rejection, scoring, provider/slice shape, inventory
  agreement, live 30-stage decode + zero-mismatch cross-check).
- No runtime, no gameplay claims. Full content issue #136 stays OPEN.