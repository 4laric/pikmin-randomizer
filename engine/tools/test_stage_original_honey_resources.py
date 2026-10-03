"""Verify genuine private Honey staging and prewrite integrity refusal."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from stage_original_honey_resources import stage


def main(source, receivers, scratch):
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="honey-stage-test-", dir=scratch) as temporary:
        work = Path(temporary)
        valid = work / "valid"
        stage(source, receivers, valid)
        receipt = json.loads((source / "assets.json").read_text(encoding="utf-8"))
        assert len(list((valid / "assets/dataDir/courses/pikmin2room").glob("*.mod"))) == 43
        provenance = json.loads((valid / "p2-original-honey-provenance.json").read_text())
        assert provenance["ordinary_gameplay"] == "UNTESTED"
        assert provenance["source_effect_audio_material"] == "DEFERRED"
        for target in ["pose", "receiver"]:
            copied = work / f"source-{target}"
            copied_receivers = work / f"receivers-{target}"
            shutil.copytree(source, copied)
            shutil.copytree(receivers, copied_receivers)
            file = copied / receipt["clips"][0]["poses"][0]["file"] if target == "pose" else copied_receivers / "mizunomi.bca"
            file.write_bytes(file.read_bytes() + b"corrupt")
            failed = work / f"failed-{target}"
            try:
                stage(copied, copied_receivers, failed)
            except ValueError:
                pass
            else:
                raise AssertionError("corrupt Honey source geometry/receiver accepted")
            assert not failed.exists(), "integrity failure must precede output writes"
    print("P2_ORIGINAL_HONEY_STAGE_PASS: 43 genuine source poses, receiver keys, prewrite corruption refusal; no gameplay claim")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("receivers", type=Path)
    parser.add_argument("scratch", type=Path)
    args = parser.parse_args()
    main(args.source, args.receivers, args.scratch)
