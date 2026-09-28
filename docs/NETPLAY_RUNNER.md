# Netplay runner: host mode vs client mirror mode (M4 lane C, issue #885)

## Modes

* **Host mode (unchanged).** `python -m randomizer run MANIFEST --session-dir SESSION
  [--exe EXE --assets ASSETS --server SERVER]` behaves exactly as before: it owns
  the Archipelago websocket (`items_handling=7`, `Sync`+`Get`, `LocationChecks`,
  `StatusUpdate`, `Bounce`/DeathLink), polls the native `hello.txt`/`checks.txt`/
  `deaths.txt` journals, and writes `session.json`, the debug `state.txt`, and
  the native campaign saves. When netplay is not requested, nothing else changed.
* **Client mirror mode.** `python -m randomizer run MANIFEST --session-dir SESSION
  --netplay-client --bootstrap HOST_BOOTSTRAP [--mirror-dir MIRROR] [--exe EXE
  --assets ASSETS]` runs the netplay client:
  - never imports or opens a websocket and never contacts Archipelago (there is
    no `websockets` reference on the client code path; `--server` is rejected);
  - never writes the host's `session.json`, `checks.txt`, `campaign/` or
    `runner.lock`. It takes the lock on the mirror directory only and writes
    only under the mirror directory;
  - derives its run token from the host bootstrap `SESSION` line (the peer
    token chosen by `export_client_bundle`), so relaunching with the same
    bootstrap resumes the same `runs/<token>/` directory, `mirror.json` and
    ingest cursor;
  - validates the native `hello.txt` handshake (`PIKMIN_HELLO <schema> <token>
    <fingerprint> <capabilities...> END`) before ingesting anything, mirroring
    the host `NativeRun` gate; a mismatched hello is fatal;
  - ingests the state updates the native client appends to `mirror-events.txt`
    into `mirror.json` (same schema as `session.json`), and renders a debug
    `state.txt` in the same format as the host for log comparison. The
    simulation itself consumes the netplay state stream, not that file.

## Mirror layout

`--mirror-dir` defaults to `SESSION/netplay/<fingerprint>/`. Each peer gets a
stable run token (the host-stamped `SESSION`), exactly like a host `NativeRun`
token:

```
SESSION/netplay/<fingerprint>/runs/<token>/bootstrap.txt      # host bootstrap, SESSION re-stamped
SESSION/netplay/<fingerprint>/runs/<token>/hello.txt          # native handshake (validated, never written by runner)
SESSION/netplay/<fingerprint>/runs/<token>/mirror-events.txt  # native-written input (append-only)
SESSION/netplay/<fingerprint>/runs/<token>/mirror.json        # session-schema mirror (overlay source)
SESSION/netplay/<fingerprint>/runs/<token>/state.txt          # debug render, same format as host (native must ignore it in client mode)
SESSION/netplay/<fingerprint>/runs/<token>/card/              # SAVE_RESULT.txt pointer copy only
SESSION/netplay/<fingerprint>/runs/<token>/.mirror-ingest.json# byte offset, last frame, prefix hash, seen lines, checkpoint
```

`mirror.json` carries exactly the `session.json` keys (`schema`, `fingerprint`,
`checked`, `received`, `ap_identity`, plus `emperor_defeated` /
`pikmin_deaths` / `death_links_received` when the manifest enables them), so
the overlay and tracker read it unchanged. The day-end checkpoint pointer
(`gen`, SHA-256, ok/fail) has no session-schema field and lives in
`.mirror-ingest.json` with a copy at `card/SAVE_RESULT.txt`.

Native file layout note: a native client launched from `runs/<token>/`
derives `campaignDirectory = <run>/../../campaign` and `saveRoot =
campaign/card`, so real day-end `*.sav` checkpoints live at
`session/netplay/<fingerprint>/campaign/` (20-digit `%020llu.sav` names, the
only names the native loader accepts). `runs/<token>/card/` holds only the
`SAVE_RESULT.txt` pointer copy.

## `mirror-events.txt` grammar

ASCII only, one event per line, `1..256` bytes per line, `\n` terminated. Lines
are split on `\n` only: a `\r` or any other control byte stays inside the line
and is rejected. The runner consumes only complete lines (bytes up to the last
`\n`), so a torn tail write is retried on the next poll; a truncated file or a
rewritten prefix (detected by length plus a SHA-256 prefix hash) is fatal.

