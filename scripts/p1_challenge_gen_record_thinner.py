"""Trial-arena .gen-record thinning tool for P1 Challenge Trial chal4 (#795).

Parses staged retail generator (.gen) files byte-exactly, identifies
buried-sprout GenObjectPiki records (spawn state p00 == 0), and emits a
thinned arena with the buried total below the field cap, with byte-level
provenance. Any unknown layout aborts with an exact offset (fail-closed).

Format (all multi-byte integers big-endian; 4-byte IDs stored as reversed
ASCII, e.g. file b"ikip" == ID 'piki'):
  file    : ID32 version ('v0.0'/'v0.1' as b"0.0v"/b"1.0v"), 3x f32 navi,
            [v0.1: f32 direction], int32 BE generator count,
            count x generator records, EOF exactly.
  record  : ID32 name, ID32 version, ID32 id70, int32 carry, 32B memo,
            3x f32 position, 3x f32 offset,
            object section, area section, type section.
  section : ID32 version, class doRead bytes, parameter entries,
            FFFFFFFF terminator.  Parameter entry: 3 ASCII ID bytes +
            1 size byte, then payload (ints/floats big-endian).
  doRead  : piki 0B (GenBase empty inline; Generator.h GenObject has no
            override); plnt 4B plant-type int (plantMgr.cpp:375);
            pelt 4B pellet ID (genPellet.cpp:doRead); item pascal string +
            64B names iff version != v0.0 (genItem.cpp:87); teki 1B type +
            2B pellet + ID32 + 5 ints + 5 floats, proven by whole-file
            tiling (genteki.cpp/TekiPersonality::read last branch);
            boss 4B (v0.0 bossID branch or readParameters flags layout,
            genBoss.cpp:41/88; other version patterns refused); work name
            string + shape string iff version v0.2/v0.3, floats iff the
            engine name table resolves the name to move stone (type 1;
            workObject.cpp:37 {bridge test:0, move stone:1}).
  areas   : pint/circ: 12B (GenArea::doRead) + params (pint none,
            circ p00 float radius).
  types   : base b00/b01 ints + variant (aton p00 / irnd p00,p01 /
            1one p00,p01,p02 ints).

Engine sources (native @ a95040b6 unless noted): Generator::read
(generator.cpp:735), GenBase::read (generator.cpp:172), Parameters::read
(parameters.cpp, PACK_ID_SIZE/UNPACK), Stream::readInt (sysCommon/stream.cpp,
big-endian file), ID32::read (sysCommon/id32.cpp), GenObjectPiki::birth
(generator.cpp:1160, p00 0:buried 1:free 2:team), factory registrations
(generator.cpp:214/267-269/412-413, genItem.cpp:81, genPellet.cpp:45,
workObject.cpp:359++, plantMgr.cpp:375, genteki.cpp:41).

Observed (retail staged chal4, impact-spawn-repair-adoption-v2 run assets):
default.gen 12557 B / 63 records (item 13, piki 15, teki 15, pelt 11,
boss 6, work 3); plants.gen 8060 B / 49 records (all plnt). All 15 piki
records buried (p00 == 0), type aton; maxCount sum == 100 == #770 me cap.

Tool only, never an engine unblock. No ADMIT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys

SCHEMA_THIN = "p1-challenge-gen-record-thinner-1"
SCHEMA_ASSESS = "p1-challenge-gen-record-assess-1"
ISSUE = 795
CAP_ME_PIKIS = 100
SQUAD_TARGET = 20
TERMINATOR = b"\xff\xff\xff\xff"


class ThinError(ValueError):
    """Fail-closed refusal: unknown layout or unsafe request."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _rev(raw):
    return raw[::-1].decode("ascii", "replace")


