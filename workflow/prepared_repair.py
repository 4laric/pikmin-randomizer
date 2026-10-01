"""Audited replacement of an unclaimed launch specification."""
import argparse
import json
from pathlib import Path
from .autofill import validate_spec, github_issue, _private, _check_conflicts
from .control import fingerprint
from .handoff import require
from .runner import write
from types import SimpleNamespace


def repair(reg, manifest_path, replacement, expected_hash, evidence, issue_reader=github_issue):
    reg.evidence(evidence)
    path=_private(reg,str(manifest_path));before=path.read_bytes();manifest=json.loads(before)
    old=next((s for s in manifest['items'] if s['id']==replacement['id']),None)
    require(old is not None and fingerprint(old)==expected_hash,'Prepared spec changed; reread before repair')
    for field in ('lane','issue','owned_files','root','native'):
        require(old['lane'][field]==replacement['lane'][field], 'Repair must preserve ownership and source pins: '+field)
    require(old['workstream']==replacement['workstream'],'Workstream must be preserved')
    validate_spec(reg,replacement,issue_reader)
    with reg.transaction() as state:
        key=old['lane']['lane']
        require(key not in state['lanes'],'Registered lanes cannot be repaired as prepared specs')
        require(not any(x['lane']==key for x in state.get('control',{}).get('launches',{}).values()),'Launch already exists')
        require(path.read_bytes()==before,'Manifest changed; retry from fresh state')
        _check_conflicts(SimpleNamespace(reg=reg,config={'lanes':{}}),state,replacement)
        backup=path.parent/'prepared-repair-backups'/(expected_hash+'.json')
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():write(backup,old)
        manifest['items']=[replacement if s['id']==old['id'] else s for s in manifest['items']]
        write(path,manifest)
        data=state.setdefault('throughput_runtime',{}).setdefault('autofill',{})
        data.setdefault('items',{}).pop(old['id'],None)
        state.setdefault('prepared_spec_repairs',{})[expected_hash]=dict(
            lane=key,replacement_hash=fingerprint(replacement),evidence=evidence,backup=str(backup),at=reg.clock())
        reg.event(state,'prepared_spec_repaired',key,previous_hash=expected_hash,replacement_hash=fingerprint(replacement))
    return replacement['id']

def main():
    from .registry import Registry
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--request',type=Path,required=True)
    a=p.parse_args();reg=Registry(a.root/'output/workflow/registry.sqlite3',a.root)
    print(repair(reg,**json.loads(a.request.read_text(encoding='utf-8-sig'))))

if __name__=='__main__':main()