```
FRAME <frame> RECEIVED <index> <item_id>
FRAME <frame> CHECKED <location>
FRAME <frame> DEATHS <total>
FRAME <frame> DEATHLINK <total>
FRAME <frame> EMPEROR
FRAME <frame> SAVE_RESULT <gen> <digest>
FRAME <frame> SAVE_FAIL <gen>
```

* `<frame>` is the netplay frame, `0..4294967295`, canonical digits (no
  leading zeros except `0` itself). Frames are non-decreasing; a retracted
  frame is rejected and the last frame persists in the ingest cursor.
* `RECEIVED` carries the 0-based AP receive index (the same index
  `Session.receive` uses) plus the Archipelago item id from the manifest pool
  (`0..2147483647`, membership-checked). The native writer must emit receipts
  in index order without gaps. Ingest applies index `len(received)`; a lower
  index with a matching item is a no-op duplicate; gaps and conflicts are
  rejected. Identical item ids at different indices are distinct receipts and
  both apply. Because `mirror.json` is saved before the ingest cursor, a crash
  between the two writes replays safely as no-ops.
* `CHECKED` carries the exact location name (`1..128` chars; names may contain
  spaces, e.g. `Pikmin: Bowsprit`). It must be an active location of the
  manifest; re-checking a known location is a no-op.
* `DEATHS` / `DEATHLINK` carry absolute session-cumulative monotonic totals
  (`0..1000000`, canonical) of ordinary Pikmin deaths / received DeathLinks,
  matching host `session.json` accumulation across days and reconnects. Equal
  replays are no-ops; retractions are rejected. Both require `death_link` in
  the manifest.
* `EMPEROR` carries no argument and requires the `emperor_bulblax` goal.
  Replays are no-ops.
* `SAVE_RESULT` carries the campaign checkpoint generation (`1..20` canonical
  digits, `1..18446744073709551615`) and the lowercase hex SHA-256 (`64`
  chars) of the checkpoint file; `SAVE_FAIL` records a failed day-end save for
  the generation.

Numbers are canonical: no leading zeros (except `0` itself). Separators are
single spaces; anything else (unknown tags, non-ASCII, over-long lines,
out-of-range values, wrong arity, blank lines) raises `ValueError`. Each poll
parses and validates the whole appended batch before applying anything, so a
bad line leaves `mirror.json`, the card pointer and the ingest cursor
untouched; the offending poll fails and the stream is fatal to the run
(matching host semantics). The native writer (parallel lanes) must implement
exactly this grammar; see `parse_mirror_line` in
`randomizer/netplay_mirror.py` as the reference parser.

## Export helper

`export_client_bundle(manifest, session_dir, peer_token, host_run_token=None)`
in `randomizer/netplay_mirror.py` describes what a client needs before the
session starts. The host runner calls it programmatically before the session
starts (there is no CLI subcommand; it reads only) and hands the returned
`bootstrap_text` (plus the checkpoint file out of band) to each peer. It reads
only and **writes nothing** into the host session:

* the host bootstrap (`runs/<token>/bootstrap.txt`, latest by mtime unless
  `host_run_token` is given, validated as a hex run token) with the `SESSION`
  line re-stamped to `peer_token`, following the `run_pair.py` pattern. Every
  other byte is identical. `restamp_bootstrap_for_peer` performs the re-stamp.
* the latest campaign checkpoint: the highest-generation exactly-20-digit
  `*.sav` under `campaign/` (the only names native accepts), returned as
  `checkpoint_path`, `checkpoint_gen` and the SHA-256 `checkpoint_hash`
  (`None` when the host has no checkpoint yet).
* the manifest `fingerprint` and a read-only `session_snapshot` copy.

## Overlay and tracker indirection

`randomizer/overlay.py` and `randomizer/tracker.py` read through
`resolve_session_file` / `load_session_data` in `randomizer/session.py`: when
`--session-dir` points at a host session, `session.json` is read (unchanged
behaviour); when it points at a mirror run directory, `mirror.json` is read.
`TrackerModel.snapshot_from_dir` is the same indirection for the tracker. No
snapshot logic is forked: validation and `state.txt` rendering live in
`randomizer/session.py` (`validate_session_data`, `render_session_state`) and
are called from both the host `Session` and the mirror store.
