"""Byte-exact RVZ validation: decode an RVZ and compare its SHA-256 with a reference ISO of the same disc.

Usage: python scripts/test_rvz_convert.py <image.rvz> <reference.iso> [--output converted.iso]
Needs Python 3.14 (compression.zstd) or the zstandard package for Zstandard images.
"""
import argparse
import hashlib
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "launcher"))
import rvz  # noqa: E402


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 * 2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(image, reference, output):
    print(rvz.describe(image))
    started = time.monotonic()
    rvz.convert_to_iso(image, output)
    print(f"decoded in {time.monotonic() - started:.0f}s")
    converted, expected = sha256(output), sha256(reference)
    assert converted == expected, f"MISMATCH {converted} != {expected}"
    print(f"PASS RVZ decode is byte-exact: {converted}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("--output", type=Path, default=Path("output") / "rvz-converted.iso")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    main(args.image, args.reference, args.output)
