"""Netplay M4 lane B1 (issue #885): check a pair's host journals against the
client's mirror-events.txt.

    check_mirror.py --host-run H --join-run J [--session-json F]
                    --root-mirror <root worktree with randomizer/netplay_mirror.py>

Checks (exit 0 only when every one holds):
  1. every line of J/mirror-events.txt parses with the root reference parser
     randomizer.netplay_mirror.parse_mirror_line (imported read-only through
     sys.path), the file ends with a newline, and frames never decrease;
  2. the host has no mirror-events.txt and the join has none of checks.txt,
     deaths.txt, emperor.txt, benefits-used.txt;
  3. host checks.txt lines are unique and equal the slots of the host's
     `[Pikmin Randomizer] CHECK <slot> <name>` log lines;
  4. the CHECKED names equal the host CHECK names plus the host CHECK_APPLIED
     names, each exactly once;
  5. the last DEATHS equals deathsBase (F's pikmin_deaths, else 0) plus the
     host deaths.txt line count, and the last deaths.txt line equals its line
     count (no DEATHS lines when there is no deaths.txt);
  6. the DEATHLINK lines equal, in order, the host's applied stream totals:
     the `[Pikmin Randomizer] DEATHLINK_TOTAL <n>` lines both peers print
     when an applied snapshot raises the session total (fix round 1, review
     E7: the host's final state.txt can be written after the last apply);
  7. EMPEROR is present exactly when host emperor.txt exists;
  8. the RECEIVED lines equal F's received list in index order (none without
     F);
  9. the stateful rules the root M4c ingest (MirrorStore.apply) treats as
     fatal, replayed over the whole file (fix round 1, review R8/E7): DEATHS
     and DEATHLINK totals never decrease, RECEIVED indices run 0, 1, 2, ...
     with no gap or repeat, and EMPEROR appears at most once. The
     manifest-level rules (CHECKED names among the manifest's active
     locations, RECEIVED ids in its item pool, death_link / emperor goal
     gating) are not replayed: run_pair's synthetic bootstraps have no
     manifest. Check 4 ties every CHECKED name to a native catalog name the
     host printed instead.

The pure checks live in verify(); tools/netplay/selftest.py drives them with
synthetic run dirs and a local stand-in parser.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

CHECK_RE = re.compile(r"\[Pikmin Randomizer\] CHECK (\d+) (.+)$")
APPLIED_RE = re.compile(r"\[Pikmin Randomizer\] CHECK_APPLIED (\d+) (.+)$")
DEATHLINK_TOTAL_RE = re.compile(r"\[Pikmin Randomizer\] DEATHLINK_TOTAL (\d+)")
JOURNALS = ("checks.txt", "deaths.txt", "emperor.txt", "benefits-used.txt")


def load_root_parser(root):
    root = Path(root).resolve()
    if not (root / "randomizer" / "netplay_mirror.py").exists():
        raise SystemExit(f"check_mirror: {root} has no randomizer/netplay_mirror.py")
    sys.path.insert(0, str(root))
    from randomizer.netplay_mirror import parse_mirror_line  # noqa: E402 (read-only import)
    return parse_mirror_line


def host_log_checks(text):
    """(CHECK names by slot, CHECK_APPLIED names) from a host native log."""
    checks, applied = [], []
    for ln in text.splitlines():
        m = APPLIED_RE.search(ln)
        if m:
            applied.append((int(m.group(1)), m.group(2).rstrip("\r")))
            continue
        m = CHECK_RE.search(ln)
        if m:
            checks.append((int(m.group(1)), m.group(2).rstrip("\r")))
    return checks, applied


def read_text(path):
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return None


def verify(host_run, join_run, parse_line, session=None):
    """Returns a list of failure strings (empty when everything matches)."""
    host_run, join_run = Path(host_run), Path(join_run)
    errors = []
    base = 0
    received = []
    if session is not None:
        base = int(session.get("pikmin_deaths", 0))
        received = list(session.get("received", []))

    # 1. grammar + monotonic frames
    events = []
    mpath = join_run / "mirror-events.txt"
    raw = mpath.read_bytes() if mpath.exists() else b""
    if raw and not raw.endswith(b"\n"):
        errors.append("mirror-events.txt does not end with a newline")
    last_frame = -1
    for n, bline in enumerate(raw.split(b"\n")[:-1] if raw else [], 1):
        try:
            line = bline.decode("ascii")
        except UnicodeDecodeError:
            errors.append(f"mirror line {n}: not ASCII")
            continue
        try:
            frame, tag, args = parse_line(line)
        except ValueError as exc:
            errors.append(f"mirror line {n}: {exc}: {line!r}")
            continue
        if frame < last_frame:
            errors.append(f"mirror line {n}: frame {frame} < previous {last_frame}")
        last_frame = frame
        events.append((frame, tag, args))

    # 2. which peer wrote what
    if (host_run / "mirror-events.txt").exists():
        errors.append("host has a mirror-events.txt")
    for name in JOURNALS:
        if (join_run / name).exists():
            errors.append(f"join has {name}")

    # 3. host checks.txt == host CHECK slots, unique
    log = read_text(host_run / "native.log") or ""
    checks, applied = host_log_checks(log)
    ctext = read_text(host_run / "checks.txt")
    clines = [ln.strip() for ln in (ctext or "").splitlines() if ln.strip()]
    if len(clines) != len(set(clines)):
        errors.append(f"host checks.txt has duplicate lines: {clines}")
    bootstrap = read_text(host_run / "bootstrap.txt") or ""
    thelynk = bootstrap.startswith("PIKMIN_THELYNK 1")
    slots = sorted(str(71400 + slot if slot < 30 else 71500 + slot - 30)
                   if thelynk else str(slot) for slot, _ in checks)
    if sorted(clines) != slots:
        errors.append(f"host checks.txt {sorted(clines)} != CHECK log slots {slots}")

    # 4. CHECKED == CHECK + CHECK_APPLIED names, each exactly once
    checked = Counter(a[0] for _f, t, a in events if t == "CHECKED")
    want = Counter([nm for _s, nm in checks] + [nm for _s, nm in applied])
    if checked != want:
        errors.append(f"CHECKED {dict(checked)} != host CHECK+CHECK_APPLIED {dict(want)}")
    if any(v != 1 for v in checked.values()):
        errors.append("a CHECKED name appears more than once")

    # 5. DEATHS
    dtext = read_text(host_run / "deaths.txt")
    dlines = [ln.strip() for ln in (dtext or "").splitlines() if ln.strip()]
    deaths = [a[0] for _f, t, a in events if t == "DEATHS"]
    if dlines:
        if dlines[-1] != str(len(dlines)):
            errors.append(f"deaths.txt last line {dlines[-1]} != line count {len(dlines)}")
        if not deaths or deaths[-1] != base + len(dlines):
            errors.append(f"last DEATHS {deaths[-1] if deaths else None} != base {base} + "
                          f"{len(dlines)} deaths.txt lines")
    elif deaths:
        errors.append(f"DEATHS lines {deaths} without a host deaths.txt")

    # 6. DEATHLINK == the host's applied totals, in order
    links = [a[0] for _f, t, a in events if t == "DEATHLINK"]
    applied_links = [int(m.group(1)) for m in DEATHLINK_TOTAL_RE.finditer(log)]
    if links != applied_links:
        errors.append(f"DEATHLINK lines {links} != host applied DEATHLINK_TOTAL {applied_links}")

    # 7. EMPEROR
    emperor = sum(1 for _f, t, _a in events if t == "EMPEROR")
    has_file = (host_run / "emperor.txt").exists()
    if (emperor > 0) != has_file or emperor > 1:
        errors.append(f"EMPEROR lines {emperor} vs host emperor.txt exists={has_file}")

    # 8. RECEIVED
    rec = [a for _f, t, a in events if t == "RECEIVED"]
    want_rec = [(i, item) for i, item in enumerate(received)]
    if [tuple(r) for r in rec] != want_rec:
        errors.append(f"RECEIVED {rec} != session received {want_rec}")

    # 9. stateful ingest rules (root MirrorStore.apply raises on these)
    last = {"DEATHS": None, "DEATHLINK": None}
    next_index = 0
    for frame, tag, args in events:
        if tag in last:
            if last[tag] is not None and args[0] < last[tag]:
                errors.append(f"{tag} retracted at frame {frame}: {args[0]} < {last[tag]}")
            last[tag] = args[0]
        elif tag == "RECEIVED":
            if args[0] != next_index:
                errors.append(f"RECEIVED index {args[0]} at frame {frame}, expected {next_index}")
            next_index = max(next_index, args[0] + 1)

    return errors, Counter(t for _f, t, _a in events)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host-run", type=Path, required=True)
    ap.add_argument("--join-run", type=Path, required=True)
    ap.add_argument("--session-json", type=Path, default=None)
    ap.add_argument("--root-mirror", type=Path, required=True)
    a = ap.parse_args(argv)
    parse_line = load_root_parser(a.root_mirror)
    session = json.loads(a.session_json.read_text()) if a.session_json else None
    errors, tags = verify(a.host_run, a.join_run, parse_line, session)
    print(f"check_mirror: mirror events by tag: {dict(sorted(tags.items()))}")
    for e in errors:
        print(f"check_mirror: FAIL: {e}")
    print(f"check_mirror: {'PASS' if not errors else 'FAIL'}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
