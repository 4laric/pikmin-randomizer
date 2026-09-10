import argparse
import json
from pathlib import Path
from .seed import generate, validate, fingerprint, solo_rewards, spheres
from .runner import launch


def main():
    parser = argparse.ArgumentParser(description="Pikmin Randomizer: standalone identity-placement milestone")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--seed", required=True)
    gen.add_argument("--slot", default="Player1")
    gen.add_argument("--mode", choices=["solo", "ap"], default="solo")
    gen.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("validate")
    check.add_argument("manifest", type=Path)
    run = sub.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--session-dir", type=Path, required=True)
    run.add_argument("--exe", type=Path)
    run.add_argument("--assets", type=Path)
    run.add_argument("--server")
    args = parser.parse_args()
    if args.command == "generate":
        manifest = generate(args.seed, args.mode, args.slot)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as f:
            f.write(json.dumps(manifest, indent=2) + "\n")
        print(f"Created {args.output}: 30 checks, 25 repair rewards, 5 unlocks; physical placements pinned")
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validate(manifest)
        if args.command == "validate":
            print(f"Valid {fingerprint(manifest)}; 28 pinned parts, 2 fixed Onion checks")
            if manifest["mode"] == "solo":
                print(f"Conservative logic: {len(spheres(solo_rewards(manifest)))} progression spheres")
        else:
            launch(manifest, args.session_dir.resolve(), args.exe, args.assets, args.server)


if __name__ == "__main__":
    main()
