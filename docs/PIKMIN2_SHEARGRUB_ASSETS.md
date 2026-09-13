# Sheargrub source asset bundles

`python -m experimental.pikmin2_sheargrub_assets --iso <local US ISO> --output <new directory> [--pose-limit 3]`

UjiA and UjiB have separate `enemy/data/<species>/model.szs` models with embedded textures. Both use `enemy/data/UjiA/anim.szs`. Their separate registrations in `enemy/parm/enemyParms.szs` select seven and nine clips respectively. Each has six named joints. The importer preserves original model/BCA bytes plus parameter, collision, animation-manager and stone metadata and hashes the source archives.

The default samples three poses per registered clip (48 MODs total); the accepted limit is 2–8. BCA rigid-pose conversion uses the existing converter with its explicit approximate material policy. Every MOD has a hash and normalized conversion sidecar. Unsupported conversion raises a per-clip status with the exact error; partial poses do not imply that clip is supported. No new native bank format or runtime consumer is installed.

The species are not interchangeable. As detailed in `PIKMIN2_GROUND_ENEMY_AUDIT.md`, UjiA attack1 event2 targets a bridge. UjiB adds attack2 events at source frames5/12/14 (events2/3/4) and Eat event2 at53. Source animation registrations are preserved as metadata, not executed by this pose bank. Collision dimensions come from the preserved source text, not visual bounds. Bridge ownership, bite/capture/consumption, underground transitions and lifecycle remain native implementation work.

Local validation at `output/p2-sheargrub-assets-batch/verified` converted all seven UjiA and nine UjiB clips into48 poses. Every output file matches a second import byte-for-byte. Three focused tests plus seven invalid-input subcases cover event preservation, malformed/duplicate registrations and pose-budget rejection. No native actors, P1 substitutions, shared converter edits, builds or asset exports were performed. All imported assets remain local.
