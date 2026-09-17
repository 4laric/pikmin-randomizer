"""Dependency-free locator/decoder for the tutorial_2 cave source (#152).

Downstream: the tutorial_2 P1 owner needs the exact
`user/Mukki/mapunits/caveinfo/tutorial_2.txt` bytes from the local legal US
GPVE01 disc. This provider locates the disc (default path plus `--iso`
override), reads the member through the existing shared
`experimental.pikmin2_assets.disc_files` reader (no parser fork), hash-pins the
bytes (offset 770662632, size 10222) and decodes the text.

Codec is shift_jis, recorded explicitly: the retail bytes are NOT plain UTF-8
(strict UTF-8 decoding fails at byte 0x8a). `light_a` cargo stays unresolved
(P0 blocker 2); nothing is guessed here.

Fail-closed: a missing disc, a missing member, or a hash mismatch raises with
an actionable message. Synthetic or P1 content is never substituted.
"""
from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

from experimental.pikmin2_assets import disc_files

DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
CAVEINFO_PATH = "user/Mukki/mapunits/caveinfo/tutorial_2.txt"
EXPECTED_OFFSET = 770662632
EXPECTED_SIZE = 10222
EXPECTED_SHA256 = "05a38ab1e37c4ad11b5f48425bec3c2101ff199a4ea0b926fc9f35fde5620049"
CODEC = "shift_jis"


class SourceMissing(FileNotFoundError):
    """The legal disc or the caveinfo member is absent."""


class HashMismatch(ValueError):
    """The caveinfo bytes do not match the pinned real-source hash."""


@dataclass(frozen=True)
class SourceBundle:
    iso: Path
    offset: int
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


def read_tutorial2_bytes(iso=None):
    """Read hash-pinned caveinfo bytes via the shared disc reader (no fork)."""
    disc = locate_source(iso)
    catalog = disc_files(disc)
    if CAVEINFO_PATH not in catalog:
        raise SourceMissing(
            "%s not present in %s. The disc is not the expected US GPVE01 "
            "revision 0 image." % (CAVEINFO_PATH, disc)
        )
    offset, length = catalog[CAVEINFO_PATH]
    if offset != EXPECTED_OFFSET or length != EXPECTED_SIZE:
        raise HashMismatch(
            "%s layout drift: catalog has offset=%d size=%d, pinned "
            "offset=%d size=%d." % (CAVEINFO_PATH, offset, length,
                                    EXPECTED_OFFSET, EXPECTED_SIZE))
    data = _read_member(disc, offset, length)
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise HashMismatch(
            "%s hash mismatch: expected %s, observed %s (%d bytes). "
            "Refusing to serve unpinned bytes." % (CAVEINFO_PATH, EXPECTED_SHA256,
                                                   digest, len(data))
        )
    return data


def decode_tutorial2(data):
    """Decode pinned caveinfo bytes to text (strict shift_jis, recorded)."""
    return data.decode(CODEC)


def locate_and_decode(iso=None):
    """Full provider contract: locate, read, pin and decode the source."""
    disc = locate_source(iso)
    data = read_tutorial2_bytes(disc)
    return SourceBundle(
        iso=disc,
        offset=EXPECTED_OFFSET,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
        text=decode_tutorial2(data),
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
    print("iso=%s offset=%d size=%d sha256=%s codec=%s"
          % (bundle.iso, bundle.offset, bundle.size, bundle.sha256, CODEC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())