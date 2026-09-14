# Dwarf Orange generated natural-run evidence (#461)

Integration review 2026-09-14, owner Codex through shared account 4laric. Source: issue461 comment5671006650 and `C:\Users\alari\pikmin-randomizer\output\qa-dwarf-orange\evidence-asg5fix.json`. Executable hash independently verified; native log inspected. This records historical runtime evidence on the exact tested pair, not a fresh run on the latest pin.

Root `87ad8e659a5434782377b50b5292baa4b2ddefff`, native `a2f4b9dccf53f2540fe505948ebe422544d7b442`. Executable SHA256 `d806dc936a115e4282430055be03f35c60d195ab7b90507440fee3da13b166c0`. Log `C:\Users\alari\pikmin-randomizer\output\qa-dwarf-orange\session-asg5fix\runs\d7c4f341c83b767f51b714936cb80e934743c66a4d5a4ddddd04e23993c33278\native.log`; log SHA256 `40cfe79224f03373399585f9dd17beb07248c2397ff63b0a3e96aa1f84e93faf`.

Candidate-run PASS: identity44 content staged66/66; BlueKochappy spawned; movement/animation and attack-state transition observed; native death at health0, corpse, ordinary Bestiary delivery check30 and both Dwarf Orange/Kochappy forget markers observed. Worker reports no injected health, damage, kill or state writes; squad deployment and captain positioning were staged interventions. This is natural engine behavior following staged setup, not full player-input sign-off. Attack-state entry alone is not an independent measurement of damage dealt to a target.

Cleanup removal PASS; combined cleanup/re-entry remains PARTIAL because revisit and process restart were not exercised. Initial generator0 then generator3670065 binding phases need review for duplicate/placeholder behavior; no duplicate actor claim is established by the two log phases alone. Source44 roster admission remains false. No whole-lane completion count changes.

Remaining: real scene revisit, process restart with reward deduplication, full player-input combat sign-off, binding-phase review and independent acceptance on the latest combined pin. Snow acceptance remains separate. The original evidence file is preserved unchanged.

## Process restart reviewed; full scene re-entry in progress

Integration inspected `output/qa-dwarf-orange/assignment4-restart-report.json` and `output/qa-dwarf-orange/restart-asg5fix3/{restart-session.json,evidence.json}`. The latter records normal exit in both runs, stable source44/generator3670065, native death/corpse in both runs, one durable delivery credit, and no repeated check on restart. This closes the historical process-restart/once-credit gate on the root87ad8e6/nativea2f4b9dc pair. It does not exercise same-process scene reconstruction or establish acceptance on native08bae251.

Integration owns the remaining scene-reentry run under #437 (comment5671210084). The replacement-main fixture uses real stage exit and section reconstruction, preserves natural combat and delivery, and requires exactly one registered/bound source44 actor and a preserved reward after reconstruction. Initial attempt under `output/qa-dwarf-orange/scene-reentry-08` exposed an early fixture deployment of only five Pikmin before START_READY; it is not acceptance evidence. The fixture now waits for all20 live starting Pikmin before deployment. Full player-input sign-off and Snow natural-chain acceptance remain open; neither identity is newly admitted by these reports.
