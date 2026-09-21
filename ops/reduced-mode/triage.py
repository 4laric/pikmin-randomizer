"""Read-only triage of branches with commits not on the canonical lines."""
import subprocess, json, re, sys
from concurrent.futures import ThreadPoolExecutor
R = 'C:/Users/alari/pikmin-randomizer'
SKIP = re.compile(r'^(workflow-|codex/content-lanes-531$|claude/p2-deepseek-wave$|merge/|kimi/)')
REPORTY = re.compile(r'(^docs/|\.md$|(^|/)(report|reports|evidence|handoff)[^/]*|\.json$|\.txt$|\.log$)', re.I)
def g(repo, *a, ok=(0,)):
    p = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode, p.stdout
def one(repo, line, ref):
    # Commits whose patch is not already on the line ('+' in git cherry).
    _, out = g(repo, 'cherry', line, ref)
    new = [l[2:] for l in out.splitlines() if l.startswith('+ ')]
    if not new: return dict(ref=ref, kind='already_landed')
    base = g(repo, 'merge-base', line, ref)[1].strip()
    files = g(repo, 'diff', '--name-only', base, ref)[1].split()
    code = [f for f in files if not REPORTY.search(f)]
    if not code: return dict(ref=ref, kind='report_only', commits=len(new), files=len(files))
    rc, mt = g(repo, 'merge-tree', '--write-tree', '--name-only', '--no-messages', line, ref)
    conflicts = mt.splitlines()[1:] if rc == 1 else []
    stat = g(repo, 'diff', '--shortstat', base, ref, '--', *code[:400])[1].strip()
    added = int((re.search(r'(\d+) insertion', stat) or [0, 0])[1])
    when = g(repo, 'log', '-1', '--format=%cI', ref)[1].strip()
    subj = g(repo, 'log', '-1', '--format=%s', ref)[1].strip()
    return dict(ref=ref, kind='conflict' if rc == 1 else ('clean' if rc == 0 else 'error'), commits=len(new),
                code_files=len(code), added=added, conflicts=conflicts[:8], n_conflicts=len(conflicts), when=when,
                subject=subj[:120], code=code[:40])
out = {}
for name, repo, line in (('root', R, 'codex/p2-main-review'), ('native', R + '/native', 'claude/p2-deepseek-wave-native')):
    refs = [r for r in g(repo, 'for-each-ref', '--format=%(refname:short)', 'refs/heads')[1].split()
            if r != line and not SKIP.search(r) and g(repo, 'log', '-1', '--format=%cI', r)[1] >= '2026-09-10']
    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(lambda r: one(repo, line, r), refs))
    out[name] = rows
    from collections import Counter
    print(name, len(rows), Counter(r['kind'] for r in rows))
json.dump(out, open(sys.argv[1], 'w'), indent=1)
