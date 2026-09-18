# PIKI_BIRTH_186_52_PACKET

Decision packet for the piki-birth challenge-setup fix (#741): exact per-file
diffs versus bases (or certified zero-diff with hashes), per-file SHA-256,
consumer ref, and review metadata for the #186 landing decision and the #52
campaign-contract coverage decision.

## Fix pins (read-only)

- Root 92fc594c329a7098e342a87da0a231046f73a0c8, native e1861e68bf4d19b51ae182be5228f471803b71d9 (base b805d9c626e4f4558c95aef7cac311a5d9a2068f).
- 4 of 5 files changed (gameCoreSection.cpp, objectMgr.cpp, pikiMgr.cpp,
  goalItem.cpp); newPikiGame.cpp certified zero-diff (base == head).
- POOL_EMPTY attribution (#721): pikiMgr->birth() null at
  goalItem.cpp:438 GoalItem::exitPiki during Onion; panic at
  system.cpp:1229.

## Decisions requested

- #186 landing: five fix files for the piki-birth challenge-setup path.
- #52 coverage: piki-birth challenge-setup path under the AP campaign contract.
- Consumer piki-birth-challenge-setup-fix (#741) records dep-2 progress only
  after both decisions land. Packet publication is scope validation, not
  acceptance. All six gates UNTESTED; no ADMIT; no gameplay claim.