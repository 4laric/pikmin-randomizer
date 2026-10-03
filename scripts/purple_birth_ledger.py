"""Read-only stock decoding for a newly observed native card, never card construction.

Source boundary: MemoryCard::writeCurrentGame writes PlayState (4 bytes +4
big-endian integers), then PlayerState's cont tag and PikiInfMgr 3x3 integers.
The caller must additionally prove actual native SAVE/cleanup, manifest/schema,
new session identity, full birth ledger, and unchanged card hash on fresh resume.
"""
import hashlib,re,struct

def decode_stock(data, *, sha256, fingerprint, benefit_count, check_count, day):
    if hashlib.sha256(data).hexdigest()!=sha256:
        raise ValueError('Observed genuine card hash changed')
    if type(benefit_count) is not int or not 3<=benefit_count<=7 or type(check_count) is not int or check_count<0:
        raise ValueError('Actual checkpoint schema required')
    if type(day) is not int or not 1<=day<=255 or not re.fullmatch('[0-9a-f]{64}',fingerprint):
        raise ValueError('Actual native day/fingerprint required')
    header,payload=data.split(b'\n',1);values=header.decode('ascii').split(' ')
    if len(payload)!=32768 or len(values)!=3+benefit_count+6+1 or values[:3]!=['PIKMIN_CAMPAIGN_PURPLE_1',fingerprint,'1']:
        raise ValueError('Native checkpoint schema/generation/size mismatch')
    if any(not re.fullmatch('0|[1-9][0-9]*',v) for v in values[3:]):
        raise ValueError('Noncanonical checkpoint integer')
    used=list(map(int,values[3:3+benefit_count]))
    if any(v>check_count for v in used):raise ValueError('Consumed benefit out of range')
    checksum=14695981039346656037
    for byte in header.rsplit(b' ',1)[0]+b'\n'+payload:
        checksum=((checksum^byte)*1099511628211)&((1<<64)-1)
    if checksum!=int(values[-1]):raise ValueError('Native checkpoint checksum mismatch')
    # Native PlayState ReadyToSave=2, actual saved day, then source cont/cach.
    if payload[0]!=2 or payload[2]!=day or payload[20:24]!=b'cont' or payload[60:64]!=b'cach':
        raise ValueError('Native PlayState/stock framing mismatch')
    rgb=list(struct.unpack('>9i',payload[24:60]));p2=list(map(int,values[3+benefit_count:-1]))
    if any(not 0<=v<=100000 for v in rgb+p2):raise ValueError('Invalid native stock count')
    # PlayState quick counts may be -1 for unopened onions; otherwise match cont.
    red,yellow,blue=struct.unpack('>3i',payload[4:16])
    for quick,total in zip((blue,red,yellow),(sum(rgb[:3]),sum(rgb[3:6]),sum(rgb[6:]))):
        if quick!=-1 and quick!=total:raise ValueError('Native quick/cont stock disagreement')
    return {'rgb':rgb,'p2':p2,'day':day,'generation':1,'sha256':sha256}

CENSUS=re.compile(r'P2_PURPLE_BIRTH_CENSUS stage=(initial|acquired|saved) species=([0-5]) maturity=([0-2]) field=(0|[1-9][0-9]*) stock=(0|[1-9][0-9]*) heads=(0|[1-9][0-9]*) read_only=1')
SAVE='P2_PURPLE_BIRTH_LEDGER_SAVE_PASS initial20=1 successful_births_only=1 exact_conversion=1 all15stock_maturities_observed=1 field0=1 heads0=1 external_card_match_required=1 read_only=1'

def saved_census(log, stock):
    """Card equality only; full receipt replay is an additional acceptance gate."""
    rows={};done=False
    for line in log.splitlines():
        if line.startswith('P2_PURPLE_BIRTH_CENSUS stage=saved'):
            match=CENSUS.fullmatch(line)
            if not match or done:raise ValueError('Malformed/late saved census')
            _,species,maturity,field,count,heads=match.groups();key=(int(species),int(maturity))
            if key in rows or int(field) or int(heads):raise ValueError('Duplicate or non-stock saved compartment')
            expected=(stock['rgb']+stock['p2']+[0,0,0])[key[0]*3+key[1]]
            if int(count)!=expected:raise ValueError('Observed stock differs from actual card')
            rows[key]=int(count)
        elif line.startswith('P2_PURPLE_BIRTH_LEDGER_SAVE_PASS'):
            if line!=SAVE or done or len(rows)!=18:raise ValueError('Incomplete/duplicate ledger save boundary')
            done=True
    if not done:raise ValueError('Actual ledger save boundary missing')
    return {'card_compartments_matched':15,'bulbmin_stock_zero':True,'receipt_replay_required':True}


"""Replay bounded read-only native receipts; never inferred requested seeds as births."""
import re
RECEIPT_KEYS=('kind frame receipt onion source head model color maturity requested pending_before pending_after physical_pellet_binding logical_demand_accounting read_only').split()
CONVERSION_KEYS=('frame bud generator input head input_species input_maturity output_species one_to_one read_only').split()

