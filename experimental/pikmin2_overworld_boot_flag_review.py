"""#186-ready review adapter for the shared overworld course boot flag (#738).

Downstream consumers: #696 (tutorial P1 native runtime), #148 (tutorial).
Reads the #707 verdicts and the `pc_port` boot dispatch read-only; proposes the
exact shared diff FOR #186 REVIEW without landing shared edits. This module never
edits shared files; it applies the proposal onto PRIVATE copies, verifies the
hook-registration grammar, and emits a hashed #186 request packet for the
single-writer integrator. No ADMIT, no runtime, no ledger. Stdlib only.

Fail-closed: anchors must match exactly; any drift, reorder, missing anchor, or
absent refusal raises ValueError and writes nothing.
"""
import argparse
import hashlib
import json
from pathlib import Path

BASE_CPP_SHA256_PREFIX = "c9b96c75200244e7"
BASE_NATIVE_COMMIT = "b805d9c626e4f4558c95aef7cac311a5d9a2068f"
BASE_H_SHA256_PREFIX = None  # filled by pin_discovery at packet time if needed

# Anchors in pc_port/pc_bbft.cpp at the base pin (read-only).
ANCHOR_ROOM_FLAG = 'if (!std::strcmp(argv[i], "--experimental-pikmin2-room")) {'
ANCHOR_ROOM_GUARD = 'if (challengeLevel >= 0) { std::fprintf(stderr,"Only one experimental preview may be selected\\n"); std::exit(2); }'
ANCHOR_CHALLENGE_FLAG = '} else if (!std::strcmp(argv[i], "--experimental-challenge-level")) {'
ANCHOR_CHALLENGE_GUARD = "if (++i>=argc || challengeLevel>=0 || std::strlen(argv[i])!=1"
ANCHOR_CHALLENGE_SET = "challengeLevel=argv[i][0]-'0';"
ANCHOR_PREVIEW_DECL = "static bool p2RoomPreview = false;"

# Proposed additive state (new lines only, except the two one-word guard extensions).
ADD_STATE = 'static std::string p2OverworldCourse;\n'
ADD_TABLE = ('static const char* const OVERWORLD_COURSES[] = {"tutorial", nullptr};\n'
             'static bool pc_overworld_course_known(const char* name) {\n'
             '    for (const char* const* c = OVERWORLD_COURSES; *c; ++c) if (!std::strcmp(*c, name)) return true;\n'
             '    return false;\n'
             '}\n'
             'const char* pc_pikipelago_overworld_course() { return p2OverworldCourse.empty() ? nullptr : p2OverworldCourse.c_str(); }\n')
ADD_BRANCH = ('        } else if (!std::strcmp(argv[i], "--experimental-p2-overworld-course")) {\n'
              '            if (++i>=argc || p2RoomPreview || challengeLevel>=0 || !*argv[i]) {\n'
              '                std::fprintf(stderr,"--experimental-p2-overworld-course requires a course name\\n"); std::exit(2);\n'
              '            }\n'
              '            if (!pc_overworld_course_known(argv[i])) {\n'
              '                std::fprintf(stderr,"Unknown P2 overworld course\\n"); std::exit(2);\n'
              '            }\n'
              '            p2OverworldCourse = argv[i];\n'
              '            std::printf("P2_OVERWORLD_BOOT course=%s\\n", p2OverworldCourse.c_str());\n')
GUARD_ROOM_NEW = 'if ((challengeLevel >= 0 || !p2OverworldCourse.empty())) { std::fprintf(stderr,"Only one experimental preview may be selected\\n"); std::exit(2); }'
GUARD_CHALLENGE_FRAG_NEW = "if (++i>=argc || challengeLevel>=0 || !p2OverworldCourse.empty() || std::strlen(argv[i])!=1"

# Header addition (pc_port/pc_bbft.h, after the room-preview accessor block).
ANCHOR_H_ROOM = "bool pc_pikipelago_room_preview();"
ADD_H_DECL = "const char* pc_pikipelago_overworld_course();"

EXPECTED_MARKER = "P2_OVERWORLD_BOOT course="


