# Independent packaged co-op consumer audit (#1158)

This audit starts from root `36ac5ddd2877b9308276f96b28a81e137ae58c5a` and native `67f91ef9a9d3a8fec9f7ae84a653321fe153c893`, the #1148 consumer/protocol candidate. It does not change producer-owned source, codecs, SDL input drivers or the completed #1093 naming crosswalk. Implementation owner: Codex through shared account 4laric.

Run in a private checkout with a fresh ignored output directory:

```powershell
py -3.12 scripts/test_packaged_coop_consumers.py --ap C:/Users/alari/Archipelago --native-sha 67f91ef9a9d3a8fec9f7ae84a653321fe153c893 --native-git C:/Users/alari/pikmin-randomizer/native --output C:/Users/alari/pikmin-randomizer/output/consumer-audit-fresh
```

The script builds the actual APWorld, loads it in a separate process with checkout paths removed, and runs twelve successful fills across ordinary P1 defaults, P1 day/DeathLink receipts, P2 defaults and P2 second-captain/day/DeathLink options. It reconstructs exact authoritative manifests, locations and rules in Universal Tracker under different defaults/seed, checks slot data remains unchanged, and exports real generated `.pikmin.json` files through the packaged world.

The exported manifests then pass through the real `Session`, `native_bootstrap`, `NativeRun.attach`, `export_client_bundle`, `NetplayClientRun`, native numeric check-journal recovery and mirror APIs. Each generated P1 profile has 62 checks/receipts and each P2 profile has 91 for the pinned seed. All checks and every item in the pool are ingested, and host/mirror state, persistent reload, replay and read-only tracker views are compared. Invalid full bootstraps and foreign attachment layouts are rejected before creating a client run.

The TheLynk fixture exercises the actual `.appik1` metadata reader, all 330 original check IDs, thirty unique part IDs and eighteen typed bonus IDs. It verifies an independent upstream item-name golden sequence, including Main Engine and both Ionium aliases, then mirror export/replay, numeric journal recovery and state parity. Duplicate unique parts and foreign seed identity refuse atomically. The check/reward/session formats and IDs remain unchanged.

## Discovered integration failure

At the pinned native source, `pc_randomizer_outbox_flush` emits `mirror_checked(..., checkName(e.slot))`. The thirty `thelynkPartNames` are internal engine names, such as `Pikmin: Main Engine`, `Pikmin: Bowsprit` and `Pikmin: Ionium Jet 1`. The Python `MirrorStore.apply` TheLynk branch accepts upstream external locations such as `TIS - Main Engine`, `TDS - Bowsprit` and `TFN - #1 Ionium Jet`. Consequently actual native ship-part `CHECKED` events are rejected as unknown locations. Population labels already match and all external IDs are correct.

Earlier producer-independent fixtures wrote external location names, so they passed while missing this integration boundary. `--native-git` reads the exact native source at `--native-sha`, extracts its real thirty-name table and exercises the current mirror consumer with those names. On the pinned candidate the audit retains all thirty failures in `protocol/thelynk/native-writer-consumer-mismatches.json` and exits nonzero. It intentionally does not turn the failure into a pass or rename persisted identities.

The fix needs explicit #1148 owner coordination: either emit canonical external names from the native TheLynk mirror writer, or add an explicit TheLynk-only internal-alias normalization in the consumer. The final combined check must use the actual corrected writer output. This lane has not modified either producer-owned API.

## Retained fixture bundle and boundaries

`evidence.json` records the tested root commit/dirty state, expected native pin, archive/files hashes and precise acceptance exclusions. Under `packaged/<profile>` are actual exported manifests and slot data. Under `protocol/<profile>` are private host/client session trees, deterministic tokens, canonical bootstrap, initial and complete state, handshakes, check journals, mirror streams and read-only client export descriptions. The bundle's manifest/bootstrap contracts and metadata patch are deterministic; the ordinary APWorld ZIP itself may include timestamp metadata.

The bootstrap/hello/check/mirror files are synthetic protocol inputs created by this audit through the real APIs. They are not files observed from a running native engine. Initial states deliberately have `ready=0`; complete states contain every check and reward for boundary testing. A gameplay harness must create fresh session/run state from the manifest and select real `ReceivedItems`/SDL actions, rather than present the all-complete protocol files as physical progression.

The TheLynk metadata fixture uses the explicit supported native preset. It is **not** an upstream-generated seed, playable ISO patch, game data or a seed fill performed by TheLynk's world. The local P1/P2 tracker consumes ordinary manifest/session schemas; no local `TrackerModel` UI support is claimed for TheLynk metadata. The packaged APWorld remains `Pikmin Randomizer`; the separate external client remains `Pikmin`.

No engine build, native execution, game assets, paired timing, save-barrier gameplay, current starting-20/Red overlay, centered 960x540 startup or full campaign/player sign-off is established here. Those remain the separately owned #1148 harness and runtime acceptance work. Python/package validation does not need a local heavy-build slot or private runner dispatch. No shared Archipelago installation is relinked.
