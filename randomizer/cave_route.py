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
from randomizer.cave_checkpoint import validate_party, wire_schema, NUMBER, INTEGER


def surface_transfer(text, token):
    rows=text.split()
    if (len(rows)<7 or rows[0] not in ('P2_CAVE_ROUTE_TRANSFER_1','P2_CAVE_ROUTE_TRANSFER_2')
            or rows[1]!=token or any(not NUMBER.fullmatch(v) for v in rows[2:6])
            or not INTEGER.fullmatch(rows[6])):
        raise ValueError('foreign surface boundary')
    position=list(map(float,rows[2:5]));health=float(rows[5]);count=int(rows[6])
    if (not all(math.isfinite(v) and abs(v)<=100000 for v in position)
        or not math.isfinite(health) or not 0<health<=1 or not 1<=count<=100
        or len(rows)!=7+count*2):raise ValueError('invalid surface boundary')
    if any(not INTEGER.fullmatch(v) for v in rows[7:]):raise ValueError('invalid surface survivor integer')
    squad=[list(map(int,rows[i:i+2])) for i in range(7,len(rows),2)]
    version=int(rows[0][-1]);validate_party(squad,health,2 if version==2 else 1)
    if version==1 and any(species>2 for species,maturity in squad):
        raise ValueError('invalid surface survivor')
    return dict(position=position,health=health,squad=squad,**({'wire_schema':2} if version==2 else {}))


