# Forest UI-stall pin audit verdict (#751)

Bounded read-only pin-discovery for the forest staged-rerun UI/loading-screen
stall (issue #751; unblocks forest P1 boundaries via #660/#149). Source: the
completed staged-rerun headed `native.log` (1546 lines) plus engine sources
(read-only). No runtime, build, manifest or ADMIT. All six gates UNTESTED.

## Verdict

The headed run settles on the **day-results screen**
(`ogScrResultMgr::RESULT_Active`) and waits there forever on **controller
input it never receives**.

## Evidence (log line numbers, staged-rerun native.log)

- Cinema chain plays through: `demo40` (line 603) -> `demo46` (748) ->
  `demo47` (757) -> `demo32` (768) -> `demo56` (773) -> `demo36` (813) ->
  `demo84` (line 826, last cinema). Per `src/plugPikiColin/moviePlayer.cpp`
  demo table, `demo84` is `DEMOID_EndOfDayRedOnyon` (:116); `demo36` is
  `DEMOID_EndOfDayResults` (:70).
- Terminal UI cluster, lines 837-970: black/account/results-screen layouts
  (`black`, `account2`, `tu_base`, `wait_char`, `ac_save`, `data_pf`,
  `save_x`, `data_b`, `data1/2/3`, `data1_n/2_n`, `data_t1/2`, `data_i`,
  `re_a_00` — all `screen/eng_blo/*.blo`, all DVD-open OK).
- Heartbeat-only tail, lines 971-1546: steady 30 fps render + stable textures,
  zero fixture boundary markers (only `P2_FOREST_P1_WINDOW` + bank
  bookkeeping lines exist; no gameplay markers, no `CAPTAIN_DOWN`).

## Wait condition (source file:line anchors, native repo)

`ogScrResultMgr::update` (`src/plugPikiOgawa/ogResult.cpp:555`) in
`RESULT_Active` (:615) calls `mSaveMgr->update(input)` (:623). It exits only
when the save manager returns 12/13/14/15 (:624-638) or, when the save status
is -1, on `input->keyClick(KBBTN_START | KBBTN_A | KBBTN_B)` (:639). The save
manager (`src/plugPikiOgawa/ogSave.cpp:148`) in turn waits on its
file-check/selection UI (`ogScrFileChkSelMgr::update`, :168) for a slot
selection (SelectionA/B/C) or ForceExit. The fixture sends no controller
input and the save path is unimplemented, so the screen never advances and the
render loop idles on the results UI.

The message-screen path (`ogScrMessageMgr::update`,
`src/plugPikiOgawa/ogMessage.cpp:602`, exiting at :649) is the same class of
input-gated wait. Movies are NOT the stall: the full cinema chain completed
(848-line span) and `MoviePlayer` went quiet after line 836.

## Owner for the fix (no engine change proposed here)

The staged-rerun fixture follow-on under #660: add controller-input injection
to the fixture (drive START/A or a save-slot select) so the results screen
advances to gameplay and boundary markers can be observed; else the #649
fixture owner if input injection belongs in the shared harness. An engine
behavior change (auto-advancing results) is explicitly NOT proposed. If input
injection is out of scope, record this verdict as the precise blocker.
