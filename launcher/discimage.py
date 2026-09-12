"""Extract game assets from a Pikmin ISO/GCM with the engine's own installer (bin/nectar-launcher.exe).

The disc image is only read. Extracted data lands in <install_root>/assets/dataDir/... and is
reused on later launches; the installer's own marker files identify a complete extraction.
"""
import subprocess
from pathlib import Path

IMAGE_EXTENSIONS = (".iso", ".gcm")


class ExtractError(Exception):
    """Actionable failure; the message is complete on its own."""


def is_disc_image(path):
    return bool(path) and Path(path).suffix.lower() in IMAGE_EXTENSIONS


def assets_ready(install_root, assets_problem):
    assets = Path(install_root) / "assets"
    return (assets / ".pikmin-assets").is_file() and assets_problem(assets) is None


def extract_image(image, extractor, install_root, assets_problem, on_line=None):
    """Return the assets folder for `image`, extracting with `extractor` when needed."""
    image = Path(image)
    if not image.is_file():
        raise ExtractError(f"Disc image not found: {image}")
    if not is_disc_image(image):
        raise ExtractError("The extractor takes .iso or .gcm images. Convert RVZ/WIA/GCZ to ISO with dolphin-tool first.")
    extractor = Path(extractor)
    if not extractor.is_file():
        raise ExtractError("bin/nectar-launcher.exe is missing from the package, so disc images cannot be extracted. "
                           "Point at an already extracted assets folder instead, or re-extract the release zip.")
    install_root = Path(install_root)
    install_root.mkdir(parents=True, exist_ok=True)
    if assets_ready(install_root, assets_problem):
        return str(install_root / "assets")
    command = [str(extractor), "--rom", str(image), "--install-dir", str(install_root), "--extract-only"]
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
    if code or not assets_ready(install_root, assets_problem):
        detail = "\n".join(tail[-6:])
        raise ExtractError(f"Extracting {image.name} failed (installer exit {code}).\n{detail}\n"
                           "The image must be an uncompressed Pikmin USA Rev 1 (GPIE01) or Europe (GPIP01) disc.")
    return str(install_root / "assets")


def progress_percent(line):
    """Percentage from an installer progress line like '[42%] dataDir/...', else None."""
    if line.startswith("[") and "%]" in line:
        digits = line[1:line.index("%]")]
        if digits.isdigit():
            return int(digits)
    return None
