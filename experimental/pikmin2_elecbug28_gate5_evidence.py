"""Evidence comparison for the staged ElecBug28 gate-5 receipt (#585).

Reads the #585 and #578 handoffs plus the #585 run evidence read-only and
reports a side-by-side verdict. No runtime, no builds, no writes. Every
observation is labelled staged versus natural; nothing here flips a gate.
"""
import json
import re

RECEIPT_RE = re.compile(r"P2_ORDINARY_P2_RECEIPT\s+seed=(\S+)\s+id=(\S+).*?\bnew=(\d)")
DIED_RE = re.compile(r"P2_ELECBUG28_DIED\s+tick=(\d+)\s+health=([0-9.]+)")
CORPSE_RE = re.compile(r"P2_ELECBUG28_CORPSE\s+pellet=(\d+)")
MOVED_RE = re.compile(r"P2_ELECBUG28_DELIVERED_TO_GOAL\s+tick=(\d+)\s+moved=([0-9.]+)")
BIND_RE = re.compile(r"P2_ELECBUG_DELIVERY_BIND\s+generator=(\d+)\s+source_id=28")
LEDGER_RE = re.compile(r"^(\S+)\s+(\S+)\s+g(\d+)\s+corpse\s*$")


def parse_receipt_line(line):
    match = RECEIPT_RE.search(line)
    if not match:
        return None
    return match.group(1), match.group(2), int(match.group(3))


def summarize_run_log(text):
    receipts = [r for r in (parse_receipt_line(l) for l in text.splitlines()) if r]
    died = DIED_RE.search(text)
    corpse = CORPSE_RE.search(text)
    moved = MOVED_RE.search(text)
    return {
        "receipts": receipts,
        "died_tick": int(died.group(1)) if died else None,
        "died_health": float(died.group(2)) if died else None,
        "corpse_pellets": int(corpse.group(1)) if corpse else None,
        "haul_moved": float(moved.group(2)) if moved else None,
        "bind_generators": sorted(set(BIND_RE.findall(text))),
    }


def parse_ledger(text):
    rows = []
    for line in text.splitlines()[1:]:
        match = LEDGER_RE.match(line.strip())
        if match:
            rows.append((match.group(1), match.group(2), int(match.group(3))))
    return rows


def compare_against_standard(run1, run2, ledger_rows, handoff585, handoff578):
    findings = {}
    r1 = [r for r in run1["receipts"] if r[1].startswith("onion:p2:28")]
    r2 = [r for r in run2["receipts"] if r[1].startswith("onion:p2:28")]
    findings["endpoint_real_ordinary"] = bool(r1 and r2)
    findings["exactly_once_across_restart"] = (
        len(r1) == 1 and r1[0][2] == 1 and len(r2) == 1 and r2[0][2] == 0
        and r1[0][:2] == r2[0][:2])
    if r1:
        findings["shared_session_ledger"] = (
            len(ledger_rows) == 1 and ledger_rows[0][1] == "onion:p2:28:0"
            and ledger_rows[0][1] == r1[0][1])
    else:
        findings["shared_session_ledger"] = False
    findings["natural_death_no_write"] = (
        run1["died_health"] == 0.0 and run1["corpse_pellets"] == 1)
    findings["natural_haul_distance"] = run1["haul_moved"]
    g578 = handoff578.get("gates", {}).get("transport_reward", {})
    findings["standard_578_transport"] = g578.get("status")
    g585 = handoff585.get("gates", {})
    findings["staged_585_all_untested"] = all(
        g.get("status") == "UNTESTED" for g in g585.values())
    uphold = all([
        findings["endpoint_real_ordinary"],
        findings["exactly_once_across_restart"],
        findings["shared_session_ledger"],
        findings["natural_death_no_write"],
        bool(findings["natural_haul_distance"]),
    ])
    findings["recommendation"] = "UPHOLD-STAGED-TOOLING" if uphold else "NATURAL-EXPERIMENT-REQUIRED"
    return findings


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run1", required=True)
    parser.add_argument("--run2", required=True)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--handoff585", required=True)
    parser.add_argument("--handoff578", required=True)
    args = parser.parse_args()

    def read(path):
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()

    result = compare_against_standard(
        summarize_run_log(read(args.run1)),
        summarize_run_log(read(args.run2)),
        parse_ledger(read(args.ledger)),
        json.loads(read(args.handoff585)),
        json.loads(read(args.handoff578)))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
