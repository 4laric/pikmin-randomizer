"""Extract game assets from a Pikmin ISO/GCM with the engine's own installer (bin/nectar-launcher.exe).

The disc image is only read. Extracted data lands in <install_root>/assets/dataDir/... and is
reused on later launches; the installer's own marker files identify a complete extraction.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import rvz  # noqa: E402

RAW_EXTENSIONS = (".iso", ".gcm")
IMAGE_EXTENSIONS = RAW_EXTENSIONS + (".rvz", ".wia")


class ExtractError(Exception):
    """Actionable failure; the message is complete on its own."""


def is_disc_image(path):
    return bool(path) and Path(path).suffix.lower() in IMAGE_EXTENSIONS


def needs_conversion(path):
    return rvz.is_rvz(path)


def convert_image(image, install_root, on_line=None):
    """Decode an RVZ/WIA into a temporary ISO under install_root; the caller deletes it after extraction."""
    iso_path = Path(install_root) / (Path(image).stem + ".converted.iso")
    if iso_path.is_file():
        return iso_path
    try:
        info = rvz.describe(image)
        if on_line:
            on_line(f"Decoding {Path(image).name}: {info['game_id']} rev {info['revision']}, {info['compression']} compression, "
                    f"{info['iso_size'] // 2**20} MiB disc")
        reported = [0]
        def progress(done, total):
            percent = done * 100 // max(1, total)
            if percent != reported[0] and on_line:
                reported[0] = percent
                on_line(f"[{percent}%] decoding disc image")
        rvz.convert_to_iso(image, iso_path, progress)
    except rvz.RvzError as exc:
        raise ExtractError(str(exc))
    except OSError as exc:
        raise ExtractError(f"Could not decode {Path(image).name}: {exc}")
    return iso_path


def assets_ready(install_root, assets_problem):
    assets = Path(install_root) / "assets"
    return (assets / ".pikmin-assets").is_file() and assets_problem(assets) is None


def extract_image(image, extractor, install_root, assets_problem, on_line=None):
    """Return the assets folder for `image`, extracting with `extractor` when needed."""
    image = Path(image)
    if not image.is_file():
        raise ExtractError(f"Disc image not found: {image}")
    if not is_disc_image(image):
        raise ExtractError("The extractor takes .iso, .gcm, .rvz or .wia images. Convert GCZ/CISO/NKit images to ISO with dolphin-tool first.")
    extractor = Path(extractor)
    if not extractor.is_file():
        raise ExtractError("bin/nectar-launcher.exe is missing from the package, so disc images cannot be extracted. "
                           "Point at an already extracted assets folder instead, or re-extract the release zip.")
    install_root = Path(install_root)
    install_root.mkdir(parents=True, exist_ok=True)
    if assets_ready(install_root, assets_problem):
        return str(install_root / "assets")
    source = image
    temporary = None
    if needs_conversion(image):
        # The installer reads raw images only; decode to a temporary ISO beside the assets, then drop it.
        temporary = source = convert_image(image, install_root, on_line)
    try:
        command = [str(extractor), "--rom", str(source), "--install-dir", str(install_root), "--extract-only"]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   encoding="utf-8", errors="replace", bufsize=1,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        tail = []
        for raw in process.stdout:
            for line in raw.replace("\r", "\n").split("\n"):
                line = line.strip()
                if not line:
                    continue
                tail.append(line)
                if on_line:
                    on_line(line)
        code = process.wait()
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
    if code or not assets_ready(install_root, assets_problem):
        detail = "\n".join(tail[-6:])
        raise ExtractError(f"Extracting {image.name} failed (installer exit {code}).\n{detail}")
    return str(install_root / "assets")


def progress_percent(line):
    """Percentage from an installer progress line like '[42%] dataDir/...', else None."""
    if line.startswith("[") and "%]" in line:
        digits = line[1:line.index("%]")]
        if digits.isdigit():
            return int(digits)
    return None
