# Hiba native integration (#437 / #447)

Owner: Codex through shared 4laric. Root baseline 6c231f1. Native c223f4424e27ab33beba408dd644362018789708, clean, based on ab7a900b. Imported f139d264 as fb9a813d, then corrected emission scanning/reporting in c223f442.

Integrated opt-in Hiba/GasHiba/ElecHiba sidecar module, pure Hiba/Dweevil policy headers, CMake/setup/update hooks and manager teardown resets. Missing sidecar stays inert. Existing Waterwraith dependency and Jellyfloat ownership hooks preserved.

Review corrections: scan during each emitting tick rather than only the first tick, and do not reserve out-of-range Pikmin in the per-attack handled set. This allows targets entering an active hazard later to be considered. Only mark a fire hit after stimulate returns true; rejected interactions can retry. This return value is interaction acceptance, not proof of a particular health delta.

Validation: 48 focused Hiba/elemental/receiver tests passed, 2 subtests passed; the Hiba C++ policy probe now runs against this native checkout instead of skipping. Exact 1734-file source export parity. Production build PASS; Ninja dry run: no work to do. All 33 native probes PASS. Executable SHA-256 C68C63ED57909FA05D7A4E989F9EF98DAA0897B3342DC427A3ABE9DC18C316CC. Private build output/p2-upstream433-build, Ninja Release/MinGW/JAudio ON, -j2. Logs output/p2-hiba-sweep-build.log and output/p2-hiba-sweep-tests.log.

No combined real-GL run. Previous worker f139d264 evidence does not prove the new late-entry/rejected-interaction behavior; repeat those scenarios with a fresh arena, current executable, live starting squad and centred 960x540 before runtime acceptance. Fire routes through the P1 receiver. Gas/electricity remain explicitly blocked. White/Bulbmin species routing, hazard models/effects, real actor binding, per-attack recycled-address identity and full scene/day re-entry remain open. This is opt-in diagnostic support, not ordinary enemy admission.

Next integration queue: shared lifecycle/receipt provider b737453 and engine-forget delta, then dependent native consumers. New animation/material bundle ce2391f and Long Legs 267e9af require current-line hook review. Seed validation/admission and staging-to-native asset connection still need the previously recorded fixes. Asset paths remain in PIKMIN2_NEXT_WAVE.md.

No upstream writes, native push or main merge.
