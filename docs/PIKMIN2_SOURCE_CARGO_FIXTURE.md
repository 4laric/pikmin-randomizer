# Source cargo native acceptance

`python -m experimental.pikmin2_source_cargo_fixture --native native --recipe <verified fixture commands.json> --output <new private build directory> --stage <fresh private source cargo stage>`

Coordinate a completed production object build before running this command. The tool compiles only a generated private fixture source and object, then links the provided stable object recipe into its own executable. It never overwrites the shared fixture or production source. Toolchain DLL lookup uses the compiler directory; runtime defaults to `C:/msys64/mingw64/bin` and accepts `--runtime`.

Instrumentation fails closed if any expected original fixture anchor has changed. `instrument` and `validate` accept configurable expected value/weight/slots; the command targets Hole of Beasts source juji_key_fc (100/5/10). Native configuration is checked before assigning transport. The existing controller walk and actual hauling use engine physics; no actor or cargo relocation is added. The private fixture observes cargo crossing the east and west connector seams in order, then requires 100 Pokos and unchanged repairs. Only after natural delivery does it call the receipt hook again to prove no duplicate credit.

Host validation additionally requires the actual catalog receipt identity, both new and duplicate journal log lines, and final native completion. It emits `source-cargo-acceptance.json` with executable hash and results. A preexisting receipt is rejected, so use a freshly prepared private stage. Unsupported enemy/plant roster entries remain unchanged; this does not validate retail generation, full cave progression, enemy actors or native save resume.

Three focused tests plus four invalid-input subcases validate source framing, expectation bounds, receipt identity, and missing duplicate evidence.

Local acceptance passed against native `8510d34c` objects: 1,131.24-unit controller movement, observed east then west cargo seam crossings, actual `treasure:juji_key_fc` receipt100, duplicate receipt100 with new=0, zero repair changes. Evidence: `output/p2-beasts-content-batch/verified/runs/bf58a441f75a41a2a6cda1614f2f19c8/source-cargo-acceptance.json`. Private executable SHA256 `2fd807502b3a4fb175356b115e5ba258eeaef1b5967ef51096afbf2221946af2`.
