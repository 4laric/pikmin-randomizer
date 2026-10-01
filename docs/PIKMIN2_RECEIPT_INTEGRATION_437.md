# Receipt/cargo provider integration (#437 / #441)

Owner Codex through shared 4laric. Root baseline 5d6ed8a; native 41304fd7953fe9166fb84a77d27ab2e1282feda6, clean. Imported only the receipt/cargo headers and standalone tests from native 4c3b32e6. No engine reward endpoint, lifecycle hook, native save layout or CMake production input changed.

Fixed FileReceiptPersistence ignoring an incomplete final record when EOF was set during chained extraction. It now rejects incomplete records. Regression covers one/two/three-field tails after a valid receipt, including a trailing newline. This prevents that corruption from silently removing a receipt on reload. The single-writer sidecar contract is not a transaction joining receipt persistence to external reward delivery; actual family/Onion/AP wiring remains separate.

Validation: Python receipt tests 32 passed / 19 subtests passed. All 35 native probes PASS, including corrected file-backed receipt and cargo-contest tests. Initial runner attempt lacked the receipt test's required directory argument; fixed the runner to pass a private output subdirectory and repeated in a fresh output directory. Export parity exact across 1738 tracked text files. Production no-work dry run; headers are not yet used by production, so existing binary/build evidence remains that of c223f442 (C68C63ED57909FA05D7A4E989F9EF98DAA0897B3342DC427A3ABE9DC18C316CC). No new link or runtime claim.

Next: review the engine-forget and ordinary endpoint candidate from lane 06/07, using this corrected provider. Worker latest bundle be8d95c reports ordinary endpoint/restart evidence, but that behavior is not integrated here. Cargo consumers must define unique carrier-token and ownership requirements; provider tests alone are not natural Breadbug cargo acceptance. Continue to preserve ordinary Onion/AP versus experimental Pod semantics.

Current lane 23 rebase 94d96c3, receiver/species 833a6b9 and Long Legs 21bcc1e remain queued for current-line review. Use the next-wave asset paths and fresh fixture adoption requirements. No main/upstream write or native-origin push.
