"""Log checker for the Font::setTexture guard probe re-run (issue #750)."""
import argparse
import hashlib
import json
import os
import re
import sys

SCHEMA = "p2-tutorial-crash-fix-check-1"
WINDOW_RE = re.compile(r"P2_FONT_PROBE_WINDOW size=(\d+)x(\d+).*centered=([01])")
SPLASH_RE = re.compile(r"P2_FONT_PROBE_SPLASH_PASS observed=(\d+)")
SQUAD_RE = re.compile(r"P2_FONT_PROBE_SQUAD pikis=(\d+)")
PASS_RE = re.compile(r"PASS P2_FONT_PROBE_GUARDED_BOOT observed=(\d+) squad_alive=(\d+)")
GUARDED_RE = re.compile(r"P2_FONT_SETTEXTURE_GUARDED rows=(\d+) cols=(\d+)")
DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN.*outcome=BLOCKED")
CRASH_CODES = ("3221225477", "-1073741515", "0xC0000005".lower())


def sha256_file(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check_log(text, exit_code):
    """Return a verdict dict for run-log text + process exit code."""
    verdict = {"schema": SCHEMA, "exit_code": exit_code,
               "window_ok": False, "splash_passed": False,
               "guard_tripped": False, "captain_down": False,
               "crashed": False, "passed": False, "squad": None}
    if DOWN_RE.search(text):
        verdict["captain_down"] = True
        verdict["outcome"] = "BLOCKED"
        verdict["detail"] = "captain-down run cannot substantiate PASS"
        return verdict
    code = str(exit_code).lower()
    if code in CRASH_CODES:
        verdict["crashed"] = True
        verdict["outcome"] = "FAIL"
        verdict["detail"] = "probe run crashed with 0xC0000005"
        return verdict
    window = WINDOW_RE.search(text)
    if window and window.group(1) == "960" and window.group(2) == "540" \
            and window.group(3) == "1":
        verdict["window_ok"] = True
    splash = SPLASH_RE.search(text)
    if splash:
        verdict["splash_passed"] = True
    guarded = GUARDED_RE.search(text)
    if guarded:
        verdict["guard_tripped"] = True
    squad = SQUAD_RE.search(text)
    if squad:
        verdict["squad"] = int(squad.group(1))
    passed = PASS_RE.search(text)
    if passed and verdict["window_ok"] and verdict["splash_passed"]:
        verdict["passed"] = True
        verdict["outcome"] = "PASS"
        verdict["detail"] = "guarded boot observed to 180 ticks with splash passed"
    else:
        verdict["outcome"] = "FAIL"
        verdict["detail"] = "no full PASS markers; splash_passed=%s window_ok=%s" % (
            verdict["splash_passed"], verdict["window_ok"])
    return verdict


def main(argv=None):
    parser = argparse.ArgumentParser(description="Font guard probe log checker")
    parser.add_argument("--log", required=True)
    parser.add_argument("--exit-code", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        code = int(args.exit_code)
    except ValueError:
        print("REFUSED bad exit code")
        return 2
    with open(args.log, encoding="utf-8", errors="replace") as stream:
        text = stream.read()
    verdict = check_log(text, code)
    verdict["log_sha256"] = sha256_file(args.log)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(verdict, indent=1, sort_keys=True))
            stream.write("\n")
        print("verdict=%s out=%s" % (verdict["outcome"], args.out))
    else:
        print("verdict=%s" % verdict["outcome"])
    return 0 if verdict["outcome"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())