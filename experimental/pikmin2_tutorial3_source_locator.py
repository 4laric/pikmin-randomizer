"""Dependency-free locator/decoder for the tutorial_3 cave source (#153).

Downstream: the tutorial_3 P1 owner needs the exact
`user/Mukki/mapunits/caveinfo/tutorial_3.txt` bytes from the local legal US
GPVE01 disc. This provider locates the disc (default path plus `--iso`
override), reads the member through the existing shared
`experimental.pikmin2_assets.disc_files` reader (no parser fork), hash-pins the
bytes (offset 770672856, size 9701) and decodes the text.

Codec is shift_jis, recorded explicitly: the retail bytes are NOT plain UTF-8
(strict UTF-8 decoding fails at byte 0x1e). shift_jis decodes 9051 chars
including the `# CaveInfo` header, the floor-count line and the per-floor
`# FloorInfo` / `# TekiInfo` / `# ItemInfo` / `# GateInfo` / `# CapInfo` blocks.

Fail-closed: a missing disc, a missing member, or a hash mismatch raises with
an actionable message. Synthetic or P1 content is never substituted.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from experimental.pikmin2_assets import disc_files

DEFAULT_ISO = Path("C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso")
CAVEINFO_PATH = "user/Mukki/mapunits/caveinfo/tutorial_3.txt"
EXPECTED_OFFSET = 770672856
EXPECTED_SIZE = 9701
EXPECTED_SHA256 = "adcc816653957fbf00919c313291142cb110b5479c7790d997399e380c9b1abb"
CODEC = "shift_jis"

FLOOR_BLOCK = re.compile(r"# FloorInfo\s*\{(.*?)\{_eof", re.S)
FIELD = re.compile(r"\{(f00[0-9A-Fa-f])\}\s+\S+\s+(\S+)")


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


@dataclass(frozen=True)
class FloorUnit:
    floor: int
    rooms: int
    unit: str
    light: str


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


def read_tutorial3_bytes(iso=None):
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


def decode_tutorial3(data):
    """Decode pinned caveinfo bytes to text (strict shift_jis, recorded)."""
    return data.decode(CODEC)


def floor_units(text):
    """Expose the per-floor unit/room structure for the tutorial_3 P1 owner.

    Returns one FloorUnit per `# FloorInfo` block in file order, carrying the
    floor index (f000), room count (f005), unit file (f008) and light ini
    (f009). Purely a read of the decoded text; nothing is guessed or defaulted.
    """
    units = []
    for block in FLOOR_BLOCK.findall(text):
        fields = {}
        for key, value in FIELD.findall(block):
            fields[key] = value
        if "f000" not in fields:
            continue
        units.append(FloorUnit(
            floor=int(fields["f000"]),
            rooms=int(fields.get("f005", "0")),
            unit=fields.get("f008", ""),
            light=fields.get("f009", ""),
        ))
    return units


def locate_and_decode(iso=None):
    """Full provider contract: locate, read, pin and decode the source."""
    disc = locate_source(iso)
    data = read_tutorial3_bytes(disc)
    return SourceBundle(
        iso=disc,
        offset=EXPECTED_OFFSET,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
        text=decode_tutorial3(data),
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
    floors = floor_units(bundle.text)
    print("iso=%s offset=%d size=%d sha256=%s codec=%s floors=%d"
          % (bundle.iso, bundle.offset, bundle.size, bundle.sha256, CODEC,
             len(floors)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
