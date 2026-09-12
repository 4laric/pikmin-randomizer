"""Assemble output/pikrando-<version>-windows-x64.zip from a production build.

    python scripts/package_release.py --version 0.28.0-playtest.1 [--exe PATH] [--dlls DLL ...]
        [--python-embed python-3.12.x-embed-amd64.zip] [--tk-source C:\\Python312]
        [--seed seed.json] [--output-dir output]

Layout inside the zip: bin/ (exe + DLLs), randomizer/ (git-tracked .py only), launcher/, Play.cmd,
examples/Player1.yaml, VERSION, README.md, CHANGELOG.md, LICENSES/, release-manifest.json and,
with --python-embed, runtime/ holding the embeddable CPython with websockets vendored and tkinter
copied from --tk-source. SHA256SUMS.txt is written beside the zip.

The package is refused when it would contain *.pdb, *session.json, native.log, a text file mentioning
C:\\Users\\, or an executable built with test hooks (the string PIKMIN_RANDOMIZER_TEST_SCRIPT; the
production build does not contain it).
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEST_HOOK_MARKER = b"PIKMIN_RANDOMIZER_TEST_SCRIPT"
FORBIDDEN_SUFFIXES = (".pdb",)
FORBIDDEN_NAMES = ("native.log",)
FORBIDDEN_NAME_SUFFIXES = ("session.json",)
TEXT_SUFFIXES = {".py", ".md", ".txt", ".cmd", ".json", ".yaml", ".yml", ".pth", ".cfg", ".ini"}
PERSONAL_PATH = b"C:\\Users\\"
TK_FILES = ("DLLs/_tkinter.pyd", "DLLs/tcl86t.dll", "DLLs/tk86t.dll", "DLLs/zlib1.dll")


class PackageError(Exception):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(args, cwd):
    try:
        return subprocess.check_output(["git", *args], cwd=str(cwd), text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def tracked_python_files(repo):
    listed = git(["ls-files", "randomizer"], repo)
    if listed is None:
        raise PackageError(f"{repo} is not a git checkout; cannot determine tracked randomizer files")
    return [Path(line) for line in listed.splitlines() if line.endswith(".py")]


def copy_tree_files(source, target, relative_paths):
    for relative in relative_paths:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)


# --- Stage assembly ----------------------------------------------------------

def stage_core(repo, stage, exe, dlls, seed):
    if not exe.is_file():
        raise PackageError(f"executable not found: {exe}")
    if TEST_HOOK_MARKER in exe.read_bytes():
        raise PackageError(f"{exe} was built with test hooks (contains {TEST_HOOK_MARKER.decode()}); "
                           "a test-hooks build must not be packaged. Rebuild without test hooks.")
    (stage / "bin").mkdir(parents=True)
    shutil.copy2(exe, stage / "bin" / "nectar.exe")
    for dll in dlls:
        if not dll.is_file():
            raise PackageError(f"runtime DLL not found: {dll}")
        shutil.copy2(dll, stage / "bin" / dll.name)
    copy_tree_files(repo, stage, tracked_python_files(repo))
    copy_tree_files(repo, stage, [Path("launcher/launcher.py")])
    shutil.copy2(repo / "launcher" / "Play.cmd", stage / "Play.cmd")
    copy_tree_files(repo, stage, [Path("examples/Player1.yaml"), Path("README.md")])
    if (repo / "CHANGELOG.md").is_file():
        shutil.copy2(repo / "CHANGELOG.md", stage / "CHANGELOG.md")
    (stage / "LICENSES").mkdir()
    for notice in ("LICENSE.MD", "LEGAL.md"):
        source = repo / "native" / notice
        if not source.is_file():
            raise PackageError(f"license notice missing: {source}")
        shutil.copy2(source, stage / "LICENSES" / notice)
    if seed:
        (stage / "seeds").mkdir()
        shutil.copy2(seed, stage / "seeds" / "seed.json")


def stage_runtime(stage, embed_zip, tk_source):
    """Extract the embeddable CPython, enable site-packages and the package root, vendor websockets."""
    runtime = stage / "runtime"
    with zipfile.ZipFile(embed_zip) as archive:
        archive.extractall(runtime)
    pth_files = list(runtime.glob("python3*._pth"))
    if len(pth_files) != 1:
        raise PackageError(f"expected exactly one python3*._pth in {embed_zip}, found {pth_files}")
    pth = pth_files[0]
    lines = [line for line in pth.read_text(encoding="utf-8").splitlines() if line.strip() not in ("#import site", "import site")]
    lines += ["..", "Lib\\site-packages", "import site"]
    pth.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    site_packages = runtime / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    vendor_websockets(site_packages)
    if tk_source:
        stage_tkinter(runtime, Path(tk_source))
    else:
        print("WARNING: no --tk-source given; tkinter is NOT in the runtime, so the overlay HUD and F8 tracker "
              "will be unavailable to players using the bundled Python.", file=sys.stderr)
    version_file = next((p for p in runtime.glob("python3*.dll")), None)
    return version_from_embed(embed_zip, version_file)


def version_from_embed(embed_zip, dll):
    name = Path(embed_zip).name  # python-3.12.10-embed-amd64.zip
    parts = name.split("-")
    if len(parts) >= 2 and parts[0] == "python":
        return parts[1]
    return dll.stem if dll else "embedded"


def vendor_websockets(site_packages):
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.check_call([sys.executable, "-m", "pip", "download", "websockets>=13,<14", "--no-deps",
                               "--dest", tmp, "--only-binary", ":all:", "--python-version", "3.12",
                               "--platform", "any", "--quiet"])
        wheels = list(Path(tmp).glob("websockets-*.whl"))
        if len(wheels) != 1:
            raise PackageError(f"expected one websockets wheel, found {wheels}")
        with zipfile.ZipFile(wheels[0]) as wheel:
            wheel.extractall(site_packages)
    for native_ext in site_packages.rglob("*.pyd"):
        native_ext.unlink()  # websockets works without its optional C speedups; keep the vendored copy pure Python.


def stage_tkinter(runtime, tk_source):
    lib_tk = tk_source / "Lib" / "tkinter"
    tcl_dir = tk_source / "tcl"
    missing = [p for p in (lib_tk, tcl_dir, *(tk_source / f for f in TK_FILES[:3])) if not p.exists()]
    if missing:
        raise PackageError("--tk-source is missing: " + ", ".join(str(m) for m in missing))
    shutil.copytree(lib_tk, runtime / "Lib" / "tkinter", ignore=shutil.ignore_patterns("__pycache__", "test"))
    shutil.copytree(tcl_dir, runtime / "tcl", dirs_exist_ok=True)
    for relative in TK_FILES:
        source = tk_source / relative
        if source.is_file():
            shutil.copy2(source, runtime / source.name)


# --- Checks and outputs -------------------------------------------------------

def audit(stage):
    problems = []
    for path in sorted(p for p in stage.rglob("*") if p.is_file()):
        relative = path.relative_to(stage).as_posix()
        name = path.name.lower()
        if name.endswith(FORBIDDEN_SUFFIXES) or name in FORBIDDEN_NAMES or name.endswith(FORBIDDEN_NAME_SUFFIXES):
            problems.append(f"forbidden file: {relative}")
        elif "__pycache__" in path.parts:
            problems.append(f"bytecode cache: {relative}")
        elif path.suffix.lower() in TEXT_SUFFIXES and not relative.startswith("runtime/") and PERSONAL_PATH in path.read_bytes():
            problems.append(f"personal path C:\\Users\\ in {relative}")
    if problems:
        raise PackageError("package contains prohibited content:\n  " + "\n  ".join(problems))


def write_manifest(stage, repo, version, exe, runtime_version):
    files = [{"path": p.relative_to(stage).as_posix(), "size": p.stat().st_size}
             for p in sorted(stage.rglob("*")) if p.is_file()]
    manifest = {
        "name": "pikmin-randomizer",
        "version": version,
        "git_commit": git(["rev-parse", "HEAD"], repo),
        "native_commit": git(["rev-parse", "HEAD"], repo / "native"),
        "exe_sha256": sha256(exe),
        "python_runtime": runtime_version,
        "files": files,
    }
    (stage / "release-manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    return manifest


def zip_stage(stage, zip_path):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in stage.rglob("*") if p.is_file()):
            archive.write(path, path.relative_to(stage).as_posix())


def package(version, exe, dlls=None, python_embed=None, tk_source=None, seed=None, output_dir=None, repo=REPO):
    exe = Path(exe).resolve()
    if dlls is None:
        dlls = [exe.parent / "SDL2.dll", exe.parent / "libwinpthread-1.dll"]
    output_dir = Path(output_dir or repo / "output")
    zip_path = output_dir / f"pikrando-{version}-windows-x64.zip"
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / f"pikrando-{version}"
        stage.mkdir()
        stage_core(repo, stage, exe, [Path(d) for d in dlls], Path(seed) if seed else None)
        (stage / "VERSION").write_bytes((version + "\n").encode("utf-8"))
        runtime_version = stage_runtime(stage, Path(python_embed), tk_source) if python_embed else "system"
        audit(stage)
        manifest = write_manifest(stage, repo, version, exe, runtime_version)
        zip_stage(stage, zip_path)
    sums = output_dir / "SHA256SUMS.txt"
    sums.write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="utf-8")
    return zip_path, sums, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", required=True, help="e.g. 0.28.0-playtest.1")
    parser.add_argument("--exe", type=Path, default=REPO / "native" / "build-randomizer" / "bin" / "nectar.exe")
    parser.add_argument("--dlls", type=Path, nargs="*", help="runtime DLLs (default: SDL2.dll, libwinpthread-1.dll next to the exe)")
    parser.add_argument("--python-embed", type=Path, help="python-3.12.x-embed-amd64.zip from python.org")
    parser.add_argument("--tk-source", type=Path, help="full CPython 3.12 install to copy tkinter from")
    parser.add_argument("--seed", type=Path, help="example seed.json copied to seeds/")
    parser.add_argument("--output-dir", type=Path, default=REPO / "output")
    args = parser.parse_args(argv)
    try:
        zip_path, sums, manifest = package(args.version, args.exe, args.dlls, args.python_embed, args.tk_source,
                                           args.seed, args.output_dir)
    except (PackageError, subprocess.CalledProcessError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Package:   {zip_path}")
    print(f"Checksums: {sums}")
    print(f"Runtime:   {manifest['python_runtime']}; {len(manifest['files'])} files; exe {manifest['exe_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
