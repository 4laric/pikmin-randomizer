# Dwarf Orange generated natural-run evidence (#461)

Integration review 2026-09-14, owner Codex through shared account 4laric. Source: issue461 comment5671006650 and `C:\Users\alari\pikmin-randomizer\output\qa-dwarf-orange\evidence-asg5fix.json`. Executable hash independently verified; native log inspected. This records historical runtime evidence on the exact tested pair, not a fresh run on the latest pin.

Root `87ad8e659a5434782377b50b5292baa4b2ddefff`, native `a2f4b9dccf53f2540fe505948ebe422544d7b442`. Executable SHA256 `d806dc936a115e4282430055be03f35c60d195ab7b90507440fee3da13b166c0`. Log `C:\Users\alari\pikmin-randomizer\output\qa-dwarf-orange\session-asg5fix\runs\d7c4f341c83b767f51b714936cb80e934743c66a4d5a4ddddd04e23993c33278\native.log`; log SHA256 `40cfe79224f03373399585f9dd17beb07248c2397ff63b0a3e96aa1f84e93faf`.

Candidate-run PASS: identity44 content staged66/66; BlueKochappy spawned; movement/animation and attack-state transition observed; native death at health0, corpse, ordinary Bestiary delivery check30 and both Dwarf Orange/Kochappy forget markers observed. Worker reports no injected health, damage, kill or state writes; squad deployment and captain positioning were staged interventions. This is natural engine behavior following staged setup, not full player-input sign-off. Attack-state entry alone is not an independent measurement of damage dealt to a target.

Cleanup removal PASS; combined cleanup/re-entry remains PARTIAL because revisit and process restart were not exercised. Initial generator0 then generator3670065 binding phases need review for duplicate/placeholder behavior; no duplicate actor claim is established by the two log phases alone. Source44 roster admission remains false. No whole-lane completion count changes.

Remaining: real scene revisit, process restart with reward deduplication, full player-input combat sign-off, binding-phase review and independent acceptance on the latest combined pin. Snow acceptance remains separate. The original evidence file is preserved unchanged.

## Process restart reviewed; full scene re-entry in progress

Integration inspected `output/qa-dwarf-orange/assignment4-restart-report.json` and `output/qa-dwarf-orange/restart-asg5fix3/{restart-session.json,evidence.json}`. The latter records normal exit in both runs, stable source44/generator3670065, native death/corpse in both runs, one durable delivery credit, and no repeated check on restart. This closes the historical process-restart/once-credit gate on the root87ad8e6/nativea2f4b9dc pair. It does not exercise same-process scene reconstruction or establish acceptance on native08bae251.

Integration owns the remaining scene-reentry run under #437 (comment5671210084). The replacement-main fixture uses real stage exit and section reconstruction, preserves natural combat and delivery, and requires exactly one registered/bound source44 actor and a preserved reward after reconstruction. Initial attempt under `output/qa-dwarf-orange/scene-reentry-08` exposed an early fixture deployment of only five Pikmin before START_READY; it is not acceptance evidence. The fixture now waits for all20 live starting Pikmin before deployment. Full player-input sign-off and Snow natural-chain acceptance remain open; neither identity is newly admitted by these reports.

## Current-pin integration runtime, 2026-09-14

Fresh delivery run (`output/qa-dwarf-orange/scene-reentry-08-v3/evidence.json`, root6726551/native08bae251): native death and carrier engagement after explicitly staged free-squad positions; corpse moved approximately495 units, then stopped near closed waypoint92 (-28.403,-45.773,2263.781). No delivery. Route issue coordination: #440 comment5671388869.

Independent historical-checkpoint lifecycle run (`output/qa-dwarf-orange/scene-reentry-08-v4/evidence.json`, root43f3179/native08bae251): real exitStage, old registry cleared, scene generation advanced, existing earned delivery check preserved. FAIL: reconstructed stage1 reports Dwarf Orange generated dwarfs=0, and the exactly-one-rebound-actor assertion fails. This is not a fresh-delivery test. The original checkpoint was copied, fingerprint checked and source hash recorded; original evidence/session untouched. Fixture binary SHA73508ae4c651f5f34b19684f94907e6be707d644483945e893693ab38fcd353c. Runtime exited1, no surviving fixture process.

Integration next work is to trace restored generator identity/birth across scene reconstruction and resolve the closed carry route. These are separate blockers. Historical process restart remains passed on its recorded pin. Full natural-chain/current-pin acceptance and roster promotion remain blocked.

## Re-entry fixed and passed on native ae00c510

The original v4 run skipped production day-end cache persistence; v5 corrected that and still lost the P2 binding. Root cause: Generator::read/write saved catalog UIDs only with ENEMY_SLOTS, but P2-only sessions use ENEMY_P2 without that option. Native `ae00c510f7f1dca6c26f49c00a6f6f96e9e52fe2` extends both matching cache predicates to the P2 bridge. Export root `3e827571ad3f5e0ceddec2b9c3aa80a71162c513`. Native clean, production build PASS, Ninja dry run no work. Immutable production pin `output/p2-integration-ae00c510/pin.json`, executable SHA256 `071c06ab8961d60cb4997cc7c4703d42dbea43c90eb2d9960771aea82c620611`.

PASS evidence: `output/qa-dwarf-orange/scene-reentry-08-v7/evidence.json`. Root084098d/nativeae00c510; replacement fixture SHA256 `7ee66f3ff531425b9df958feeb313dc742f41587b795f5ff48ad0965ea023ff1`. Real cleanupDayEnd -> exitDayEnd -> exitStage -> softReset -> section reconstruction. Scene generation1->2, old registration cleared, exactly one registered and bound source44 actor, earned reward preserved, 20 surviving Pikmin in Onion storage, exit0. Initial live20 and centered960x540 fixture startup retained. Historical checkpoint copied with provenance; no fresh delivery claimed. This supersedes the missing-actor blocker. Runtime log/run46601628e06a719a533668356779fd1d553c04391a9071ec003016857142546d is recorded and hashed in evidence.

Remaining: fresh natural delivery through an opened ordinary route, deceased-actor re-entry on this pin, full player-input sign-off and Snow natural-chain acceptance. Gate92 free-squad work attempt is not a route pass. No roster admission change.
