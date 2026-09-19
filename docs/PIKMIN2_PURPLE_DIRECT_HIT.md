# Pikmin 2 Purple direct-hit adapter

Status: opt-in native implementation with adult direct-damage runtime acceptance, 2026-09-13. Tracking: #393, parent #113. Implementation owner: Codex through shared account `4laric`.

The adapter follows the audited `PikiHipDropState::collisionCallback` order: a descending direct receiver runs first, the existing nondamaging earthquake emits separately, source vertical velocity is read again, and the additional Press stage runs only while still descending. A source token can claim the direct sequence once, independently of the wave's one-shot consumption.

Direct behavior needs both `impact red_earthquake_v1` in `p2-purple.txt` and a separate `p2-purple-direct.txt`. Omitting the latter preserves the earlier earthquake-only protocol. Generate it with `experimental.pikmin2_purple_direct.write_profile(path, adult_generator_ids)`; an empty list enables the registered Red dwarf crush path without adult bindings.

Two receiver families are enabled:

- A registered Red Dwarf Bulborb uses the native Chappy Pressed event. Acceptance is the observed transition to Chappy state 2, not `InteractPress::actTeki`'s unconditional `true`. An accepted press bypasses generic damage, matching P2 `KochappyBase::pressCallBack`; the existing P1 pressed state supplies the crush/death lifecycle.
- Explicit `TEKI_Swallow` generator IDs are adult Bulborb mechanics adapters. Their generic hipdrop fallback queues one native `InteractAttack` for retail Chappy `fp36=50`. The final P2 Press is rejected for this family. Attachment mirrors the P1 engine's supported platform and collision/tube part dispatch; calling its object attachment path for other nominally stickable shapes panics. The P1 generic `InteractPress` is deliberately not called because it reports success and emits Pressed for every Teki, unlike the P2 adult base callback.

Retail provenance is GPVE01 revision 0 `enemy/parm/enemyParms.szs`, SHA-256 `3618455a8561f1e1b0aad0253a75a69fae1fe3a47160d1c1efa294b0ddeb2a84`; member `chappy/enemyparm.txt`, SHA-256 `12abc387cf05d4bf2c53f453694a268bec4d00e4fee33b03626d0d071b0f80c4`, has general `fp36=50`. The source fallback in `enemyBase.cpp` ignores the direct payload and uses this parameter.

The private JAudio-enabled Release build passed at native commit `acd6d46d`. The source-provenance fixture staged an actual captain throw into a deterministic descending collision with registered runtime Swallow ID `0x17000000`. It observed one queued native attack, rejected a replay with the consumed throw token, then observed health `1100.0` to `1050.1`. The `0.1` is native per-frame health regeneration in `BTeki::update`; the queued damage was exactly `50`. A second collision from health `40.1` entered the normal native death path and produced exactly one corpse, stable for 30 frames. Helper-level checks also rejected non-Purple, ascending, and non-enemy contacts. Fixture 07 executable SHA-256 is `a84d5f3d8b50684790ed4ec9792b3a7311006568ec4c667b096329712089715b`.

The follow-up Red dwarf fixture staged a real descending collision at `(185.0, 2.0, -180.0)`, but the bounded run did not pass the receiver eligibility gate and therefore did not observe Pressed state or a corpse. The compiled policy tests cover profile validation and one-token decisions, while native dwarf crush acceptance remains pending a fixture that captures and controls its live state/option at collision. This is native injected-fixture evidence, not controller gameplay signoff.

Adult evidence is in `output/p2-purple-direct393/fixture-07/provenance.json` and `run-adult-02/native-window-07.log` under the same lane directory. The later dwarf attempt uses `fixture-08/provenance.json`, pinned to private HEAD `8af0f51da7d8632bf487e9412b940d84c8dc3e63`; it is not a runtime pass. See [combined integration evidence](PIKMIN2_PURPLE_WHITE_INTEGRATION.md) for the maintained build and exported snapshot.

Current limits remain: this adapter begins from P1 `PIKISTATE_Flying`, without the P2 HipDrop pause, homing, descent/spin state or landing recovery. Adult binding asserts mechanics identity only and does not claim a new P2 visual asset. Bitter/hard-constraint parity and additional receiver families remain unsupported. Fixture injection is not controller signoff.