class _Cur:
    def __init__(self, data):
        self.d = data
        self.o = 0

    def take(self, n, why):
        if self.o + n > len(self.d):
            raise ThinError("truncated at offset %d: need %d bytes (%s)" % (
                self.o, n, why))
        out = self.d[self.o:self.o + n]
        self.o += n
        return out

    def i32(self, why):
        return struct.unpack(">i", self.take(4, why))[0]

    def f32(self, why):
        return struct.unpack(">f", self.take(4, why))[0]

    def u8(self, why):
        return self.take(1, why)[0]

    def id32(self, why):
        return _rev(self.take(4, why))

    def cstring(self, why):
        ln = self.i32(why + ":strlen")
        if ln < 0 or ln > 256:
            raise ThinError("bad string length %d at offset %d (%s)" % (
                ln, self.o - 4, why))
        return self.take(ln, why + ":bytes").decode("ascii", "replace")


_OBJ_PARAM_KINDS = {
    "piki": {"p00": "i", "p01": "i"},
    "plnt": {},
    "pelt": {},
    "item": {"p00": "i", "p01": "i", "p02": "i", "p03": "i"},
    "teki": {},
    "boss": {},
    "work": {"p00": "i", "p01": "i", "p02": "i", "p03": "f"},
}
_TYPE_PARAM_KINDS = {
    "1one": {"b00": "i", "b01": "i", "p00": "i", "p01": "i", "p02": "i"},
    "aton": {"b00": "i", "b01": "i", "p00": "i"},
    "irnd": {"b00": "i", "b01": "i", "p00": "i", "p01": "i"},
}
_AREA_PARAM_KINDS = {"pint": {}, "circ": {"p00": "f"}}
_AREA_DOREAD = {"pint": 12, "circ": 12}
# workObject.cpp:37 engine name table; v0.3 floats iff type == 1.
_WORK_OBJECT_TYPE = {"bridge test": 0, "move stone": 1}
# TekiPersonality last-branch counts, proven by whole-file tiling of the
# retail chal4 default.gen (63/63 records, EOF exact).
_TEKI_INTS = 5
_TEKI_FLOATS = 5


def _params(cur, allowed, why):
    out = {}
    while True:
        head = cur.take(4, "parm-header:" + why)
        if head == TERMINATOR:
            return out
        pid = head[0:3].decode("ascii", "replace")
        size = head[3]
        if pid not in allowed:
            raise ThinError("unknown parameter %r at offset %d (%s)" % (
                pid, cur.o - 4, why))
        payload = cur.take(size, "parm-payload:%s:%s" % (why, pid))
        kind = allowed[pid]
        if kind == "i":
            if size != 4:
                raise ThinError("bad int size %d for %s at offset %d" % (
                    size, pid, cur.o - size))
            out[pid] = struct.unpack(">i", payload)[0]
        elif kind == "f":
            if size != 4:
                raise ThinError("bad float size %d for %s at offset %d" % (
                    size, pid, cur.o - size))
            out[pid] = struct.unpack(">f", payload)[0]
        else:
            out[pid] = payload.hex()


def _gen_object(cur, obj):
    start = cur.o - 4
    ver = cur.id32("obj-version")
    if obj == "piki":
        pass
    elif obj == "plnt":
        cur.take(4, "plant-type")
    elif obj == "pelt":
        cur.take(4, "pellet-id")
    elif obj == "item":
        cur.cstring("item-name")
        if ver != "v0.0":
            cur.take(64, "item-names")
    elif obj == "teki":
        cur.u8("teki-type")
        cur.take(2, "teki-pellet")
        cur.id32("teki-pellet-id")
        for _ in range(_TEKI_INTS):
            cur.i32("teki-int")
        for _ in range(_TEKI_FLOATS):
            cur.f32("teki-float")
    elif obj == "boss":
        # v0.0: bossID branch; file bytes 02 00 00 00: flags layout
        # (readParameters, 1 int); both proven by terminator position.
        if ver not in ("v0.0", "\x00\x00\x00\x02"):
            raise ThinError("unsupported boss version %r at offset %d" % (
                ver, start))
        cur.take(4, "boss-flags")
    elif obj == "work":
        name = cur.cstring("work-name").rstrip("\x00")
        if ver in ("v0.2", "v0.3"):
            cur.cstring("work-shape")
        elif ver not in ("v0.0", "v0.1"):
            raise ThinError("unsupported work version %r at offset %d" % (
                ver, start))
        if ver == "v0.3":
            if name == "move stone":
                cur.take(12, "work-hinderrock")
            elif name != "bridge test":
                raise ThinError("work v0.3 unknown name %r at offset %d" % (
                    name, cur.o))
    else:
        raise ThinError("unsupported generator object %r at offset %d" % (
            obj, start))
    oparams = _params(cur, _OBJ_PARAM_KINDS[obj], "obj:" + obj)
    return ver, oparams


