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


# OpenCode matches each parsed bash command against these wildcards; the last match wins,
# so they follow any existing catch-all. `git *` also covers `git -C <tree> ...`. Per-file
# conflict shortcuts (checkout --ours/--theirs, <ref> -- <path>, restore) count as -X ours/theirs.
INTEGRATOR_GIT_DENY = (
    'git *merge*-X*ours*', 'git *merge*-X*theirs*', 'git *merge*--strategy-option*', 'git *merge*-s*ours*',
    'git *pull*-X*', 'git *pull*--strategy*', 'git *pull*-s*ours*',
    'git *cherry-pick*-X*', 'git *rebase*-X*', 'git *reset*--hard*', 'git *clean*-*f*',
    'git *checkout*--ours*', 'git *checkout*--theirs*', 'git *checkout*-- *', 'git *checkout* .',
    'git *restore*--source*', 'git *restore*--worktree*', 'git restore *', 'git -C * restore *',
    'git *push*--force*', 'git *push* -f*', 'git *push*--mirror*', 'git *push* +*')


def load_config(path):
    """A launch config as a dict; tolerates only OpenCode's own schema-hint insertion. None if unreadable."""
    try:
        raw = Path(path).read_bytes()
        try:
            data = json.loads(raw.decode('utf-8-sig'))
        except ValueError:
            prefix = b'{\n  "$schema": "https://opencode.ai/config.json",'
            if not raw.startswith(prefix):
                return None
            data = json.loads((b'{' + raw[len(prefix):]).decode('utf-8-sig'))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def integrator_guard(data):
    """Deny destructive git in maintained worktrees for an integrator launch; None refuses the launch."""
    data = dict(data)
    if any(isinstance(section, dict) and any(isinstance(v, dict) and 'permission' in v for v in section.values())
           for section in (data.get('agent'), data.get('mode'))):
        return None  # An agent-level permission replaces the top-level one and would drop the guard.
    permissions = data.get('permission', {})
    if isinstance(permissions, str):
        permissions = {'*': permissions}
    if not isinstance(permissions, dict):
        return None
    bash = permissions.get('bash', permissions.get('*'))
    if bash == 'deny':
        return data  # Every shell command is already refused.
    if bash is not None and not isinstance(bash, (str, dict)):
        return None
    # No bash rule keeps OpenCode's default for unmatched commands; denies are only added.
    rules = {} if bash is None else {'*': bash} if isinstance(bash, str) else dict(bash)
    for pattern in INTEGRATOR_GIT_DENY:
        rules.pop(pattern, None)
        rules[pattern] = 'deny'
    data['permission'] = dict(permissions, bash=rules)
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
