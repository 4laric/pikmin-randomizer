"""Pure profile-bound Beasts checkpoint reference. No native or disk integration."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
import re
from experimental.pikmin2_campaign import squad_valid
from experimental.pikmin2_beasts_lifecycle_reference import budgets

SCHEMA='P2_BEASTS_CHECKPOINT_REFERENCE_1'

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def receipts_valid(receipts):
    if not isinstance(receipts,dict) or len(receipts)>1024:raise ValueError('Invalid receipts')
    for key,value in receipts.items():
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_:/-]{1,100}',key) or type(value) is not int or not 0<=value<=1000000:
            raise ValueError('Invalid receipt identity/value')
    if sum(receipts.values())>2147483647:raise ValueError('Receipt balance overflow')


def party_valid(squad,health):
    squad_valid(squad)
    if type(health) not in (int,float) or not math.isfinite(health) or not 0<=health<=1:raise ValueError('Invalid health')


class BeastsReferenceAdapter:
    def __init__(self,audit,content,floor_receipts):
        if not isinstance(content,str) or not re.fullmatch('[0-9a-f]{64}',content):raise ValueError('Invalid content identity')
        if audit.get('cave')!='forest_1' or audit.get('slots_per_flower')!=5:raise ValueError('Unsupported source profile')
        if [(f['floor'],f['next_floor'],f['geyser'],f['clogged']) for f in audit['floors']]!=[(1,2,False,False),(2,3,False,False),(3,4,False,False)]:
            raise ValueError('Unsupported floor edges')
        if set(floor_receipts)!={1,2,3} or floor_receipts[2]:raise ValueError('Floor2 has no supported receipts')
        instances={}
        for allowed in floor_receipts.values():
            receipts_valid(allowed)
            for key,value in allowed.items():
                if key in instances and instances[key]!=value:raise ValueError('Conflicting profile receipt value')
                instances[key]=value
        self.profile=deepcopy(dict(content=content,audit=audit,receipts=floor_receipts))
        self.identity=digest(self.profile)

    def token(self,state):
        return digest(dict(profile=self.identity,trip=state['trip'],floor=state['floor'],revision=state['revision']))

    def context(self,floor,context,squad):
        if not isinstance(context,dict):raise ValueError('Invalid generation context')
        if floor!=2:
            if context!={}:raise ValueError('Unexpected destination context')
            return {},{}
        if set(context)!={'global_plus_cave_purple','spawned_flowers'}:raise ValueError('Missing generation population/instances')
        population=context['global_plus_cave_purple'];flowers=context['spawned_flowers']
        allowed=budgets(5,population)
        if population<sum(p['species']=='purple' for p in squad):raise ValueError('Global context excludes incoming Purple')
        if not isinstance(flowers,list) or any(not isinstance(f,str) for f in flowers) or len(flowers)!=len(set(flowers)) or any(f not in allowed for f in flowers):
            raise ValueError('Invalid or suppressed Violet spawn')
        return deepcopy(context),{f:allowed[f] for f in flowers}

    def initial(self,trip,squad,health,receipts):
        if not isinstance(trip,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',trip):raise ValueError('Invalid trip')
        party_valid(squad,health);receipts_valid(receipts)
        if not squad or health<=0:raise ValueError('Initial party must be alive')
        return dict(schema=SCHEMA,profile=self.identity,trip=trip,revision=0,floor=1,status='active',
                    squad=deepcopy(squad),health=health,receipts=dict(receipts),context={},budgets={},events={},conversions={})

    def validate(self,state):
        if not isinstance(state,dict) or set(state)!={'schema','profile','trip','revision','floor','status','squad','health','receipts','context','budgets','events','conversions'}:
            raise ValueError('Invalid checkpoint fields')
        if state['schema']!=SCHEMA or state['profile']!=self.identity:raise ValueError('Checkpoint profile changed')
        if not isinstance(state['trip'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',state['trip']):raise ValueError('Invalid checkpoint trip')
        if type(state['floor']) is not int or state['floor'] not in (1,2,3) or type(state['revision']) is not int or not 0<=state['revision']<=3:
            raise ValueError('Invalid checkpoint floor/revision')
        if state['status'] not in ('active','failed') or state['revision']!=state['floor']-1+(state['status']=='failed'):
            raise ValueError('Invalid checkpoint phase')
        party_valid(state['squad'],state['health']);receipts_valid(state['receipts'])
        if state['status']=='active' and (not state['squad'] or state['health']<=0):raise ValueError('Missing survivors')
        if state['status']=='failed' and state['squad']:raise ValueError('Failed checkpoint has survivors')
        if state['floor']==3 and state['status']=='failed' and state['health']!=0:
            raise ValueError('Floor3 failure requires normalized zero health')
        if not isinstance(state['events'],dict) or len(state['events'])!=state['revision']:raise ValueError('Missing boundary event')
        if any(not isinstance(k,str) or not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',k) or not re.fullmatch('[0-9a-f]{64}',v) for k,v in state['events'].items()):raise ValueError('Invalid boundary fingerprint')
        if not isinstance(state['conversions'],dict):raise ValueError('Invalid conversion history')
        used=Counter()
        flowers=budgets(5,0)
        for identifier,event in state['conversions'].items():
            if (not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9_:/-]{1,100}',identifier)
                    or not isinstance(event,dict) or set(event)!={'id','flower','input','floor'}
                    or event['id']!=identifier or type(event['floor']) is not int or event['floor']!=2
                    or not isinstance(event['flower'],str) or event['flower'] not in flowers
                    or event['input'] not in ('red','blue','yellow','purple')):
                raise ValueError('Invalid conversion history record')
            # Witnesses are committed at a boundary, never during an active floor.
            if state['floor']<2 or (state['floor']==2 and state['status']!='failed'):
                raise ValueError('Conversion history precedes its boundary')
            if event['input']!='purple':
                used[event['flower']]+=1
                if used[event['flower']]>flowers[event['flower']]:raise ValueError('Conversion history exceeds Violet capacity')
        if len(state['conversions'])>1000:raise ValueError('Conversion history too large')
        # Generation snapshot is historical: later conversions may exceed its Purple count.
        _,expected=self.context(state['floor'],state['context'],[])
        if state['budgets']!=expected:raise ValueError('Conversion budget changed')
        if state['floor']==2 and any(event['flower'] not in expected for event in state['conversions'].values()):
            raise ValueError('Conversion history uses suppressed Violet')
        return state

    def launch_requirement(self,state):
        self.validate(state)
        if state['status']=='failed':raise ValueError('Terminal checkpoint cannot launch')
        if state['floor']==3:raise ValueError('Floor3 remains durable but native staging is unsupported')
        return dict(floor=state['floor'],token=self.token(state),native_ready=False,
                    reason='Reference adapter only; native witnesses/anchors/receiver integration required')

    def fail_floor3(self,state,token,reason):
        self.validate(state)
        if reason not in ('extinction','knockout'):raise ValueError('Invalid failure reason')
        fingerprint=digest(dict(policy='P2_BEASTS_FAILURE_1',reason=reason))
        if token in state['events']:
            if state['events'][token]!=fingerprint:raise ValueError('Conflicting failure replay')
            return deepcopy(state)
        if state['floor']!=3 or state['status']!='active' or token!=self.token(state):
            raise ValueError('Failure requires the active floor3 boundary')
        result=deepcopy(state)
        result.update(revision=state['revision']+1,status='failed',squad=[],health=0)
        result['events'][token]=fingerprint
        return self.validate(result)

    def apply(self,state,token,squad,health,receipts,conversions,destination_context):
        self.validate(state);party_valid(squad,health);receipts_valid(receipts)
        payload=dict(squad=squad,health=health,receipts=receipts,conversions=conversions,destination_context=destination_context)
        fingerprint=digest(payload)
        if token in state['events']:
            if state['events'][token]!=fingerprint:raise ValueError('Conflicting boundary replay')
            return deepcopy(state)
        if state['status']!='active' or token!=self.token(state):raise ValueError('Stale or terminal boundary')
        if state['floor']==3:raise ValueError('Unsupported floor3 handoff')
        for key,value in state['receipts'].items():
            if receipts.get(key)!=value:raise ValueError('Receipts regressed')
        allowed=self.profile['receipts'][state['floor']]
        for key,value in receipts.items():
            if key not in state['receipts'] and allowed.get(key)!=value:raise ValueError('Unapproved receipt')
        available=Counter(p['species'] for p in state['squad']);used=Counter();seen=set(state['conversions'])
        if not isinstance(conversions,list) or len(conversions)>1000:raise ValueError('Invalid conversion witness list')
        for event in conversions:
            if not isinstance(event,dict) or set(event)!={'id','flower','input'}:raise ValueError('Invalid conversion witness')
            identifier=event['id'];flower=event['flower'];color=event['input']
            if not isinstance(identifier,str) or not re.fullmatch('[A-Za-z0-9_:/-]{1,100}',identifier) or identifier in seen:raise ValueError('Duplicate/invalid conversion identity')
            seen.add(identifier)
            if flower not in state['budgets'] or color not in ('red','blue','yellow','purple') or available[color]<=0:raise ValueError('Impossible conversion input')
            if color!='purple':
                used[flower]+=1;available[color]-=1;available['purple']+=1
                if used[flower]>state['budgets'][flower]:raise ValueError('Violet capacity exceeded')
        after=Counter(p['species'] for p in squad)
        if len(squad)>len(state['squad']) or any(after[c]>available[c] for c in after):raise ValueError('Unwitnessed population/species increase')
        failed=not squad or health<=0
        floor=state['floor'] if failed else state['floor']+1
        if failed:
            if destination_context!={}:raise ValueError('Failure cannot stage a destination')
            context,limits=state['context'],state['budgets']
        else:context,limits=self.context(floor,destination_context,squad)
        result=deepcopy(state)
        result.update(revision=state['revision']+1,floor=floor,status='failed' if failed else 'active',
                      squad=[] if failed else deepcopy(squad),health=health,receipts=dict(receipts),context=context,budgets=limits)
        result['events'][token]=fingerprint
        for event in conversions:result['conversions'][event['id']]=dict(event,floor=state['floor'])
        return self.validate(result)
