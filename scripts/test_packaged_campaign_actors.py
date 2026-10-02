"""Run the extracted launch command through real staging, stopping before native.

Uses supplied legal prepared content. Only the native process boundary is
intercepted; no family installer, actor, seed, or receipt is mocked.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--content", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect", choices=("staged", "missing-actors"), required=True)
    args = parser.parse_args()
    package = args.package.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise ValueError("preserve prior evidence; use a fresh output directory")
    output.mkdir(parents=True)
    sys.path.insert(0, str(package / "launcher"))
    sys.path.insert(0, str(package))
    import launcher
    from randomizer import runner

    assert Path(runner.__file__).is_relative_to(package)
    assert Path(launcher.__file__).is_relative_to(package)
    command = launcher.build_command(args.seed, output / "session", package / "bin/nectar.exe",
                                     args.assets, p2_content=args.content)
    assert "--p2-actors" not in command
    observed = {}

    class Staged(BaseException):
        pass

    def stop_native(argv, **kwargs):
        run = Path(kwargs["cwd"])
        receipt = json.loads((run / "p2-binding-receipt.json").read_text())
        manifest = json.loads(args.seed.read_text())
        expected = {row["target"]: int(row["target"])
                    for row in manifest["p2_layout"]["bindings"]}
        assert receipt["bindings"] == manifest["p2_layout"]["bindings"]
        canonical = {"bindings": receipt["bindings"], "actor_bindings": expected}
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True,
                                          separators=(",", ":")).encode()).hexdigest()
        assert receipt["plan_digest"] == digest
        for name, expected_sha256 in receipt["files"].items():
            assert hashlib.sha256((run / name).read_bytes()).hexdigest() == expected_sha256, name
        observed.update(native_argv=argv, run=str(run), actor_count=len(expected),
                        identity_count=len({b["source_id"] for b in receipt["bindings"]}),
                        receipt_sha256=hashlib.sha256((run / "p2-binding-receipt.json").read_bytes()).hexdigest(),
                        cached=bool(receipt.get("cached")))
        raise Staged

    runner.subprocess.Popen = stop_native
    sys.argv = command[3:]
    failure = None
    import contextlib
    import io
    cli_output = io.StringIO()
    try:
        with contextlib.redirect_stdout(cli_output), contextlib.redirect_stderr(cli_output):
            runpy.run_module("randomizer", run_name="__main__")
    except Staged:
        assert args.expect == "staged"
    except SystemExit as error:
        failure = str(error)
        assert args.expect == "missing-actors" and error.code != 0
        assert "no actor generator binding" in cli_output.getvalue(), cli_output.getvalue()
        assert not observed
    else:
        raise AssertionError("launch unexpectedly returned without reaching staging boundary")
    result = dict(scope="actual extracted launch command and real staging; native not started",
                  package=str(package), command=command, expected=args.expect,
                  observed=observed, cli_exit=failure)
    (output / "cli.log").write_text(cli_output.getvalue(), encoding="utf-8")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
