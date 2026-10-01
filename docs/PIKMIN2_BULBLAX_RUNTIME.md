# Bulblax sampled native display — #235

This unblocks local visual inspection of Queen, Baby and KingChappy from #234. It is a noninteractive display binding, not boss gameplay or material fidelity acceptance.

## Fixed machine-local launchers

Under `C:/Users/alari/pikmin-randomizer/output/p2-root-integration/output/p2-bulblax-native235/kimi/`:

- `Play-Queen.cmd`
- `Play-Baby.cmd`
- `Play-KingChappy.cmd`

Each creates a fresh private stage with five red and five blue Pikmin, uses the copied `runtime/fixture.exe` and four DLLs, and stays open after the diagnostic sequence. Close the game to stop. Existing sessions and saves are not reused. Python 3.12, this checkout, prepared profile01 and the local P1 assets remain dependencies; this is not a distributable retail-asset bundle.

## Verified scope

`output/p2-bulblax-native235/validation01/result.json` records four completed native runs: Queen wait1, Baby move, KingChappy move1, and disabled control. All passed completion, selected sample changes, reset, reload, squad, no-reward and exact identity/XYZ/yaw checks. Both native READY rounds are compared against profile placements. Captures were inspected: all three models are visible, Queen disappears after reset, and KingChappy returns after reload.

Every run emitted the same one preexisting GX texture-format 0x11 warning as disabled control. There were zero additional warnings. This is not a claim that the renderer has no warnings.

The source placement IDs and coordinates are unchanged:

| ID | Species | Clip | XYZ |
|---|---|---|---|
| 230001 | Queen | wait1 | -120, 30, 1800 |
| 230002 | Baby | move | -100, 30, 1820 |
| 230003 | KingChappy | move1 | 150, 30, 1500 |

These are engineered display placements on original P1 terrain. KingChappy visibly straddles a ledge. Native ground samples are logged, but this is not collision or traversal validation. Unit scale and yaw zero are preserved. A private, unregistered camera target frames each species; different camera distances are not a scale comparison.

## Known visual and gameplay limits

Queen has an incorrect black/silver reflective body appearance. Baby is very bright and flat. KingChappy has recognizable textures but intersects terrain. Material follow-up is #239. The bank retains its documented approximate materials and normal policies; skeletal animation, source BTK animation and full TEV parity are not implemented here.

The native module draws sampled meshes only. There is no boss Teki, AI, hitbox, health, combat, bomb interaction, drops, rewards or source FSM. Only three selected clips were exercised in native runtime, not the entire clip bank.

## Protocol and provenance

`P2_BULBLAX_VISUAL_1` strictly validates species 30/31/53, known clip names, ordered bounded source frames, finite coordinates, unique unsigned IDs and trailing data. Missing configuration is a no-op; malformed opt-in configuration fails closed. Reset clears all references and playback state. The host validates all 174 models (8,154,624 bytes); native loads only selected clips with a 1 MiB per-clip and 16 MiB selected-bank cap. Geometry and source-frame timing are retained.

Private fixture provenance: `output/p2-bulblax-native235/fixture01/build/provenance.json`. Snapshot native revision `2c08d6b8d6d085318f239c07297be0bb5c33dbdf`, with the recorded known line-ending dirty baseline; both Ninja freshness checks reported no work. This does not certify a pristine historical checkout.

Fixture and copied executable SHA256: `686415002b6cc1bceb18a7365a092395431f57be65bb0aa787445eb047710f1e`. Runtime DLL closure and hashes are in `kimi/runtime/runtime-provenance.json`. Prepared assets are in `profile01`; local imports are not tracked or published.

Validation: six Python tests passed, including altered-byte refusal, reproducible 174-model installation, exact generator squad, source ID/XYZ rejection and disabled rendering rejection. The standalone native policy test passed strict compilation and execution. Manual visual quality, gameplay and all unexercised clips remain open gates.
