'''Landing-presence checker for the accepted #129 cave generator provider.

Review-only tool (lane cave-generator-landing-contract-review): given a native
source tree, assert the provider landing is present without building anything:

- pc_port/pc_p2_cave_generate.h exists and declares
  pc_p2_cave_generate_run (inline bool, observed in e44b5d70);
- pc_port/pc_p2_cave_generate.cpp exists and references
  kP2CaveGenerateModule;
- pc_port/pc_p2_cave.cpp contains the hook include for
  pc_p2_cave_generate.h and the hook call pc_p2_cave_generate_run().

Pure presence/content assertions on the supplied tree; no invented values,
no gameplay claims. Stdlib only.
'''
import argparse
import json
from pathlib import Path

HEADER = "pc_port/pc_p2_cave_generate.h"
TU = "pc_port/pc_p2_cave_generate.cpp"
HOOK_FILE = "pc_port/pc_p2_cave.cpp"
HEADER_MARKER = "pc_p2_cave_generate_run"
TU_MARKER = "kP2CaveGenerateModule"
HOOK_INCLUDE = '#include "pc_p2_cave_generate.h"'
HOOK_CALL = "pc_p2_cave_generate_run();"


def check_landing(native_root):
    """Return {checks, passed} for a native source tree path."""
    root = Path(native_root)
    checks = {}
    header = root / HEADER
    text = header.read_text(encoding="utf-8", errors="replace") if header.is_file() else ""
    checks["module_header"] = bool(header.is_file() and HEADER_MARKER in text)
    tu = root / TU
    text = tu.read_text(encoding="utf-8", errors="replace") if tu.is_file() else ""
    checks["module_tu"] = bool(tu.is_file() and TU_MARKER in text)
    hook = root / HOOK_FILE
    text = hook.read_text(encoding="utf-8", errors="replace") if hook.is_file() else ""
    checks["hook_include"] = bool(hook.is_file() and HOOK_INCLUDE in text)
    checks["hook_call"] = bool(hook.is_file() and HOOK_CALL in text)
    return {"checks": checks, "passed": all(checks.values())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", required=True, help="native source tree to inspect")
    args = parser.parse_args(argv)
    report = check_landing(args.native)
    print(json.dumps(report, indent=1))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()