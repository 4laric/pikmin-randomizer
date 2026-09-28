"""Fail-closed tests for the trial-arena .gen-record thinning tool (#795).

Hermetic synthetic fixtures (built byte-by-byte per the engine format) plus
read-only checks against the staged retail chal4 files. No runtime, no ADMIT.
"""

import json
import os
import struct
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from p1_challenge_gen_record_thinner import (
    ThinError,
    assess,
    is_buried_sprout,
    parse_gen,
    sprout_contribution,
    thin,
)

CHAL4 = (r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill"
         r"\planning-shards\p1-challenge\prepared"
         r"\impact-spawn-repair-adoption-v2\out\run\assets\dataDir\stages\chal4")


def _id(text):
    assert len(text) == 4
    return text[::-1].encode("ascii")


def _parm(pid, value):
    assert len(pid) == 3
    return pid.encode("ascii") + b"\x04" + struct.pack(">i", value)


def _section(version, doread, params):
    return (_id(version) + doread + b"".join(params)
            + b"\xff\xff\xff\xff")


def _record(obj, over, doread, oparams, area="pint", aparams=(),
            gtype="aton", tparams=(("b00", 0), ("b01", 0), ("p00", 1)),
            memo=b"t", pos=(0.0, 0.0, 0.0)):
    head = (_id("    ") + _id("v0.0") + _id("abcd") + struct.pack(">i", 0)
            + memo.ljust(32, b"\x00")
            + struct.pack(">fff", *pos) + struct.pack(">fff", 0.0, 0.0, 0.0)
            + _id(obj))
    return (head + _section(over, doread, [_parm(k, v) for k, v in oparams])
            + _id(area) + _section("v0.0", b"\x00" * 12,
                                   [_parm(k, v) for k, v in aparams])
            + _id(gtype) + _section("v0.0", b"",
                                    [_parm(k, v) for k, v in tparams]))


def _piki(p00, count, memo=b"p"):
    return _record("piki", "v0.0", b"", (("p00", p00), ("p01", 0)),
                   tparams=(("b00", 0), ("b01", 0), ("p00", count)),
                   memo=memo)


def _file(*records):
    body = b"".join(records)
    return (_id("v0.1") + struct.pack(">fff", 0.0, 0.0, 0.0)
            + struct.pack(">f", 0.0) + struct.pack(">i", len(records))
            + body)


def test_parse_minimal_piki():
    header, records = parse_gen(_file(_piki(0, 8)))
    assert header["count"] == 1
    assert len(records) == 1
    assert is_buried_sprout(records[0])
    assert sprout_contribution(records[0]) == 8


def test_free_piki_not_buried():
    _, records = parse_gen(_file(_piki(1, 8)))
    assert not is_buried_sprout(records[0])
    assert sprout_contribution(records[0]) == 0


def test_thin_removes_largest_first():
    data = _file(_piki(0, 90), _piki(0, 5), _piki(0, 5))
    out, packet = thin(data, cap=100, squad=20)
    # me=100, headroom 0, required 20: drop the 90-record only.
    assert packet["buried_before"] == 100
    assert packet["buried_after"] == 10
    assert len(packet["removed"]) == 1
    assert packet["removed"][0]["contribution"] == 90
    vheader, vrecords = parse_gen(out)
    assert vheader["count"] == 2
    assert len(out) < len(data)


def test_thin_noop_under_cap():
    data = _file(_piki(0, 5))
    out, packet = thin(data, cap=100, squad=20)
    assert packet["removed"] == []
    assert out == data


def test_thin_keeps_other_records_byte_identical():
    keep = _record("plnt", "v0.0", struct.pack(">i", 5), ())
    data = _file(_piki(0, 95), keep)
    out, packet = thin(data, cap=100, squad=20)
    assert packet["removed"][0]["contribution"] == 95
    assert out.endswith(keep)


def test_refuse_empty():
    with pytest.raises(ThinError):
        parse_gen(b"")


def test_refuse_bad_version():
    with pytest.raises(ThinError):
        parse_gen(b"XXXX" + b"\x00" * 32)


def test_refuse_unknown_object():
    rec = _record("zzzz", "v0.0", b"", ())
    with pytest.raises(ThinError) as info:
        parse_gen(_file(rec))
    assert "offset" in str(info.value)


def test_refuse_truncated():
    data = _file(_piki(0, 8))[:-7]
    with pytest.raises(ThinError):
        parse_gen(data)


def test_refuse_trailing_bytes():
    with pytest.raises(ThinError):
        parse_gen(_file(_piki(0, 1)) + b"\x00")


def test_refuse_count_mismatch():
    data = bytearray(_file(_piki(0, 1), _piki(0, 1)))
    struct.pack_into(">i", data, 20, 5)
    with pytest.raises(ThinError):
        parse_gen(bytes(data))


def _chal4(name):
    with open(os.path.join(CHAL4, name), "rb") as handle:
        return handle.read()


def test_retail_plants_tiling():
    header, records = parse_gen(_chal4("plants.gen"))
    assert header["count"] == 49 == len(records)
    assert {r["obj"] for r in records} == {"plnt"}
    assert sum(sprout_contribution(r) for r in records) == 0


def test_retail_default_tiling_and_buried_sum():
    header, records = parse_gen(_chal4("default.gen"))
    assert header["count"] == 63 == len(records)
    buried = [r for r in records if is_buried_sprout(r)]
    assert len(buried) == 15
    assert all(r["oparams"]["p00"] == 0 for r in buried)
    assert sum(sprout_contribution(r) for r in buried) == 100


def test_retail_default_thin_roundtrip():
    data = _chal4("default.gen")
    out, packet = thin(data, cap=100, squad=20)
    assert packet["buried_before"] == 100
    assert packet["buried_after"] <= 80
    vheader, vrecords = parse_gen(out)
    assert vheader["count"] == len(vrecords) == 63 - len(packet["removed"])
    kept = [r for r in vrecords]
    assert kept  # non-empty arena remains
    for entry in packet["removed"]:
        assert entry["contribution"] >= 5
    assert packet["output"]["sha256"] != packet["input"]["sha256"]


def test_cli_assess_and_thin(tmp_path):
    src = tmp_path / "in.gen"
    dst = tmp_path / "out.gen"
    src.write_bytes(_file(_piki(0, 60), _piki(0, 60)))
    tool = os.path.join(os.path.dirname(__file__), "..", "scripts",
                        "p1_challenge_gen_record_thinner.py")
    proc = subprocess.run([sys.executable, tool, "assess", "--in", str(src)],
                          capture_output=True, text=True)
    assert proc.returncode == 0
    report = json.loads(proc.stdout)
    assert report["buried_total"] == 120
    assert report["required_reduction"] == 40
    prov = tmp_path / "prov.json"
    proc = subprocess.run([sys.executable, tool, "thin", "--in", str(src),
                           "--out", str(dst), "--provenance", str(prov)],
                          capture_output=True, text=True)
    assert proc.returncode == 0
    packet = json.loads(proc.stdout)
    assert packet["buried_after"] <= 80
    assert json.loads(prov.read_text())["output"]["sha256"] == packet[
        "output"]["sha256"]


def test_cli_refuses_unknown(tmp_path):
    src = tmp_path / "bad.gen"
    src.write_bytes(b"\x00\x01\x02\x03junk")
    tool = os.path.join(os.path.dirname(__file__), "..", "scripts",
                        "p1_challenge_gen_record_thinner.py")
    proc = subprocess.run([sys.executable, tool, "assess", "--in", str(src)],
                          capture_output=True, text=True)
    assert proc.returncode == 3
    assert "refused" in proc.stderr
