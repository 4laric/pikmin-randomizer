# Experimental cave checkpoints

Issue [#112](https://github.com/4laric/pikmin-randomizer/issues/112), owned by Codex through shared account 4laric. This is an increment on `codex/pikmin2-room-preview`, outside Pikipelago v0.1.

The two existing standalone room previews now form a persistent run: twenty Reds enter floor 1 with the Citrus Lump; survivors descend to floor 2 with two Violet Candypops and the Spherical Atlas. This is an engineering layout, not the complete authored Emergence Cave or its three-treasure roster.

## Playing

Local launcher: `output/pikmin2-lifecycle112/Play.cmd`. Press **F6 near the Research Pod**, then confirm, to descend or leave. Pluck all sprouts and withdraw Pikmin from flowers/combat first. Living Pikmin across the floor transfer together, including their species and maturity; captain health and delivered treasure/corpse receipts transfer too. The window title shows floor, population, Purple count and Pokos. Cave time is frozen.

The launcher starts the next native process automatically. Leaving floor 2 saves the result and closes the game; there is not yet a surface scene to return to. The engineering launcher remains silent while the earlier audio issue is investigated.

## Save contract

- `play-session/checkpoint.json` is the authority. Squad, health, destination and receipts are committed in one atomic replacement at descent or exit.
- Closing or crashing mid-floor replays that floor from its entry checkpoint. Both casualties/conversions and that floor's new collections roll back together. This is not a mid-day or mid-floor world save.
- Full extinction or captain knockout records a failed run. Relaunching an exited or failed run displays its saved result without creating a replacement squad.
- Checkpoints are tied to the imported layout, Pod and Purple assets. Corrupt, incompatible or missing checkpoints in an existing session fail visibly instead of silently resetting. A session lock prevents two launchers writing the same save.
- Each native handoff has a fresh token. Unexpected receipt IDs/values, population increases, stale handoffs and duplicate JSON fields are rejected. Corpse IDs include the floor to avoid collisions between reused generator templates.
- A crash before the atomic replacement leaves the old entry checkpoint authoritative. Native per-run receipts alone are never treated as campaign progress.

To start another run, use a different `--session` directory with `py -3.12 -m experimental.pikmin2_campaign`; keep the previous directory intact. Assets and sessions remain local and are not included in Git.

The source basis is the local P2 decomp's `singleGS_CaveGame.cpp` cave boundary saves, `singleGameSection.cpp::saveCaveMore`, and `pikiMgr.cpp::caveSaveAllPikmins`. The present single-captain implementation carries all living survivors; it does not claim full P2 death, surface-return or multi-captain fidelity.

## Validation

The full Python suite passed: 162 tests and 12 subtests. Focused checkpoint tests cover rollback, stale/malformed transfers, receipt regression, corrupt/incompatible saves, interrupted replacement and concurrent writers. Windows production and native fixture builds passed (native `a78ea6d6`). The ordinary no-cave room regression also passed controller movement, treasure delivery, combat and far corpse transport; its fixture uses explicit transport assignment as documented in the room preview.

The native lifecycle fixture passed two floor processes with 19 survivors, ten Purples, preserved leaf/bud/flower counts, 62.5% captain health and an atomic 380-Poko result. Relaunching the exited profile created no new run. Two additional native boots restored the mixed squad exactly. A separate extinction run exercised the production tick and saved zero survivors without replenishment. Logs are under `output/pikmin2-lifecycle112/native-check-final-02`.

These lifecycle tests inject a casualty and conversions and call the collection hook directly. They prove native restoration and checkpoint plumbing, not controller gameplay or transport AI. Prior Purple tests cover actual conversion and carrying separately. Entry captures were inspected, but their early landing effects obscure much of the scene; they are not a new visual-fidelity acceptance gate.

## Next integration gate

Complete the surface pocket and entry/return snapshots, physical hole/geyser interactions, full authored floor/treasure roster, and a player-driven round trip with reload. Issues #111, #112 and #114 remain open; this batch does not complete the vertical slice.
