# Day-clock / save-anchor field audit for the save-progression provider (#132)

Lane `provider-save-dayclock-anchor-audit`, issue #132 (stays OPEN). Owner:
Codex through shared account 4laric. Read-only review: no runtime, no builds,
no shared edits, no ADMIT. All six runtime gates remain UNTESTED; no
playability is claimed.

This audit bounds the future day/surface + durable-save provider. It is an
inventory of retail anchors in the two research sources named by #132, or the
exact missing prerequisite. Values below are transcribed, never invented.

## Method

- Adapter: `experimental/pikmin2_save_dayclock_anchor_audit.py` (stdlib-only,
  line-indexed scanner; reuses the project adapter framing, no forked parser).
- Tests: `tests/test_pikmin2_save_dayclock_anchor_audit.py` (8 focused
  malformed/missing-input and boundary tests).
- Sources are read-only research text under
  `native/pikmin2-research/src/plugProjectKandoU/`:
  - `singleGameSection.cpp`
  - `gamePlayData.cpp`
- Machine inventory: `output/workflow/autofill/planning-shards/provider-save-progression/prepared/save-anchor-audit/out/inventory.json`.
  Verdict `complete`; gaps `['sprout_regeneration']` (expected-absent note);
  `unresolved_groups` empty; `claimed_absent_verbatim: true`.

## Verbatim file finding

The #132 anchor text names `gameSingleGameSection*.cpp`. No such file exists
in the research tree: the retail implementation is
`src/plugProjectKandoU/singleGameSection.cpp`. The audit records this absence
verbatim and does not invent the named file.

## Day-clock anchors

`singleGameSection.cpp`:

- `:216 section->advanceDayCount();` — cave day-end advances the day count.
- `:183 CaveDayEndState::init` / `:209 CaveDayEndState::exec` — cave day-end state.
- `:217 gameSystem->mTimeMgr->setStartTime();` — time manager reset on day start.
- `:388` / `:1050 gameSystem->mTimeMgr->mDayCount == 0` — day-1 gating.
- `:1183 disp.mIsNotDay1 = gameSystem->mTimeMgr->mDayCount;` — HUD day flag.
- `:1187` / `:1311 disp.mDataGame.mDayNum = gameSystem->mTimeMgr->mDayCount + 1;`.

## Sunset-loss anchors

`singleGameSection.cpp`:

- `:676 playData->mCaveSaveData.mTime = gameSystem->mTimeMgr->mCurrentTimeOfDay;`
  — cave entry captures the current time of day.
- `:686 gameSystem->mTimeMgr->setTime(playData->mCaveSaveData.mTime);` —
  restore on cave re-entry (the sunset-loss restore point).
- `:1188` / `:1312 disp.mDataGame.mSunGaugeRatio = gameSystem->mTimeMgr->getSunGaugeRatio();`
  — sun-gauge display anchors.

## Debt / equipment anchors

`gamePlayData.cpp`:

- `:257 isStoryFlag(STORY_DebtPaid) && !isStoryFlag(STORY_AllTreasuresCollected) && mZukanStat->completeAll()`
  — debt-paid completion condition.
- `:455 mDebtProgressFlags.clear();` / `:456 mBackupDebtProgressFlags.clear();`.
- `:460 getDebtProgressFlags(...) |= ...` — per-byte debt progress bit set.
- `:1336 f32 level = _aiConstants->mDebt.mData;` / `:1368` bit test — debt level.
- `:464 mPokoCount = 0;` / `:465 mCavePokoCount = 0;` / `:466 mPokoCountOld = 0;`
  and `:832 mPokoCount += pellet->mConfig->mParams.mMoney.mData;` —
  poko accumulation (equipment/treasure value).
- `:1543 mPokoCountOld = mPokoCount;` / `:1597 return mPokoCountOld;`.

`singleGameSection.cpp`:

- `:1077 disp.mSMenuMap.mDataMap.mPokos = _aiConstants->mDebt.mData - playData->mPokoCount;`.
- `:1098 disp.mSMenuPause.mDebtRemaining = _aiConstants->mDebt.mData - playData->mPokoCount;`
  and `:1099 mPokoCount`.
- `:1222 if (playData->isStoryFlag(STORY_DebtPaid)) { :1223 disp.mPayDebt = true;`.

## Louie / President anchors

`singleGameSection.cpp`:

- `:837 playData->mNaviLifeMax[NAVIID_Olimar] = ...->mMaxHealth;`
  and `:838 ... [NAVIID_Louie] = ...->mMaxHealth;` — max life saved.
- `:858 ... [NAVIID_Olimar] = naviMgr->getAt(NAVIID_Olimar)->mHealth;`
  and `:859 ... [NAVIID_Louie] = naviMgr->getAt(NAVIID_Louie)->mHealth;`.
- `:1236 disp.mLouieData.mActiveNaviID = FALSE;` / `:1239 ... = TRUE;`.

Note: `NAVIID_President` has no literal anchor in either named file; only
Olimar/Louie life anchors appear. Recorded, not invented.

## Save-migration anchors

`gamePlayData.cpp`:

- `:490 mCaveSaveData.clear();` / `:491 mMailSaveData.clear();` — save-data reset.
- `:705 mCaveSaveData.mCourseIdx = id;`.
- `:714 mCaveSaveData.mIsInCave = false;` / `:724 ... .mCurrentFloor = floor;`
  / `:725 ... .mIsInCave = true;`.
- `:723 mCaveSaveData.mCurrentCaveID.setID(caveID.getID());`.

`singleGameSection.cpp`:

- `:253 mCaveSaveCallback = new Delegate<Game::SingleGameSection>(this, saveCaveMore);`.
- `:660 void SingleGameSection::saveMainMapSituation(bool isSubmergedCastle)`.
- `:674 pikiMgr->caveSaveFormationPikmins(false);`.
- `:677 saveToGeneratorCache(mCurrentCourseInfo);`.
- `:740` / `:776 playData->setSaveFlag(STORYSAVE_Cave, nullptr);`.
- `:789 void SingleGameSection::saveCaveMore()`.

Related STORYSAVE variants (outside the two named files, recorded as context
only): `singleGS_FileSelect.cpp:137-185`, `singleGS_Ending.cpp:202,263,287`,
`singleGS_MainResult.cpp:97`, `singleGS_CaveResult.cpp:283`.

## Sprout-regeneration: exact anchor location (out of the two named files)

Neither named file contains a sprout/regeneration anchor (0 literal matches).
The retail anchor lives elsewhere in the research tree, e.g.:

- `src/plugProjectKandoU/onyonMgr.cpp:67-73` — `ItemPikihead::Item* newSprout`
  creation, `BirthMgr::inc`, `movie_begin`, `doEmit`.
- `src/plugProjectKandoU/itemPikihead.cpp:985-1000` — sprout head/colour/effect
  handling.

This is recorded as a note and a routing requirement, not as an invented
anchor inside the two audited files.

## Verdict

- Day-clock, sunset-loss, debt/equipment, Louie (Olimar/Louie) and
  save-migration anchors are inventoried with file:line citations in the two
  named files. The future day/surface + durable-save provider can be bounded
  from these anchors plus the existing cave-save-contract seam.
- Sprout-regeneration anchors are NOT in the two named files; the exact
  location (onyonMgr.cpp / itemPikihead.cpp) is recorded so a future slice
  can extend the audit rather than invent values.
- `gameSingleGameSection*.cpp` absence recorded verbatim.
- All six runtime gates UNTESTED; no build/runtime/ADMIT claim.
- Treasure ledger and floor generation remain with their shards. Shared
  findings go through #186 review, not silent edits.
