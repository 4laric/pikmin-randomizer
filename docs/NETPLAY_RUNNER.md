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
  - ingests the state updates the native client appends to `mirror-events.txt`
    into `mirror.json` (same schema as `session.json`), and renders a debug
    `state.txt` in the same format as the host for log comparison. The
    simulation itself consumes the netplay state stream, not that file.

## Mirror layout

`--mirror-dir` defaults to `SESSION/netplay/<fingerprint>/`. Each client launch
gets a private run token, exactly like a host `NativeRun`:

```
SESSION/netplay/<fingerprint>/runs/<token>/bootstrap.txt      # host bootstrap, SESSION re-stamped
SESSION/netplay/<fingerprint>/runs/<token>/mirror-events.txt  # native-written input (append-only)
SESSION/netplay/<fingerprint>/runs/<token>/mirror.json        # session-schema mirror (overlay source)
SESSION/netplay/<fingerprint>/runs/<token>/state.txt          # debug render, same format as host
SESSION/netplay/<fingerprint>/runs/<token>/card/              # mirror card (SAVE_RESULT copies)
SESSION/netplay/<fingerprint>/runs/<token>/.mirror-ingest.json# byte offset, seen lines, checkpoint
```

`mirror.json` carries exactly the `session.json` keys (`schema`, `fingerprint`,
`checked`, `received`, `ap_identity`, plus `emperor_defeated` /
`pikmin_deaths` / `death_links_received` when the manifest enables them), so
the overlay and tracker read it unchanged. The day-end checkpoint pointer
(`gen`, SHA-256, ok/fail) has no session-schema field and lives in
`.mirror-ingest.json` with a copy at `card/SAVE_RESULT.txt`.

## `mirror-events.txt` grammar

ASCII only, one event per line, `1..256` bytes per line, `\n` terminated. The
runner consumes only complete lines (bytes up to the last `\n`), so a torn
tail write is retried on the next poll; a truncated file is fatal.

```
FRAME <frame> RECEIVED <item_id>
FRAME <frame> CHECKED <location>
FRAME <frame> DEATHS <total>
FRAME <frame> DEATHLINK <total>
FRAME <frame> EMPEROR
FRAME <frame> SAVE_RESULT <gen> <digest>
FRAME <frame> SAVE_FAIL <gen>
```

* `<frame>` is the netplay frame, `0..4294967295` (max 10 digits).
* `RECEIVED` carries an Archipelago item id from the manifest pool
  (`0..2147483647`, membership-checked). Each `(frame, item)` line applies
  once; an exact-duplicate line is a no-op.
* `CHECKED` carries the exact location name (`1..128` chars; names may contain
  spaces, e.g. `Pikmin: Bowsprit`). It must be an active location of the
  manifest; re-checking a known location is a no-op.
* `DEATHS` / `DEATHLINK` carry absolute monotonic totals (`0..1000000`) of
  ordinary Pikmin deaths / received DeathLinks. Equal replays are no-ops;
  retractions are rejected. Both require `death_link` in the manifest.
* `EMPEROR` carries no argument and requires the `emperor_bulblax` goal.
  Replays are no-ops.
* `SAVE_RESULT` carries the campaign checkpoint generation (`1..20` digits)
  and the lowercase hex SHA-256 (`64` chars) of the checkpoint file;
  `SAVE_FAIL` records a failed day-end save for the generation.

Separators are single spaces; anything else (unknown tags, non-ASCII,
over-long lines, out-of-range values, wrong arity) raises `ValueError` and the
offending poll fails without applying the line. The native writer (parallel
lanes) must implement exactly this grammar; see `parse_mirror_line` in
`randomizer/netplay_mirror.py` as the reference parser.

## Export helper

`export_client_bundle(manifest, session_dir, peer_token, host_run_token=None)`
in `randomizer/netplay_mirror.py` describes what a client needs before the
session starts. It reads only and **writes nothing** into the host session:

* the host bootstrap (`runs/<token>/bootstrap.txt`, latest by mtime unless
  `host_run_token` is given) with the `SESSION` line re-stamped to
  `peer_token`, following the `run_pair.py` pattern. Every other byte is
  identical. `restamp_bootstrap_for_peer` performs the re-stamp.
* the latest campaign checkpoint: the highest-generation `*.sav` under
  `campaign/` (or `runs/*/campaign/`), returned as `checkpoint_path`,
  `checkpoint_gen` and the SHA-256 `checkpoint_hash` (`None` when the host has
  no checkpoint yet).
* the manifest `fingerprint` and a read-only `session_snapshot` copy.

## Overlay and tracker indirection

`randomizer/overlay.py` and `randomizer/tracker.py` read through
`resolve_session_file` / `load_session_data` in `randomizer/session.py`: when
`--session-dir` points at a host session, `session.json` is read (unchanged
behaviour); when it points at a mirror run directory, `mirror.json` is read.
`TrackerModel.snapshot_from_dir` is the same indirection for the tracker. No
snapshot logic was forked: the overlay `snapshot` and tracker `snapshot`
functions take the mirror data unchanged.
