"""Durable single-player surface -> generated floors -> surface route.

The launcher holds its OS session lock. Each boundary consumes the actual private
native transfer; a run directory or successful process exit is never a boundary.
"""
import copy
import hashlib
from pathlib import Path
import math

from randomizer.cave_floor import atomic_write, fingerprint
from randomizer.cave_journey import identity, initial_entry, encoded, read_json


def surface_transfer(text, token):
    rows=text.split()
    if len(rows)<7 or rows[:2]!=['P2_CAVE_ROUTE_TRANSFER_1',token]:
        raise ValueError('foreign surface boundary')
    position=list(map(float,rows[2:5]));health=float(rows[5]);count=int(rows[6])
    if (not all(math.isfinite(v) and abs(v)<=100000 for v in position)
        or not math.isfinite(health) or not 0<health<=1 or not 1<=count<=100
        or len(rows)!=7+count*2):raise ValueError('invalid surface boundary')
    squad=[list(map(int,rows[i:i+2])) for i in range(7,len(rows),2)]
    if any(not 0<=species<=2 or not 0<=maturity<=2 for species,maturity in squad):
        raise ValueError('invalid surface survivor')
    return dict(position=position,health=health,squad=squad)


class Route:
    def __init__(self,directory,journey,placements,content_identity):
        self.directory=Path(directory).resolve();self.journey=journey
        self.identity=hashlib.sha256(encoded(dict(journey=identity(journey),content=content_identity)).encode()).hexdigest()
        self.manifests={n:journey['floors'][n-1]['descriptor'] for n in (1,2)}
        self.placements=placements
        # Reuse the delivered journey's strict seed/floor/item identity checks.
        from randomizer.cave_journey import Session
        Session(self.directory,journey,placements)
        self.state_path=self.directory/'route-state.json';self.pending_path=self.directory/'route-pending.json'

    def ledger_path(self,floor):return self.directory/f'route-floor-{floor}-receipts.txt'

    def ledger(self,floor):
        from scripts.play_pikmin2_cave import receipts
        text=self.ledger_path(floor).read_text();receipts(text,self.placements[floor]);return text

    def initialize(self,surface):
        self.directory.mkdir(parents=True,exist_ok=True)
        if self.state_path.exists():return self.load()
        if self.pending_path.exists() or any(self.directory.glob('route-floor-*-receipts.txt')):
            raise ValueError('missing route state; refusing party/receipt reset')
        self.validate_surface(surface)
        for n in (1,2):atomic_write(self.ledger_path(n),'P2_RECEIPTS_1\n')
        state=dict(schema=1,identity=self.identity,phase='surface',revision=0,visit=0,
                   surface=copy.deepcopy(surface),entry=None,last_boundary=None)
        atomic_write(self.state_path,encoded(state)+'\n');return self.load()

    @staticmethod
    def validate_surface(surface):
        if type(surface) is not dict or set(surface)!={'position','health','squad'}:raise ValueError('invalid surface state')
        # Apply the same reader to persisted values, including finite numbers.
        text='P2_CAVE_ROUTE_TRANSFER_1 t '+' '.join(map(str,surface['position']))+' '+str(surface['health'])+' '+str(len(surface['squad']))+' '+ ' '.join(str(x) for p in surface['squad'] for x in p)
        if surface_transfer(text,'t')!=surface:raise ValueError('invalid surface state')

    def load(self):
        state=read_json(self.state_path)
        if (set(state)!={'schema','identity','phase','revision','visit','surface','entry','last_boundary'}
            or state['schema']!=1 or state['identity']!=self.identity
            or state['phase'] not in ('surface','floor1','floor2')
            or type(state['visit']) is not int or state['visit']<0
            or type(state['revision']) is not int or state['revision']<0):raise ValueError('foreign route state')
        expected=state['visit']*3+{'surface':0,'floor1':-2,'floor2':-1}[state['phase']]
        if state['revision']!=expected:raise ValueError('route revision differs from phase')
        self.validate_surface(state['surface']);self.ledger(1);self.ledger(2)
        if state['phase']=='surface':
            if state['entry'] is not None:raise ValueError('surface has cave entry')
        else:
            n=int(state['phase'][-1]);entry=state['entry']
            if type(entry) is not dict or entry.get('fingerprint')!=fingerprint(self.manifests[n]):raise ValueError('foreign cave entry')
            self.validate_surface(dict(position=state['surface']['position'],health=entry['health'],squad=entry['squad']))
        if state['revision']==0:
            if state['last_boundary'] is not None:raise ValueError('initial route has a boundary')
        else:
            b=state['last_boundary'];run=Path(b['run']).resolve()
            if not self.valid_run(run):raise ValueError('foreign saved boundary')
            name='p2-cave-surface-transfer.txt' if state['phase']=='floor1' else 'p2-cave-transfer.txt'
            source=run/name
            if hashlib.sha256(source.read_bytes()).hexdigest()!=b['sha256']:raise ValueError('saved boundary changed')
            if state['phase']=='floor1':
                original=surface_transfer(source.read_text(),source.read_text().split()[1])
                if state['surface']!=original or state['entry']!=initial_entry(self.manifests[1],original['squad'],original['health']):raise ValueError('entry differs from saved surface boundary')
            else:
                from scripts.play_pikmin2_cave import checkpoint
                n=1 if state['phase']=='floor2' else 2
                original=checkpoint(source.read_text(),(run/'p2-cave-bud-transfer.txt').read_text(),self.ledger(n),self.manifests[n],self.placements[n])
                if state['phase']=='floor2':
                    if state['entry']!=initial_entry(self.manifests[2],original['squad'],original['health']):raise ValueError('entry differs from saved floor boundary')
                elif state['surface']['squad']!=original['squad'] or state['surface']['health']!=original['health']:raise ValueError('surface differs from terminal boundary')
        return state

    def begin(self,run,state,token,inputs):
        if self.pending_path.exists():raise ValueError('unresolved route launch')
        if self.load()!=state:raise ValueError('stale route launch')
        run=Path(run).resolve()
        if not self.valid_run(run) or not run.is_dir():raise ValueError('foreign route run')
        if len(token)!=32 or any(c not in '0123456789abcdef' for c in token):raise ValueError('invalid launch token')
        hashes={}
        for name in inputs:
            path=(run/name).resolve()
            if not path.is_relative_to(run) or not path.is_file():raise ValueError('foreign pending input')
            hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        atomic_write(self.pending_path,encoded(dict(schema=1,identity=self.identity,phase=state['phase'],revision=state['revision'],token=token,run=str(run),inputs=hashes))+'\n')

    def valid_run(self,run):
        runs=(self.directory/'runs').resolve()
        return run.parent==runs or (run.name=='run' and run.parent.parent==runs)

    def stop_unsaved(self):
        pending=read_json(self.pending_path);run=Path(pending['run']).resolve()
        if not self.valid_run(run):raise ValueError('foreign pending route')
        result=read_json(run/'run-result.json')
        if result.get('exit_code')!=0 or result.get('timed_out') or result.get('captain_down'):
            raise ValueError('interrupted route; preserved without automatic party reset')
        if any((run/name).exists() for name in ('p2-cave-surface-transfer.txt','p2-cave-transfer.txt')):
            raise ValueError('unsaved stop has an unconsumed boundary')
        self.pending_path.unlink()

    def recover(self,live_paths=()):
        state=self.load()
        if not self.pending_path.exists():return state,False
        pending=read_json(self.pending_path);run=Path(pending['run']).resolve()
        if (pending.get('identity')!=self.identity or pending.get('schema')!=1
            or not self.valid_run(run)):raise ValueError('foreign pending route')
        if any(Path(p).resolve() in (run,run/'nectar.exe') for p in live_paths):raise ValueError('route child still live')
        for name,digest in pending['inputs'].items():
            if not (run/name).resolve().is_relative_to(run) or not (run/name).is_file():raise ValueError('foreign pending input')
            if hashlib.sha256((run/name).read_bytes()).hexdigest()!=digest:raise ValueError('route run input changed')
        source=run/('p2-cave-surface-transfer.txt' if pending['phase']=='surface' else 'p2-cave-transfer.txt')
        if not source.exists():return state,False
        boundary=hashlib.sha256(source.read_bytes()).hexdigest()
        if state['revision']==pending['revision']+1:
            if state['last_boundary']!=dict(run=str(run),sha256=boundary):raise ValueError('conflicting recovered boundary')
            self.pending_path.unlink();return state,False
        if state['revision']!=pending['revision'] or state['phase']!=pending['phase']:raise ValueError('stale route boundary')
        next_state=copy.deepcopy(state)
        if state['phase']=='surface':
            surface=surface_transfer(source.read_text(),pending['token'])
            next_state.update(phase='floor1',visit=state['visit']+1,surface=surface,
                              entry=initial_entry(self.manifests[1],surface['squad'],surface['health']))
        else:
            from scripts.play_pikmin2_cave import checkpoint
            n=int(state['phase'][-1]);saved=checkpoint(source.read_text(),(run/'p2-cave-bud-transfer.txt').read_text(),self.ledger(n),self.manifests[n],self.placements[n])
            if n==1:next_state.update(phase='floor2',entry=initial_entry(self.manifests[2],saved['squad'],saved['health']))
            else:
                surface=dict(position=state['surface']['position'],squad=saved['squad'],health=saved['health'])
                self.validate_surface(surface);next_state.update(phase='surface',surface=surface,entry=None)
        next_state.update(revision=state['revision']+1,last_boundary=dict(run=str(run),sha256=boundary))
        atomic_write(self.state_path,encoded(next_state)+'\n');self.pending_path.unlink()
        return self.load(),True
