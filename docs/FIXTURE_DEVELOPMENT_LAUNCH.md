Private Linux development fixtures can opt in to direct execution with the
generic launcher. The production-controller path remains the default for its
existing service callers.

```python
result = guarded.launch(exe, run, arguments, expected_markers, timeout=60,
                        canonical_root=root, session_root=session,
                        development_launch=True)
```

The generic CLI exposes the same explicit choice:

```sh
python3 scripts/run_pikmin2_fixture.py --development-launch \
  --exe /private/fixture --run-dir /checkout/output/session/run \
  --arg=--experimental-pikmin2-room --pass-marker 'YOUR REAL PASS MARKER'
```

The existing boot-asset, fresh-run and private-output checks remain. Linux still
inspects the actual ELF interpreter/dependency closure and executable hashes,
rejects loader overrides, records physical RAM availability against the 95%
ceiling, and uses the bounded owned-process supervisor. It preserves the 20-Pikmin
staging and 960x540 window requirement; it does not create a gameplay arena.

`development-execution.json` records the observed private run, executable,
helper source and capacity. `run-inputs.json` records the actual runtime closure
and `execution_mode: development`; the ordinary log/result records owned cleanup.
No controller proof is consulted or synthesized, and no admission, requested
source pin or compiled-source attestation is implied. Owners retain real source,
build and gameplay evidence in their issues. Missing dependencies, executable
drift, unavailable capacity or unsuccessful cleanup still fail the test.

Captain or other wrappers can expose their own `--development-launch` switch
and forward `development_launch=True`. Their production mode remains unchanged.
Use a new run directory after a fix and preserve the prior failure logs.
