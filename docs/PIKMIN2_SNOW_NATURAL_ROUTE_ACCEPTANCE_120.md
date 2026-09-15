# Snow generated natural route acceptance (#120 / #437 / #440)

2026-09-14. Implementation owner: Codex through shared account 4laric; integration lead.

**PASS within staged-fixture scope:** native gate work, Snow combat/death, visible corpse, actual six-Pikmin carry, one Onion delivery check, deceased-actor scene reconstruction, and durable check preservation across a new process. Snow remains P1-proxy behavior. This is not full player-input or native campaign memory-card save acceptance. Product admission remains false.

## Recovery audit

DeepSeek left untracked recovery work in `output/p2-asg2-snow-natural` (base `43c4334`) and `output/p2-asg2-snow-natural-run1/evidence.json`. The latter explicitly reports `passed=false`, `death_corpse=false`. The new fixture's provenance is `rejected` (unsupported response file); capture.json identifies an older lifecycle executable. No natural completion was consumed from that attempt. Worker files remain untouched.

The old content manifest's import directory no longer exists. All 121 entries were recovered from the prior integration Snow smoke run's staged assets and verified against the original SHA-256 values. Only source paths changed in ignored `output/qa-snow-natural/content-recovered.json`; destinations, identity and hashes are unchanged. Fresh session assets were generated anew.

## Reproducible pin

- Root fixture commit: `3b59973df597cfa3b9964f6e8e6af67e91107900`, clean.
- Native: `ae00c510f7f1dca6c26f49c00a6f6f96e9e52fe2`, clean; no native production changes required.
- Source: `scripts/p2_generated_snow_route_fixture.cpp`, adapted from the passing Orange route fixture.
- Private build: `output/native-nectar-qol-build`; fixture: `output/p2-generated-snow-route-fixture-v1/fixture.exe`.
- SHA-256: `cf15d37035bfe994d57367420bb2a90e19287ce92f1106ec886a89699505302d`.
- Fixture provenance `status=built`; native dependency freshness reports `ninja: no work to do`.
- Prepared session: `output/qa-snow-natural/route-v1-fresh/prepared.json`; candidate source 45, target slot 1849273021, stage 1. GL-A specs live alongside it.
- Mandatory baseline observed in both runs: `P2_REENTRY_WINDOW size=960x540 centered_after_settings=1`, `START_READY stage=1 field_red=20`; active gameplay, no immediate extinction.

## Observed chain

Fresh run `355df5028dfda06f0ad1187e809b1aedd710fd518ebebcce69f940f4cfa28066`, exit 0:

```text
P2_ROUTE_GATE_OPEN waypoint=92 staged_squad=1 frame=1355
P2_ORD_DEATH frame=1413
P2_SNOW_DRAW corpse=1
P2_ORD_RESULT natural_carry=1 route=981.569
[Pikmin Randomizer] CHECK 30 Bestiary: Deliver Dwarf Bulborb
PASS P2_GENERATED_SCENE_REENTRY generation=2 old_generation=1 registered=0 bound=0 expected=0 live=0 stored=6 reward_preserved=1 resets=3
```

The log contains one delivery CHECK. Normal day-end cleanup, Onion storage, stage exit and scene reconstruction preserve the earned check and do not respawn the delivered actor before its rebirth interval.

Restart run `9c7af47ae9d1984ef57ae2d834068ee3de492cf128823b5898d7787d667f0490`, same session and executable, exit 0: no new delivery CHECK. Durable session journal contains one delivery. The fresh-process live-actor checkpoint then reconstructs one registered/bound Snow, with 20 Pikmin stored and the earned check preserved. This tests session journal recovery, not restoration of an unsaved field through a native memory-card save.

Evidence files:

- `output/qa-snow-natural/route-v1-fresh/evidence.json`
- `output/qa-snow-natural/route-v1-fresh/restart-evidence.json`
- `output/qa-snow-natural/route-v1-fresh/restart-session.json`
- GL results: `output/gl-lanes/run-1789426833361455200/result.json` and `output/gl-lanes/run-1789426933144026300/result.json`.

## Scope and next review

Staged interventions: starting squad, free-squad positions outside the gate work spheres, safe captain position, free squad around the exact bound Snow, free carriers beside its corpse, and normal day-end lifecycle calls. No enemy health/state writes, forced attack assignment, transport state, reward calls or waypoint flags. The gate opens through ordinary Pikmin work. Its opening is a placement prerequisite, not unconditional route approval.

Lane 04/33 can now review this candidate natural chain alongside Orange. Do not silently admit source 45, claim P2 FSM parity, or close the whole family issue. Independent review and broader player-input/campaign acceptance remain distinct. Both GL lanes were free and no fixture/native runtime remained after completion.
