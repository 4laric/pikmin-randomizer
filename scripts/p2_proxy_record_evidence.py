"""Record proxy-tier probe evidence into species declaration rows.

A campaign probe result (e.g. ``C:/cop/a6/result.json``) looks like::

    {
      "probe": "a6",
      "ok": true,
      "fatal": null,
      "exe_sha256": "<64 hex>",
      "table": [...],
      "bound_species": [2, 17],
      "drawn_live": {"2": {"frames": 120}, "17": {"frames": 96}},
      "expected": [2, 17],
      "skips": [],
      "log": "probe.log",
      "log_sha256": "<64 hex>"
    }

Field shapes the recorder accepts:

* ``expected`` / ``bound_species``: source ids (ints) or enum names (strings).
* ``drawn_live``: a mapping keyed by source id (as int or string) or enum
  name; a species "has an entry" when its key is present with a truthy value.
* ``table``: a list of campaign table rows, a mapping with a non-empty
  ``rows`` entry, or a non-empty string; anything else counts as empty.
* ``skips``: a list of strings or mappings; a skip names a species when one
  of its tokens (split on non-alphanumerics) equals the source id or the
  enum name.
* ``fatal``: must be empty (null, "", [], {}). ``ok`` must be true.
* ``log``: path to the probe log; relative paths resolve against the result
  file's directory. ``log_sha256`` is re-verified against the file on disk
  and the whole run is refused on mismatch.

For each expected species that is in ``bound_species``, has a ``drawn_live``
entry, with ``table`` non-empty, no ``fatal``, ``ok`` true and no skip
naming it, the recorder writes the ``evidence`` block into that species'
row JSON under ``--rows-dir`` (default ``randomizer/p2_proxy``)::

    "evidence": {"run": <probe>, "log": <log as given>, "log_sha256": <verified>,
                 "native_commit": <from --native-commit>, "recorded": <today>,
                 "markers": {"table": true, "bind": true, "draw": true}}

A species that is bound but not drawn is NOT recorded. Everything else is
refused with a clear per-species reason; the exit status is nonzero when any
expected species is refused. Re-running a recorded probe is a no-op success
(identical block: no write). No other row field is touched.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_COMMIT_RE = re.compile(r"[0-9a-fA-F]{7,40}")
_HEX64_RE = re.compile(r"[0-9a-fA-F]{64}")
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _fail(message):
    raise ValueError(message)


def _species_key(source_id, enum_name):
    return f"{source_id}/{enum_name}"


def _load_rows(rows_dir):
    from randomizer.p2_proxy import load_rows

    rows = load_rows(directory=rows_dir)
    by_id = {row["source_id"]: row for row in rows}
    by_enum = {row["enum_name"]: row for row in rows}
    return rows, by_id, by_enum


def _resolve_species(ref, by_id, by_enum):
    """Normalize an expected/bound ref (source id or enum name) to a row."""
    if type(ref) is int and not isinstance(ref, bool):
        row = by_id.get(ref)
        if row is None:
            _fail(f"probe names source id {ref} with no declaration row")
        return row
    if isinstance(ref, str):
        if ref.isdigit():
            return _resolve_species(int(ref), by_id, by_enum)
        row = by_enum.get(ref)
        if row is None:
            _fail(f"probe names enum {ref!r} with no declaration row")
        return row
    _fail(f"probe species ref must be a source id or enum name: {ref!r}")


def _table_non_empty(table):
    if isinstance(table, str):
        return bool(table.strip())
    if isinstance(table, list):
        return bool(table)
    if isinstance(table, dict):
        rows = table.get("rows", table.get("bindings"))
        return isinstance(rows, list) and bool(rows)
    return False


def _skip_names_species(skip, source_id, enum_name):
    if isinstance(skip, dict):
        tokens = set()
        for value in skip.values():
            tokens.update(_TOKEN_RE.findall(str(value)))
        return (str(source_id) in tokens) or (enum_name in tokens)
    tokens = set(_TOKEN_RE.findall(str(skip)))
    return str(source_id) in tokens or enum_name in tokens


def _drawn_entry(drawn_live, source_id, enum_name):
    """Return the drawn_live entry for one species, or None when absent."""
    if not isinstance(drawn_live, dict):
        return None
    for key in (source_id, str(source_id), enum_name):
        if key in drawn_live:
            return drawn_live[key]
    return None


def _verify_log(result_path, log_ref, claimed_digest, log_root=None):
    if not isinstance(log_ref, str) or not log_ref.strip():
        _fail("probe result has no log path")
    if not isinstance(claimed_digest, str) or not _HEX64_RE.fullmatch(claimed_digest):
        _fail("probe result log_sha256 must be 64 hex")
    log_path = Path(log_ref)
    if not log_path.is_absolute():
        # Evidence is cited workspace-relative (e.g. ``output/<lane>/.../native.log``) like the rest of
        # the repository's evidence; ``--log-root`` names that workspace. Default: next to the result.
        base = Path(log_root) if log_root is not None else result_path.parent
        log_path = base / log_path
    if not log_path.is_file():
        _fail(f"probe log not found on disk: {log_path}")
    actual = hashlib.sha256(log_path.read_bytes()).hexdigest()
    if actual.lower() != claimed_digest.lower():
        _fail(f"probe log sha256 mismatch for {log_path}: "
              f"claimed {claimed_digest} != on-disk {actual}")
    return actual.lower()


def decide(result, rows_dir):
    """Split the expected species into (recordable, refused).

    Returns ``(decisions, context)`` where ``decisions`` maps
    ``"<source_id>/<enum>"`` to ``(row, None)`` for recordable species or
    ``(row, reason)`` for refused ones, and ``context`` carries the verified
    log digest, probe name and row-file paths. Structural probe failures
    (bad shape, log mismatch) raise ``ValueError`` and refuse the whole run.
    """
    result_path = Path(result.get("__path__", "."))
    rows, by_id, by_enum = _load_rows(rows_dir)
    if not isinstance(result, dict):
        _fail("probe result must be a JSON object")
    expected = result.get("expected")
    if not isinstance(expected, list) or not expected:
        _fail("probe result has no expected species list")
    bound_refs = result.get("bound_species")
    if not isinstance(bound_refs, list):
        _fail("probe result has no bound_species list")
    bound_ids = set()
    for ref in bound_refs:
        bound_ids.add(_resolve_species(ref, by_id, by_enum)["source_id"])
    if result.get("ok") is not True:
        _fail("probe result ok is not true; refusing the whole run")
    if result.get("fatal") not in (None, "", [], {}):
        _fail(f"probe result carries fatal={result.get('fatal')!r}; "
              f"refusing the whole run")
    table_ok = _table_non_empty(result.get("table"))
    skips = result.get("skips")
    if skips is None:
        skips = []
    if not isinstance(skips, list):
        _fail("probe result skips must be a list")
    digest = _verify_log(result_path, result.get("log"), result.get("log_sha256"),
                         log_root=result.get("__log_root__"))
    probe = result.get("probe")
    if probe is None or (isinstance(probe, str) and not probe.strip()):
        probe = result_path.parent.name
    if not isinstance(probe, str):
        _fail("probe result probe name must be a string")
    decisions = {}
    seen = set()
    for ref in expected:
        row = _resolve_species(ref, by_id, by_enum)
        source_id, enum_name = row["source_id"], row["enum_name"]
        key = _species_key(source_id, enum_name)
        if key in seen:
            continue
        seen.add(key)
        if source_id not in bound_ids:
            decisions[key] = (row, "expected but not in bound_species")
            continue
        if not table_ok:
            decisions[key] = (row, "probe table is empty")
            continue
        entry = _drawn_entry(result.get("drawn_live"), source_id, enum_name)
        if not entry:
            decisions[key] = (row, "bound but not drawn live; not recorded")
            continue
        naming = [skip for skip in skips
                  if _skip_names_species(skip, source_id, enum_name)]
        if naming:
            decisions[key] = (row, f"probe skips name this species: {naming!r}")
            continue
        decisions[key] = (row, None)
    context = {"log_sha256": digest, "probe": probe,
               "log": result.get("log"), "rows_dir": Path(rows_dir)}
    return decisions, context


def _row_path(rows_dir, row):
    return Path(rows_dir) / f"{row['source_id']}_{row['enum_name']}.json"


def apply(decisions, context, native_commit, today=None):
    """Write evidence blocks for recordable species; return per-species lines."""
    if not isinstance(native_commit, str) or not _COMMIT_RE.fullmatch(native_commit):
        _fail("native commit must be 7-40 hex")
    today = today or datetime.date.today().isoformat()
    lines = []
    for key in sorted(decisions):
        row, reason = decisions[key]
        if reason is not None:
            lines.append(f"REFUSED {key}: {reason}")
            continue
        path = _row_path(context["rows_dir"], row)
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            _fail(f"declaration row unreadable: {path.name}: {error}")
        block = {"run": context["probe"], "log": context["log"],
                 "log_sha256": context["log_sha256"],
                 "native_commit": native_commit, "recorded": today,
                 "markers": {"table": True, "bind": True, "draw": True}}
        existing = document.get("evidence")
        if existing == block:
            lines.append(f"UNCHANGED {key}: evidence already recorded")
            continue
        if isinstance(existing, dict):
            same = dict(existing)
            same["recorded"] = today
            if same == block:
                lines.append(f"UNCHANGED {key}: evidence already recorded")
                continue
        previous = "absent" if "evidence" not in document else "re-recorded"
        document["evidence"] = block
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        lines.append(f"RECORDED {key}: evidence {previous} (run {context['probe']})")
    return lines


def record(result_path, rows_dir, native_commit, log_root=None):
    """Decide and apply one probe result; return (lines, refused_count)."""
    result_path = Path(result_path)
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        _fail(f"probe result unreadable: {result_path}: {error}")
    if not isinstance(result, dict):
        _fail("probe result must be a JSON object")
    result["__path__"] = str(result_path)
    if log_root is not None:
        result["__log_root__"] = str(log_root)
    decisions, context = decide(result, rows_dir)
    lines = apply(decisions, context, native_commit)
    refused = sum(1 for _row, reason in decisions.values() if reason is not None)
    return lines, refused


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--result", type=Path, required=True,
                        help="probe result JSON (fields log/log_sha256/table/"
                             "bound_species/drawn_live/skips/fatal/exe_sha256/"
                             "ok/expected)")
    parser.add_argument("--rows-dir", type=Path,
                        default=ROOT / "randomizer" / "p2_proxy",
                        help="species declaration directory (default: %(default)s)")
    parser.add_argument("--log-root", type=Path, default=None,
                        help="workspace that a relative `log` path in the result is relative to "
                             "(default: the result file's directory)")
    parser.add_argument("--native-commit", required=True,
                        help="native commit hash (7-40 hex) the probe ran against")
    args = parser.parse_args(argv)
    try:
        lines, refused = record(args.result, args.rows_dir, args.native_commit, log_root=args.log_root)
    except ValueError as error:
        print(f"REFUSED ALL: {error}")
        return 1
    for line in lines:
        print(line)
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
