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

def stage_core(repo, stage, exe, dlls, seed, extractor=None):
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
    # The engine's installer lets the launcher extract assets straight from a disc image.
    extractor = Path(extractor) if extractor else exe.parent / "nectar-launcher.exe"
    if extractor.is_file():
        shutil.copy2(extractor, stage / "bin" / "nectar-launcher.exe")
    else:
        print(f"WARNING: {extractor} not found; players must supply an already extracted assets folder.", file=sys.stderr)
    copy_tree_files(repo, stage, tracked_python_files(repo))
    copy_tree_files(repo, stage, [Path("launcher/launcher.py"), Path("launcher/gui.py"), Path("launcher/discimage.py")])
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


INSTALL_SKIP_DIRS = {"site-packages", "test", "tests", "idlelib", "ensurepip", "__pycache__", "turtledemo", "pydoc_data"}


def stage_runtime_from_install(stage, install_dir):
    """Copy a python.org CPython installation (relocatable) into runtime/ with tkinter and vendored websockets.

    A ._pth file next to python.exe pins the module search path to the copied Lib/DLLs, the package
    root and Lib/site-packages, so the bundled interpreter ignores any Python on the player's machine.
    """
    install_dir = Path(install_dir)
    python = install_dir / "python.exe"
    if not python.is_file() or not (install_dir / "Lib").is_dir() or not (install_dir / "DLLs").is_dir():
        raise PackageError(f"--python-install must be a full CPython install directory (python.exe, Lib, DLLs): {install_dir}")
    # Tcl 9 builds (Python 3.14 install manager) ship the Tcl library inside the DLL; older ones need tcl/.
    if not (install_dir / "Lib" / "tkinter").is_dir() or not (install_dir / "DLLs" / "_tkinter.pyd").is_file():
        raise PackageError(f"{install_dir} has no tkinter; install python.org Python with 'tcl/tk and IDLE' selected")
    runtime = stage / "runtime"
    runtime.mkdir()
    for name in ("python.exe", "pythonw.exe", "LICENSE.txt"):
        if (install_dir / name).is_file():
            shutil.copy2(install_dir / name, runtime / name)
    for dll in list(install_dir.glob("python3*.dll")) + list(install_dir.glob("vcruntime*.dll")):
        shutil.copy2(dll, runtime / dll.name)
    shutil.copytree(install_dir / "DLLs", runtime / "DLLs", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(install_dir / "Lib", runtime / "Lib", ignore=lambda d, names: [n for n in names if n in INSTALL_SKIP_DIRS])
    if (install_dir / "tcl").is_dir():
        shutil.copytree(install_dir / "tcl", runtime / "tcl", ignore=shutil.ignore_patterns("__pycache__"))
    site_packages = runtime / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)
    vendor_websockets(site_packages)
    version = next((p.stem[len("python"):] for p in runtime.glob("python3*.dll") if p.stem != "python3"), "312")
    (runtime / f"python{version}._pth").write_bytes(b"Lib\nDLLs\n..\nLib\\site-packages\nimport site\n")
    reported = subprocess.run([str(runtime / "python.exe"), "-B", "-c", "import sys, tkinter, websockets; print(sys.version.split()[0])"],
                              capture_output=True, text=True)
    if reported.returncode:
        raise PackageError("bundled runtime self-check failed: " + (reported.stderr or reported.stdout).strip())
    for cache in runtime.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)  # The audit forbids bytecode caches in the package.
    return reported.stdout.strip()


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

RUNTIME_DLLS = ("SDL2.dll", "libwinpthread-1.dll", "libgcc_s_seh-1.dll", "libstdc++-6.dll")
MINGW_BIN = Path(os.environ.get("MINGW_BIN", r"C:\msys64\mingw64\bin"))
SYSTEM_DLLS = {"kernel32.dll", "user32.dll", "msvcrt.dll", "opengl32.dll", "ws2_32.dll", "comdlg32.dll", "ole32.dll",
               "shell32.dll", "advapi32.dll", "gdi32.dll", "imm32.dll", "oleaut32.dll", "setupapi.dll", "version.dll",
               "winmm.dll", "ntdll.dll", "shlwapi.dll", "dbghelp.dll", "uuid.dll", "crypt32.dll", "bcrypt.dll",
               "userenv.dll", "ws2_32.dll", "psapi.dll", "dinput8.dll", "xinput1_4.dll", "hid.dll", "dwmapi.dll",
               "d3d11.dll", "dxgi.dll", "avrt.dll", "mmdevapi.dll", "wininet.dll", "iphlpapi.dll"}


def imported_dlls(binary):
    """DLL names referenced by a PE file (string scan; covers import tables and LoadLibrary names)."""
    import re
    return {m.decode("ascii").lower() for m in re.findall(rb"[A-Za-z0-9_+.\-]{1,60}\.dll", binary.read_bytes())}


def audit_binaries(stage):
    """Every non-system DLL a packaged executable references must ship in bin/."""
    bin_dir = stage / "bin"
    if not bin_dir.is_dir():
        return []
    present = {p.name.lower() for p in bin_dir.iterdir()}
    problems = []
    for binary in sorted(bin_dir.glob("*.exe")):
        for name in sorted(imported_dlls(binary)):
            if name in SYSTEM_DLLS or name.startswith("api-ms-win") or name.startswith("ext-ms-") or name in present:
                continue
            if name.startswith(("lib", "sdl")) or name.endswith(("-6.dll", "-1.dll")):
                problems.append(f"{binary.name} needs {name}, which is not in bin/")
    return problems


def audit(stage):
    problems = audit_binaries(stage)
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


def package(version, exe, dlls=None, python_embed=None, tk_source=None, seed=None, output_dir=None, repo=REPO,
            python_install=None, extractor=None):
    exe = Path(exe).resolve()
    if dlls is None:
        # MinGW builds also need the GCC runtime; take it from beside the exe or from the toolchain.
        dlls = []
        for name in RUNTIME_DLLS:
            candidates = [exe.parent / name] + ([MINGW_BIN / name] if name.startswith("lib") else [])
            dlls.append(next((c for c in candidates if c.is_file()), candidates[0]))
    if python_embed and python_install:
        raise PackageError("use either --python-embed or --python-install, not both")
    output_dir = Path(output_dir or repo / "output")
    zip_path = output_dir / f"pikrando-{version}-windows-x64.zip"
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / f"pikrando-{version}"
        stage.mkdir()
        stage_core(repo, stage, exe, [Path(d) for d in dlls], Path(seed) if seed else None, extractor)
        (stage / "VERSION").write_bytes((version + "\n").encode("utf-8"))
        if python_install:
            runtime_version = stage_runtime_from_install(stage, python_install)
        else:
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
    parser.add_argument("--python-install", type=Path, help="full python.org CPython 3.12 install to copy as the bundled runtime (with tkinter)")
    parser.add_argument("--extractor", type=Path, help="nectar-launcher.exe for disc-image extraction (default: next to the exe)")
    parser.add_argument("--seed", type=Path, help="example seed.json copied to seeds/")
    parser.add_argument("--output-dir", type=Path, default=REPO / "output")
    args = parser.parse_args(argv)
    try:
        zip_path, sums, manifest = package(args.version, args.exe, args.dlls, args.python_embed, args.tk_source,
                                           args.seed, args.output_dir, python_install=args.python_install, extractor=args.extractor)
    except (PackageError, subprocess.CalledProcessError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Package:   {zip_path}")
    print(f"Checksums: {sums}")
    print(f"Runtime:   {manifest['python_runtime']}; {len(manifest['files'])} files; exe {manifest['exe_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