def integers(line,prefix,keys):
    if not line.startswith(prefix+' '):raise ValueError('Wrong receipt marker')
    words=line[len(prefix)+1:].split(' ')
    if len(words)!=len(keys):raise ValueError('Incomplete receipt')
    out={}
    for word,key in zip(words,keys):
        pair=word.split('=')
        if len(pair)!=2 or pair[0]!=key or not re.fullmatch('-1|0|[1-9][0-9]*',pair[1]):raise ValueError('Malformed/duplicate receipt field')
        out[key]=int(pair[1])
    return out

def validate_birth_receipts(log):
    census={name:{} for name in ('initial','acquired','saved')};births=[0,0,0];baseline=None;at_stage={}
    pending={};demands={};receipts=set();conversion=None;last_frame=-1;done=False;next_receipt=1
    for line in log.splitlines():
        if line.startswith('P2_PURPLE_BIRTH_RECEIPT'):
            if done or census['saved']:raise ValueError('Late birth receipt')
            e=integers(line,'P2_PURPLE_BIRTH_RECEIPT',RECEIPT_KEYS)
            if e['read_only']!=1 or e['physical_pellet_binding']!=0 or e['logical_demand_accounting']!=1 or e['frame']<last_frame:
                raise ValueError('Wrong source qualification/tick')
            last_frame=e['frame'];kind=e['kind'];onion=e['onion'];color=e['color'];receipt=e['receipt']
            if not 0<=kind<=3 or onion<=0 or not 0<=color<3 or receipt<=0:raise ValueError('Unknown/foreign receipt')
            if any(not 0<=e[k]<(1<<64) for k in ('frame','receipt','onion','source','head')) or not 0<=e['model']<(1<<32):raise ValueError('Native receipt width exceeded')
            if kind in (0,3):
                if receipt!=next_receipt:raise ValueError('Skipped/reordered native receipt')
                next_receipt+=1
            before,after=e['pending_before'],e['pending_after'];current=pending.get(onion,0)
            if before!=current or not 0<=before<=100000 or not 0<=after<=100000:raise ValueError('Unaccounted native pending demand')
            if kind==0:
                if receipt in receipts or e['source']<=0 or e['head'] or e['maturity']!=-1 or not 0<=e['requested']<=100000 or after-before!=e['requested']:
                    raise ValueError('Malformed actual demand')
                receipts.add(receipt);demands.setdefault(onion,[]).append([receipt,color,e['requested']])
            elif kind in (1,2):
                if e['source'] or e['model'] or e['requested'] or before<=0 or after!=before-1:
                    raise ValueError('Malformed successful birth')
                available=[d for d in demands.get(onion,[]) if d[2]>0]
                if not available or available[0][:2]!=[receipt,color]:raise ValueError('Wrong logical source-demand receipt')
                if (kind==1 and (e['head']<=0 or e['maturity']!=-1)) or (kind==2 and (e['head'] or e['maturity']!=0)):
                    raise ValueError('Emitted/stored native path mismatch')
                available[0][2]-=1;births[color]+=1
            else:
                if receipt in receipts or before or after or e['source'] or e['model'] or e['requested'] or e['head']<=0 or e['maturity']!=-1:
                    raise ValueError('Malformed boot birth')
                receipts.add(receipt);births[color]+=1
            pending[onion]=after
        elif line.startswith('P2_PURPLE_CONVERSION_RECEIPT'):
            if done or conversion is not None:raise ValueError('Late/duplicate replacement')
            e=integers(line,'P2_PURPLE_CONVERSION_RECEIPT',CONVERSION_KEYS)
            if any(e[k]<=0 for k in ('bud','generator','input','head')) or e['input']==e['head'] or e['frame']<last_frame or e['input_species']!=1 or not 0<=e['input_maturity']<=2 or e['output_species']!=3 or e['one_to_one']!=1 or e['read_only']!=1:
                raise ValueError('Wrong typed actual Red-to-Purple replacement')
            conversion=e;last_frame=e['frame']
        elif line.startswith('P2_PURPLE_BIRTH_CENSUS'):
            if done:raise ValueError('Late census')
            m=CENSUS.fullmatch(line)
            if not m:raise ValueError('Malformed census')
            stage,species,maturity,field,stock,heads=m.groups();key=int(species),int(maturity)
            if key in census[stage]:raise ValueError('Duplicate census compartment')
            if stage=='initial' and baseline is None:
                if conversion is not None:raise ValueError('Replacement precedes initial baseline')
                baseline=births.copy()
            if stage!='initial' and (conversion is None or baseline is None or len(census['initial'])!=18):raise ValueError('Initial full census missing')
            if stage=='saved' and len(census['acquired'])!=18:raise ValueError('Acquisition full census missing')
            if stage not in at_stage:at_stage[stage]=births.copy()
            values=tuple(map(int,(field,stock,heads)))
            if any(v>100000 for v in values):raise ValueError('Unbounded census count')
            census[stage][key]=values
        elif line.startswith('P2_PURPLE_BIRTH_LEDGER_SAVE_PASS'):
            if line!=SAVE or done or any(len(v)!=18 for v in census.values()):raise ValueError('Missing/duplicate full save proof')
            done=True
    if not done or conversion is None or baseline is None or any(pending.values()):raise ValueError('Incomplete successful native birth/replacement proof')
    initial=census['initial']
    if sum(initial[1,m][0] for m in range(3))!=20 or any(stock or heads or (s!=1 and field) for (s,m),(field,stock,heads) in initial.items()):
        raise ValueError('Initial20 full field/stock/sprouts baseline refused')
    delta=[births[s]-baseline[s] for s in range(3)]
    for stage in ('acquired','saved'):
        delta_at=[at_stage[stage][s]-baseline[s] for s in range(3)]
        for s in range(6):
            expected=(20 if s==1 else 0)+(delta_at[s] if s<3 else 0)+(1 if s==3 else -1 if s==1 else 0)
            rows=[census[stage][s,m] for m in range(3)]
            if sum(field+stock+heads for field,stock,heads in rows)!=expected:
                raise ValueError('Unaccounted population/color at actual census boundary')
            if stage=='saved' and any(field or heads for field,stock,heads in rows):
                raise ValueError('Saved duplicate field/sprout')
    return {'initial':20,'successful_earned_births':delta,'replacement_count':1,'saved_total':20+sum(delta),'physical_pellet_binding':False, 'acquired_compartments': {name:sum(row[index] for row in census['acquired'].values()) for index,name in enumerate(('field','stock','heads'))}, 'acquired_red':sum(census['acquired'][1,m][0] for m in range(3)), 'acquired_purple':sum(census['acquired'][3,m][0] for m in range(3))}


