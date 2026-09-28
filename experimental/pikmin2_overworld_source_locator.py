"""Dependency-free locator/decoder for the real overworld stage source.

Downstream: the stranded ``p2-overworld-tutorial`` P0 owner (#148) needs the
exact ``user/Abe/stages.txt`` bytes from the local legal US GPVE01 disc.
This provider locates the disc (default path plus ``--iso`` override), reads
the member through the existing shared
``experimental.pikmin2_assets.disc_files`` reader (no parser fork),
hash-pins the bytes and decodes the text.

Fail-closed: a missing disc, a missing member, or a hash mismatch raises
with an actionable message. Synthetic or P1 content is never substituted.
"""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

from experimental.pikmin2_assets import disc_files

DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
STAGES_PATH = "user/Abe/stages.txt"
EXPECTED_SHA256 = "4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8"
EXPECTED_SIZE = 3275


class SourceMissing(FileNotFoundError):
    """The legal disc or the stages member is absent."""


class HashMismatch(ValueError):
    """The stages bytes do not match the pinned real-source hash."""


@dataclass(frozen=True)
class SourceBundle:
    iso: Path
    size: int
    sha256: str
    data: bytes
    text: str


def locate_source(iso=None):
    """Return the disc path, or raise SourceMissing with an actionable message."""
    candidate = Path(iso) if iso is not None else DEFAULT_ISO
    if not candidate.is_file():
        raise SourceMissing(
            "Legal US GPVE01 disc not found at %s. Place the local legal disc "
            "at the default path or pass --iso <path-to-iso>. "
            "No synthetic or P1 substitute is used." % candidate
        )
    return candidate


def _read_member(iso, offset, length):
    with iso.open("rb") as handle:
        handle.seek(offset)
        return handle.read(length)


def read_stages_bytes(iso=None):
    """Read hash-pinned stages bytes via the shared disc reader (no fork)."""
    disc = locate_source(iso)
    catalog = disc_files(disc)
    if STAGES_PATH not in catalog:
        raise SourceMissing(
            "%s not present in %s. The disc is not the expected US GPVE01 "
            "revision 0 image." % (STAGES_PATH, disc)
        )
    offset, length = catalog[STAGES_PATH]
    data = _read_member(disc, offset, length)
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise HashMismatch(
            "%s hash mismatch: expected %s, observed %s (%d bytes). "
            "Refusing to serve unpinned bytes." % (STAGES_PATH, EXPECTED_SHA256, digest, len(data))
        )
    return data


def decode_stages(data):
    """Decode pinned stages bytes to text (strict UTF-8, newlines preserved)."""
    return data.decode("utf-8")


def locate_and_decode(iso=None):
    """Full provider contract: locate, read, pin and decode the source."""
    disc = locate_source(iso)
    data = read_stages_bytes(disc)
    return SourceBundle(
        iso=disc,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
        text=decode_stages(data),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        bundle = locate_and_decode(args.iso)
    except SourceMissing as exc:
        print("SOURCE_MISSING %s" % exc)
        return 2
    except HashMismatch as exc:
        print("HASH_MISMATCH %s" % exc)
        return 3
    if args.out is not None:
        args.out.write_text(bundle.text, encoding="utf-8")
    print("iso=%s size=%d sha256=%s" % (bundle.iso, bundle.size, bundle.sha256))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
