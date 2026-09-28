"""Read the maintained admission contract in an isolated, read-only process."""
import json
from pathlib import Path
import subprocess
import sys


def snapshot(root, settings):
    source = settings.get('source')
    result = dict(status='unavailable', admitted=None, total=None, names=[], source=source)
    if not source:
        return result
    try:
        tree = (Path(root) / source).resolve()
        if not tree.is_relative_to(Path(root).resolve()):
            raise ValueError('Admission source must be inside the workspace')
        code = '''
import json
from experimental.pikmin2_enemy_roster import load_and_validate, admission_contract, identity_role
roster = load_and_validate()
eligible = [e for e in roster if identity_role(e) in ('source', 'variant')]
accepted = set(admission_contract(roster)['admitted'])
print(json.dumps(dict(status='observed', admitted=len(accepted), total=len(eligible),
    names=[e.common_name for e in eligible if e.source_id in accepted], ids=sorted(accepted),
    families=[dict(id=e.source_id, enum=e.enum_name, name=e.common_name)
              for e in eligible if e.source_id in accepted])))
'''
        run = subprocess.run([sys.executable, '-B', '-c', code], cwd=tree,
            capture_output=True, text=True, encoding='utf-8', timeout=15)
        if run.returncode:
            raise ValueError('Canonical admission validation failed')
        data = json.loads(run.stdout)
        if not (type(data['admitted']) is int and type(data['total']) is int and
                0 <= data['admitted'] <= data['total'] and data['total'] > 0):
            raise ValueError('Invalid admission counts')
        result.update(data)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result['error'] = str(exc)
    return result
