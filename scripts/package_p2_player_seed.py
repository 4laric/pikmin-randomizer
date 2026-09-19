"""Build a checked PLAYER launch package for the pinned P2 seed (#643)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experimental.pikmin2_player_package import (
    PreflightFailed,
    preflight,
    write_launch_package,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-dir', type=Path, required=True)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--native-root', type=Path, default=None)
    parser.add_argument('--native-exe', type=Path, default=None)
    parser.add_argument('--session-base', type=Path, default=None)
    parser.add_argument('--write', action='store_true',
                        help='Write Play.cmd + launch.py only if preflight passes')
    args = parser.parse_args(argv)
    try:
        if args.write:
            result = write_launch_package(
                args.seed_dir, args.tree,
                str(args.native_root) if args.native_root else None,
                str(args.native_exe) if args.native_exe else None,
                str(args.session_base) if args.session_base else None)
            print(json.dumps(dict(ok=True, **result), indent=2))
        else:
            ok, gaps, evidence = preflight(
                args.seed_dir, args.tree,
                str(args.native_root) if args.native_root else None,
                str(args.native_exe) if args.native_exe else None)
            print(json.dumps(dict(ok=ok, gaps=gaps, evidence=evidence), indent=2))
            if not ok:
                return 1
        return 0
    except PreflightFailed as exc:
        print(json.dumps(dict(ok=False, gaps=[str(exc)], evidence={}), indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
