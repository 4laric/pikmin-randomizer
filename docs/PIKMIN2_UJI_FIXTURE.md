# Private Uji developer regression

`python -m experimental.pikmin2_uji_fixture --native native --recipe <fixture commands.json> --output <new private fixture directory>` generates and links a private fixture only after the coordinating production build supplies the new Uji object. It does not modify native sources or rebuild shared objects.

The fixture checks both registered species and source corpse values, positions the pair nearby for a synthetic live capture, forces zero health to exercise native proxy death, captures both corpses, and assigns native transport actions without moving those corpses. It requires the actual Pod total of three Pokos, unchanged repairs, and no repeated credit. Explicit registration forgetting must remove both name and receipt ownership. These tests do not establish full P2 AI, natural player combat, save persistence or allocator reuse behavior. Kimi's independent manual QA remains separate.

Three focused tests pass. Actual private native fixture03 passed against606c0c17 objects: both registered species and live/corpse captures, real corpse hauling1+2 Pokos, duplicate economy replay0, repairs unchanged, explicit forget ownership fallback. Evidence is output/p2-uji-fixture-batch/runs/9bfb86815780433598e646f74deef574/acceptance.json. Allocator rebirth and manual visual QA remain separate.

Duplicate replay is instrumented inside a private copy of the valid native delivery callback; P1 clears corpse ownership after delivery, so invoking that callback later with a recycled corpse pointer is invalid. Both private sources/objects are isolated; production source stays unchanged.