class ProposalRejected(ValueError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def apply_proposal(cpp_text, h_text):
    """Return (patched_cpp, patched_h); raise ProposalRejected on any drift."""
    for name, text in (("cpp", cpp_text), ("h", h_text)):
        if not isinstance(text, str) or not text:
            raise ProposalRejected("Empty %s source" % name)
    for anchor in (ANCHOR_ROOM_FLAG, ANCHOR_ROOM_GUARD, ANCHOR_CHALLENGE_FLAG,
                   ANCHOR_CHALLENGE_GUARD, ANCHOR_CHALLENGE_SET, ANCHOR_PREVIEW_DECL):
        if cpp_text.count(anchor) != 1:
            raise ProposalRejected("CPP anchor must occur exactly once: " + anchor[:60])
    if "p2OverworldCourse" in cpp_text or "P2_OVERWORLD_BOOT course=" in cpp_text:
        raise ProposalRejected("Proposal already applied or foreign overworld state present")
    if h_text.count(ANCHOR_H_ROOM) != 1:
        raise ProposalRejected("H anchor must occur exactly once")
    if ADD_H_DECL in h_text:
        raise ProposalRejected("Header declaration already present")
    patched = cpp_text.replace(ANCHOR_PREVIEW_DECL, ANCHOR_PREVIEW_DECL + "\n" + ADD_STATE, 1)
    patched = patched.replace(ANCHOR_ROOM_GUARD, GUARD_ROOM_NEW, 1)
    patched = patched.replace(ANCHOR_CHALLENGE_GUARD, GUARD_CHALLENGE_FRAG_NEW, 1)
    marker = "        }\n"
    pos = patched.find(ANCHOR_CHALLENGE_SET)
    close = patched.find(marker, pos)
    if close < 0:
        raise ProposalRejected("Challenge arm block end not found")
    insert_at = close + len(marker)
    patched = patched[:insert_at] + ADD_TABLE + ADD_BRANCH + patched[insert_at:]
    patched_h = h_text.replace(ANCHOR_H_ROOM, ANCHOR_H_ROOM + "\n" + ADD_H_DECL, 1)
    return patched, patched_h


def verify_proposal(patched_cpp, patched_h):
    """Verify the proposed hook-registration grammar; return a findings dict."""
    f = {"state": "static std::string p2OverworldCourse;" in patched_cpp,
         "table": "OVERWORLD_COURSES" in patched_cpp and '"tutorial"' in patched_cpp,
         "known": "pc_overworld_course_known(argv[i])" in patched_cpp,
         "branch": "--experimental-p2-overworld-course" in patched_cpp,
         "marker": EXPECTED_MARKER in patched_cpp,
         "refusal_empty": "--experimental-p2-overworld-course requires a course name" in patched_cpp,
         "refusal_unknown": "Unknown P2 overworld course" in patched_cpp,
         "guard_room": "!p2OverworldCourse.empty()" in patched_cpp,
         "accessor": "pc_pikipelago_overworld_course()" in patched_cpp,
         "header": ADD_H_DECL in patched_h,
         "existing_intact": False, "ordered": False}
    room = patched_cpp.find(ANCHOR_ROOM_FLAG)
    challenge = patched_cpp.find(ANCHOR_CHALLENGE_FLAG)
    branch = patched_cpp.find("--experimental-p2-overworld-course")
    fallback = patched_cpp.find("pc_randomizer_init(argc, argv)")
    f["ordered"] = 0 <= room < challenge < branch < fallback
    f["existing_intact"] = ('--experimental-pikmin2-room' in patched_cpp
                            and '--experimental-challenge-level' in patched_cpp
                            and "challengeLevel=argv[i][0]-'0';" in patched_cpp)
    f["ok"] = all((f["state"], f["table"], f["known"], f["branch"], f["marker"],
                   f["refusal_empty"], f["refusal_unknown"], f["guard_room"],
                   f["accessor"], f["header"], f["ordered"], f["existing_intact"]))
    return f


def request_packet(cpp_text, h_text, out_dir):
    """Apply + verify onto private copies; write patched files + #186 packet JSON."""
    patched_cpp, patched_h = apply_proposal(cpp_text, h_text)
    findings = verify_proposal(patched_cpp, patched_h)
    if not findings["ok"]:
        raise ProposalRejected("Hook verification failed: %s" % findings)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cpp_path = out_dir / "pc_bbft.cpp.proposed"
    h_path = out_dir / "pc_bbft.h.proposed"
    packet_path = out_dir / "overworld-boot-flag-186-request.json"
    for p in (cpp_path, h_path, packet_path):
        if p.exists():
            raise ProposalRejected("Refusing to overwrite existing " + p.name)
    cpp_path.write_text(patched_cpp, encoding="utf-8", newline="")
    h_path.write_text(patched_h, encoding="utf-8", newline="")
    packet = {
        "schema": 1, "issue": 738, "downstream_consumers": [696, 148],
        "base_native_commit": BASE_NATIVE_COMMIT,
        "base_cpp_sha256_prefix": BASE_CPP_SHA256_PREFIX,
        "patched_cpp_sha256": sha256_bytes(patched_cpp.encode("utf-8")),
        "patched_h_sha256": sha256_bytes(patched_h.encode("utf-8")),
        "hook_findings": findings,
        "owner_decision_needed": "#186 existing-owner approval to land the proposed pc_bbft.{cpp,h} diff verbatim (flag + registration + marker + refusals + two guard extensions)",
        "gates": "all six runtime gates UNTESTED; no build, no runtime, no ADMIT",
    }
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    return {"cpp": str(cpp_path), "header": str(h_path), "packet": str(packet_path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpp", type=Path, required=True)
    parser.add_argument("--header", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = request_packet(args.cpp.read_text(encoding="utf-8"),
                            args.header.read_text(encoding="utf-8"), args.out)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())