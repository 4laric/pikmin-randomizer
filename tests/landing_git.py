"""Temporary git repositories for tests that record integration receipts (not a test module)."""
from pathlib import Path
import subprocess


def git(path, *args):
    return subprocess.run(['git', '-C', str(path), '-c', 'user.email=t@example.invalid', '-c', 'user.name=Test',
                           '-c', 'core.autocrlf=false', '-c', 'commit.gpgsign=false', *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files, message='change'):
    """Write/delete files ({path: text or None}) and commit them in repo (initialised on first use)."""
    repo = Path(repo)
    if not (repo / '.git').exists():
        repo.mkdir(parents=True, exist_ok=True)
        git(repo, 'init', '-q')
        (repo / '.gitignore').write_text('/output/\n/native/\n__pycache__/\n')
        git(repo, 'add', '.gitignore'); git(repo, 'commit', '-qm', 'base')
    for name, text in files.items():
        path = repo / name
        if text is None:
            git(repo, 'rm', '-q', '--', name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        git(repo, 'add', '--', name)
    git(repo, 'commit', '-qm', message, '--allow-empty')
    return git(repo, 'rev-parse', 'HEAD')


def head(repo):
    return git(repo, 'rev-parse', 'HEAD')


def source(reg, key, files, repo='root'):
    """Commit files and point the lane's root/native source at that one-commit range, revision unchanged."""
    tree = reg.root if repo == 'root' else reg.root / 'native'
    if not (tree / '.git').exists():
        commit(tree, {}, 'base')
    base = head(tree)
    sha = commit(tree, files, 'lane ' + key)
    with reg.transaction() as state:
        state['lanes'][key][repo] = dict(base=base, head=sha, commits=[sha], dirty='', worktree=str(tree))
        return state['lanes'][key]
