"""Private conversion-staging integrity checks; no gameplay claims."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

spec = importlib.util.spec_from_file_location("stage_original_wisp_resources", Path(__file__).with_name("stage_original_wisp_resources.py"))
stage_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_module)

def main(source):
    with tempfile.TemporaryDirectory(prefix="p2-original-wisp-stage-") as temp:
        root = Path(temp)
        destination = root / "valid"
        stage_module.stage(source, destination)
        bank = (destination / "p2-original-wisp-bank.txt").read_text()
        assert "clip damage 5 35 original_wisp_damage 1\nevents 5 2\n" in bank
        assert "parameters 90.0 1.75 20.0 400.0 0.5 35.0 180.0 250.0 99999.0" in bank
        assert "physics 0.1 15.0 0.0 0.5" in bank
        assert len(list((destination / "assets/dataDir/courses/pikmin2room").glob("*.mod"))) == 21
        changed = root / "changed"
        shutil.copytree(source, changed)
        pose = changed / "damage_01.mod"
        data = bytearray(pose.read_bytes())
        data[-1] ^= 1
        pose.write_bytes(data)
        failed = root / "invalid"
        try:
            stage_module.stage(changed, failed)
        except ValueError as error:
            assert "pose bytes" in str(error)
        else:
            raise AssertionError("corrupted source pose accepted")
        assert not failed.exists(), "integrity rejection must precede output mutation"
        provenance = json.loads((destination / "p2-original-wisp-provenance.json").read_text())
        assert provenance["ordinary_gameplay"] == "UNTESTED"
        assert provenance["source_effect_audio_backend"] == "DEFERRED"
    print("P2_ORIGINAL_WISP_STAGE_PASS actual hashes, exact events/parameters, prewrite rejection; no gameplay claim")

if __name__ == "__main__":
    main(Path(sys.argv[1]))
