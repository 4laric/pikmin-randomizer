"""Reject unusable export patches before they become integrator-ready packets."""
from .handoff import require


def validate(reg, details):
    path=reg.evidence(details.get('export_patch'))
    raw=path.read_bytes()
    require(b'\0' not in raw, 'Export patch contains NUL bytes; generate UTF-8, not UTF-16')
    text=raw.decode('utf-8-sig')
    lines=text.splitlines()
    require(any(x.startswith('diff --git ') for x in lines) and
            any(x.startswith('--- ') for x in lines) and
            any(x.startswith('+++ ') for x in lines) and
            any(x.startswith('@@ ') for x in lines), 'Export patch must contain a UTF-8 unified Git diff')
    reg.evidence(details.get('export_validation'))


def error(reg, action):
    if action.get('target',{}).get('kind')!='export_preparation':return None
    try:
        validate(reg,action['details'])
    except (ValueError,OSError,KeyError,TypeError) as exc:
        return str(exc)
    return None
