# Converter integration #419

Implementation owner: Codex through shared account `4laric`. Maintained base:
`50332f9` on `codex/pikmin2-room-preview`. Candidate:
`codex/p2-converter-integration`. Shared root and native dirty work left untouched.

## Integrated scope

Pushed converter commits `22d9f93` and `0190fa7` (#405), the blocker/fan-out
reference docs (#404), and starting-squad overlay `a51b301`. Existing workflow
policy is retained; the batch runbook points to private builds. This is Python
conversion and documentation integration; no native build/export or gameplay pass.

The newer maintained normal converter rejects annihilated normal directions.
The worker base implicitly emitted zero vectors; transplanting #405 alone only
converted 3/10 Pelplant clips, with 46 rejected poses. Added the explicit
`transpose-adjugate-zero` normal policy and enabled it for Pelplant only. Strict
and existing cofactor behavior remain unchanged. Zero normals are an explicit
collapsed-geometry approximation, not verified source lighting. Maintained
skeletal bindings, determinant-sign handling, seam-aware normal generation and
deterministic manifests remain intact.

## Validation

Evidence directory: `output/p2-converter-integration-evidence/` in the original
workspace. Real extraction command, run twice with distinct output directories:

```powershell
py -3.12 -m experimental.pikmin2_flora_assets --iso C:/Users/alari/pikmin-randomizer/output/pikmin2-runtime/pikmin2-source-test.iso --source C:/Users/alari/pikmin-randomizer/native/pikmin2-research --output <fresh-output-directory> --pose-limit 6
```

`run1` captures the failed initial transplant. `run2` and `run3` are the
reconciled converter: 10/10 Pelplant clips, 60 Pelplant poses; all 675 files
(including deterministic manifests and 282 models) byte-identical between runs.
All 222 non-Pelplant models match run1. HikariKinoko remains unsupported.
Focused converter/flora/normal-policy/squad regressions: 36 passed, 3 skipped.
The new regression explicitly preserves cofactor rejection while testing zero
normal opt-in and ordinary nonsingular output.

## Pushed handoff inventory and remaining work

| Candidate | Disposition |
|---|---|
| `opencode/p2-converter-128` at `0190fa7` | Integrated with the explicit normal-policy reconciliation above |
| `codex/p2-skeletal-crossfade` at `1c8e5b4` | Already merged in maintained base through #417 |
| `opencode/p2-flora-397` at `8e7ad1b` | Separate downstream arena/lifecycle candidate; needs combined native rebind review and new bank hash binding before maintained runtime acceptance |
| `opencode/p2-lifecycle-397` at `9151e32` | Separate reusable replacement-main fixture; requires matching native lifecycle hooks and its own baseline adoption validation |
| `opencode/p2-mamuta-death-root` at `643d2c9` | Separate native patch series, candidate `da285dbf`; death/corpse integration needs native build and combined runtime review |
| `kimi/p2-bulblax-import` at `cc2ee2e` | Armor source-event slice and active unrelated root/native work; not folded into converter scope |
| `opencode/p2-batch5-bulblax` at `0ec7b81` | King death and behavior-clock gates; separate native reconciliation |
| `opencode/p2-bulblax-envmap` at `c8aa791` | Review against maintained Queen specular implementation already merged through #401 before adoption; worker describes older renderer assumptions |

The native small-centred-window candidate `1d5a242b` (historical root export
`541bfba`) exists in the family line but is absent from maintained engine base
`50332f9`. The required adoption guide explicitly requires checking this capability
in each lane executable. Importing the Python overlay does not update executables.
Window/native reconciliation remains distinct from this converter-only merge;
no claim that every active agent has adopted or run either fixture baseline.
