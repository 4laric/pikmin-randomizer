# Orange and Snow roster admission (#438 / #440)

2026-09-14. Integration review and implementation owner: Codex through shared account 4laric. User authorized admitting both after completing a second-slot natural run.

The reviewed roster admits **44 BlueKochappy (Dwarf Orange)** and **45 YellowKochappy (Snow)**. All other identities retain their prior default-deny/candidate status. P2 mode remains opt-in. Snow uses P1 proxy behavior; Orange uses the opt-in KochappyBase FSM with the documented receiver scope. Neither entry claims complete P2 fidelity or full native campaign save acceptance.

## Placement and prerequisites

Use `docs/PIKMIN2_ADMITTED_PLACEMENT.json` with ordinary `p2_enemies=True` generation. It supplies two exact approved pairs:

| Source | Stage | Campaign slot | Source generator |
|---|---|---|---|
| Orange 44 | Forest of Hope, day 2 | 1849273021 | 0-29.gen@4189 |
| Snow 45 | Forest of Hope, day 2 | 2049888785 | 0-29.gen@3592 |

Both demonstrated corpse routes require opening the ordinary soft gate controlling waypoint92 through native Pikmin work. The profile notes preserve this prerequisite. No gate/route flags are forced by generation. Optional `accepted_slot_uids` restricts each profile to its reviewed pair, rather than extending evidence to every physically compatible slot. An explicit empty list denies all slots; omission preserves previous schema behavior.

Normal generation requires a placement document and verifies every admitted identity receives its own accepted target. Removing either slot fails closed. Existing non-P2 generation is unchanged. Both corpse deliveries retain the shared P1 Dwarf Bulborb bestiary check, as before; admission adds no new reward identity.

## Evidence reviewed

- Orange: `PIKMIN2_DWARF_ORANGE_ROUTE_ACCEPTANCE_440.md`, natural combat, six-carrier delivery, exactly-once check, deceased-actor reconstruction and fresh-process journal preservation on native ae00c510.
- Snow first slot: `PIKMIN2_SNOW_NATURAL_ROUTE_ACCEPTANCE_120.md`, same chain on native ae00c510, plus earlier family movement/receiver evidence at documented proxy scope.
- Snow second slot: `output/qa-snow-natural/second-slot-v1/evidence.json`, fresh run `1e1c06965fe8d1e6b225f01aaeabea07f9176d1f7f73ffaec955662fd17e090c`, exit0. Gate opened frame1060, death1113, visible Snow corpse, six native carriers, one Onion check, scene generation2 with zero registered/bound Snow and eight Pikmin stored. Log SHA-256 `fbab9a2412545da37b02155b99920e5aeb2542ff26e7dd69d43adcc90663fdd1`.
- Second-slot launch root `00132e9290fa7a51cadbaa23e95965b7ccc67991`; native `ae00c510f7f1dca6c26f49c00a6f6f96e9e52fe2` clean. Fixture source commit3b59973, executable SHA-256 `cf15d37035bfe994d57367420bb2a90e19287ce92f1106ec886a89699505302d`, verified build with no pending Ninja work. Root placement/test edits were made while this run completed; the executable/native inputs were unchanged.
- GL result `output/gl-lanes/run-1789427317829611900/result.json`. Fresh assets, 20 live reds, observed 960x540 centered window and active gameplay. Prior rejected DeepSeek fixture was not used.

Runtime setup staged captain/free-squad positions and invoked normal day-end lifecycle calls. It did not write enemy health/state, force attack or transport, inject a reward, or change gate flags. These are native natural-gameplay witnesses after staged setup, not full player-input sign-off. Historical candidate evidence remains labeled candidate; this document records the later integration admission decision.

## Validation

Focused roster, placement, evidence-ingestion, generation, candidate-session, generated-acceptance and seed-bridge suite: **163 passed, 17 subtests passed**. Coverage includes exact pair acceptance, malformed/empty approval rejection, ordinary generation for four seeds without candidate scope, round-trip manifest validation, deterministic layouts, lost-slot denial, and unchanged non-P2 generation.

## Combined admitted runtime

On root `11f1f095cb032e6de76f51ce1949e201b61b8c32` (clean) and the same clean native ae00c510, ordinary `randomizer.seed.generate` created both approved bindings with no candidate environment variables. All187 combined content entries verified and staged successfully. The ordinary `python -m randomizer run` launcher spawned one Snow and one Orange in the same stage.

Combined run `36a9fac863725ed896058d0e635c268e95aef3d679739219a743a1ffb4b9cc93`, exit0: native gate work, Snow death/corpse/carry/one delivery, then deceased-Snow scene reconstruction passed while Orange remained the live control. Log SHA-256 `e74e479c5c64097533d41da75f615ea17230f6e13f13c4e1db6453a2616ba053`. Evidence: `output/qa-snow-natural/admitted-combined-v1/evidence.json`; GL result `output/gl-lanes/run-1789427591177910500/result.json`.

Same-session restart `9c7d3b20e62218cb29e2fffa4404ae0a7f14622a95bc63bdfca4ec0219b32131`, exit0, no new delivery check, live Snow rebound1, stored35 after earned benefits. Log SHA-256 `058b662506e2afe08761717d90c23ecccc0a724e6e200bba969332aed9cc7e1f`. Evidence: `restart-evidence.json` and `restart-session.json` alongside the combined report; GL result `output/gl-lanes/run-1789427693221582000/result.json`. This restart emits `START_STAGE ... stored=20` instead of first-start `START_READY`; the fixture's live>=20 guard was satisfied before checkpoint teardown. The initial marker-only parser miss is preserved in `restart-marker-audit.json`; no runtime failure was suppressed.

CLI generation and validation also passed with no candidate overrides:

```powershell
py -3.12 -m randomizer generate --seed orange-snow-admitted-cli --p2-enemies --p2-placement docs/PIKMIN2_ADMITTED_PLACEMENT.json --output ../qa-snow-natural/admitted-combined-v1/cli-manifest.json
py -3.12 -m randomizer validate ../qa-snow-natural/admitted-combined-v1/cli-manifest.json
```

This validates the ordinary generation and launch paths using a replacement-main gameplay fixture. The fixture supplies the staged positions described above. Native production source was unchanged; no export or native-origin push was needed. Both GL lanes free; no lingering fixture/native process.
