# Mar corpse-pellet pin audit (issue #799)

Lane mar-corpse-pellet-pin-fresh, generation 2. Diagnosis only: read-only
source mapping, no engine/file edits, no runtime, no ADMIT, no ledger writes.
Downstream consumer: mar-corpse-emission-native (#716, blocked gen3 rev6).
Machine-readable audit: experimental/pikmin2_mar_corpse_pellet_pin_audit.py.
All six runtime gates UNTESTED.

## Consumer evidence (read-only)

- out/consumer-verification-evidence.md sha256
  e04ae668153333c5206b9839ab99d6f8d0c97bc012a5930dc56b48996c8b081d:
  natural kill completes (P2_MAR_DEAD generator=375001, CORPSE_OBSERVED_DEAD)
  but corpse=0 at ticks 3600/4200; no EMITTED/RECEIPT_RESOLVED. Consumer check
  passed=false, prerequisite_resolved=false.
- Staged arena: .../mar-corpse-emission-native/out/consumer-run (Mar teki 16,
  Puffy Blowhog; Pod staged; scene P1 Impact Site).

## Death-to-pellet chain (file:line citations, canonical native tree)

- native/src/plugPikiNakata/tekibteki.cpp:622-637 BTeki::dieSoon: on
  TEKICORPSE_LeaveCorpse calls becomePellet(getTypeId(mTekiType),...).
- native/src/plugPikiKando/pelletMgr.cpp:165-172 PelletView::becomePellet
  calls pelletMgr->newPellet(id, this); null pellet when newPellet is null.
- pelletMgr.cpp:1546+ PelletMgr::newPellet looks up getConfig(pelletID);
  null config returns null (no pellet).
- pelletMgr.cpp:1733+ getConfig scans mConfigList, populated by readConfigs
  from the pelletsbin archive stream.
- native/src/plugPikiColin/gameSetup.cpp:101 maps archives/pelletsbin.dir to
  dataDir/archives/pelletsbin.arc.

## Missing pin (verified, not assumed)

- Staged pelletsbin .../consumer-run/assets/dataDir/archives/pelletsbin.dir
  sha256 198ce40fa08db94a8e0e88bebedb76d9f51bbaa57dcfc35e5c3d3789d468e16b
  contains EXACTLY 4 entries, all white pellets (white1..white4.bin) and zero
  enemy-corpse entries (adapter verdict absence-verified on the real tree).
- Therefore getConfig(marTypeId) cannot match and becomePellet binds nothing:
  the observed corpse=0 follows necessarily. No numeric id is invented: with
  zero non-white entries, every enemy teki type id fails lookup.

## Owner + first bounded executable staging slice

No live lane stages arena pellet data for this consumer (registry checked).
Owner: a NEW bounded staging lane. First slice owns exactly:
- experimental/pikmin2_mar_pellet_staging.py
- tests/test_pikmin2_mar_pellet_staging.py
- docs/PIKMIN2_MAR_PELLET_STAGING.md
Slice: author a Mar PelletConfig entry into the staged pelletsbin following the
white-entry byte format (read-only template), rebuild the .arc/.dir pair,
re-run the #716 consumer check; downstream mar-corpse-emission-native (#716).
Arena geometry/assets untouched. Higher authority (retail-data sourcing) stays
with the integrator if the authored entry is rejected.

## Method and safety

- Adapter audits pelletsbin.dir entry names plus run-log markers, failing
  closed on missing/malformed input. 7 focused tests green.
- Every citation above was read from the pinned sources; no callsites or ids
  invented. No runtime run (tooling pin-discovery); captain safety #632
  engages nothing.
