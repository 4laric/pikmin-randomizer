# Native diagnostic to checkpoint reference bridge (#283)

Owner: Codex using shared 4laric account. `checkpoint_witnesses` in
`experimental/pikmin2_beasts_witness_bridge.py` consumes a complete native Beasts
fixture trace and readiness report together with an active reference floor2
checkpoint. It first runs the strict native evidence validator, then checks
generation population, selected flowers, conversion budgets and the incoming
fixture population against the checkpoint.

Validated records become reference events with IDs formed from the boundary
token and process-local sequence. Generators 62000/62001 map to source flower
instances `forest_1:floor2:BlackPom:0/1`; actual input colors are retained.
Different trip/boundary tokens give different event identities. Suppressed
generation yields an empty list. The function does not mutate its inputs or
write any save file.

This is a diagnostic bridge, not authentication. A caller can forge logs; the
native process does not attest the reference token. The report explicitly sets
`native_handoff_authenticated=false` and `native_ready=false`. Its text hash
covers the supplied UTF-8 text, which may have normalized newlines, rather than
claiming to hash original log bytes. Health, maturity and individual survivor
identity are not supplied by these diagnostics and must come from a future
native handoff. No inferred squad or health is returned as authoritative state.

Local replay evidence: `output/beasts283-bridge/replay.json`. The ordinary and
refund native logs from #279 yielded ten and eleven events respectively. Both
advanced the reference to floor3 and replayed without another transition.
The replay used explicitly synthetic health/maturity inputs and the fixture's
observed species totals. The existing reference still refuses floor3 launch.
The report is local test evidence, not a durable campaign checkpoint.

Validation: bridge, runtime, generation and checkpoint/lifecycle suites passed
29 tests and 79 subtests. Rejection coverage includes wrong floor, mismatched
generation or starting population, missing native evidence and omitted context;
success coverage includes suppression, input immutability and exact replay.
No native sources or shared save protocols changed in this batch. Persistent
single-ledger integration, authenticated native handoffs and playable floor3
remain open.
