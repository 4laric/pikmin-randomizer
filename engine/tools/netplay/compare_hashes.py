"""Compare two netplay state-hash logs.

Usage: compare_hashes.py A B

Exit 0 if identical. Otherwise prints the first divergent tick and which
sub-hash columns differ there, then exits 1. Also exits 1 (with a reason)
when the files have different line counts or a line fails to parse.
"""

import sys

COLUMNS = ["total", "navi", "piki", "teki", "item", "world", "rng", "rand"]


def parse_line(line, lineno, path):
    parts = line.split()
    if len(parts) != 8 and len(parts) != 9:
        return None, f"{path}:{lineno}: expected 8 or 9 columns, got {len(parts)}"
    tick_tok = parts[0]
    try:
        # Tick is decimal; accept 16-digit hex too (forward compatibility).
        if len(tick_tok) == 16 and all(
            c in "0123456789abcdefABCDEF" for c in tick_tok
        ):
            try:
                tick = int(tick_tok, 16)
            except ValueError:
                tick = int(tick_tok)
        else:
            tick = int(tick_tok)
    except ValueError:
        return None, f"{path}:{lineno}: bad tick {tick_tok!r}"
    hashes = []
    for tok in parts[1:]:
        if len(tok) != 16 or any(c not in "0123456789abcdefABCDEF" for c in tok):
            return None, f"{path}:{lineno}: bad hash {tok!r}"
        hashes.append(tok.lower())
    return (tick, hashes), None


def main(argv):
    if len(argv) != 3:
        print("usage: compare_hashes.py A B", file=sys.stderr)
        return 2
    with open(argv[1], "r", errors="replace") as f:
        lines_a = f.read().splitlines()
    with open(argv[2], "r", errors="replace") as f:
        lines_b = f.read().splitlines()

    rows_a = [ln for ln in lines_a if ln.strip()]
    rows_b = [ln for ln in lines_b if ln.strip()]
    if rows_a and rows_b:
        wa = len(rows_a[0].split())
        wb = len(rows_b[0].split())
        if wa != wb:
            print(f"width mismatch: {argv[1]} has {wa} columns, {argv[2]} has {wb} columns "
                  f"(8 = legacy, 9 = with rand)")
            return 1
    # m6 fix: the width must hold on every row, not just the first (a
    # mid-file truncation from 9 to 8 columns used to compare misaligned).
    for path, rows in ((argv[1], rows_a), (argv[2], rows_b)):
        expect = len(rows[0].split()) if rows else 0
        for i, ln in enumerate(rows):
            if len(ln.split()) != expect:
                print(f"{path}:{i + 1}: expected {expect} columns, got {len(ln.split())}")
                return 1
    n = min(len(rows_a), len(rows_b))
    for i in range(n):
        pa, err = parse_line(rows_a[i].strip(), i + 1, argv[1])
        if err is not None:
            print(err)
            return 1
        pb, err = parse_line(rows_b[i].strip(), i + 1, argv[2])
        if err is not None:
            print(err)
            return 1
        if pa != pb:
            ta, ha = pa
            tb, hb = pb
            if ta != tb:
                print(f"first divergence at file line {i + 1}: tick {ta} vs {tb}")
            else:
                diff = [c for c, x, y in zip(COLUMNS, ha, hb) if x != y]
                print(f"first divergence at tick {ta}: columns differ: {', '.join(diff)}")
                for c, x, y in zip(COLUMNS, ha, hb):
                    if x != y:
                        print(f"  {c}: {x} vs {y}")
            return 1
    if len(rows_a) != len(rows_b):
        print(
            f"length mismatch: {argv[1]} has {len(rows_a)} lines, "
            f"{argv[2]} has {len(rows_b)} lines (first {n} identical)"
        )
        return 1
    print(f"identical: {len(rows_a)} ticks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
