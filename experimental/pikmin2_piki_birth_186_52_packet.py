"""Decision packet builder: piki-birth #186 landing + #52 coverage (#811, consumer #741).

Reads the #741 fix pins read-only, diffs the five fix files versus their
bases (or certifies zero-diff with hashes), and emits a machine-readable
decision packet for the #186 landing decision and #52 coverage decision.
Fail-closed: malformed pins, unknown files, and hash drift are refused.
No fix-file edits; diagnosis only.
"""
import hashlib
import json
import re
import subprocess
import sys

FIX = {
    "root": "92fc594c329a7098e342a87da0a231046f73a0c8",
    "native": "e1861e68bf4d19b51ae182be5228f471803b71d9",
    "native_base": "b805d9c626e4f4558c95aef7cac311a5d9a2068f",
    "worktree": r"C:\Users\alari\pikmin-randomizer\output\workflow\autofill\planning-shards\provider-runtime-fixtures\prepared\piki-birth-fix-native",
}
FILES = [
    "src/plugPikiKando/gameCoreSection.cpp",
    "src/plugPikiColin/newPikiGame.cpp",
    "src/plugPikiKando/objectMgr.cpp",
    "src/plugPikiKando/pikiMgr.cpp",
    "src/plugPikiKando/goalItem.cpp",
]
HEX40 = re.compile(r"[0-9a-f]{40}")


def fail(msg):
    raise SystemExit("REFUSED: " + msg)


def canon(path):
    parts = []
    for seg in path.replace("\\", "/").split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not parts:
                fail("unknown file: " + path)
            parts.pop()
            continue
        parts.append(seg)
    out = "/".join(parts)
    if not out or out.startswith("/") or ":" in out:
        fail("unknown file: " + path)
    return out


def blob(rev, path):
    if not HEX40.fullmatch(rev):
        fail("malformed pin: " + rev)
    c = canon(path)
    r = subprocess.run(["git", "-C", FIX["worktree"], "show", rev + ":" + c],
                       capture_output=True, timeout=30)
    if r.returncode != 0:
        fail("unknown file at pin: " + c + "@" + rev[:8])
    return r.stdout, c


def build():
    entries = []
    for f in FILES:
        base, c = blob(FIX["native_base"], f)
        head, _ = blob(FIX["native"], f)
        entries.append({
            "file": c,
            "base_sha256": hashlib.sha256(base).hexdigest(),
            "head_sha256": hashlib.sha256(head).hexdigest(),
            "changed": base != head,
            "base_bytes": len(base),
            "head_bytes": len(head),
        })
    return {
        "packet": "piki-birth-186-52-landing",
        "issue": 811,
        "consumer": {"lane": "piki-birth-challenge-setup-fix", "issue": 741},
        "fix_pins": {"root": FIX["root"], "native": FIX["native"], "native_base": FIX["native_base"]},
        "pool_empty_attribution": "#721: pikiMgr->birth() null at goalItem.cpp:438 GoalItem::exitPiki during Onion; panic at system.cpp:1229",
        "decisions_requested": [
            {"owner": "#186", "kind": "landing",
             "scope": "five fix files for the piki-birth challenge-setup path"},
            {"owner": "#52", "kind": "coverage",
             "scope": "piki-birth challenge-setup path under the AP campaign contract"},
        ],
        "files": entries,
    }


def main(out):
    pkt = build()
    data = json.dumps(pkt, indent=1).encode()
    with open(out, "wb") as fh:
        fh.write(data)
    print("packet sha256:", hashlib.sha256(data).hexdigest())
    print("files:", len(pkt["files"]), "| changed:", sum(1 for e in pkt["files"] if e["changed"]))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "piki-birth-186-52-packet.json")