def parse_gen(data):
    """Strictly parse .gen bytes; returns (header, records).

    Raises ThinError with an exact offset on any unknown layout.
    """
    if not data:
        raise ThinError("empty generator bytes at offset 0")
    cur = _Cur(data)
    version = cur.id32("file-version")
    if version not in ("v0.0", "v0.1"):
        raise ThinError("unknown file version %r at offset 0" % version)
    navi = (cur.f32("navi-x"), cur.f32("navi-y"), cur.f32("navi-z"))
    direction = cur.f32("navi-direction") if version == "v0.1" else None
    count = cur.i32("generator-count")
    if count < 0 or count > 65536 or count > len(data):
        raise ThinError("implausible generator count %d at offset %d" % (
            count, cur.o - 4))
    header_end = cur.o
    records = []
    for _ in range(count):
        start = cur.o
        cur.id32("record-name")
        cur.id32("record-version")
        cur.id32("record-id70")
        cur.i32("record-carry")
        memo = cur.take(32, "record-memo")
        pos = (cur.f32("pos-x"), cur.f32("pos-y"), cur.f32("pos-z"))
        cur.take(12, "record-offset")
        obj = cur.id32("object-id")
        over, oparams = _gen_object(cur, obj)
        area = cur.id32("area-id")
        if area not in _AREA_DOREAD:
            raise ThinError("unknown area %r at offset %d" % (
                area, cur.o - 4))
        cur.id32("area-version")
        cur.take(_AREA_DOREAD[area], "area-doread:" + area)
        aparams = _params(cur, _AREA_PARAM_KINDS[area], "area:" + area)
        gtype = cur.id32("type-id")
        if gtype not in _TYPE_PARAM_KINDS:
            raise ThinError("unknown generator type %r at offset %d" % (
                gtype, cur.o - 4))
        cur.id32("type-version")
        tparams = _params(cur, _TYPE_PARAM_KINDS[gtype], "type:" + gtype)
        records.append({
            "start": start, "end": cur.o,
            "bytes": data[start:cur.o],
            "obj": obj, "oparams": oparams,
            "area": area, "aparams": aparams,
            "type": gtype, "tparams": tparams,
            "pos": pos, "memo": memo.split(b"\x00")[0].decode(
                "ascii", "replace"),
        })
    if cur.o != len(data):
        raise ThinError("trailing %d bytes after %d records at offset %d" % (
            len(data) - cur.o, len(records), cur.o))
    return ({"version": version, "navi": navi, "direction": direction,
             "count": count, "header_end": header_end}, records)


def is_buried_sprout(record):
    """True for GenObjectPiki records with spawn state 0 (buried)."""
    return record["obj"] == "piki" and record["oparams"].get("p00") == 0


def sprout_contribution(record):
    """Buried-sprout birth contribution of one generator.

    aton maxCount (p00) and 1one (exactly 1) are exact. irnd births a
    random min..max count, so the conservative maximum (p01) is used and
    flagged; over-thinning is the safe direction (consumer re-verifies).
    """
    if not is_buried_sprout(record):
        return 0
    if record["type"] == "aton":
        return int(record["tparams"]["p00"])
    if record["type"] == "1one":
        return 1
    if record["type"] == "irnd":
        return int(record["tparams"]["p01"])
    raise ThinError("buried piki with unsupported type %r at offset %d" % (
        record["type"], record["start"]))


