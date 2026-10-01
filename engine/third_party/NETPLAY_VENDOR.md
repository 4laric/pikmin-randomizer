# Vendored netplay libraries (#876)

Source-only copies for online co-op netplay. Nothing here is built by default; it is wired into CMake in
milestone M3 and only when the netplay option is enabled.

| Directory | Upstream | Pinned commit | License |
|---|---|---|---|
| `gekkonet/` | https://github.com/HeatXD/GekkoNet | `3b21722ad09824638ed6eb43282c463008053a91` (2026-09-02, release v20260902101441-3b21722) | BSD-2-Clause (`gekkonet/LICENSE`) |
| `gekkonet/GekkoLib/thirdparty/zpp/` | zpp_bits, as bundled by GekkoNet | same | MIT (`gekkonet/GekkoLib/thirdparty/zpp/LICENSE`) |
| `libjuice/` | https://github.com/paullouisageneau/libjuice | `b89c792e3612faf2f12cf35bcc56857313a06be3` (tag v1.7.4, 2026-09-27) | MPL-2.0 (`libjuice/LICENSE`) |

## What was copied

Files were copied with `git archive` at the pinned commits. Nothing in them has been modified.

**GekkoNet:**
- `LICENSE`, `README.md`, `GekkoLib/include`, `GekkoLib/src`, `GekkoLib/thirdparty/zpp`
- Excluded: the bundled ASIO (`GekkoLib/thirdparty/asio`), `Examples/`, `docs/`, the MSVC project files and the CI workflows.
- Build with `GEKKONET_NO_ASIO` defined. The game supplies its own transport through `GekkoNetAdapter`.
- The library needs C++20 (`-std=gnu++20`), so it gets its own static target outside the game's C++17 options.

**libjuice:**
- `LICENSE`, `README.md`, `include`, `src`, `CMakeLists.txt` (kept for reference; the game uses its own target)
- Excluded: `test/`, `fuzzer/`, `cmake/`, `Makefile` and CI.
- Links `ws2_32` and `bcrypt` on Windows. The optional Nettle backend is not used.

MPL-2.0 is a file-level copyleft. If a libjuice file is modified, the modified file must stay under MPL-2.0 and its
source must remain available. Keep any local patches as separate, clearly marked commits.

Compile check: every `.cpp` / `.c` in both libraries was compiled with MinGW g++/gcc 16.2 (`-std=gnu++20
-DGEKKONET_NO_ASIO`, `-std=c11`). The log is in `output/netplay-wave/scratch/vendor-compile.log` (local, not
committed).
