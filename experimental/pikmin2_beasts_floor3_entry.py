"""Validated checkpoint-to-native Beasts floor 3 entry; supervisor launch remains separate."""
import json
import re
from experimental.pikmin2_beasts_party_restore import restore_party
from experimental.pikmin2_beasts_checkpoint_reference import digest
from experimental.pikmin2_beasts_floor3_runtime import stage, sha
from experimental.pikmin2_campaign import SPECIES


def entry_text(party, token):
    party=restore_party(party)
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Invalid floor3 boundary token')
    lines=['P2_BEASTS_FLOOR3_ENTRY_1',token,f'3 {party["health"]:.9g} 20']
    lines += [f'{SPECIES.index(p["species"])} {p["maturity"]}' for p in party['squad']]
    return '\n'.join(lines)+'\n'


def stage_checkpoint(adapter, checkpoint, assets, assembly, purple, pod, output):
    adapter.validate(checkpoint)
    if checkpoint['floor']!=3 or checkpoint['status']!='active':raise ValueError('Expected active floor3 checkpoint')
    party=restore_party(dict(health=checkpoint['health'],squad=checkpoint['squad']))
    token=adapter.token(checkpoint)
    encoded=entry_text(party,token).encode()
    directory=stage(assets,assembly,purple,pod,output,party)
    overrides={'p2-cave-entry.txt':encoded,'p2-floor3-boundary.txt':(token+'\n').encode(),
               'checkpoint.json':(json.dumps(checkpoint,indent=2)+'\n').encode()}
    for name,data in overrides.items():(directory/name).write_bytes(data)
    report=json.loads((directory/'survey.json').read_bytes())
    report.update(policy='P2_BEASTS_FLOOR3_ENTRY_SURVEY_1',party_restore_protocol_floor=3,
                  native_profile='forest_1',boundary_token=token,checkpoint_identity=digest(checkpoint),
                  checkpoint_profile=adapter.identity,descent_enabled=False)
    report['input_sha256'].update({name:sha(data) for name,data in overrides.items()})
    report['limitations'][0]='Explicit native Beasts floor3 entry; supervisor launch authorization and floor4 descent remain unavailable.'
    (directory/'survey.json').write_text(json.dumps(report,indent=2)+'\n')
    return directory
