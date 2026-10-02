"""Day-end save comparison for netplay M4 lane B2 (issue #885).

After a pair crossed a day end, the host's real campaign checkpoint and card
must be byte-equal to the client's mirror, and the client's
mirror-events.txt must carry the SAVE_RESULT of that checkpoint:

  1. the newest %020llu.sav in --host-campaign and --join-campaign have the
     same name and the same bytes;
  2. every file in <campaign>/card/card0/ is byte-equal between the two
     (same names, same bytes);
  3. <join-run>/mirror-events.txt contains `FRAME <f> SAVE_RESULT <gen>
     <sha256 of that .sav>`, parsed with the root M4c reference parser
     randomizer/netplay_mirror.py:parse_mirror_line (imported read-only from
     --root-m4c), and every line of the file parses;
  4. (fix round 1, X9) the file also passes the root runner's ingest rules
     (randomizer/runner.py MirrorRun.poll): ASCII, newline terminated, no
     blank line, frames never decrease (exact duplicate lines excepted).

--root-m4c is required unless the default root checkout exists; there is no
silent fallback to another copy of the parser.

Exit 0 when all hold, 1 otherwise. Read-only: it never writes anything.

  py -3.12 tools/netplay/check_saves.py --host-campaign OUT/campaign \
      --join-campaign OUT/join/campaign --join-run OUT/join/peer/run
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

SAV = re.compile(r"^\d{20}\.sav$")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def newest_sav(campaign):
    savs = sorted(p for p in Path(campaign).glob("*.sav") if SAV.match(p.name))
    return savs[-1] if savs else None


def card_files(campaign):
    card0 = Path(campaign) / "card" / "card0"
    if not card0.is_dir():
        return {}
    return {p.name: p for p in sorted(card0.iterdir()) if p.is_file()}


def load_parser(root):
    if root is None:
        raise SystemExit("check_saves: pass --root-m4c with the actual pinned consumer checkout")
    if not (Path(root) / "randomizer" / "netplay_mirror.py").is_file():
        raise SystemExit(f"check_saves: {root} has no randomizer/netplay_mirror.py")
    sys.path.insert(0, str(Path(root)))
    from randomizer.netplay_mirror import parse_mirror_line  # noqa: E402
    return parse_mirror_line, Path(root)


def ingest_rules(raw):
    """The root runner's stream rules (runner.py MirrorRun.poll) over the whole
    file; returns a list of violations (empty = ok). Line grammar is checked
    separately with parse_mirror_line."""
    bad = []
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return ["mirror event file is not ASCII"]
    if text and not text.endswith("\n"):
        bad.append("mirror event batch is not newline terminated")
    lines = text.split("\n")[:-1] if text.endswith("\n") else text.split("\n")
    if any(ln == "" for ln in lines):
        bad.append("invalid mirror event: blank line")
    running, seen = -1, set()
    for ln in lines:
        if ln in seen or not ln.startswith("FRAME "):
            continue
        seen.add(ln)
        try:
            frame = int(ln.split(" ")[1])
        except (IndexError, ValueError):
            continue
        if frame < running:
            bad.append(f"mirror frame retracted: {ln}")
        running = max(running, frame)
    return bad


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host-campaign", type=Path, required=True)
    p.add_argument("--join-campaign", type=Path, required=True)
    p.add_argument("--join-run", type=Path, required=True, help="the client's run dir (mirror-events.txt)")
    p.add_argument("--root-m4c", type=Path, required=True,
                   help="Actual pinned root checkout holding randomizer/netplay_mirror.py")
    a = p.parse_args(argv)
    ok = True

    hs, js = newest_sav(a.host_campaign), newest_sav(a.join_campaign)
    if hs is None or js is None:
        print(f"check_saves: FAIL: newest checkpoint host={hs} join={js}")
        return 1
    hsha, jsha = sha256(hs), sha256(js)
    same = hs.name == js.name and hs.read_bytes() == js.read_bytes()
    print(f"check_saves: newest checkpoint host={hs.name} {hsha} ({hs.stat().st_size} B)")
    print(f"check_saves: newest checkpoint join={js.name} {jsha} ({js.stat().st_size} B)")
    print(f"check_saves: checkpoint byte-equal: {same}")
    ok = ok and same

    hc, jc = card_files(a.host_campaign), card_files(a.join_campaign)
    if not hc:
        print("check_saves: FAIL: the host has no card files")
        ok = False
    if sorted(hc) != sorted(jc):
        print(f"check_saves: FAIL: card file names differ host={sorted(hc)} join={sorted(jc)}")
        ok = False
    for name in sorted(set(hc) & set(jc)):
        eq = hc[name].read_bytes() == jc[name].read_bytes()
        print(f"check_saves: card/card0/{name}: host {sha256(hc[name])} join {sha256(jc[name])} "
              f"byte-equal: {eq}")
        ok = ok and eq

    parse, used = load_parser(a.root_m4c)
    print(f"check_saves: mirror grammar from {used / 'randomizer' / 'netplay_mirror.py'}")
    gen = int(hs.name[:20])
    mirror = a.join_run / "mirror-events.txt"
    try:
        raw = mirror.read_bytes()
    except OSError:
        print(f"check_saves: FAIL: no {mirror}")
        return 1
    violations = ingest_rules(raw)
    for v in violations:
        print(f"check_saves: FAIL: root ingest rule: {v}")
    print(f"check_saves: root ingest rules (ASCII, newline terminated, no blank line, frames never decrease): "
          f"{'ok' if not violations else 'VIOLATED'}")
    ok = ok and not violations
    lines = raw.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    found = []
    for i, ln in enumerate(lines, 1):
        try:
            frame, tag, args = parse(ln.decode("ascii"))
        except (ValueError, UnicodeDecodeError) as e:
            print(f"check_saves: FAIL: mirror line {i} rejected by parse_mirror_line: {ln!r} ({e})")
            ok = False
            continue
        if tag in ("SAVE_RESULT", "SAVE_FAIL"):
            print(f"check_saves: mirror line {i}: {ln.decode('ascii')}")
        if tag == "SAVE_RESULT" and args[0] == gen and args[1] == hsha:
            found.append(frame)
    print(f"check_saves: mirror SAVE_RESULT {gen} {hsha}: {'found at frame ' + str(found[0]) if found else 'MISSING'}"
          f" ({len(lines)} lines parsed)")
    ok = ok and bool(found)
    print(f"check_saves: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
