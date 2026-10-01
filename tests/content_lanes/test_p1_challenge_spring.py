"""P0 import-contract tests for p1-challenge-spring (lane p1-challenge-spring, #566).

Synthetic stage-table and stage-ini malformed/missing-input tests run
anywhere; the live decode test runs only where the local P1 asset tree is
present. No runtime, no placements, no invented values.
"""
import importlib.util
import unittest
from pathlib import Path

_ADAPTER = (Path(__file__).resolve().parent.parent.parent
            / "experimental" / "content_lanes" / "p1-challenge-spring.py")

ASSETS = Path("C:/Users/alari/bbft/dist/cohesion/pikmin/assets")


def _load():
    spec = importlib.util.spec_from_file_location(
        "p1_challenge_spring_lane", _ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lane = _load()
LANE = _lane.LANE
LEVEL_KEY = _lane.LEVEL_KEY
STAGE_INFO_INDEX = _lane.STAGE_INFO_INDEX
parse_stage_table = _lane.parse_stage_table
parse_stage_ini = _lane.parse_stage_ini
check_contract = _lane.check_contract
check_closure = _lane.check_closure
read_asset = _lane.read_asset

CAMPAIGN_BLOCK = (
    'new_map\tvisible {\n'
    '\tname\t"Stage3 Yakushima"\n'
    '\tid\t3\n'
    '\tfile\tstages/stage3.ini\n'
    '\tgenerator {\n'
    '\t\tgenfile\t0-14.gen\t0\t14\t14\n'
    '\t\tgenfile\t4-29.gen\t4\t29\t29\n'
    '\t\t}\n'
    '\t}\n'
)

CHALLENGE_BLOCK = (
    'new_map\tvisible {\n'
    '\tname\t"Challenge 3"\n'
    '\tid\t3\n'
    '\tchid\t3\n'
    '\tfile\tstages/chal3.ini\n'
    '\t}\n'
)


def light_block(kind=3, attach=1, colour="255 255 255 255", extra=True):
    text = "  light 0 {\n"
    text += "    type  " + str(kind) + "\n"
    text += "    attach  " + str(attach) + "\n"
    if extra:
        text += "    fov  45.0\n"
        text += "    position  0.00 330.00 0.00\n"
        text += "    direction  0.00 -1.00 0.00\n"
    text += "    colour  " + colour + "\n"
    text += "    }\n"
    return text


def timesetting_block(index, label):
    text = "timesetting " + str(index) + " {" + ("  // " + label if label else "") + "\n"
    text += light_block()
    text += "  ambient {\n    colour  70 80 120 0\n    }\n"
    text += "  fog {\n    colour  10 0 15 48\n    dist  1000.00 5000.00\n    }\n"
    text += "  }\n"
    return text


def stage_ini(labels=("night", "morning", "day", "evening", "movie"),
              numsettings=None, navi="0.0\t0.0",
              geometry="courses/stage3/yakusima.mod", day="1.4"):
    if numsettings is None:
        numsettings = len(labels)
    text = "// Level 2\n"
    text += "navi_start\t\t" + navi + "\n"
    text += "map_file\t\t" + geometry + "\n\n"
    text += "day_multiply\t" + day + "\n\n\n"
    text += "dayMgr {\nnumsettings " + str(numsettings) + "\n\n"
    for index, label in enumerate(labels):
        text += timesetting_block(index, label)
    text += "}\n\n"
    text += "new_room {\n\t// Starting room\n\tindex\t\t0\n\tradius\t\t4.0\n\tcentre\t\t0.0\t0.0\n\t}\n"
    return text


def table_with(record, before=19):
    records = [{"index": i, "visible": True, "name": "filler",
                "id": i, "chal_id": None, "file": "stages/filler.ini",
                "generators": []} for i in range(before)]
    records.append(record)
    return records


def challenge_record():
    return {"index": 19, "visible": True, "name": "Challenge 3", "id": 3,
            "chal_id": 3, "file": "stages/chal3.ini", "generators": []}


class StageTableTests(unittest.TestCase):
    def test_campaign_block_parses_generators(self):
        table = parse_stage_table(CAMPAIGN_BLOCK)
        self.assertEqual(len(table), 1)
        record = table[0]
        self.assertEqual(record["index"], 0)
        self.assertEqual(record["name"], "Stage3 Yakushima")
        self.assertEqual(record["id"], 3)
        self.assertIsNone(record["chal_id"])
        self.assertEqual(record["file"], "stages/stage3.ini")
        self.assertEqual(record["generators"],
                         [{"name": "0-14.gen", "first": 0, "last": 14, "total": 14},
                          {"name": "4-29.gen", "first": 4, "last": 29, "total": 29}])

    def test_challenge_block_parses_chid(self):
        table = parse_stage_table(CHALLENGE_BLOCK)
        record = table[0]
        self.assertEqual(record["chal_id"], 3)
        self.assertEqual(record["generators"], [])
        self.assertTrue(record["visible"])

    def test_index_increments_per_block(self):
        table = parse_stage_table(CAMPAIGN_BLOCK + CHALLENGE_BLOCK)
        self.assertEqual([r["index"] for r in table], [0, 1])

    def test_malformed_tables_fail_closed(self):
        bad = [
            "new_map visible { name \"x\"",
            "new_map visible { unknown 3 }",
            "new_map visible { generator { genfile a 1 2 } }",
            "new_map visible { generator { bogus a 1 2 3 } }",
            "new_map visible { id 3",
            "",
        ]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_stage_table(text)


class StageIniTests(unittest.TestCase):
    def test_full_stage_parses(self):
        stage = parse_stage_ini(stage_ini())
        self.assertEqual(stage["navi_start"], (0.0, 0.0))
        self.assertEqual(stage["map_file"], "courses/stage3/yakusima.mod")
        self.assertEqual(stage["day_multiply"], 1.4)
        self.assertEqual(stage["numsettings"], 5)
        self.assertEqual(len(stage["timesettings"]), 5)
        self.assertEqual(stage["timesettings"][0]["index"], 0)
        self.assertEqual(len(stage["timesettings"][0]["lights"]), 1)
        self.assertEqual(stage["timesettings"][0]["lights"][0]["type"], 3.0)
        self.assertEqual(stage["timesettings"][0]["lights"][0]["colour"],
                         [255, 255, 255, 255])
        self.assertEqual(stage["timesettings"][0]["ambient"]["colour"],
                         [70, 80, 120, 0])
        self.assertEqual(stage["timesettings"][0]["fog"]["dist"],
                         [1000.0, 5000.0])
        self.assertEqual(stage["new_rooms"],
                         [{"index": 0, "radius": 4.0, "centre": (0.0, 0.0)}])

    def test_movie_light_without_fov_ok(self):
        text = stage_ini()
        text = text.replace(light_block(), light_block(extra=False), 1)
        stage = parse_stage_ini(text)
        self.assertIsNone(stage["timesettings"][0]["lights"][0]["fov"])
        self.assertEqual(stage["timesettings"][0]["lights"][0]["colour"],
                         [255, 255, 255, 255])

    def test_malformed_stage_fails_closed(self):
        cases = [
            stage_ini().replace("navi_start\t\t0.0\t0.0", "navi_start\t\t0.0"),
            stage_ini().replace("dayMgr {", "dayMgr"),
            stage_ini().replace("day_multiply\t1.4", "day_multiply\tmany"),
            stage_ini().replace("numsettings 5", "numsettings 9"),
            stage_ini().replace("numsettings 5", "numsettings -1"),
            stage_ini().replace("timesetting 0 {", "timeset 0 {"),
            stage_ini().replace("ambient {", "bogus {"),
            stage_ini().replace("dist  1000.00 5000.00", "dist  1000.00"),
            stage_ini().replace("index\t\t0", "index\t\tx"),
            stage_ini() + "surprise 1\n",
            stage_ini().replace('map_file\t\tcourses/stage3/yakusima.mod',
                                'map_file\t\t"unterminated'),
        ]
        for text in cases:
            with self.subTest(text=text[-40:]), self.assertRaises(ValueError):
                parse_stage_ini(text)


class ContractTests(unittest.TestCase):
    def test_matching_contract_is_empty(self):
        stage = parse_stage_ini(stage_ini())
        labels = ["night", "morning", "day", "evening", "movie"]
        self.assertEqual(check_contract(table_with(challenge_record()), stage, labels), [])

    def test_missing_index_is_reported(self):
        stage = parse_stage_ini(stage_ini())
        self.assertTrue(check_contract(table_with(challenge_record(), before=5),
                                       stage, ["night"]))

    def test_record_drift_is_reported(self):
        record = challenge_record()
        record["file"] = "stages/chal4.ini"
        mismatches = check_contract(table_with(record), parse_stage_ini(stage_ini()),
                                    ["night", "morning", "day", "evening", "movie"])
        self.assertTrue(any("file" in m for m in mismatches))

    def test_stage_drift_is_reported(self):
        stage = parse_stage_ini(stage_ini(day="2.0"))
        mismatches = check_contract(table_with(challenge_record()), stage,
                                    ["night", "morning", "day", "evening", "movie"])
        self.assertTrue(any("day_multiply" in m for m in mismatches))


class InputBoundaryTests(unittest.TestCase):
    def test_missing_asset_fails_closed(self):
        with self.assertRaises(FileNotFoundError):
            read_asset(ASSETS, "dataDir/stages/does-not-exist.ini")

    def test_closure_reports_missing(self):
        missing = check_closure(Path("C:/nonexistent-assets-566"),
                                {"map_file": "courses/stage3/yakusima.mod"})
        self.assertIn("courses/stage3/yakusima.mod", missing)
        self.assertEqual(len(missing), 3)

    def test_lane_identity(self):
        self.assertEqual(LANE, "p1-challenge-spring")
        self.assertEqual(LEVEL_KEY, "challenge:spring")
        self.assertEqual(STAGE_INFO_INDEX, 19)


@unittest.skipUnless(ASSETS.is_dir(), "local P1 asset tree unavailable")
class LiveDecodeTests(unittest.TestCase):
    def test_live_contract_and_closure(self):
        import tempfile
        packet = _lane.run(ASSETS, Path(tempfile.mkdtemp()))
        self.assertEqual(packet["stage_info_index"], 19)
        self.assertEqual(packet["stage_record"]["name"], "Challenge 3")
        self.assertEqual(packet["stage_record"]["id"], 3)
        self.assertEqual(packet["stage_record"]["chal_id"], 3)
        self.assertEqual(packet["stage_record"]["file"], "stages/chal3.ini")
        self.assertEqual(packet["navi_start"], [0.0, 0.0])
        self.assertEqual(packet["map_file"], "courses/stage3/yakusima.mod")
        self.assertEqual(packet["day_multiply"], 1.4)
        self.assertEqual(packet["numsettings"], 5)
        self.assertEqual(packet["timesetting_labels"],
                         ["night", "morning", "day", "evening", "movie"])
        self.assertEqual(packet["new_rooms"],
                         [{"index": 0, "radius": 4.0, "centre": [0.0, 0.0]}])
        self.assertEqual(packet["contract_mismatches"], [])
        self.assertEqual(packet["missing_closure"], [])
        self.assertFalse(packet["generated"])
        self.assertIn("dataDir/stages/chal3/default.gen", packet["generator_sha256"])


if __name__ == "__main__":
    unittest.main()