"""Diff two netplay desync state dumps (issue #1037).

Each game writes `desync-objects.txt` into its run folder when GekkoNet reports
a desync (one section per tick, `# tick N: ...`, then one line per object:
`kind ord=.. type=.. state=.. hp=.. pos=(..) rot=(..) vel=(..) drv=(..) face=..
aux=[..] hash=.. xhash=..`). The replay (`replay_session.py --dump-ticks`)
writes `replay-objects.txt` in the same format, so a replay can be diffed
against either game's dump.

  py -3.12 tools/netplay/diff_desync.py <host run>/desync-objects.txt <join run>/desync-objects.txt

Prints, per tick present in both files, the objects whose lines differ (the
differing fields named), the objects present in one file only, and a summary.
Exit code 0: no difference; 1: at least one differing or missing object.
Whitespace and the section comment lines are ignored.
"""

import re
import sys
from pathlib import Path

TICK_RE = re.compile(r"^# tick (\d+)")
FIELD_RE = re.compile(r"(\w+)=(\([^)]*\)|\[[^\]]*\]|\S+)")


def parse(path):
    """{tick: {(kind, ord): {field: value}}}, plus the raw lines for display."""
    ticks = {}
    cur = None
    for ln in Path(path).read_text(errors="replace").splitlines():
        m = TICK_RE.match(ln)
        if m:
            cur = int(m.group(1))
            ticks.setdefault(cur, {})
            continue
        if not ln.strip() or ln.startswith("#"):
            continue
        if cur is None:
            continue
        kind, _, rest = ln.partition(" ")
        fields = dict(FIELD_RE.findall(rest))
        key = (kind, int(fields.get("ord", "0")))
        ticks[cur][key] = {"fields": fields, "line": ln}
    return ticks


def diff(a_path, b_path, out=print):
    a = parse(a_path)
    b = parse(b_path)
    common = sorted(set(a) & set(b))
    out(f"ticks in {Path(a_path).name}: {sorted(a)}; in {Path(b_path).name}: {sorted(b)}")
    n_diff = 0
    first_tick = None
    differing = []
    for t in common:
        da, db = a[t], b[t]
        tick_diffs = []
        for key in sorted(set(da) | set(db)):
            oa, ob = da.get(key), db.get(key)
            if oa is None or ob is None:
                tick_diffs.append((key, "only in " + (Path(a_path).parent.name if ob is None else Path(b_path).parent.name), None))
                continue
            names = [f for f in oa["fields"] if oa["fields"][f] != ob["fields"].get(f)]
            if names:
                tick_diffs.append((key, ",".join(names), (oa, ob)))
        if tick_diffs:
            n_diff += len(tick_diffs)
            if first_tick is None:
                first_tick = t
            out(f"tick {t}: {len(tick_diffs)} object(s) differ")
            for key, what, pair in tick_diffs[:40]:
                out(f"  {key[0]}#{key[1]}: {what}")
                if pair is not None:
                    for name in what.split(","):
                        if name in ("hash", "xhash"):
                            continue
                        out(f"      {name}: {pair[0]['fields'].get(name)}  vs  {pair[1]['fields'].get(name)}")
                differing.append((t, key))
            if len(tick_diffs) > 40:
                out(f"  ... {len(tick_diffs) - 40} more")
        else:
            out(f"tick {t}: identical ({len(da)} objects)")
    if not common:
        out("no tick is present in both files")
    out(f"summary: {n_diff} differing object(s)" + (f", first at tick {first_tick}" if first_tick else ""))
    return n_diff, first_tick, differing


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__)
        return 2
    n, _first, _d = diff(argv[0], argv[1])
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
