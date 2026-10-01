"""Explicit native floor4 diagnostic entry; no host campaign adapter or progress mutation."""
import json
import re
from experimental.pikmin2_campaign import SPECIES
from experimental.pikmin2_beasts_party_restore import restore_party
from experimental.pikmin2_beasts_floor4 import stage
from experimental.pikmin2_beasts_floor3_runtime import sha


def entry_text(party,token):
    party=restore_party(party)
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{64}',token):raise ValueError('Expected64 lowercase hexadecimal diagnostic token')
    lines=['P2_BEASTS_FLOOR4_ENTRY_1',token,f'4 {party["health"]:.9g} 20']
    lines += [f'{SPECIES.index(p["species"])} {p["maturity"]}' for p in party['squad']]
    return '\n'.join(lines)+'\n'


def stage_profile(assets,assembly,purple,pod,output,party,token):
    data=entry_text(party,token).encode()
    directory=stage(assets,assembly,purple,pod,output,party)
    overrides={'p2-cave-entry.txt':data,'p2-floor4-boundary.txt':(token+'\n').encode()}
    for name,raw in overrides.items():(directory/name).write_bytes(raw)
    report=json.loads((directory/'survey.json').read_bytes())
    report.update(policy='P2_BEASTS_FLOOR4_ENTRY_SURVEY_1',native_profile='forest_1',party_restore_protocol_floor=4,
        boundary_token=token,token_source='caller_declared_diagnostic',descent_enabled=False,failure_checkpoint_enabled=False)
    report['input_sha256'].update({name:sha(raw) for name,raw in overrides.items()})
    report['limitations'][0]='Explicit native floor4 diagnostic entry; no source-bound host campaign adapter or authorized progression.'
    report['limitations'].append('Floor5 descent and floor4 extinction/knockout persistence are disabled.')
    (directory/'survey.json').write_text(json.dumps(report,indent=2)+'\n')
    return directory