class Route:
    def __init__(self,directory,journey,placements,content_identity):
        self.directory=Path(directory).resolve();self.journey=journey
        self.identity=hashlib.sha256(encoded(dict(journey=identity(journey),content=content_identity)).encode()).hexdigest()
        self.container_schema=2 if journey['schema']=='p2-cave-journey/2' else 1
        self.phases=('surface','acquisition','floor1','floor2') if self.container_schema==2 else ('surface','floor1','floor2')
        self.phase_indices={phase:i for i,phase in enumerate(self.phases[1:],0 if self.container_schema==2 else 1)}
        self.manifests={n:spec['descriptor'] for n,spec in zip(self.phase_indices.values(),journey['floors'])}
        self.placements=placements
        from experimental.pikmin2_cave_lane41_generator import _seed_uint64
        if set(placements)!=set(self.manifests):raise ValueError('route placement phases differ')
        for n,manifest in self.manifests.items():
            table=manifest['table'];placement=placements[n]
            expected={(f"item:{t['slot_id']}:0",t['slot_id'],t['treasure_id']) for t in table['treasures']}
            actual={(v['slot_id'],v['host'],v['item']) for v in placement['items']}
            if (placement['floor']!=table['floor'] or placement['cave']!=table['cave_id']
                or placement['seed']!=_seed_uint64(table['seed']) or actual!=expected
                or len(placement['items'])!=len(expected)):raise ValueError('floor placement identity differs from route')
        self.state_path=self.directory/'route-state.json';self.pending_path=self.directory/'route-pending.json'

    def entry_for(self,index,squad,health,wire_schema=None):
        if index not in self.manifests:raise ValueError('unknown route phase index')
        if self.container_schema==2 and index==0:wire_schema=2
        return initial_entry(self.manifests[index],squad,health,wire_schema)

    def ledger_path(self,floor):return self.directory/f'route-floor-{floor}-receipts.txt'

    def ledger(self,floor):
        from scripts.play_pikmin2_cave import receipts
        text=self.ledger_path(floor).read_text();receipts(text,self.placements[floor]);return text

    @staticmethod
    def surface_from_floor(saved,position):
        surface=dict(position=copy.deepcopy(position),squad=copy.deepcopy(saved['squad']),health=saved['health'])
        # Native cave1 includes Purple; custom surface1 does not. Promote the
        # surface explicitly without reinterpreting the actual cave boundary.
        if saved.get('wire_schema')==2 or any(species>2 for species,maturity in saved['squad']):surface['wire_schema']=2
        Route.validate_surface(surface);return surface

    def initialize(self,surface):
        self.directory.mkdir(parents=True,exist_ok=True)
        if self.state_path.exists():return self.load()
        if self.pending_path.exists() or any(self.directory.glob('route-floor-*-receipts.txt')):
            raise ValueError('missing route state; refusing party/receipt reset')
        self.validate_surface(surface)
        for n in self.manifests:atomic_write(self.ledger_path(n),'P2_RECEIPTS_1\n')
        state=dict(schema=self.container_schema,identity=self.identity,phase='surface',revision=0,visit=0,
                   surface=copy.deepcopy(surface),entry=None,last_boundary=None)
        if self.container_schema==2:state['wfg_white_boundary']=None
        atomic_write(self.state_path,encoded(state)+'\n');return self.load()

    @staticmethod
    def validate_surface(surface):
        if (type(surface) is not dict or set(surface) not in ({'position','health','squad'},{'position','health','squad','wire_schema'})
                or ('wire_schema' in surface and (type(surface['wire_schema']) is not int or surface['wire_schema']!=2))):raise ValueError('invalid surface state')
        validate_party(surface['squad'],surface['health'],2 if surface.get('wire_schema')==2 else 1)
        # Apply the same reader to persisted values, including finite numbers.
        version=2 if surface.get('wire_schema')==2 else 1
        text=f'P2_CAVE_ROUTE_TRANSFER_{version} t '+' '.join(map(str,surface['position']))+' '+str(surface['health'])+' '+str(len(surface['squad']))+' '+ ' '.join(str(x) for p in surface['squad'] for x in p)
        if surface_transfer(text,'t')!=surface:raise ValueError('invalid surface state')

    def load(self):
        state=read_json(self.state_path)
        if (set(state)!=({'schema','identity','phase','revision','visit','surface','entry','last_boundary'} | ({'wfg_white_boundary'} if self.container_schema==2 else set()))
            or type(state['schema']) is not int or state['schema']!=self.container_schema or state['identity']!=self.identity
            or state['phase'] not in self.phases
            or type(state['visit']) is not int or state['visit']<0
            or type(state['revision']) is not int or state['revision']<0):raise ValueError('foreign route state')
        expected=state['visit']*len(self.phases)+(0 if state['phase']=='surface' else self.phases.index(state['phase'])-len(self.phases))
        if state['revision']!=expected:raise ValueError('route revision differs from phase')
        self.validate_surface(state['surface'])
        for n in self.manifests:self.ledger(n)
        if self.container_schema==2:
            if state['revision']<2 and state['wfg_white_boundary'] is not None:
                raise ValueError('WFG evidence predates acquisition boundary')
            self.validate_white_boundary(state['wfg_white_boundary'])
        if state['phase']=='surface':
            if state['entry'] is not None:raise ValueError('surface has cave entry')
        else:
            n=self.phase_indices[state['phase']];entry=state['entry']
            if type(entry) is not dict or entry.get('fingerprint')!=fingerprint(self.manifests[n]):raise ValueError('foreign cave entry')
            wire_schema(entry)
        if state['revision']==0:
            if state['last_boundary'] is not None:raise ValueError('initial route has a boundary')
        else:
            b=state['last_boundary'];run=Path(b['run']).resolve()
            if not self.valid_run(run):raise ValueError('foreign saved boundary')
            name='p2-cave-surface-transfer.txt' if state['phase']==self.phases[1] else 'p2-cave-transfer.txt'
            source=run/name
            if hashlib.sha256(source.read_bytes()).hexdigest()!=b['sha256']:raise ValueError('saved boundary changed')
            if state['phase']==self.phases[1]:
                original=surface_transfer(source.read_text(),source.read_text().split()[1])
                if state['surface']!=original or state['entry']!=self.entry_for(self.phase_indices[self.phases[1]],original['squad'],original['health'],original.get('wire_schema')):raise ValueError('entry differs from saved surface boundary')
            else:
                from scripts.play_pikmin2_cave import checkpoint
                previous=self.phases[self.phases.index(state['phase'])-1] if state['phase']!='surface' else self.phases[-1]
                n=self.phase_indices[previous]
                original=checkpoint(source.read_text(),(run/'p2-cave-bud-transfer.txt').read_text(),self.ledger(n),self.manifests[n],self.placements[n])
                if state['phase']!='surface':
                    if state['entry']!=self.entry_for(self.phase_indices[state['phase']],original['squad'],original['health'],original.get('wire_schema')):raise ValueError('entry differs from saved floor boundary')
                elif state['surface']!=self.surface_from_floor(original,state['surface']['position']):raise ValueError('surface differs from terminal boundary')
        return state

    def white_acquired(self,saved):
        # checkpoint() already validates the complete budget wire against the
        # acquisition descriptor. Living White alone could be incoming carry.
        words=saved['buds'].split()
        used={words[i]:int(words[i+1]) for i in range(5,len(words),2)}
        slots=[bud['slot_id'] for bud in self.manifests[0]['table']['buds'] if bud['species']=='white']
        return any(species==4 for species,maturity in saved['squad']) and any(used[slot]>0 for slot in slots)

    def validate_white_boundary(self,boundary):
        if boundary is None:return
        if type(boundary) is not dict or set(boundary)!={'run','sha256','buds_sha256'}:
            raise ValueError('invalid WFG White boundary evidence')
        run=Path(boundary['run']).resolve()
        if not self.valid_run(run):raise ValueError('foreign WFG White boundary')
        source=run/'p2-cave-transfer.txt';buds=run/'p2-cave-bud-transfer.txt'
        if (hashlib.sha256(source.read_bytes()).hexdigest()!=boundary['sha256']
            or hashlib.sha256(buds.read_bytes()).hexdigest()!=boundary['buds_sha256']):
            raise ValueError('WFG White boundary changed')
        from scripts.play_pikmin2_cave import checkpoint
        saved=checkpoint(source.read_text(),buds.read_text(),self.ledger(0),self.manifests[0],self.placements[0])
        if not self.white_acquired(saved):raise ValueError('WFG boundary lacks White acquisition evidence')

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
        atomic_write(self.pending_path,encoded(dict(schema=self.container_schema,identity=self.identity,phase=state['phase'],revision=state['revision'],token=token,run=str(run),inputs=hashes))+'\n')

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
        if (pending.get('identity')!=self.identity or pending.get('schema')!=self.container_schema
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
            next_state.update(phase=self.phases[1],visit=state['visit']+1,surface=surface,
                              entry=self.entry_for(self.phase_indices[self.phases[1]],surface['squad'],surface['health'],surface.get('wire_schema')))
        else:
            from scripts.play_pikmin2_cave import checkpoint
            n=self.phase_indices[state['phase']];saved=checkpoint(source.read_text(),(run/'p2-cave-bud-transfer.txt').read_text(),self.ledger(n),self.manifests[n],self.placements[n])
            if state['phase']=='acquisition' and self.white_acquired(saved):
                next_state['wfg_white_boundary']=dict(run=str(run),sha256=boundary,
                    buds_sha256=hashlib.sha256((run/'p2-cave-bud-transfer.txt').read_bytes()).hexdigest())
            if state['phase']!=self.phases[-1]:
                phase=self.phases[self.phases.index(state['phase'])+1]
                next_state.update(phase=phase,entry=self.entry_for(self.phase_indices[phase],saved['squad'],saved['health'],saved.get('wire_schema')))
            else:
                surface=self.surface_from_floor(saved,state['surface']['position'])
                next_state.update(phase='surface',surface=surface,entry=None)
        next_state.update(revision=state['revision']+1,last_boundary=dict(run=str(run),sha256=boundary))
        atomic_write(self.state_path,encoded(next_state)+'\n');self.pending_path.unlink()
        return self.load(),True
