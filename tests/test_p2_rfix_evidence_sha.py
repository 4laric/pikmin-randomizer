"""Roster rfix (#871): evidence log sha256 provenance pins.

Every ``native.log (sha256 X...)`` citation in the roster evidence overlay and
in ``P2_PLAYABLE_POOL`` must carry the real sha256 prefix of the cited log
file -- earlier roster-wave entries copied per-family exe hashes from the pool
rows instead. Where a cited log path exists locally the test recomputes the
hash and fails on mismatch (this fails on the pre-fix entries); where the
path does not exist (other machines, pruned logs) the entry is skipped.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EVIDENCE = ROOT / "docs" / "PIKMIN2_ENEMY_ROSTER_EVIDENCE.json"

LOGPAT = re.compile(r"C:/cop/[^\s:\)\"']+\.log")
SHAPAT = re.compile(r"\(sha256 ([0-9a-f]{16})\.\.\.\)")


def cited_pairs():
    """Yield (where, log path, cited 16-hex prefix) for evidence + pool rows."""
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    pairs = []
    for key, entry in ev["entries"].items():
        blobs = [entry.get("delivery_receipt", "")] + entry.get("notes", [])
        for blob in blobs:
            for match in LOGPAT.finditer(blob):
                tail = blob[match.end():match.end() + 40]
                sha = SHAPAT.search(tail)
                if sha:
                    pairs.append((f"evidence:{key}", match.group(0), sha.group(1)))
    from randomizer.seed import P2_PLAYABLE_POOL

    for row in P2_PLAYABLE_POOL:
        log = (row.get("evidence") or {}).get("log", "")
        for match in LOGPAT.finditer(log):
            tail = log[match.end():match.end() + 40]
            sha = SHAPAT.search(tail)
            if sha:
                pairs.append((f"pool:{row['source_id']}", match.group(0), sha.group(1)))
    # dedupe, keep order
    seen = set()
    unique = []
    for item in pairs:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def test_corrected_own_token_lines():
    """69 binds and 34/70 draws are cited on the species' own generator token.

    69's old L1585 BIND is sibling generator 1787125272 (own token is
    1945764764 at L1586); the roster handoff's 34/70 DRAW lines L1146/L1151
    are sibling generator 3850487044 (own token 3921089765 draws at
    L1161/L1166). Fails on the pre-fix citations.
    """
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    notes69 = " ".join(ev["entries"]["69"]["notes"])
    assert "L1586" in notes69 and "1945764764" in notes69
    assert "L1585 BIND is sibling generator 1787125272" in notes69
    for kid, line, species in (("34", 1161, "SnakeCrow"), ("70", 1166, "SnakeWhole")):
        notes = " ".join(ev["entries"][kid]["notes"])
        assert f"L{line}" in notes, f"entry {kid} must cite own-token DRAW L{line}"
    cases = [
        ("C:/cop/botcamp-inst-legs-69b-69-BigFoot/session/runs/"
         "d7683ffb7f6a225e090df66ee446cec0cffa9bc09a8c35ba0051a265354d5a3f/"
         "native.log", 1586, "P2_LONG_LEGS_BIND generator=1945764764"),
        ("C:/cop/botcamp-roster-34-SnakeCrow/session/runs/"
         "91159f7966460d11d0b36b7237abf405dc51f67862777c068b91acb8fd752367/"
         "native.log", 1161,
         "P2_SNAKEJOINT_DRAW generator=3921089765 key=snagret|SnakeCrow"),
        ("C:/cop/botcamp-roster-70-SnakeWhole/session/runs/"
         "0c0532433f2c8a11cfee469284351429885fda2afc0b91b0f77faad2929aef77/"
         "native.log", 1166,
         "P2_SNAKEJOINT_DRAW generator=3921089765 key=snagret|SnakeWhole"),
    ]
    for path, line, marker in cases:
        if not Path(path).is_file():
            continue
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        assert marker in lines[line - 1], f"{path} L{line}: {lines[line-1][:120]}"


def test_cited_log_shas_match_where_logs_exist():
    pairs = cited_pairs()
    assert pairs, "no C:/cop native.log sha citations found"
    checked = 0
    skipped = []
    for where, path, cited in pairs:
        if not Path(path).is_file():
            skipped.append(f"{where} {path}")
            continue
        real = hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
        assert cited == real, f"{where}: {path} cites sha {cited}... but file is {real}..."
        checked += 1
    assert checked > 0, f"no cited logs exist locally; skipped: {skipped}"
