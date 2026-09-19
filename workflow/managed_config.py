"""Repository-scoped access for unattended lanes; preserve explicit policies."""
import json
import hashlib
from pathlib import Path


def pinned_config_matches(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() == expected:
        return True
    # OpenCode inserts this schema hint into a supplied config. Accept only
    # that exact insertion when removing it recovers the pinned bytes.
    prefix = b'{\n  "$schema": "https://opencode.ai/config.json",'
    return raw.startswith(prefix) and hashlib.sha256(b'{' + raw[len(prefix):]).hexdigest() == expected


def output_access(config, output, root, brief=None):
    output, root = Path(output).resolve(), Path(root).resolve()
    if not output.is_relative_to(root / 'output'):
        return None
    try:
        data = json.loads(Path(config).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return None
    permissions = data.get('permission', {})
    if not isinstance(permissions, dict) or 'external_directory' in permissions or '*' in permissions:
        return None
    # Managed tasks need canonical scripts, registry, evidence and private
    # worktrees, not just their output folder. Ownership rules still govern
    # edits. Unattended launches have no permission responder: reject unknown
    # paths back to the model instead of leaving a tool waiting forever. The
    # specific repository exception follows the catch-all (last match wins).
    data['permission'] = dict(permissions, external_directory={
        '*': 'deny', root.as_posix() + '/**': 'allow'})
    return data


def permission_path_allowed(directory, rules):
    candidate = Path(directory).resolve()
    for rule in rules:
        if str(rule).endswith('/**'):
            if candidate.is_relative_to(Path(str(rule)[:-3]).resolve()):
                return True
        elif candidate == Path(rule).resolve():
            return True
    return False
