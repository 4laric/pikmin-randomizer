# Native Beasts survivor snapshots (#287)

Owner: Codex using shared 4laric account. The native Beasts fixture reports its
actual living party immediately before its final PASS: captain health divided
by maximum health, and each survivor's species and maturity. The fixture checks
finite living health, twenty survivors, valid maturity and no attached Pikmin.
The enclosing conversion/suppression checks already require zero sprouts.

```
P2_BEASTS_PARTY health=1 count=20
P2_BEASTS_SURVIVOR index=0 species=purple maturity=0
...
P2_BEASTS_PARTY_END
```

The host parser requires one complete ordered block after readiness and plucking
(when applicable) and before the final PASS. It rejects nonfinite/out-of-range
health, invalid species/maturity, missing/duplicate/out-of-order entries, stray
records, and population disagreement. The current runtime CLI requires this
snapshot; the old trace validator alone retains historical compatibility.

The checkpoint diagnostic bridge also requires the snapshot and returns it as
`party_snapshot`. A caller can pass its `squad` and `health` directly into the
reference adapter alongside the conversion events. This replaces the synthetic
outgoing health/maturity used by #283. The incoming party still comes from the
known engineering fixture setup. No individual identity, native boundary token
attestation, save-file transaction or actual cave-exit interaction is provided.

Native candidate: `eb627e9ebfa5721493ee03ba7c0e434ab2a66df0`, fixture-only change.
Linked from the completed private production build with no pending build work
before/after linking. No production native gameplay or shared save code changed.

Reproduce a fresh ordinary run with:

```powershell
python -m experimental.pikmin2_beasts_floor2_runtime --root ../.. --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --exe output/beasts287-final/linked/fixture.exe --output output/beasts287-repeat --global-purple-count 19
```

Add `--refund` for the mixed-input case; use population 20 without that switch
for the suppressed case. These remain scripted engineering fixtures. The
bridge reports `native_ready=false` and `native_handoff_authenticated=false`;
floor3 launch and full single-ledger campaign persistence remain unsupported.

Focused parser/bridge/runtime/generation/checkpoint/lifecycle and fixture-builder
validation passed 44 tests and 101 subtests.

Final executable SHA256:
`06ee99113a2cac73586f2f9319956fd5452b0229e0d551a55801861ee22707e9`.
All three native runs passed with full health, twenty leaf-stage survivors,
zero cargo/Pokos and unchanged repairs/input/executable hashes:

| Case | Run under `output/beasts287-final/` | Outgoing population | Log SHA256 |
|---|---|---|---|
| Ordinary | `ordinary/e3a9f121d26044b396b5d089d9208cff` | 10 Red, 10 Purple | `1c7ef316998ac5f7c2804e4c8f758e99bf1f82b139e7b4cda1f2856d9d3172b9` |
| Refund | `refund/4ecb25bc098b4cff9d5c8ead5be43e0f` | 9 Red, 11 Purple | `649a2f3b3e0b1ebe434d1defbbc39314a4f0f56f5a670cf02cf991a31b7a3857` |
| Suppressed | `suppressed/3226e41545954271b7085849e398d2ef` | 20 Red | `da14e6724f98035441b4030aafd72dfb89f1660cfa4c8e93b5d259523da4e1df` |

`output/beasts287-final/replay.json` records all three reference transitions and
exact replays using native outgoing snapshots. Ten, eleven and zero conversion
events respectively advance to reference floor3. The local replay script can
be rerun from the root worktree with
`Get-Content -Raw output/beasts287-final/replay.py | python -`.
No synthetic outgoing health or maturity is supplied. These fixture runs do not
exercise damaged captains or bud/flower maturity; parser tests cover preservation
of those valid field values.
