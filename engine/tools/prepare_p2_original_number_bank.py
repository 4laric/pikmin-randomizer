"""Prepare a private GPVE01 rev0 numeric geometry bank; no native gameplay proof."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys


ARCHIVES = {
    "user/Abe/Pellet/us/pelletlist_us.szs": "1f09fd4222d1d582cb31edb7c3f2b0dd50b0b83b2b518ac8822a29cdbe2424ba",
    "user/Abe/Pellet/us/pellet.szs": "702c5328df9e24491704773ad4cb97d2e99524c10d64a6117b6d4c36cf8aed75",
    "user/Abe/Pellet/us/pellet_texts.szs": "1b7b932244dfd75c41359f97f35481e239b9d4962c8cbd8b8485ca212fbb1b8e",
}
MEMBERS = {
    "numberpellet_config.txt": "68613c8887a0855c97f545156ebe809b266dfe517568c3476ca2b9ebfb4177ac",
    "white1.bmd": "4398d4785dbc740159f3cf304727d8655e89122f3be1cc3aca5259f5ee468f39",
    "white2.bmd": "bc941851d8e5191b77f55b2719ccd80c3ca97f84ee87c779671de7c355dd14cf",
    "pellet1.bck": "c5041fdfbd8fa31b30f057eeb7db7450be63eba8e90d6329b93e053ade0d9c26",
    "pellet2.bck": "e84fac4a1aa46d78525a558a1ade1834c7199e03fd3f672e2f9516127f2855e1",
    "pellet1coll.txt": "cc72bc42dc51f7182d0a68f7ed2b78c0d441ce0fe925057049a5376ee70fb50a",
    "pellet2coll.txt": "881bef63b7db5d13e0971daf559ea4b6cfdfe1bbe4804b48a032525d24fc4e52",
}
COLORS = {"blue": (0, 51, 255, 255), "red": (251, 17, 0, 255), "yellow": (255, 220, 52, 255)}
PROFILES = {
    1: dict(carry_min=1, carry_max=2, matching_yield=2, nonmatching_yield=1,
            radius=10.0, pick_radius=10.0, height=7.6, inertia_scaling=90.0,
            particles=0, particle_size=0.5, friction=0.5, dynamics="never",
            model="white1.bmd", animation="pellet1.bck", collision="pellet1coll.txt"),
    5: dict(carry_min=5, carry_max=10, matching_yield=5, nonmatching_yield=3,
            radius=20.0, pick_radius=20.0, height=14.0, inertia_scaling=200.0,
            particles=4, particle_size=1.0, friction=0.9, dynamics="lod",
            model="white2.bmd", animation="pellet2.bck", collision="pellet2coll.txt"),
}
MAX_ARCHIVE = 128 * 1024
MAX_OUTPUT = 2 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reject_links(path):
    """Reject each existing component, including Windows junctions/reparse points."""
    for component in (path, *path.parents):
        if component.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(component):
            raise ValueError("Output path contains a symlink or junction")
        if component.exists():
            attributes = getattr(component.lstat(), "st_file_attributes", 0)
            if attributes & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
                raise ValueError("Output path contains a reparse point")


def private_output(repo_root, requested):
    raw = Path(os.path.abspath(requested))
    reject_links(raw)
    target = raw.resolve()
    private = repo_root / "output"
    reject_links(private)
    if target == private or not target.is_relative_to(private):
        raise ValueError("Output must be a new directory inside repo-root/output")
    if target.exists():
        raise ValueError("Output directory already exists; use a fresh bank directory")
    return target


def check_mod(data, report):
    """Reparse native MOD chunk framing, vertex bounds and terminal marker."""
    if not data or len(data) > MAX_OUTPUT:
        raise ValueError("Numeric MOD exceeds size bound")
    at = 0
    chunks = {}
    while at + 8 <= len(data):
        tag, length = struct.unpack_from(">II", data, at)
        end = at + 8 + length
        if end > len(data) or tag in chunks:
            raise ValueError("Invalid/duplicate numeric MOD chunk")
        chunks[tag] = (at, end)
        at = end
        if tag == 65535:
            break
    if at != len(data) or tag != 65535 or not {16, 32, 34, 48, 96}.issubset(chunks):
        raise ValueError("Incomplete numeric MOD")
    start, end = chunks[16]
    count = struct.unpack_from(">I", data, start + 8)[0]
    first = start + 32
    if count != report["vertices"] or first + count * 12 > end:
        raise ValueError("Numeric vertex span differs from report")
    vertices = [struct.unpack_from(">3f", data, first + i * 12) for i in range(count)]
    if not vertices or not all(math.isfinite(v) for vertex in vertices for v in vertex):
        raise ValueError("Non-finite/empty numeric vertices")
    bounds = [min(v[k] for v in vertices) for k in range(3)] + [max(v[k] for v in vertices) for k in range(3)]
    if bounds != report["bounds"]:
        raise ValueError("Reparsed numeric bounds differ from report")
    return dict(bytes=len(data), vertices=count, bounds=bounds, chunk_tags=list(chunks))


def prepare(iso, repo_root, requested):
    repo_root = repo_root.resolve(strict=True)
    if not (repo_root / "experimental/pikmin2_assets.py").is_file():
        raise ValueError("repo-root lacks the existing experimental asset reader")
    output = private_output(repo_root, requested)
    sys.path.insert(0, str(repo_root))
    from experimental.pikmin2_assets import disc_files, archive_files
    from experimental.pikmin2_convert import decode, write_model

    catalog = disc_files(iso)
    source_hashes = {}
    members = {}
    with iso.open("rb") as disc:
        for path, expected in ARCHIVES.items():
            offset, length = catalog[path]
            if not 0 < length <= MAX_ARCHIVE:
                raise ValueError("Numeric source archive exceeds byte bound")
            disc.seek(offset)
            raw = disc.read(length)
            if len(raw) != length or sha(raw) != expected:
                raise ValueError("Source archive hash mismatch: " + path)
            source_hashes[path] = expected
            for name, data in archive_files(raw).items():
                if name not in MEMBERS:
                    continue
                if name in members or sha(data) != MEMBERS[name]:
                    raise ValueError("Source member hash mismatch/duplicate: " + name)
                members[name] = data
                source_hashes[path + ":" + name] = MEMBERS[name]
    if set(members) != set(MEMBERS):
        raise ValueError("Incomplete original numeric source closure")
    # Decode every required model before any output or prospective native RNG.
    for number, profile in PROFILES.items():
        decoded = decode(members[profile["model"]], approximate_materials=True, bake_rigid=True)
        if len(decoded[2]) != 1:
            raise ValueError("Expected the audited single numeric material/shape")
    output.mkdir(parents=True, exist_ok=False)
    reject_links(output)
    records = []
    total = 0
    for number, profile in PROFILES.items():
        for color, rgba in COLORS.items():
            reject_links(output)
            name = "number{}_{}.mod".format(number, color)
            path = output / name
            decoded = decode(members[profile["model"]], approximate_materials=True, bake_rigid=True)
            report = write_model(decoded, path, "user/Abe/Pellet/us/pellet.szs:" + profile["model"],
                                 y_offset=0.0, material_colors=[rgba])
            model_bytes = path.read_bytes()
            report_bytes = path.with_suffix(".json").read_bytes()
            if json.loads(report_bytes) != report:
                raise ValueError("Written converter report differs from returned report")
            total += len(model_bytes) + len(report_bytes)
            if total > MAX_OUTPUT:
                raise ValueError("Numeric bank exceeds total byte bound")
            records.append(dict(number=number, color=color, color_id=list(COLORS).index(color),
                                rgba=list(rgba), mod=name, mod_sha256=sha(model_bytes),
                                report=path.with_suffix(".json").name, report_sha256=sha(report_bytes),
                                reparsed=check_mod(model_bytes, report)))
    manifest = dict(schema=1, bank="original_p2_number_one_five_static", disc="GPVE01", revision=0,
                    source_sha256=source_hashes, profiles=PROFILES, resources=records,
                    native_rng_used=False, source_closure_validated_before_conversion=True,
                    converter_policy=dict(approximate_materials=True, bake_rigid=True, y_offset=0.0,
                                          pose="identity bind / BCK frame-zero rest pose",
                                          material="source geometry/textures with explicit audited RGBA; original TEV not reproduced"),
                    limitations=["BCK carry animation unsupported; static initial/rest pose only.",
                                 "No native factory admission, gameplay, save/resume or SAVE proof."],
                    generated_bytes=total)
    reject_links(output)
    receipt = output / "manifest.json"
    receipt.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if receipt.stat().st_size > 32 * 1024:
        raise ValueError("Numeric manifest exceeds byte bound")
    return dict(output=str(output), models=len(records), manifest_sha256=sha(receipt.read_bytes()), generated_bytes=total)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.iso, args.repo_root, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
