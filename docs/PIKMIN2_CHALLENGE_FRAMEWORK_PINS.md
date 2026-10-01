# P2 challenge framework consumer pins (#136)

Implementation owner: Codex through shared account `4laric`. Lane
`challenge-0-framework-pin-discovery` (tooling only, no build/runtime/ADMIT).

## Finding

The framework contract lane committed schema + validator + tests on
`codex/prereq-p2-challenge-framework-contract` (`b9bb55f0`), but that commit
is **not an ancestor of any canonical checkout** (verified against
`codex/content-lanes-531` and `main`). However, the contract content itself
**was** integrated onto the content line at `fc5cbdeb` ("content(#531):
integrate p2-challenge framework contract (#136)") with byte-identical files
(all three sha256 verified), and the 7/7 contract tests pass at the consumer
pin. No new merge is needed for the content itself; consumers pin the
integration line below.

## Coherent consumer pins (verified this turn, never invented)

| Role | Pin | Branch | Evidence |
|---|---|---|---|
| Root consumer | `b08e3bdc2dfb758c0d48e4dab074081a0ee34246` | `codex/content-lanes-531` | 3 contract files byte-identical to `b9bb55f0`; `test_pikmin2_challenge_framework_contract.py` 7/7 green at this pin |
| Native consumer | `ab81cf5d0fa1856f46cc80b527b7e184afec97eb` | `claude/p2-deepseek-wave-native` | latest species-integration line; carries #129 cave-generate wiring + #642 guarded boot fixture tool |
| Framework commit | `b9bb55f0c52d1722a6c8cada958f2b1452a5ae99` | `codex/prereq-p2-challenge-framework-contract` | present on its branch + `codex/shard-challenge-2-contract-consumer`; not ancestral to consumer lines |
| Root fork point | `b5309fb6c402c067afc7f1817ef06365bcb822d6` | ? | merge-base of `content-lanes-531` and the prereq branch |

Contract file hashes at the root pin:

- `docs/PIKMIN2_CHALLENGE_FRAMEWORK_CONTRACT.md`
  `55ef70425c665c8a6e1e523707f40d1f61d5d58bc3d7329b64ccf6b41179f545`
- `experimental/pikmin2_challenge_framework_contract.py`
  `7236c25309287e822c67cd619c8fe652281c21aa2ab03f98f7a9b2e6efc93517`
- `tests/test_pikmin2_challenge_framework_contract.py`
  `714b4d5c1462ae6776176472e89e4b396e2fd7ffc56d7514561fbcc808499e62`

The contract is root-only (doc + experimental + tests; the framework lane
recorded native null), so native coherence means: a maintained integration
native base, no native component required.

## Downstream routing

- Ten challenge-0 P1 scopes pin this pair: `ch_NARI_01kusachi`,
  `ch_MUKI_king`, `ch_MAT_t_hunter_enemy`, `ch_MUKI_enemyzero`,
  `ch_MIYA_oopan`, `ch_MUKI_bombing`, `ch_MAT_t_hunter_otakara`,
  `ch_NARI_09suikomi`, `ch_MAT_route_rover`, `ch_MAT_crawler`.
- Host-mode dispatch via #570.
- Helpers: `experimental/pikmin2_challenge_framework_pins.py`
  (`check_coherent_pair`, `verify_contract_files`, branch/merge-base
  queries); tests: `tests/test_pikmin2_challenge_framework_pins.py`
  (11 green: pure-logic positive/negative + live immutable-git-fact checks).

No ADMIT. Final pin authority rests with the integrator; pins move only by
re-running the helpers and re-verifying hashes.
