"""Evidence guard shared by handoff validation and fixture log audits."""
import re

DOWN = re.compile(r'^\s*P2_[A-Z0-9_]*CAPTAIN_DOWN(?:\s|$)', re.MULTILINE)

def captain_interrupted(path):
    if path.suffix.lower() not in ('.log', '.txt', '.jsonl'): return False
    with path.open(encoding='utf-8',errors='replace') as stream:
        return any(DOWN.search(line) for line in stream)

def require_uninterrupted(paths, refs, label):
    from .handoff import require
    for key in refs:
        require(not captain_interrupted(paths[key]), label + ': captain-down run cannot substantiate PASS: ' + key)
