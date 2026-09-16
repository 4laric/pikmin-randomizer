"""Opt-in Beasts floor2 native transfer codec and diagnostic receiver."""
import math
import re
from experimental.pikmin2_campaign import SPECIES
from experimental.pikmin2_beasts_checkpoint_reference import party_valid
from experimental.pikmin2_beasts_boundary import boundary_text
from experimental.pikmin2_beasts_witness_bridge import bound_checkpoint_witnesses


def transfer_party(text,token):
    boundary_text(token)
    lines=text.splitlines()
    if len(lines)<3 or lines[0]!='P2_BEASTS_TRANSFER_1' or lines[1]!=token:
        raise ValueError('Wrong Beasts transfer identity')
    match=re.fullmatch(r'2 3 ([0-9.eE+-]+) ([0-9]+)',lines[2])
    if match is None:raise ValueError('Invalid Beasts transfer edge/header')
    health=float(match[1]);count=int(match[2])
    if count>100 or len(lines)!=3+count:raise ValueError('Invalid transfer count')
    squad=[]
    for line in lines[3:]:
        record=re.fullmatch(r'([0-3]) ([0-2])',line)
        if record is None:raise ValueError('Invalid transfer survivor')
        squad.append(dict(species=SPECIES[int(record[1])],maturity=int(record[2])))
    party_valid(squad,health)
    if bool(squad)!=(health>0):raise ValueError('Inconsistent transfer failure state')
    return dict(squad=squad,health=health)


def checkpoint_payload(adapter,checkpoint,log,readiness,transfer):
    result=bound_checkpoint_witnesses(adapter,checkpoint,log,readiness)
    markers=['P2_BEASTS_EXIT_REMOTE_REJECTED','P2_BEASTS_EXIT_TRANSFER_WRITTEN','P2_BEASTS_PARTY health=']
    if any(log.count(m)!=1 for m in markers) or [log.index(m) for m in markers]!=sorted(log.index(m) for m in markers):
        raise ValueError('Missing/invalid native hole interaction evidence')
    party=transfer_party(transfer,result['token'])
    snapshot=result['party_snapshot']
    if party['squad']!=snapshot['squad'] or not math.isclose(party['health'],snapshot['health'],rel_tol=1e-6,abs_tol=1e-7):
        raise ValueError('Native transfer differs from observed party')
    return dict(**party,receipts=dict(checkpoint['receipts']),conversions=result['events'],destination_context={})
