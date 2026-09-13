"""Strict parser for the Beasts fixture's diagnostic survivor snapshot."""
from collections import Counter
import math
import re


def party_snapshot(log, population):
    lines=log.splitlines()
    starts=[i for i,line in enumerate(lines) if line.startswith('P2_BEASTS_PARTY') and line!='P2_BEASTS_PARTY_END']
    ends=[i for i,line in enumerate(lines) if line=='P2_BEASTS_PARTY_END']
    if len(starts)!=1 or len(ends)!=1:raise ValueError('Missing or duplicate party snapshot')
    start,end=starts[0],ends[0]
    match=re.fullmatch(r'P2_BEASTS_PARTY health=([0-9.eE+-]+) count=([0-9]+)',lines[start])
    if match is None:raise ValueError('Malformed party header')
    health=float(match[1]);count=int(match[2])
    if not math.isfinite(health) or not 0<health<=1 or count!=20 or end-start!=count+1:
        raise ValueError('Invalid party health/count')
    squad=[]
    for index,line in enumerate(lines[start+1:end]):
        record=re.fullmatch(r'P2_BEASTS_SURVIVOR index=([0-9]+) species=(red|blue|yellow|purple) maturity=([012])',line)
        if record is None or record[1]!=str(index):raise ValueError('Malformed or unordered survivor')
        squad.append(dict(species=record[2],maturity=int(record[3])))
    if any(line.startswith('P2_BEASTS_SURVIVOR') for line in lines[:start]+lines[end+1:]):
        raise ValueError('Survivor outside snapshot')
    totals=Counter(p['species'] for p in squad)
    if totals!=Counter(red=population['red'],purple=population['purple']) or population['sprouts']!=0:
        raise ValueError('Party snapshot disagrees with observed population')
    ready=[i for i,line in enumerate(lines) if line.startswith('P2_BEASTS_READY ')]
    passed=[i for i,line in enumerate(lines) if line.startswith('PASS P2_BEASTS_')]
    if len(ready)!=1 or len(passed)!=1 or not ready[0]<start<end<passed[0]:
        raise ValueError('Party snapshot outside completion phase')
    pluck=[i for i,line in enumerate(lines) if line.startswith('P2_BEASTS_CAPTAIN_PLUCK ')]
    if population['purple'] and (len(pluck)!=1 or pluck[0]>=start):
        raise ValueError('Party snapshot precedes plucking')
    return dict(squad=squad,health=health)
