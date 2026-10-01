# Violet conversion diagnostics (#276)

Owner: Codex using shared 4laric account. This extends the Beasts floor2
runtime evidence from #263/#269, without changing conversion gameplay or saves.

`pc_p2_convert_violet` emits one diagnostic after allocating and starting the
replacement sprout and consuming the input Pikmin:

```
P2_VIOLET_WITNESS sequence=1 generator=62000 input=red
```

The input species is captured before consumption, including the native Purple
flag. Sequence numbers increase for the lifetime of the process. A missing
generator is reported as zero, and an unsupported input color as `unknown`;
neither is accepted by the Beasts fixture. Rejected inputs and failed sprout
allocation leave the conversion path before the emission site.

The runtime runner now requires ten witnesses numbered 1–10, split five each
between generators 62000 and 62001, with Red inputs. Witnesses must occur between
readiness and the ten-sprout observation, and each batch count must match its
preceding witnesses. Suppressed generation must contain no witnesses. The
validator can still read historical logs without witnesses when explicitly
called with its default compatibility behavior; the CLI always requires them.

These records are diagnostics, not durable Pikmin identities or authenticated
campaign events. They do not establish which original individual was consumed,
bind a session token, survive restart, or certify the later sprout's survival.
The existing fixture separately checks original deaths, sprout totals and final
plucked population. Native same-color slot refunds and the full P2 Pom state
machine remain outside this batch. The subsequent [#279 refund candidate](PIKMIN2_VIOLET_REFUND.md)
implements and exercises same-color slot accounting.

Native candidate: `2f1451ccceb124676350f24cd5e842b4f4335834`.
Private Release build completed; fixture provenance records no pending native
build work before and after linking. Executable SHA256:
`3afca7d275425caa395d9cd66baa394eefd267627788c2b9bb1350a88f54c726`.

Reproduce from the private root worktree, using its completed private build:

```powershell
python -m experimental.pikmin2_beasts_floor2_runtime --root ../.. --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --exe output/beasts276-final/linked/fixture.exe --output output/beasts276-repeat --global-purple-count 19
```

Repeat with population 20 for suppression. The population is a declared
generation snapshot, not an authoritative native storage count.

Validation: 37 tests and 77 subtests passed across the runtime, generation,
checkpoint reference, lifecycle reference and fixture builder suites. Coverage
includes missing/duplicate/reordered or malformed witnesses, wrong source/color,
phase placement and forbidden witnesses on suppressed floors.

Local native conversion evidence:
`output/beasts276-final/count19/649c26f3138c4cea89fd123f32db913f/acceptance.json`.
Ten ordered witnesses, two five-conversion batches, ten Reds and ten Purples,
zero cargo/Pokos, unchanged repairs and unchanged executable/input hashes.
Log SHA256: `a9a2e5f7c849abe4577e53115e2e2b11bf9c72a8fe176cd0234a1b86d0a4afa4`.

Suppression evidence:
`output/beasts276-final/count20/63db192b9bfb4db89bb6317967b8399d/acceptance.json`.
Passed with twenty Reds, zero flowers, sprouts or conversion witnesses, zero
cargo/Pokos and unchanged repairs/input hashes. Log SHA256:
`9b47d05bc407bfb7a6bb2449b871365cce17dc64552035c0f875e07d8bf9afee`.
