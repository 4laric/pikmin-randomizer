"""Descend-policy registry + boot-log verifier for #757 (root tooling half).

Records the exact pins/hashes of the tutorial-2 floors 3-8 engine path and
fail-closed checks over the headed boot logs. No engine execution here; the
runtime proof lives in the hashed boot logs.
"""
import hashlib

NATIVE_BASE = "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54"
NATIVE_COMMITS = (
    "f2c136b99760941e5cc6f3df765e054f935af4d5",
    "eaabe9c816478b35b95e7fe8efe4de9a87096537",
)
ENGINE_EXE_SHA256 = ("62e52cda0c825edf5c2ee7a9da7a3da54786a4cdb7918dfa4c5dd32af874fafe")
FIXTURE_EXE_SHA256 = ("cdedd5042445d68bb0e2f34a2dd32d5b744bbfe1890a22ae47a41399326c00fb")
GUARD_SHA256 = ("d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")

ENTRY_VERSION = "P2_CAVE_ENTRY_4"
FLOORS = (3, 4, 5, 6, 7, 8)
SQUAD_COUNT = 8

BOOT_LOGS = {
    3: "528f3b561dfc61576284bce5c7eeb07b32846e4b4a16bc68f6632d6a1ada80d6",
    4: "4d078ae12ad924cb532dd91cc82c6872bffc25d8fc48d8c284f85060c18f1984",
    5: "6ad53577db111cd7c931b8fbc7af99dafd90db0bf37df9aa359403156026a619",
    6: "386a05150f2d41773784d71fd1eafbded58b4bb60858275738247e5751fb85fd",
    7: "565a8306f789058c59fd7702c3b67252f4e4eebeb1aa67ab3d35b00e332b0b96",
    8: "b6340cb58ee66cb6cb141d6cade8c3a2d830904ba840f3e1fad4854d49162ee7",
}

FORBIDDEN = (
    "P2_FIXTURE_CAPTAIN_DOWN",
    "FAIL TUTORIAL2_DESCEND",
)


def read_log_text(path):
    """Decode a boot log regardless of UTF-8/UTF-16 console encoding."""
    raw = open(path, "rb").read()
    for encoding in ("utf-8", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("boot log is not UTF-8 or UTF-16: " + str(path))


def verify_boot_log(path, floor):
    """Fail-closed check of one floor boot. Returns the descend flag."""
    text = read_log_text(path)
    for bad in FORBIDDEN:
        if bad in text:
            raise ValueError("forbidden marker present: " + bad)
    ready = "P2_CAVE_READY floor=%d survivors=%d" % (floor, SQUAD_COUNT)
    if ready not in text:
        raise ValueError("READY marker absent: " + ready)
    policy = "P2_TUTORIAL2_DESCEND_POLICY floor=%d descend=" % floor
    at = text.find(policy)
    if at < 0:
        raise ValueError("descend-policy marker absent for floor %d" % floor)
    flag = text[at + len(policy)]
    if flag not in ("0", "1"):
        raise ValueError("malformed descend flag for floor %d" % floor)
    expect = "1" if floor <= 7 else "0"
    if flag != expect:
        raise ValueError("floor %d descend=%s, expected %s"
                         % (floor, flag, expect))
    if "PASS TUTORIAL2_DESCEND" not in text:
        raise ValueError("PASS marker absent for floor %d" % floor)
    return flag


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
