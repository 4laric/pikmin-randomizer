# Independent P2 QA lane

Kimi owns independent runtime QA. The separate Codex worker on #135 owns fixture-build reproducibility; local implementation agents own code changes and focused developer fixtures. Record bounded QA scope on #135 before testing and report actionable defects to their implementation issues.

Start with the [manual bounded entrance loop](PIKMIN2_MANUAL_SURFACE.md). Use a fixed copy of both executables and record their SHA256 hashes, source/build provenance when available, exact launch command, asset manifest identities, and session directory. Never test against a binary that another worker is rebuilding. Use a new private session; preserve it with logs when reporting a failure.

Initial acceptance cases:

- Real F6 opens one confirmation at the entrance; cancellation preserves play. Settings menus must not trigger cave entry.
- Enter, play both cave floors, collect treasures and convert Pikmin normally, then leave through the geyser.
- Verify returned party species, maturity, health and receipts against the departure state and cave result.
- Close and restart during a cave floor: the floor-entry checkpoint should return, not a mid-floor world save. Check completed boundaries separately.
- Reopening a completed session must not award duplicate treasure or corpse rewards.
- Confirm the entrance fence contains movement and thrown Pikmin. Visible terrain beyond it is intentionally unavailable.

Current one-trip launcher limits are documented behavior: no full-surface water/world/day save, one cave trip per session, and explicit refusal to stage returns above 20 survivors rather than truncating them. The repeat-entry implementation is a separate changing lane; test it only after receiving a new fixed build and its acceptance contract.

Each bug report should include expected/actual behavior, minimal reproduction, build hashes, logs and save location, repeatability, and any screenshot/video evidence. Distinguish an implementation defect from a declared prototype limitation. Do not change code, fixtures or saved state to make a test pass. Automated fixture success is context, not a replacement for independent input and gameplay testing.
