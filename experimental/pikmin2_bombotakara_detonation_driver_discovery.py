"""Pin/ownership discovery for the BombOtakara93 detonation driver (gate-3, #573).

Bounded DIAGNOSIS producer contract (never an engine unblock) for lane
`shard-enemies-3-bombotakara93-detonation-discovery`. It pins the exact
detonation driver callsites, build membership and owner routing for the #186
shared-hook review of enemy-bombotakara93-payload gate-3. It consumes the DONE
bombotakara93-bridge-pin-audit (#791) and provider-bomb-mgr-birth (#616)
outputs read-only and never duplicates them.

Method: verify the maintained native reference pin read-only (a95040b6) for
the shared blast primitive and the Teki forget seam, record explicit ABSENT
verdicts for the owner-scoped payload/birth drivers there, verify the owner
trees (#573 payload, #616 birth) for the exact detonation callsites with
file:line, attach the exact shared-review contract per item, name the
downstream #573 consumer commands, and emit a pinned registry JSON.
Fail-closed: unknown inputs, missing files, or pin drift raise before any
verdict. Stdlib only. No engine edits, no builds, no runtime runs, no ADMIT.
All six gates UNTESTED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

SCHEMA = "bombotakara93-detonation-driver-discovery-v1"
NATIVE_PIN = "a95040b66a0ffc9cdbfc649502569a29e66949a7"
BIRTH_COMMIT = "6d4cbc4a"

# Maintained-native reference pins (read-only; verified this turn at the pin).
# File+symbol is the contract; line numbers are observed references.
MAINTAINED = {
    "shared_blast_primitive": {
        "file": "pc_port/pc_p2_bombsarai_blast.h",
        "symbols": ["p2_bombsarai_route_blast", "P2BombSaraiBlastEvent"],
        "expect": "present",
        "contract": "#169 owns the blast primitive + #186 (shared blast path)",
    },
    "teki_forget_seam": {
        "file": "pc_port/pc_p2_batch2.h",
        "symbols": ["pc_p2_batch2_forget"],
        "expect": "present",
        "contract": "#186 (tekibteki TekiMgr forget path; shared engine seam)",
    },
    "payload_detonate_gate": {
        "file": "pc_port/pc_p2_bombotakara.cpp",
        "symbols": [],
        "expect": "absent",
        "contract": "#573 owns the payload driver + #186 (absent in maintained)",
    },
    "birth_hook_detonate": {
        "file": "pc_port/pc_p2_bomb_mgr_birth.cpp",
        "symbols": [],
        "expect": "absent",
        "contract": "#616 owns the birth hook + #186 (absent in maintained)",
    },
}

# Owner-tree pins (read-only). Exact file:line observed this turn.
OWNERS = {
    "payload_detonate_gate": {
        "owner": "enemy-bombotakara93-payload",
        "issue": 573,
        "files": {
            "pc_p2_bombotakara_policy.h": ["DetonationResult", "inline DetonationResult detonate"],
            "pc_p2_bombotakara.cpp": ["void detonate(Unit&", "applyBlast", "BlastOwner", "TriggerDeath"],
        },
        "contract": "#573 owns the payload driver + #186 (payload driver on shared blast path)",
    },
    "birth_hook_detonate": {
        "owner": "provider-bomb-mgr-birth",
        "issue": 616,
        "files": {
            "pc_p2_bomb_mgr_birth.h": ["int detonate(P2BombMgrHandle", "int blastCount"],
            "pc_p2_bomb_mgr_birth.cpp": ["P2BombMgr::detonate", "blastCount() const"],
        },
        "contract": "#616 owns the birth hook + #186 (birth hook on shared BTeki path)",
    },
}

# Downstream consumer: enemy-bombotakara93-payload (#573) gate-3 rerun over the
# landed drivers. The rerun is the consumer lane's action; the command shape
# below is the contract it must satisfy, not a claim about an existing run.
CONSUMER_LANE = "enemy-bombotakara93-payload"
CONSUMER_COMMAND = ("scripts/run_pikmin2_fixture.py --arena <bombotakara-arena> "
                    "--fixture <bombotakara-gate3-fixture.exe> --seconds <budget>")
EXPECTED_BEHAVIOR = {
    "detonate_once": "P2_BOMBOTAKARA_DETONATE exactly_once=1 total_detonations=1 on the fatal trigger; suppressed reruns emit DETONATE_SUPPRESSED",
    "blast_route": "P2_BOMBOTAKARA_BLAST with receivers routed via p2_bombsarai_route_blast; invalid blasts emit BLAST_BLOCKED",
    "birth_hook": "P2BombMgr::detonate binds the payload and routes the blast; blastCount increments once per detonation",
}


class DiscoveryRejected(ValueError):
    pass


def git_show(native_repo, commit, path):
    """Return file bytes at a commit, or None if absent (read-only)."""
    proc = subprocess.run(
        ["git", "-C", str(native_repo), "show", "%s:%s" % (commit, path)],
        capture_output=True)
    if proc.returncode != 0:
        return None
    return proc.stdout


def check_symbols(text, symbols):
    """Return (found, missing) for substring symbols in text."""
    found = [s for s in symbols if s in text]
    return found, [s for s in symbols if s not in text]


def verify_maintained(native_repo, commit=NATIVE_PIN):
    """Verify each maintained boundary as present/ABSENT per expectation."""
    findings = {}
    for item, spec in MAINTAINED.items():
        blob = git_show(native_repo, commit, spec["file"])
        if blob is None:
            verdict = "ABSENT"
            ok = spec["expect"] == "absent"
            detail = {"present": False, "symbols_found": [], "symbols_total": len(spec["symbols"])}
        else:
            text = blob.decode("utf-8", errors="replace")
            found, missing = check_symbols(text, spec["symbols"])
            verdict = "PRESENT" if not missing else "PARTIAL"
            ok = spec["expect"] == "present" and not missing
            detail = {"present": True, "symbols_found": found, "symbols_total": len(spec["symbols"]),
                      "missing_symbols": missing}
        findings[item] = {"file": spec["file"], "expect": spec["expect"],
                          "verdict": verdict, "ok": ok, "contract": spec["contract"],
                          "detail": detail}
        if not ok:
            raise DiscoveryRejected("Maintained pin mismatch for %s: %s" % (item, findings[item]))
    return findings


def verify_owner(tree_root, files):
    """Verify owner-tree files exist and carry the pinned symbols (read-only)."""
    root = Path(tree_root)
    findings = {}
    for rel, symbols in files.items():
        path = root / rel
        if not path.is_file():
            raise DiscoveryRejected("Owner file missing: %s" % path)
        text = path.read_text(errors="replace")
        found, missing = check_symbols(text, symbols)
        if missing:
            raise DiscoveryRejected("Owner symbols missing in %s: %s" % (rel, missing))
        findings[rel] = {"symbols_found": found, "symbols_total": len(symbols)}
    return findings


def build_registry(native_repo, owner_573_root, birth_repo,
                   native_pin=NATIVE_PIN, birth_commit=BIRTH_COMMIT):
    """Verify all boundaries; return the pinned registry dict (no writes)."""
    maintained = verify_maintained(native_repo, native_pin)
    payload = verify_owner(owner_573_root, OWNERS["payload_detonate_gate"]["files"])
    birth_pc_port = Path(birth_repo) / "pc_port"
    birth = verify_owner(birth_pc_port, OWNERS["birth_hook_detonate"]["files"])
    # Birth files live in the native repo at the #616 commit; confirm via git.
    for rel in OWNERS["birth_hook_detonate"]["files"]:
        if git_show(birth_repo, birth_commit, "pc_port/" + rel) is None:
            raise DiscoveryRejected("Birth reference missing: %s" % rel)
    items = {
        "payload_detonate_gate": {
            "maintained": maintained["payload_detonate_gate"]["verdict"],
            "owner": OWNERS["payload_detonate_gate"],
            "owner_verified": payload,
            "contract": MAINTAINED["payload_detonate_gate"]["contract"],
        },
        "birth_hook_detonate": {
            "maintained": maintained["birth_hook_detonate"]["verdict"],
            "owner": OWNERS["birth_hook_detonate"],
            "owner_verified": birth,
            "contract": MAINTAINED["birth_hook_detonate"]["contract"],
        },
        "shared_blast_primitive": {
            "maintained": maintained["shared_blast_primitive"]["verdict"],
            "owner": {"owner": "projectiles/BombSarai", "issue": 169},
            "contract": MAINTAINED["shared_blast_primitive"]["contract"],
        },
        "teki_forget_seam": {
            "maintained": maintained["teki_forget_seam"]["verdict"],
            "owner": {"owner": "shared engine seam (tekibteki)", "issue": 186},
            "contract": MAINTAINED["teki_forget_seam"]["contract"],
        },
    }
    return {"schema": SCHEMA, "native_pin": native_pin, "birth_commit": birth_commit,
            "bridge_audit": "consumed read-only from DONE bombotakara93-bridge-pin-audit (#791); not re-derived here",
            "birth_provider": "consumed read-only from DONE provider-bomb-mgr-birth (#616); not re-derived here",
            "items": items,
            "consumer": {"lane": CONSUMER_LANE, "command": CONSUMER_COMMAND,
                         "expected": EXPECTED_BEHAVIOR},
            "gates": "all six runtime gates UNTESTED; no runtime run, no ADMIT"}


def emit_registry(native_repo, owner_573_root, birth_repo, out_dir,
                  native_pin=NATIVE_PIN, birth_commit=BIRTH_COMMIT):
    """Verify, then write the pinned registry JSON; return paths + hashes."""
    registry = build_registry(native_repo, owner_573_root, birth_repo,
                              native_pin, birth_commit)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "bombotakara93-detonation-driver-registry.json"
    if path.exists():
        raise DiscoveryRejected("Refusing to overwrite existing registry")
    blob = (json.dumps(registry, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(blob)
    return {"registry": str(path),
            "sha256": hashlib.sha256(blob).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-repo", type=Path, required=True)
    parser.add_argument("--native-pin", default=NATIVE_PIN)
    parser.add_argument("--owner-573", type=Path, required=True)
    parser.add_argument("--birth-repo", type=Path, required=True)
    parser.add_argument("--birth-commit", default=BIRTH_COMMIT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = emit_registry(args.native_repo, args.owner_573, args.birth_repo,
                           args.out, args.native_pin, args.birth_commit)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
