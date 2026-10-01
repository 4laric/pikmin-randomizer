"""Fail-closed tests for the boot-flag delivery checker.

Positive case runs the checker against the real pinned launch config and
registry. Negative cases prove refusal on tampered pins, missing input and
malformed config. Exits 0 only when every case passes. Writes a JSON report.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
WORKTREE = HERE.parent.parent
CHECKER = WORKTREE / "scripts" / "p2_yakushima_boot_flag_delivery.py"


def run_checker(extra):
    completed = subprocess.run(
        [sys.executable, str(CHECKER)] + extra,
        capture_output=True, text=True, timeout=120)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Test boot-flag delivery checker")
    parser.add_argument("--root", default="C:/Users/alari/pikmin-randomizer")
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root)
    launch = root / "output/workflow/autofill/planning-shards/provider-save-progression/prepared/yakushima-boot-flag-delivery-launch"
    outdir = root / "output/workflow/autofill/planning-shards/provider-save-progression/prepared/yakushima-boot-flag-delivery-output"
    config = launch / "config.json"
    proof = launch / "issue-767-proof.json"
    packet = outdir / "yakushima-boot-flag-delivery-packet.json"
    base = ["--root", str(root), "--config", str(config), "--issue-proof", str(proof), "--out", str(packet)]
    cases = []
    try:
        config_data = json.loads(config.read_text(encoding="utf-8-sig"))
        pinned_sha = (config_data.get("handoff") or {}).get("sha256")
        downstream_issue = (config_data.get("downstream") or {}).get("issue")
        rc, output = run_checker(base)
        packet_data = json.loads(packet.read_text(encoding="utf-8")) if packet.is_file() else {}
        positive = (rc == 0 and "DELIVERY_VERIFIED" in output
                    and packet_data.get("handoff", {}).get("sha256") == pinned_sha
                    and packet_data.get("evidence_verified", {}).get("count") == 11
                    and packet_data.get("downstream", {}).get("issue") == downstream_issue == 150)
        cases.append({"name": "positive-pinned-verification", "exit_code": rc, "pass": bool(positive), "detail": output.strip().splitlines()[-1] if output.strip() else "no output"})
        rc, output = run_checker(base + ["--expect-sha", "0" * 64])
        cases.append({"name": "refuse-tampered-sha", "exit_code": rc, "pass": rc != 0 and "DELIVERY_REFUSED" in output, "detail": output.strip().splitlines()[-1] if output.strip() else "no output"})
        rc, output = run_checker(base + ["--handoff-path", str(outdir / "does-not-exist.json")])
        cases.append({"name": "refuse-missing-handoff", "exit_code": rc, "pass": rc != 0 and "DELIVERY_REFUSED" in output, "detail": output.strip().splitlines()[-1] if output.strip() else "no output"})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="ascii") as stream:
            stream.write("{not valid json")
            bad_config = stream.name
        rc, output = run_checker(["--root", str(root), "--config", bad_config, "--issue-proof", str(proof), "--out", str(packet)])
        cases.append({"name": "refuse-malformed-config", "exit_code": rc, "pass": rc != 0 and "DELIVERY_REFUSED" in output, "detail": output.strip().splitlines()[-1] if output.strip() else "no output"})
        rc, output = run_checker(["--root", str(root), "--config", str(outdir / "does-not-exist.json"), "--issue-proof", str(proof), "--out", str(packet)])
        cases.append({"name": "refuse-missing-config", "exit_code": rc, "pass": rc != 0 and "DELIVERY_REFUSED" in output, "detail": output.strip().splitlines()[-1] if output.strip() else "no output"})
    except Exception as exc:
        cases.append({"name": "harness-error", "exit_code": -1, "pass": False, "detail": type(exc).__name__ + ": " + str(exc)[:200]})
    report = {"cases": cases, "passed": sum(1 for c in cases if c["pass"]), "failed": sum(1 for c in cases if not c["pass"])}
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for case in cases:
        sys.stdout.write(("PASS " if case["pass"] else "FAIL ") + case["name"] + " rc=" + str(case["exit_code"]) + "\n")
    sys.stdout.write("RESULT passed=" + str(report["passed"]) + " failed=" + str(report["failed"]) + "\n")
    return 0 if report["failed"] == 0 and report["passed"] == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