STOCK = re.compile(r'P2_PURPLE_RESUME_STOCK kind=(rgb|p2) color=([0-4]) maturity=([0-2]) count=(0|[1-9][0-9]*) read_only=1')

def compare_stock_observation(log, stock):
    expected_rgb, expected_p2 = stock["rgb"], stock["p2"]
    observed = "P2_PURPLE_RESUME_STOCK_OBSERVED day=%d generations=1 checkpoint_resumed=1 field=0 heads=0 starting_population_validated=0 external_card_comparison_required=1 saved_bytes_injected=0" % stock["day"]
    if len(expected_rgb) != 9 or len(expected_p2) != 6:
        raise ValueError('Complete independent card stock required')
    if any(type(x) is not int or not 0 <= x <= 100000 for x in expected_rgb + expected_p2):
        raise ValueError('Invalid independent card stock')
    wanted = {('rgb', c, m): expected_rgb[c * 3 + m] for c in range(3) for m in range(3)}
    wanted.update({('p2', c + 3, m): expected_p2[c * 3 + m] for c in range(2) for m in range(3)})
    seen = {}
    complete = False
    for line in log.splitlines():
        if line.startswith('P2_PURPLE_RESUME_STOCK_OBSERVED'):
            if line != observed or complete or seen != wanted:
                raise ValueError('Incomplete/duplicate/wrong stock observation boundary')
            complete = True
        elif line.startswith('P2_PURPLE_RESUME_STOCK'):
            match = STOCK.fullmatch(line)
            if not match or complete:
                raise ValueError('Malformed or late stock observation')
            kind, color, maturity, count = match.groups()
            key = (kind, int(color), int(maturity))
            if key not in wanted or key in seen or int(count) != wanted[key]:
                raise ValueError('Duplicate/foreign/mismatching stock compartment')
            seen[key] = int(count)
        elif 'P2_PURPLE_ORDINARY_RESUME_PASS' in line:
            raise ValueError('Original strict starting-population result is a separate contract')
    if not complete:
        raise ValueError('Missing stock observation boundary')
    return {'qualification': 'new genuine card fresh resume stock consistency only', 'rgb': expected_rgb,
            'p2': expected_p2, 'field': 0, 'heads': 0, 'starting_population_validated': False}


def validate_acquisition_report(log, marker):
    """Bind actual field reporting to complete earned receipts and all compartments."""
    proof=validate_birth_receipts(log)
    rows=[line for line in log.splitlines() if line.startswith('P2_PURPLE_ACQUISITION_CENSUS')]
    if len(rows)!=1:raise ValueError('Missing/duplicate actual acquisition census report')
    m=re.fullmatch(r'P2_PURPLE_ACQUISITION_CENSUS field=(0|[1-9][0-9]*) red=(0|[1-9][0-9]*) purple=(0|[1-9][0-9]*) stock=(0|[1-9][0-9]*) heads=(0|[1-9][0-9]*) whole=(0|[1-9][0-9]*) baseline=20 successful_births_only=1 read_only=1',rows[0])
    if not m:raise ValueError('Malformed actual acquisition census report')
    actual=dict(zip(('field','red','purple','stock','heads','whole'),map(int,m.groups())))
    expected=dict(proof['acquired_compartments'],red=proof['acquired_red'],purple=proof['acquired_purple'])
    expected['whole']=sum(proof['acquired_compartments'].values())
    if actual!=expected or any(marker.get(k)!=str(actual[k]) for k in ('field','red','purple')):
        raise ValueError('Acquisition marker differs from actual earned census compartments')
    return actual
