"""Durable single-player surface -> generated floors -> surface route.

The launcher holds its OS session lock. Each boundary consumes the actual private
native transfer; a run directory or successful process exit is never a boundary.
"""
import copy
import hashlib
from pathlib import Path, PurePosixPath
import math
import re

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
        text=self.member(self.directory,self.ledger_path(floor).name).read_text();receipts(text,self.placements[floor]);return text

    @staticmethod
    def surface_from_floor(saved,position):
        surface=dict(position=copy.deepcopy(position),squad=copy.deepcopy(saved['squad']),health=saved['health'])
        # Native cave1 includes Purple; custom surface1 does not. Promote the
        # surface explicitly without reinterpreting the actual cave boundary.
        if saved.get('wire_schema')==2 or any(species>2 for species,maturity in saved['squad']):surface['wire_schema']=2
        Route.validate_surface(surface);return surface

    def initialize(self,surface):
        self.directory.mkdir(parents=True,exist_ok=True)
        if self.state_path.exists() or self.state_path.is_symlink():return self.load()
        if self.pending_path.exists() or self.pending_path.is_symlink() or (self.directory/'runs').exists() or any(self.directory.glob('route-floor-*-receipts.txt')):
            raise ValueError('missing route state; refusing party/receipt reset')
        self.validate_surface(surface)
        for n in self.manifests:atomic_write(self.ledger_path(n),'P2_RECEIPTS_1\n')
        state=dict(schema=self.container_schema,identity=self.identity,phase='surface',revision=0,visit=0,
                   surface=copy.deepcopy(surface),entry=None,last_boundary=None,boundary_proofs=[])
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
        state=read_json(self.member(self.directory,'route-state.json'))
        if type(state) is dict and 'boundary_proofs' not in state:
            raise ValueError('historical route lacks durable input proofs; preserve it immutably, do not promote it to new acceptance')
        if (type(state) is not dict or set(state)!=({'schema','identity','phase','revision','visit','surface','entry','last_boundary','boundary_proofs'} | ({'wfg_white_boundary'} if self.container_schema==2 else set()))
            or type(state['schema']) is not int or state['schema']!=self.container_schema or state['identity']!=self.identity
            or state['phase'] not in self.phases
            or type(state['visit']) is not int or state['visit']<0
            or type(state['revision']) is not int or state['revision']<0):raise ValueError('foreign route state')
        expected=state['visit']*len(self.phases)+(0 if state['phase']=='surface' else self.phases.index(state['phase'])-len(self.phases))
        if state['revision']!=expected:raise ValueError('route revision differs from phase')
        # First validate every retained original input and actual output byte.
        # A later semantic reader must not run before the complete proof pass.
        proofs=self.validate_proofs(state['boundary_proofs'],state['revision'])
        self.validate_surface(state['surface'])
        for n in self.manifests:self.ledger(n)
        if self.container_schema==2:
            if state['revision']<2 and state['wfg_white_boundary'] is not None:
                raise ValueError('WFG evidence predates acquisition boundary')
            self.validate_white_boundary(state['wfg_white_boundary'],state['boundary_proofs'],proofs)
        if state['phase']=='surface':
            if state['entry'] is not None:raise ValueError('surface has cave entry')
        else:
            n=self.phase_indices[state['phase']];entry=state['entry']
            if type(entry) is not dict or entry.get('fingerprint')!=fingerprint(self.manifests[n]):raise ValueError('foreign cave entry')
            wire_schema(entry)
        if state['revision']==0:
            if state['last_boundary'] is not None:raise ValueError('initial route has a boundary')
        else:
            b=state['last_boundary'];proof=state['boundary_proofs'][-1]
            if b!=dict(run=proof['run'],sha256=proof['transfer']['sha256']):raise ValueError('saved boundary differs from durable proof')
            run=self.checked_run(b['run'])
            name='p2-cave-surface-transfer.txt' if state['phase']==self.phases[1] else 'p2-cave-transfer.txt'
            source=self.member(run,name)
            if hashlib.sha256(source.read_bytes()).hexdigest()!=b['sha256']:raise ValueError('saved boundary changed')
            if state['phase']==self.phases[1]:
                original=proofs[-1]
                if state['surface']!=original or state['entry']!=self.entry_for(self.phase_indices[self.phases[1]],original['squad'],original['health'],original.get('wire_schema')):raise ValueError('entry differs from saved surface boundary')
            else:
                original=proofs[-1]
                if state['phase']!='surface':
                    if state['entry']!=self.entry_for(self.phase_indices[state['phase']],original['squad'],original['health'],original.get('wire_schema')):raise ValueError('entry differs from saved floor boundary')
                elif state['surface']!=self.surface_from_floor(original,state['surface']['position']):raise ValueError('surface differs from terminal boundary')
        return state

    def member(self,root,name):
        if (type(name) is not str or not name or '\\' in name or ':' in name
            or PurePosixPath(name).is_absolute() or any(p in ('','.','..') for p in name.split('/'))):
            raise ValueError('foreign proof member path')
        path=Path(root)
        for part in name.split('/'):
            path=path/part
            if path.is_symlink() or getattr(path,'is_junction',lambda:False)():
                raise ValueError('foreign proof member link')
        if not path.is_file() or not path.resolve().is_relative_to(root):raise ValueError('missing or foreign proof member')
        return path

    def checked_run(self,value):
        if type(value) not in (str,Path) and not isinstance(value,Path):raise ValueError('foreign route run')
        run=Path(value)
        if not run.is_absolute() or '..' in run.parts:raise ValueError('foreign route run')
        try:parts=run.relative_to(self.directory).parts
        except ValueError:raise ValueError('foreign route run') from None
        if not (len(parts)==2 and parts[0]=='runs' or len(parts)==3 and parts[0]=='runs' and parts[2]=='run'):
            raise ValueError('foreign route run')
        current=self.directory
        for part in parts:
            current=current/part
            if current.is_symlink() or getattr(current,'is_junction',lambda:False)():raise ValueError('foreign route run link')
        if run.resolve()!=run or not run.is_dir():raise ValueError('foreign route run')
        return run

    def validate_inputs(self,run,inputs):
        if type(inputs) is not dict or not inputs:raise ValueError('missing original input proof')
        for name,digest in inputs.items():
            if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('invalid original input digest')
            if hashlib.sha256(self.member(run,name).read_bytes()).hexdigest()!=digest:raise ValueError('route run input changed')

    def validate_proofs(self,proofs,revision):
        if type(proofs) is not list or len(proofs)!=revision:raise ValueError('missing durable boundary proofs')
        seen=set();contents=[]
        for index,proof in enumerate(proofs,1):
            if (type(proof) is not dict or set(proof)!={'schema','revision','phase','run','token','inputs','transfer','buds','receipts'}
                or type(proof['schema']) is not int or proof['schema']!=1
                or type(proof['revision']) is not int or proof['revision']!=index
                or proof['phase']!=self.phases[(index-1)%len(self.phases)]
                or type(proof['token']) is not str or not re.fullmatch('[0-9a-f]{32}',proof['token'])):
                raise ValueError('foreign durable boundary proof')
            run=self.checked_run(proof['run'])
            if str(run) in seen:raise ValueError('reused durable run')
            seen.add(str(run));self.validate_inputs(run,proof['inputs'])
            payload={}
            for field,name in [('transfer','p2-cave-surface-transfer.txt' if proof['phase']=='surface' else 'p2-cave-transfer.txt'),('buds','p2-cave-bud-transfer.txt')]:
                item=proof[field]
                if field=='buds' and proof['phase']=='surface':
                    if item is not None:raise ValueError('surface proof has bud output')
                    continue
                if (type(item) is not dict or set(item)!={'name','sha256'} or item['name']!=name
                    or type(item['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}',item['sha256'])):
                    raise ValueError('invalid durable output proof')
                payload[field]=self.member(run,name).read_bytes()
                if hashlib.sha256(payload[field]).hexdigest()!=item['sha256']:
                    raise ValueError('durable boundary changed')
            if (proof['phase']=='surface' and proof['receipts'] is not None
                or proof['phase']!='surface' and type(proof['receipts']) is not str):raise ValueError('invalid boundary receipt snapshot')
            contents.append(payload)
        # checkpoint() is a pure parser in the pinned source. Keep its invocation
        # behind the all-proof pass even if a future parser acquires side effects.
        from scripts.play_pikmin2_cave import checkpoint,receipts
        saved=[]
        for proof,payload in zip(proofs,contents):
            if proof['phase']=='surface':
                saved.append(surface_transfer(payload['transfer'].decode('utf-8'),proof['token']))
            else:
                n=self.phase_indices[proof['phase']]
                if proof['token']!=fingerprint(self.manifests[n])[:32]:raise ValueError('foreign floor proof token')
                receipt_text=proof['receipts']
                if not set(receipts(receipt_text,self.placements[n])).issubset(receipts(self.ledger(n),self.placements[n])):
                    raise ValueError('durable receipt snapshot missing from advancing ledger')
                saved.append(checkpoint(payload['transfer'].decode('utf-8'),payload['buds'].decode('utf-8'),receipt_text,self.manifests[n],self.placements[n]))
        return saved

    def white_acquired(self,saved):
        # checkpoint() already validates the complete budget wire against the
        # acquisition descriptor. Living White alone could be incoming carry.
        words=saved['buds'].split()
        used={words[i]:int(words[i+1]) for i in range(5,len(words),2)}
        slots=[bud['slot_id'] for bud in self.manifests[0]['table']['buds'] if bud['species']=='white']
        return any(species==4 for species,maturity in saved['squad']) and any(used[slot]>0 for slot in slots)

    def validate_white_boundary(self,boundary,records,proofs):
        if boundary is None:return
        if type(boundary) is not dict or set(boundary)!={'run','sha256','buds_sha256'}:
            raise ValueError('invalid WFG White boundary evidence')
        candidates=[saved for proof,saved in zip(records,proofs)
            if proof['phase']=='acquisition' and proof['run']==boundary['run']
            and proof['transfer']['sha256']==boundary['sha256'] and proof['buds']['sha256']==boundary['buds_sha256']]
        if len(candidates)!=1:raise ValueError('WFG White boundary changed or lacks durable original input proof')
        saved=candidates[0]
        if not self.white_acquired(saved):raise ValueError('WFG boundary lacks White acquisition evidence')

    def pending_present(self):
        return (self.pending_path.exists() or self.pending_path.is_symlink()
                or getattr(self.pending_path,'is_junction',lambda:False)())

    def begin(self,run,state,token,inputs):
        if self.pending_present():
            self.member(self.directory,'route-pending.json')
            raise ValueError('unresolved route launch')
        if self.load()!=state:raise ValueError('stale route launch')
        run=self.checked_run(run)
        if any(proof['run']==str(run) for proof in state['boundary_proofs']):raise ValueError('route run was already consumed')
        if len(token)!=32 or any(c not in '0123456789abcdef' for c in token):raise ValueError('invalid launch token')
        if type(inputs) not in (list,tuple) or not inputs or any(type(name) is not str for name in inputs):
            raise ValueError('invalid launch input inventory')
        hashes={}
        # The controller concatenates floor, blueprint and copied-input lists.
        # Pin each exact member once while preserving all path validation.
        for name in dict.fromkeys(inputs):
            path=self.member(run,name)
            hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        atomic_write(self.pending_path,encoded(dict(schema=self.container_schema,identity=self.identity,phase=state['phase'],revision=state['revision'],token=token,run=str(run),inputs=hashes))+'\n')

    def valid_run(self,run):
        try:self.checked_run(run);return True
        except (ValueError,OSError):return False

    def stop_unsaved(self):
        pending=read_json(self.member(self.directory,'route-pending.json'))
        run=self.checked_run(pending['run'])
        result=read_json(run/'run-result.json')
        if result.get('exit_code')!=0 or result.get('timed_out') or result.get('captain_down'):
            raise ValueError('interrupted route; preserved without automatic party reset')
        if any((run/name).exists() or (run/name).is_symlink() for name in ('p2-cave-surface-transfer.txt','p2-cave-transfer.txt')):
            raise ValueError('unsaved stop has an unconsumed boundary')
        self.pending_path.unlink()

    def recover(self,live_paths=()):
        state=self.load()
        if not self.pending_present():return state,False
        pending=read_json(self.member(self.directory,'route-pending.json'))
        if (type(pending) is not dict or set(pending)!={'schema','identity','phase','revision','token','run','inputs'}
            or type(pending['schema']) is not int or pending['schema']!=self.container_schema or pending['identity']!=self.identity
            or pending['phase'] not in self.phases or type(pending['revision']) is not int or pending['revision']<0
            or type(pending['token']) is not str or not re.fullmatch('[0-9a-f]{32}',pending['token'])):raise ValueError('foreign pending route')
        run=self.checked_run(pending['run'])
        if any(Path(p).resolve() in (run,run/'nectar.exe') for p in live_paths):raise ValueError('route child still live')
        self.validate_inputs(run,pending['inputs'])
        source=run/('p2-cave-surface-transfer.txt' if pending['phase']=='surface' else 'p2-cave-transfer.txt')
        if not source.exists() and not source.is_symlink():return state,False
        source=self.member(run,source.name)
        boundary=hashlib.sha256(source.read_bytes()).hexdigest()
        if state['revision']==pending['revision']+1:
            proof=state['boundary_proofs'][-1]
            if (state['last_boundary']!=dict(run=str(run),sha256=boundary)
                or any(proof[key]!=pending[key] for key in ('run','phase','token','inputs'))):raise ValueError('conflicting recovered boundary')
            self.pending_path.unlink();return state,False
        if state['revision']!=pending['revision'] or state['phase']!=pending['phase']:raise ValueError('stale route boundary')
        proof=dict(schema=1,revision=state['revision']+1,phase=state['phase'],run=str(run),token=pending['token'],
            inputs=copy.deepcopy(pending['inputs']),transfer=dict(name=source.name,sha256=boundary),buds=None,receipts=None)
        if state['phase']!='surface':
            buds=self.member(run,'p2-cave-bud-transfer.txt')
            proof['buds']=dict(name=buds.name,sha256=hashlib.sha256(buds.read_bytes()).hexdigest())
            proof['receipts']=self.ledger(self.phase_indices[state['phase']])
        records=state['boundary_proofs']+[proof]
        # Validate the entire candidate proof chain and parse all actual
        # boundaries BEFORE the one durable state publication.
        saved_proofs=self.validate_proofs(records,state['revision']+1)
        next_state=copy.deepcopy(state)
        if state['phase']=='surface':
            surface=saved_proofs[-1]
            next_state.update(phase=self.phases[1],visit=state['visit']+1,surface=surface,
                              entry=self.entry_for(self.phase_indices[self.phases[1]],surface['squad'],surface['health'],surface.get('wire_schema')))
        else:
            n=self.phase_indices[state['phase']];saved=saved_proofs[-1]
            if state['phase']=='acquisition' and self.white_acquired(saved):
                next_state['wfg_white_boundary']=dict(run=str(run),sha256=boundary,
                    buds_sha256=proof['buds']['sha256'])
            if state['phase']!=self.phases[-1]:
                phase=self.phases[self.phases.index(state['phase'])+1]
                next_state.update(phase=phase,entry=self.entry_for(self.phase_indices[phase],saved['squad'],saved['health'],saved.get('wire_schema')))
            else:
                surface=self.surface_from_floor(saved,state['surface']['position'])
                next_state.update(phase='surface',surface=surface,entry=None)
        next_state.update(revision=state['revision']+1,last_boundary=dict(run=str(run),sha256=boundary),boundary_proofs=records)
        atomic_write(self.state_path,encoded(next_state)+'\n');self.pending_path.unlink()
        return self.load(),True