def assess(data, cap=CAP_ME_PIKIS, squad=SQUAD_TARGET):
    """Read-only census: buried total, headroom, required reduction."""
    header, records = parse_gen(data)
    buried = [r for r in records if is_buried_sprout(r)]
    total = sum(sprout_contribution(r) for r in buried)
    headroom = cap - total
    required = max(0, squad - headroom)
    return {
        "schema": SCHEMA_ASSESS, "issue": ISSUE,
        "bytes": len(data), "version": header["version"],
        "records": len(records), "buried_records": len(buried),
        "buried_total": total, "cap": int(cap), "squad": int(squad),
        "headroom": headroom, "required_reduction": required,
    }


def thin(data, cap=CAP_ME_PIKIS, squad=SQUAD_TARGET):
    """Emit thinned arena bytes plus a provenance packet.

    Removes buried-sprout records largest-first until the remaining total
    leaves room for the squad under the cap. Output is re-parsed and all
    kept records verified byte-identical.
    """
    header, records = parse_gen(data)
    buried = [r for r in records if is_buried_sprout(r)]
    total = sum(sprout_contribution(r) for r in buried)
    required = max(0, squad - (cap - total))
    doomed = []
    if required > 0:
        order = sorted(buried,
                       key=lambda r: (-sprout_contribution(r), r["start"]))
        removed = 0
        for rec in order:
            doomed.append(rec)
            removed += sprout_contribution(rec)
            if removed >= required:
                break
    doomed_starts = {r["start"] for r in doomed}
    kept = [r for r in records if r["start"] not in doomed_starts]
    head = data[:header["header_end"] - 4] + struct.pack(
        ">i", len(kept))
    out = head + b"".join(r["bytes"] for r in kept)
    # Verify: output re-parses and kept bytes are untouched.
    vheader, vrecords = parse_gen(out)
    if len(vrecords) != len(kept):
        raise ThinError("verification re-parse mismatch: %d vs %d" % (
            len(vrecords), len(kept)))
    for a, b in zip(vrecords, kept):
        if a["bytes"] != b["bytes"]:
            raise ThinError("verification: kept record changed at offset %d"
                            % b["start"])
    removed_total = sum(sprout_contribution(r) for r in doomed)
    packet = {
        "schema": SCHEMA_THIN, "issue": ISSUE,
        "input": {"sha256": _sha(data), "bytes": len(data),
                  "records": len(records)},
        "output": {"sha256": _sha(out), "bytes": len(out),
                   "records": len(kept)},
        "cap": int(cap), "squad": int(squad),
        "buried_before": total,
        "buried_after": total - removed_total,
        "removed": [{
            "start": r["start"], "length": r["end"] - r["start"],
            "sha256": _sha(r["bytes"]), "memo": r["memo"],
            "p00": r["oparams"].get("p00"), "p01": r["oparams"].get("p01"),
            "type": r["type"], "contribution": sprout_contribution(r),
        } for r in doomed],
    }
    return out, packet


def _read(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError as exc:
        raise ThinError("unreadable input %s: %s" % (path, exc))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pa = sub.add_parser("assess", help="read-only census of a .gen file")
    pa.add_argument("--in", dest="src", required=True)
    pa.add_argument("--cap", type=int, default=CAP_ME_PIKIS)
    pa.add_argument("--squad", type=int, default=SQUAD_TARGET)
    pt = sub.add_parser("thin", help="emit a thinned arena copy")
    pt.add_argument("--in", dest="src", required=True)
    pt.add_argument("--out", dest="dst", required=True)
    pt.add_argument("--cap", type=int, default=CAP_ME_PIKIS)
    pt.add_argument("--squad", type=int, default=SQUAD_TARGET)
    pt.add_argument("--provenance", dest="prov", default=None)
    args = parser.parse_args(argv)
    try:
        data = _read(args.src)
        if args.command == "assess":
            print(json.dumps(assess(data, args.cap, args.squad), indent=1))
            return 0
        out, packet = thin(data, args.cap, args.squad)
        with open(args.dst, "wb") as handle:
            handle.write(out)
        text = json.dumps(packet, indent=1)
        if args.prov:
            with open(args.prov, "w", encoding="utf-8") as handle:
                handle.write(text + "\n")
        print(text)
        return 0
    except ThinError as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
