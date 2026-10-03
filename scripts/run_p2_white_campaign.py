"""Prepare source-bound ordinary White campaign sessions and assess raw evidence.

Native launch remains owned by the fixed runner recipe: ship F10 requires real
OS keyboard input to its isolated native window. This module never repairs it.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
import re
import sys

def strict_json(data):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate IPC field')
            result[key]=value
        return result
    return json.loads(data,object_pairs_hook=unique)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from randomizer.runner import NativeRun
from randomizer.seed import generate
from randomizer.session import Session


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_inputs(stage):
    stage = Path(stage).resolve(strict=True)
    facts = json.loads((stage/'white-campaign-inputs.json').read_text())
    required = facts.get('required_P2_retail')
    if (facts.get('ordinary_campaign') is not True or facts.get('room_preview') is not False
            or facts.get('original_red_uids') != list(range(1, 21)) or not required
            or any(required.get(k) != v for k, v in {'id':'dia_a_red','value':180,'minimum':15,'maximum':25,
                   'ivory_uids':[25,28,29],'natural_white_target':15,'receiver_uid':23}.items())):
        raise ValueError('Original P2 retail fifteen-White stage required')
    if facts.get('engineering_cargo_override') is not False:
        raise ValueError('Engineering cargo profile refused')
    for name, expected in facts['hashes'].items():
        path = stage/name
        if not path.resolve(strict=True).is_relative_to(stage) or digest(path) != expected:
            raise ValueError('Staged input escaped or changed: '+name)
    tokens = (stage/'p2-pod.txt').read_text().split()
    if tokens != ['P2_POD_1','dia_a_red','180','15','25','Kochappy','2']:
        raise ValueError('Original retail descriptor required')
    return facts


def prepare_session(stage, directory):
    facts = validate_inputs(stage)
    directory = Path(directory).resolve()
    if directory.exists():
        raise ValueError('Fresh private session required')
    manifest = generate('white-campaign-1191-retail15', starting_area='impact',
                        collection_checks=True, p2_enemies=True, p2_species=[79],
                        p2_purple_campaign=True, p2_white_campaign=True,
                        p2_white_treasure_campaign=True)
    session = Session(manifest, directory)
    native = NativeRun(session)
    layout = manifest['p2_layout']
    session.save()
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    native.write_state(True)
    # The valid bridge binding is dormant: this stage has no Teki generators.
    receipt = {'schema':1,'issue':1191,'stage':str(Path(stage).resolve()),'session':str(directory),
               'cwd':str(Path(stage).resolve()),'bootstrap':str(native.bootstrap),'bootstrap_sha256':digest(native.bootstrap),
               'state':str(native.directory/'state.txt'),'state_sha256':digest(native.directory/'state.txt'),
               'manifest_fingerprint':session.fingerprint,'profile':manifest['profile'],
               'manifest':str(directory/'manifest.json'),'manifest_sha256':digest(directory/'manifest.json'),
               'bridge_binding':layout,'bridge_binding_dormant_no_Teki_generators':True,
               'native_save_directory':str(directory/'campaign'),
               'input_hashes':facts['hashes'],'gameplay_accepted':False,'runtime_launched':False,
               'runtime_requirements':['Reviewed exact selected fixture source/executable/root/native and stager admission',
                   'Owned isolated OS keyboard input for fixed native F10 requests',
                   'Fixed positive240/other60 deadline, owned process-group cleanup, full raw logs and file hashes',
                   'Resume must reuse SAME private session/card with fresh native PID and fresh run token/state; preserve old bootstrap']}
    (directory/'white-campaign-session.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def rows(text, marker):
    result=[]
    for line in text.splitlines():
        if line.startswith(marker+' '):
            pairs=re.findall(r'(\w+)=([^\s]+)',line)
            if len(pairs)!=len(dict(pairs)):raise ValueError('Duplicate observation key')
            result.append(dict(pairs))
    return result


def phase_limit(mode):
    """Fixed development profile: full positive route240, other phases60."""
    if mode not in ('ready','forced-down','paused-down','positive','resume'):
        raise ValueError('Unknown fixed ordinary White mode')
    return 240 if mode=='positive' else 60


def assess_save_counter(text, save, generation):
    ready = rows(text,'P2_WHITE_CAMPAIGN_SAVE_READY')
    defaults = rows(text,'P2_WHITE_CAMPAIGN_DEFAULT_FILE_READY')
    if len(ready)!=1 or ready[0].get('source_notice_ready')!='1' or int(ready[0].get('backup_slot','0')) not in (1,2,3,4):
        raise ValueError('One actual ready-to-save baseline required')
    initial=int(save['native_save_index_before']);baseline=int(save['native_save_ready_index'])
    if (int(ready[0]['initial_index'])!=initial or int(ready[0]['measured_index'])!=baseline
            or int(ready[0]['generation_before'])!=generation-1
            or int(save['native_save_index_after'])!=baseline+1):
        raise ValueError('Exactly one native card save after measured baseline required')
    if ready[0].get('default_created')=='1':
        if (len(defaults)!=1 or defaults[0].get('native_successful_default_observer')!='1'
                or int(defaults[0]['initial_index'])!=initial or int(defaults[0]['measured_index'])!=baseline
                or baseline!=initial+4):
            raise ValueError('Actual successful four-area first-file initialization required')
    elif ready[0].get('default_created')!='0' or defaults or baseline!=initial:
        raise ValueError('Unexplained native card baseline change')
    if text.index('P2_WHITE_CAMPAIGN_SAVE_READY')>text.index('P2_WHITE_CAMPAIGN_SAVE_PASS'):
        raise ValueError('Measured native save baseline must precede completion')
    if defaults and text.index('P2_WHITE_CAMPAIGN_DEFAULT_FILE_READY')>text.index('P2_WHITE_CAMPAIGN_SAVE_READY'):
        raise ValueError('Default initialization must precede actual save baseline')


def assess_positive(text, *, exit_code, elapsed, timed_out, source_proof, card_proof, phase_budget=60):
    if phase_budget not in (60,240):raise ValueError('Fixed positive assessment budget required')
    if (exit_code!=0 or timed_out or not math.isfinite(elapsed) or not 0<elapsed<=phase_budget
            or source_proof is not True or not isinstance(card_proof,dict) or card_proof.get('native_block_size')!=32768):
        raise ValueError('Exact source, raw bounded0 and native paired-card proof required')
    if 'P2_WHITE_CAMPAIGN_FAIL' in text or 'P2_FIXTURE_CAPTAIN_DOWN' in text:
        raise ValueError('Native failure present')
    window=rows(text,'P2_WHITE_CAMPAIGN_WINDOW')
    if window != [{'width':'960','height':'540','centered':'1'}]:raise ValueError('Actual centered window required')
    baseline=rows(text,'P2_WHITE_CAMPAIGN_BASELINE')
    expected={'red':'20','white':'0','heads':'0','stock':'0','ivory':'3','spent':'0','cargo_uid':'26','minimum':'15','maximum':'25','value':'180'}
    if baseline != [expected]:raise ValueError('Original twenty Red/source retail baseline required')
    buds=rows(text,'P2_WHITE_CAMPAIGN_IVORY_COMPLETE')
    expected_buds=[{'uid':str(uid),'natural_outputs':'5','red':str(20-5*(i+1)),'white_heads':str(5*(i+1)),'spent':str(5*(i+1))} for i,uid in enumerate((25,28,29))]
    if buds!=expected_buds:raise ValueError('Three actual natural budget witnesses required')
    acquired=rows(text,'P2_WHITE_CAMPAIGN_ACQUIRED')
    if acquired != [{'red':'5','white':'15','heads':'0','body_total':'20','spent':'15','ordinary_birth_pluck':'1'}]:raise ValueError('Fifteen ordinary White births/plucks required')
    samples=rows(text,'P2_WHITE_CAMPAIGN_HAUL')
    if len(samples)<10:raise ValueError('Sustained actual fifteen-White haul required')
    previous=None
    for sample in samples:
        if any(sample.get(k)!=v for k,v in {'cargo_uid':'26','white':'15','red':'0','others':'0','strength':'15','native_strength':'15','natural_body_total':'20'}.items()):raise ValueError('Actual fifteen native carriers required')
        frame=int(sample['frame'])
        if previous is not None and frame!=previous+1:raise ValueError('Consecutive native haul frames required')
        previous=frame
        if any(not math.isfinite(float(sample[k])) for k in ('x','y','z','goal_distance')):raise ValueError('Finite haul geometry required')
    distance=math.hypot(float(samples[-1]['x'])-float(samples[0]['x']),float(samples[-1]['z'])-float(samples[0]['z']))
    if distance<30 or float(samples[0]['goal_distance'])-float(samples[-1]['goal_distance'])<20:raise ValueError('Actual toward-receiver transport required')
    receipts=rows(text,'P2_WHITE_TREASURE_RECEIPT')
    if receipts != [{'stage':'0','cargo':'26','receiver':'23','id':'dia_a_red','value':'180','new':'1','pokos':'180','seeds':'0','native_suction_completed':'1'}]:raise ValueError('Exactly one original retail suction receipt required')
    delivered=rows(text,'P2_WHITE_CAMPAIGN_DELIVERED')
    if delivered != [{'cargo_removed':'1','pokos':'180','stable_frames':'60','natural_white':'15'}]:raise ValueError('Removed cargo and stable once ledger required')
    save=rows(text,'P2_WHITE_CAMPAIGN_SAVE_PASS')
    if len(save)!=1 or any(save[0].get(k)!=v for k,v in {'stock':'15','white_leaf':'15','spent':'15','pokos':'180','external_CAMPAIGN_SAVED_required':'1','fresh_process_resume_pending':'1'}.items()):raise ValueError('Actual day UI SAVE witness required')
    generation=int(save[0]['generation'])
    if generation<1 or int(save[0]['day'])!=int(save[0]['day_before'])+1:raise ValueError('One ordinary day/generation required')
    assess_save_counter(text, save[0], generation)
    before=rows(text,'P2_WHITE_CAMPAIGN_P1_BEFORE_STOCK');saved=rows(text,'P2_WHITE_CAMPAIGN_P1_SAVE_STOCK')
    keys=['b_leaf','b_bud','b_flower','r_leaf','r_bud','r_flower','y_leaf','y_bud','y_flower']
    if len(before)!=1 or len(saved)!=1 or set(before[0])!=set(keys) or set(saved[0])!=set(keys):
        raise ValueError('Actual all-color maturity population history required')
    original=[int(before[0][k]) for k in keys];expected=original.copy();expected[3]+=5
    if any(n<0 or n>100000 for n in original) or [int(saved[0][k]) for k in keys]!=expected:
        raise ValueError('Five remaining original Red and other colors must persist without duplication')
    if (card_proof.get('p1_stock')!=expected or card_proof.get('native_saved_day')!=int(save[0]['day'])
            or card_proof.get('generation')!=generation
            or card_proof.get('native_card_save_index')!=int(save[0]['native_save_index_after'])-1):
        raise ValueError('Actual same native card must bind day/index/all-color stock history')
    commits=rows(text,'[Pikmin Randomizer] CAMPAIGN_SAVED')
    if commits!=[{'generation':str(generation)}]:raise ValueError('One production native card generation required')
    markers=['P2_WHITE_CAMPAIGN_BASELINE ','P2_WHITE_CAMPAIGN_IVORY_COMPLETE ','P2_WHITE_CAMPAIGN_ACQUIRED ','P2_WHITE_CAMPAIGN_HAUL ','P2_WHITE_TREASURE_RECEIPT ','P2_WHITE_CAMPAIGN_DELIVERED ','P2_WHITE_CAMPAIGN_SAVE_PASS ']
    positions=[text.index(marker) for marker in markers]
    if positions!=sorted(positions):raise ValueError('Original ordinary gameplay order required')
    for line in text.splitlines():
        if line.startswith('P2_WHITE_CAMPAIGN_IVORY_COMPLETE ') and text.index(line)>positions[2]:raise ValueError('All natural Ivory outputs must precede acquisition')
        if line.startswith('P2_WHITE_CAMPAIGN_HAUL ') and text.index(line)>positions[4]:raise ValueError('All real haul samples must precede native receipt')
    return {'slice_passed':True,'gameplay_accepted':False,'fresh_resume_pending':True,'day':int(save[0]['day']),
            'generation':generation,'p1_stock':expected,'original_p1_stock':original,'original_red_conserved':5,'original_white_conserved':15,'original_population':20,'physical_displacement':distance,'retail_minimum':15,'retail_maximum':25,'value':180}


def verify_native_card(path, *, fingerprint, generation, stage, check_count, expected_day, expected_p1_stock):
    """Read-only exact ordinary fixture card parser; never changes card/actors."""
    path = Path(path)
    if (path.is_symlink() or not path.is_file() or
            path.name != f'{generation:020d}.sav' or type(generation) is not int or generation < 1):
        raise ValueError('Exact immutable native generation required')
    size = path.stat().st_size
    if not 32768 < size <= 34816:
        raise ValueError('Bounded native paired card required')
    data = path.read_bytes()
    header, separator, block = data.partition(b'\n')
    if not separator or len(block) != 32768:
        raise ValueError('Exactly one full native card block required')
    try:
        fields = header.decode('ascii').split()
    except UnicodeError as exc:
        raise ValueError('ASCII native metadata required') from exc
    config = (Path(stage)/'p2-white-treasure-campaign.txt').read_text().split()
    if len(config)!=7 or config[:4]!=['P2_WHITE_TREASURE_CAMPAIGN_1','0','26','23']:
        raise ValueError('Exact original retail source config required')
    validate_inputs(stage)
    identity = hashlib.sha256(' '.join(config[1:]).encode('ascii')).hexdigest()
    # Fixture uses no traps: three consumed-benefit counters, then six stock
    # cells (Purple leaf/bud/flower, White leaf/bud/flower), three sorted budgets.
    expected = ['PIKMIN_CAMPAIGN_WHITE_TREASURE_1', fingerprint, str(generation)]
    if len(fields)!=25 or fields[:3]!=expected:
        raise ValueError('Exact White retail metadata/version/fingerprint required')
    if type(check_count) is not int or check_count<1:raise ValueError('Actual manifest check count required')
    benefits = fields[3:6]
    if any(not value.isascii() or not value.isdecimal() or int(value)>check_count for value in benefits):
        raise ValueError('Invalid consumed-benefit counters')
    if fields[6:12]!=['0','0','0','15','0','0']:
        raise ValueError('Same-generation fifteen leaf White stock required')
    if fields[12:23]!=['3','0','25','5','0','28','5','0','29','5',identity]:
        raise ValueError('Same-generation original Ivory budget/config identity required')
    if fields[23]!='1' or not fields[24].isdecimal():
        raise ValueError('Same-generation delivered retail ledger required')
    prefix, space, checksum = header.rpartition(b' ')
    if not space or checksum.decode('ascii')!=fields[24]:
        raise ValueError('Canonical native checksum delimiter required')
    computed=14695981039346656037
    for byte in prefix+b'\n'+block:
        computed=((computed^byte)*1099511628211)&((1<<64)-1)
    if computed!=int(checksum):raise ValueError('Native metadata/block FNV checksum differs')
    if (type(expected_day) is not int or not 1<=expected_day<=255 or
            not isinstance(expected_p1_stock,list) or len(expected_p1_stock)!=9 or
            any(type(n) is not int or not 0<=n<=100000 for n in expected_p1_stock)):
        raise ValueError('Actual saved day/all-color maturity stock expectation required')
    if block[0]!=2 or block[2]!=expected_day or block[20:24]!=b'cont' or block[60:64]!=b'cach':
        raise ValueError('Actual native PlayState day and PikiInf serialization boundary required')
    native_stock=list(struct.unpack_from('>9i',block,24))
    if native_stock!=expected_p1_stock:
        raise ValueError('Full native all-color maturity stocks differ from original population history')
    summary=struct.unpack_from('>3i',block,4)
    totals=[sum(native_stock[3:6]),sum(native_stock[6:9]),sum(native_stock[0:3])]
    if summary[0]!=totals[0] or any(summary[i]!=totals[i] and not (totals[i]==0 and summary[i]==-1) for i in (1,2)):
        raise ValueError('Actual native PlayState population summary differs')
    value=0x32546532
    for i,(word,) in enumerate(struct.iter_unpack('>I',block[:0x7ff8])):
        j=i&255;mix=(j<<24)|(((j+1)&255)<<16)|(((j-1)&255)<<8)|((j+2)&255)
        value=(value+mix+word)&0xffffffff
    checksum=(0x32546532-value)&0xffffffff
    native_index,native_checksum=struct.unpack_from('>2I',block,0x7ff8)
    if native_checksum!=checksum:raise ValueError('Actual native card checksum differs')
    return {'generation':generation,'fingerprint':fingerprint,'sha256':hashlib.sha256(data).hexdigest(),
            'native_block_sha256':hashlib.sha256(block).hexdigest(),'native_block_size':32768,
            'stock_white_leaf':15,'ivory_budget_spent':15,'retail_pokos':180,
            'native_saved_day':expected_day,'p1_stock':native_stock,'native_card_save_index':native_index,
            'native_day_requires_runtime_save_and_fresh_resume_observation':True}


def assess_resume(text, *, exit_code, elapsed, timed_out, saved_card, current_card, source_proof, expected_day):
    if (exit_code!=0 or timed_out or not math.isfinite(elapsed) or not 0<elapsed<=60
            or source_proof is not True or saved_card!=current_card):
        raise ValueError('Fresh bounded native resume and unchanged paired card required')
    if 'P2_WHITE_CAMPAIGN_FAIL' in text or 'P2_FIXTURE_CAPTAIN_DOWN' in text:
        raise ValueError('Native resume failure')
    if type(expected_day) is not int or expected_day<1:
        raise ValueError('Actual producer saved day required')
    if not isinstance(saved_card,dict) or saved_card.get('native_block_size')!=32768:
        raise ValueError('Validated full native paired card required')
    baseline=rows(text,'P2_WHITE_CAMPAIGN_RESUME_BASELINE')
    if baseline!=[{'stock':'15','leaf':'15','spent':'15','pokos':'180','consumed_source_absent':'1','native_checkpoint_resumed':'1'}]:
        raise ValueError('Restored same-generation stock/budget/ledger/source consumption required')
    withdrawals=rows(text,'P2_SHIP_WITHDRAW')
    if withdrawals!=[{'species':'4','maturity':'0','stored':str(n)} for n in range(14,-1,-1)]:
        raise ValueError('Fifteen actual conserved ordinary ship withdrawals required')
    if rows(text,'P2_SHIP_CHOICE')!=[{'captain':'0','species':'4'}]:
        raise ValueError('Actual resumed native White choice required')
    p1=rows(text,'P2_WHITE_CAMPAIGN_P1_RESUME_STOCK')
    keys=['b_leaf','b_bud','b_flower','r_leaf','r_bud','r_flower','y_leaf','y_bud','y_flower']
    if (len(p1)!=1 or set(p1[0])!=set(keys) or [int(p1[0][k]) for k in keys]!=saved_card.get('p1_stock')
            or saved_card.get('native_saved_day')!=expected_day):
        raise ValueError('Fresh native all-color/maturity stock must match the producer card')
    if rows(text,'P2_WHITE_TREASURE_RECEIPT') or rows(text,'P2_SHIP_DEPOSIT'):
        raise ValueError('Fresh resume must not credit original cargo or deposit again')
    result=rows(text,'P2_WHITE_CAMPAIGN_RESUME_PASS')
    expected={'white':'15','stock':'0','leaf':'15','spent':'15','pokos':'180',
              'native_checkpoint_resumed':'1','ordinary_ship_keyboard':'1','original_red_conserved':'5',
              'original_white_conserved':'15','original_population':'20','red_field':'0'}
    if len(result)!=1 or any(result[0].get(k)!=v for k,v in expected.items()):
        raise ValueError('Fresh native natural White withdrawal/conservation required')
    if int(result[0]['day'])!=expected_day:raise ValueError('Fresh actual resumed day differs from producer SAVE')
    displacement=float(result[0]['displacement'])
    if not math.isfinite(displacement) or displacement<=30:
        raise ValueError('Actual usable fresh White formation movement required')
    commits=rows(text,'[Pikmin Randomizer] CAMPAIGN_RESUMED')
    if commits!=[{'day':str(expected_day)}]:
        raise ValueError('Exactly the accepted ordinary native day must resume')
    checkpoint=rows(text,'P2_WHITE_CAMPAIGN_RESUME_CHECKPOINT')
    if checkpoint!=[{'generation':str(saved_card['generation']),'sha256':saved_card['sha256']}]:
        raise ValueError('Loader-compatible checkpoint observation must match the unchanged paired card')
    if rows(text,'[Pikmin Randomizer] CAMPAIGN_SAVED'):
        raise ValueError('Unexpected additional save in read-only fresh resume witness')
    return {'fresh_resume_passed':True,'gameplay_accepted':False,
            'day':int(result[0]['day']),'generation':saved_card['generation'],
            'physical_displacement':displacement}


class ShipKeyProtocol:
    """Fixed request/effect protocol over an independently verified owned window.

    Backend.verify must check current PID/start, isolated display and window PID,
    focus and 960x540 geometry on each press. Backends cannot inject actor state.
    Real backend/supervisor approval remains required before native execution.
    """
    KEYS = {'SHIFT_F10': ('SHIFT', 'F10'), 'CTRL_F10': ('CTRL', 'F10'), 'F10': ('F10',)}

    def __init__(self, backend, clock, *, resume=False, started=None, phase_budget=60):
        if phase_budget not in (60,240) or (resume and phase_budget!=60):raise ValueError('Fixed key protocol budget required')
        self.phase_budget=phase_budget
        self.backend=backend; self.clock=clock; self.started=clock() if started is None else started
        self.resume=resume; self.sequence=0; self.pending=None; self.closed=False
        self.effects=[]

    def release(self):
        errors=[]
        for key in ('F10','CTRL','SHIFT'):
            try: self.backend.key(key,False)
            except Exception as exc: errors.append(str(exc))
        self.pending=None
        if errors: raise RuntimeError('Owned key release failed: '+'; '.join(errors))

    def close(self):
        try: self.release()
        finally: self.closed=True

    def tick(self):
        elapsed=self.clock()-self.started
        if not math.isfinite(elapsed) or elapsed<0 or elapsed>=self.phase_budget:
            self.close(); raise ValueError('Absolute selected native deadline')
        if self.pending and self.clock()-self.pending[2]>=2:
            self.close(); raise ValueError('No observed native ship key effect')

    def line(self,line):
        self.tick()
        request=re.fullmatch(r'P2_WHITE_NATIVE_KEY_REQUEST seq=([1-9][0-9]*) key=(SHIFT_F10|CTRL_F10|F10) actual_SDL_keyboard_required=1',line.strip())
        if request:
            seq=int(request[1]);key=request[2]
            valid = (key=='CTRL_F10' and seq==1) or (key=='F10' and seq>1) if self.resume else key=='SHIFT_F10' and seq==1
            if self.closed or seq<=self.sequence or self.pending or not valid:
                self.close();raise ValueError('Unexpected/duplicate/overlapping native key request')
            self.backend.verify()
            self.tick()
            try:
                for item in self.KEYS[key]:
                    self.tick();self.backend.key(item,True);self.tick()
            except Exception:
                self.close();raise
            self.sequence=seq;self.pending=(seq,key,self.clock())
            return
        if line.startswith('P2_WHITE_NATIVE_KEY_REQUEST'):
            self.close();raise ValueError('Malformed native key request')
        if self.pending:
            key=self.pending[1]
            effect = ((key=='CTRL_F10' and re.fullmatch(r'P2_SHIP_CHOICE captain=[01] species=4',line.strip()))
                or (key=='SHIFT_F10' and re.fullmatch(r'P2_SHIP_DEPOSIT species=4 maturity=0 stored=([1-9]|1[0-5])',line.strip()))
                or (key=='F10' and re.fullmatch(r'P2_SHIP_WITHDRAW species=4 maturity=0 stored=([0-9]|1[0-4])',line.strip())))
            if effect:
                self.effects.append({'sequence':self.pending[0],'key':key,'native_effect':line.strip()})
                self.release()


class OwnedX11Keys:
    """Real XTest keys on a child Xvfb display and exact owned native window.

    Construction is deliberately separate from any native launch. The reviewed
    fixed runner must supply genuine executable admission before constructing it.
    """
    SYMBOLS={'F10':0xffc7,'CTRL':0xffe3,'SHIFT':0xffe1}

    @staticmethod
    def process(pid, *, live=True):
        import os
        if type(pid) is not int or pid<2:raise ValueError('Owned child PID required')
        base=Path('/proc')/str(pid)
        if base.stat().st_uid!=os.getuid():raise ValueError('Foreign process UID')
        raw=(base/'stat').read_text()
        parts=raw[raw.rfind(')')+2:].split()
        if len(parts)<20 or (live and parts[0]=='Z'):raise ValueError('Live process required')
        return int(parts[1]),parts[19]

    def __init__(self, *, native_pid, xvfb_pid, display, executable_sha256, deadline, clock, supervisor_pid):
        import ctypes as c
        import os, sys, stat
        if sys.platform!='linux' or not re.fullmatch(r':[0-9]{1,6}',display):
            raise ValueError('Private numbered Linux Xvfb display required')
        if not re.fullmatch(r'[0-9a-f]{64}',executable_sha256):raise ValueError('Reviewed executable digest required')
        if not math.isfinite(deadline) or not 0<deadline-clock()<=240:
            raise ValueError('Selected bounded native deadline required')
        self.clock=clock;self.deadline=deadline;self.native_pid=native_pid;self.xvfb_pid=xvfb_pid
        if supervisor_pid!=os.getppid():raise ValueError('Actual helper parent must own both target children')
        self.supervisor_pid=supervisor_pid;self.supervisor_start=self.process(supervisor_pid)[1]
        self.sha=executable_sha256;self.closed=False;self.handle=None;self.window=None
        parent, self.native_start=self.process(native_pid)
        xparent,self.xvfb_start=self.process(xvfb_pid)
        if parent!=self.supervisor_pid or xparent!=self.supervisor_pid:raise ValueError('Both processes must be actual supervisor children')
        args=(Path('/proc')/str(xvfb_pid)/'cmdline').read_bytes()
        if len(args)>4096:raise ValueError('Unbounded Xvfb command')
        words=args.rstrip(b'\0').split(b'\0')
        if (Path(os.fsdecode(words[0])).name!='Xvfb' or b'-displayfd' not in words
                or b'-nolisten' not in words or words[words.index(b'-nolisten')+1]!=b'tcp'
                or not words[words.index(b'-displayfd')+1].isdigit()
                or digest(Path('/proc')/str(xvfb_pid)/'exe')!=digest('/usr/bin/Xvfb')):
            raise ValueError('Owned displayfd Xvfb command/executable differs')
        socket=Path('/tmp/.X11-unix')/('X'+display[1:]);meta=socket.lstat()
        if not stat.S_ISSOCK(meta.st_mode) or meta.st_uid!=os.getuid():
            raise ValueError('Owned Xvfb socket required')
        self.c=c;self.x=c.CDLL('libX11.so.6');self.xt=c.CDLL('libXtst.so.6')
        self.x.XOpenDisplay.argtypes=[c.c_char_p];self.x.XOpenDisplay.restype=c.c_void_p
        self.x.XDefaultRootWindow.argtypes=[c.c_void_p];self.x.XDefaultRootWindow.restype=c.c_ulong
        self.x.XInternAtom.argtypes=[c.c_void_p,c.c_char_p,c.c_int];self.x.XInternAtom.restype=c.c_ulong
        self.x.XQueryTree.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(c.c_ulong),c.POINTER(c.c_ulong),c.POINTER(c.POINTER(c.c_ulong)),c.POINTER(c.c_uint)];self.x.XQueryTree.restype=c.c_int
        self.x.XGetWindowProperty.argtypes=[c.c_void_p,c.c_ulong,c.c_ulong,c.c_long,c.c_long,c.c_int,c.c_ulong,c.POINTER(c.c_ulong),c.POINTER(c.c_int),c.POINTER(c.c_ulong),c.POINTER(c.c_ulong),c.POINTER(c.POINTER(c.c_ubyte))];self.x.XGetWindowProperty.restype=c.c_int
        self.x.XFree.argtypes=[c.c_void_p];self.x.XFree.restype=c.c_int
        self.x.XGetGeometry.argtypes=[c.c_void_p,c.c_ulong,c.POINTER(c.c_ulong),c.POINTER(c.c_int),c.POINTER(c.c_int),c.POINTER(c.c_uint),c.POINTER(c.c_uint),c.POINTER(c.c_uint),c.POINTER(c.c_uint)];self.x.XGetGeometry.restype=c.c_int
        self.x.XTranslateCoordinates.argtypes=[c.c_void_p,c.c_ulong,c.c_ulong,c.c_int,c.c_int,c.POINTER(c.c_int),c.POINTER(c.c_int),c.POINTER(c.c_ulong)];self.x.XTranslateCoordinates.restype=c.c_int
        self.x.XSetInputFocus.argtypes=[c.c_void_p,c.c_ulong,c.c_int,c.c_ulong];self.x.XSetInputFocus.restype=c.c_int
        self.x.XGetInputFocus.argtypes=[c.c_void_p,c.POINTER(c.c_ulong),c.POINTER(c.c_int)];self.x.XGetInputFocus.restype=c.c_int
        self.x.XKeysymToKeycode.argtypes=[c.c_void_p,c.c_ulong];self.x.XKeysymToKeycode.restype=c.c_ubyte
        self.x.XSync.argtypes=[c.c_void_p,c.c_int];self.x.XSync.restype=c.c_int
        self.x.XCloseDisplay.argtypes=[c.c_void_p];self.x.XCloseDisplay.restype=c.c_int
        self.xt.XTestFakeKeyEvent.argtypes=[c.c_void_p,c.c_uint,c.c_int,c.c_ulong];self.xt.XTestFakeKeyEvent.restype=c.c_int
        self.handle=self.x.XOpenDisplay(display.encode())
        if not self.handle:raise ValueError('Owned Xvfb display unavailable')
        try:
            self.root=self.x.XDefaultRootWindow(self.handle)
            self.pid_atom=self.x.XInternAtom(self.handle,b'_NET_WM_PID',1)
            if not self.pid_atom:raise ValueError('Native window PID property unavailable')
            self.window=self.find_window()
            self.verify(focus=False)
            self.x.XSetInputFocus(self.handle,self.window,1,0);self.x.XSync(self.handle,0)
            self.verify()
        except Exception:
            self.close();raise

    def guard(self):
        if self.closed or self.clock()>=self.deadline:raise ValueError('Owned display deadline expired')
        import os
        if self.process(self.supervisor_pid)[1]!=self.supervisor_start or self.process(self.native_pid)!=(self.supervisor_pid,self.native_start) or self.process(self.xvfb_pid)!=(self.supervisor_pid,self.xvfb_start):
            raise ValueError('Owned child identity changed')
        if self.clock()>=self.deadline:raise ValueError('Owned display deadline expired after identity verification')

    def pid(self,window):
        c=self.c;kind=c.c_ulong();fmt=c.c_int();count=c.c_ulong();remaining=c.c_ulong();data=c.POINTER(c.c_ubyte)()
        try:
            status=self.x.XGetWindowProperty(self.handle,window,self.pid_atom,0,1,0,6,c.byref(kind),c.byref(fmt),c.byref(count),c.byref(remaining),c.byref(data))
            if status or kind.value!=6 or fmt.value!=32 or count.value!=1 or remaining.value or not data:return None
            return c.cast(data,c.POINTER(c.c_ulong))[0]
        finally:
            if data:self.x.XFree(data)

    def find_window(self):
        c=self.c;stack=[(self.root,0)];seen=set();matches=[]
        while stack:
            self.guard();window,depth=stack.pop()
            if window in seen:raise ValueError('Repeated X11 window')
            seen.add(window)
            if len(seen)>4096 or depth>8:raise ValueError('Bounded X11 window tree exceeded')
            if self.pid(window)==self.native_pid:matches.append(window)
            root=c.c_ulong();parent=c.c_ulong();children=c.POINTER(c.c_ulong)();count=c.c_uint()
            try:
                if not self.x.XQueryTree(self.handle,window,c.byref(root),c.byref(parent),c.byref(children),c.byref(count)):
                    raise ValueError('Window tree query failed')
                if count.value>4096-len(seen):raise ValueError('Bounded X11 children exceeded')
                stack.extend((children[n],depth+1) for n in range(count.value))
            finally:
                if children:self.x.XFree(children)
        if len(matches)!=1:raise ValueError('Exactly one native PID window required')
        return matches[0]

    def geometry(self,window):
        c=self.c;root=c.c_ulong();x=c.c_int();y=c.c_int();w=c.c_uint();h=c.c_uint();border=c.c_uint();depth=c.c_uint()
        if not self.x.XGetGeometry(self.handle,window,c.byref(root),c.byref(x),c.byref(y),c.byref(w),c.byref(h),c.byref(border),c.byref(depth)):
            raise ValueError('Window geometry unavailable')
        return w.value,h.value

    def verify(self,*,focus=True):
        self.guard()
        if digest(Path('/proc')/str(self.native_pid)/'exe')!=self.sha or self.pid(self.window)!=self.native_pid:
            raise ValueError('Native executable/window provenance changed')
        if self.geometry(self.window)!=(960,540):raise ValueError('Actual 960x540 native window required')
        c=self.c;x=c.c_int();y=c.c_int();child=c.c_ulong()
        if not self.x.XTranslateCoordinates(self.handle,self.window,self.root,0,0,c.byref(x),c.byref(y),c.byref(child)):
            raise ValueError('Native window root position unavailable')
        width,height=self.geometry(self.root)
        if abs(2*x.value+960-width)>4 or abs(2*y.value+540-height)>4:
            raise ValueError('Actual native centered window required')
        if focus:
            current=c.c_ulong();revert=c.c_int();self.x.XGetInputFocus(self.handle,c.byref(current),c.byref(revert))
            if current.value!=self.window:raise ValueError('Owned native window lost focus')

    def key(self,key,pressed):
        if key not in self.SYMBOLS or type(pressed) is not bool:raise ValueError('Only fixed ship keys allowed')
        if pressed:self.verify()
        if self.closed or not self.handle:
            if pressed:raise ValueError('Owned display closed')
            return
        code=self.x.XKeysymToKeycode(self.handle,self.SYMBOLS[key])
        if pressed:self.guard()
        if not code or not self.xt.XTestFakeKeyEvent(self.handle,code,int(pressed),0):
            raise ValueError('Owned XTest key event failed')
        self.x.XSync(self.handle,0)

    def close(self):
        if self.handle:
            errors=[]
            try:
                for key in self.SYMBOLS:
                    try:self.key(key,False)
                    except Exception as exc:errors.append(str(exc))
            finally:
                self.x.XCloseDisplay(self.handle);self.handle=None;self.closed=True
            if errors:raise RuntimeError('Owned X11 release failed: '+'; '.join(errors))


def read_display_fd(fd,*,deadline):
    import os,selectors,time
    os.set_blocking(fd,False);selector=selectors.DefaultSelector();selector.register(fd,selectors.EVENT_READ)
    data=b''
    try:
        while True:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise ValueError('Owned Xvfb displayfd startup deadline')
            for key,event in selector.select(min(.02,remaining)):
                try:chunk=os.read(fd,16)
                except BlockingIOError:continue
                if not chunk:raise ValueError('Owned Xvfb displayfd closed')
                data+=chunk
                if len(data)>7:raise ValueError('Bounded Xvfb displayfd response exceeded')
                if b'\n' in data:
                    if not re.fullmatch(rb'[0-9]{1,6}\n',data):raise ValueError('Malformed Xvfb displayfd response')
                    return ':'+data[:-1].decode('ascii')
    finally:selector.close()


class PipeRPC:
    """Bounded JSON pipe requests to a direct, separately killable child."""
    def __init__(self,process,*,deadline,clock):
        import os
        self.process=process;self.deadline=deadline;self.clock=clock;self.sequence=0;self.closed=False
        os.set_blocking(process.stdin.fileno(),False);os.set_blocking(process.stdout.fileno(),False)

    def request(self,operation,*,limit=.5,**fields):
        import os,selectors
        if self.closed or self.process.poll() is not None:raise ValueError('X11 helper unavailable')
        self.sequence+=1
        payload=(json.dumps({'seq':self.sequence,'op':operation,**fields},separators=(',',':'))+'\n').encode()
        if len(payload)>2048:raise ValueError('Bounded helper request exceeded')
        stop=min(self.deadline,self.clock()+limit);sent=0;answer=b''
        selector=selectors.DefaultSelector()
        try:
            selector.register(self.process.stdin,selectors.EVENT_WRITE)
            while True:
                remaining=stop-self.clock()
                if remaining<=0:raise ValueError('X11 helper IPC deadline')
                if self.process.poll() is not None:raise ValueError('X11 helper died')
                for key,event in selector.select(min(.02,remaining)):
                    if key.fileobj is self.process.stdin:
                        try:count=os.write(key.fileobj.fileno(),payload[sent:])
                        except BlockingIOError:continue
                        if count<=0:raise ValueError('X11 helper request closed')
                        sent+=count
                        if sent==len(payload):
                            selector.unregister(self.process.stdin);selector.register(self.process.stdout,selectors.EVENT_READ)
                    else:
                        try:data=os.read(key.fileobj.fileno(),4096)
                        except BlockingIOError:continue
                        if not data:raise ValueError('X11 helper response closed')
                        answer+=data
                        if len(answer)>2048:raise ValueError('Bounded helper response exceeded')
                        if b'\n' in answer:
                            if not answer.endswith(b'\n') or answer.count(b'\n')!=1:raise ValueError('Unexpected helper response records')
                            reply=strict_json(answer)
                            if (not isinstance(reply,dict) or set(reply)!={'seq','ok','error'}
                                or type(reply['seq']) is not int or reply['seq']!=self.sequence
                                or type(reply['ok']) is not bool
                                or (reply['error'] is not None and (not isinstance(reply['error'],str) or len(reply['error'])>512))):
                                raise ValueError('Malformed helper response')
                            if not reply['ok'] or reply['error'] is not None:raise ValueError('X11 helper refused: '+str(reply['error']))
                            return
        except Exception:
            self.abort();raise
        finally:selector.close()

    def abort(self):
        self.closed=True
        if self.process.poll() is None:self.process.kill()

    def reap(self,deadline):
        self.abort()
        self.process.wait(timeout=max(.001,min(.25,deadline-self.clock())))
        for stream in (self.process.stdin,self.process.stdout):stream.close()


class OwnedX11Client:
    """Supervisor holds only bounded pipes; all synchronous Xlib is in child."""
    def __init__(self,*,native_pid,xvfb_pid,display,executable_sha256,deadline,cleanup_deadline,clock,diagnostic_path=None):
        import os,subprocess
        self.clock=clock;self.cleanup_deadline=cleanup_deadline;self.closed=False;self.pressed_keys=set()
        diagnostic=Path(diagnostic_path).open('xb') if diagnostic_path is not None else None
        try:
            self.process=subprocess.Popen([sys.executable,'-I','-B',str(Path(__file__).resolve()),'--x11-helper'],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=diagnostic if diagnostic is not None else subprocess.DEVNULL)
        finally:
            if diagnostic is not None:diagnostic.close()
        self.start=OwnedX11Keys.process(self.process.pid,live=False)[1]
        self.rpc=PipeRPC(self.process,deadline=deadline,clock=clock)
        try:
            self.rpc.request('init',limit=1,native_pid=native_pid,xvfb_pid=xvfb_pid,display=display,
                             executable_sha256=executable_sha256,deadline=deadline,supervisor_pid=os.getpid())
        except Exception as primary:
            try:self.close()
            except Exception as cleanup:primary.add_note('Helper cleanup: '+str(cleanup))
            raise

    def verify(self):self.rpc.request('verify')
    def key(self,key,pressed):
        if key not in OwnedX11Keys.SYMBOLS or type(pressed) is not bool:raise ValueError('Only fixed ship keys allowed')
        if pressed:
            self.pressed_keys.add(key);self.rpc.request('key',key=key,pressed=True)
        elif self.rpc.closed:
            if key in self.pressed_keys:raise ValueError('Helper unavailable; key neutralization requires owned display teardown')
        else:
            self.rpc.deadline=self.cleanup_deadline
            self.rpc.request('key',limit=.15,key=key,pressed=False);self.pressed_keys.discard(key)

    def close(self):
        if self.closed:return
        errors=[]
        try:
            if self.rpc.closed and self.pressed_keys:errors.append('Helper unavailable; neutralization unconfirmed until owned display teardown')
            if not self.rpc.closed:
                self.rpc.deadline=self.cleanup_deadline
                for key in ('F10','CTRL','SHIFT'):
                    try:
                        self.rpc.request('key',limit=.15,key=key,pressed=False);self.pressed_keys.discard(key)
                    except Exception as exc:errors.append(str(exc))
                if not self.rpc.closed:
                    try:self.rpc.request('close',limit=.15)
                    except Exception as exc:errors.append(str(exc))
        finally:
            self.closed=True
            if self.process.poll() is None:
                import os
                if OwnedX11Keys.process(self.process.pid,live=False)!=(os.getpid(),self.start):raise ValueError('Helper PID identity changed')
            self.rpc.reap(self.cleanup_deadline)
        if errors:raise RuntimeError('Owned X11 cleanup refused: '+'; '.join(errors))


def x11_helper():
    """No user-selected commands: fixed bounded pipe grammar and owned parent."""
    import os,time
    backend=None;sequence=0
    try:
        while True:
            line=sys.stdin.buffer.readline(2049)
            if not line or len(line)>2048 or not line.endswith(b'\n'):raise ValueError('Bounded helper input required')
            request=strict_json(line)
            if not isinstance(request,dict) or type(request.get('seq')) is not int or request['seq']!=sequence+1:
                raise ValueError('Sequential helper request required')
            sequence=request['seq'];operation=request.get('op')
            try:
                if operation=='init':
                    fields={'seq','op','native_pid','xvfb_pid','display','executable_sha256','deadline','supervisor_pid'}
                    if backend or set(request)!=fields:raise ValueError('Exact actual helper parent required')
                    backend=OwnedX11Keys(**{k:v for k,v in request.items() if k not in ('seq','op')},clock=time.monotonic)
                elif operation=='verify':
                    if not backend or set(request)!={'seq','op'}:raise ValueError('Helper init required')
                    backend.verify()
                elif operation=='key':
                    if not backend or set(request)!={'seq','op','key','pressed'}:raise ValueError('Exact fixed key request required')
                    backend.key(request['key'],request['pressed'])
                elif operation=='close':
                    if not backend or set(request)!={'seq','op'}:raise ValueError('Exact helper close required')
                    backend.close()
                else:raise ValueError('Unknown helper operation')
                print(json.dumps({'seq':sequence,'ok':True,'error':None}),flush=True)
                if operation=='close':return 0
            except Exception as exc:
                print(json.dumps({'seq':sequence,'ok':False,'error':str(exc)[:512]}),flush=True)
                return 1
    except Exception as exc:
        print('X11 helper startup/protocol error: '+str(exc)[:512],file=sys.stderr,flush=True)
        return 1
    finally:
        # A stalled native Xlib call may stall this finally too. The separate
        # parent kills this child and the entire owned display, making keys
        # neutral by teardown before any later phase is possible.
        if backend:backend.close()


def prepare_resume(stage, directory, *, expected_day, expected_p1_stock, generation):
    """Create a new token/process input over the SAME accepted private card."""
    validate_inputs(stage)
    directory=Path(directory).resolve(strict=True)
    if type(expected_day) is not int or not 1<=expected_day<=10000:
        raise ValueError('Observed saved day required')
    manifest=json.loads((directory/'manifest.json').read_text())
    if any(manifest.get(flag) is not True for flag in ('p2_purple_campaign','p2_white_campaign','p2_white_treasure_campaign')):
        raise ValueError('Same original campaign manifest required')
    session=Session(manifest,directory)
    card=verify_native_card(directory/'campaign'/f'{generation:020d}.sav',fingerprint=session.fingerprint,
        generation=generation,stage=stage,check_count=len(session.names),expected_day=expected_day,expected_p1_stock=expected_p1_stock)
    native=NativeRun(session);native.write_state(True)
    receipt={'schema':1,'resume':True,'expected_day':expected_day,'session':str(directory),
             'bootstrap':str(native.bootstrap),'bootstrap_sha256':digest(native.bootstrap),
             'manifest_fingerprint':session.fingerprint,'token':native.token,'expected_p1_stock':expected_p1_stock,
             'generation':generation,'paired_card':card,
             'runtime_launched':False,'gameplay_accepted':False}
    (native.directory/'resume-inputs.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def _run_phase_worker(exe,stage,session_directory,run_directory,*,mode,root_pin,native_pin,source_sha,
                     bootstrap,phase_started,expected_day=None,expected_p1_stock=None,saved_generation=None):
    """Private Linux development run with real scoped XTest keyboard.

    Run inside a fresh owned user-manager service with a whole-phase deadline.
    Heavy build and runtime coordination belongs to the shared runner owner.
    """
    import os, selectors, signal, subprocess, time
    from scripts.fixture_platform import runtime_evidence
    phase_budget=phase_limit(mode)
    work_budget=phase_budget-6
    work_deadline=phase_started+work_budget
    cleanup_deadline=phase_started+phase_budget-3
    def phase_guard():
        if time.monotonic()>=work_deadline:raise ValueError('Phase work deadline reached; cleanup reserved within selected phase')
    phase_guard()
    if sys.platform!='linux':raise ValueError('Reviewed fixed Linux recipe required')
    if mode not in ('ready','forced-down','paused-down','positive','resume'):
        raise ValueError('Unknown fixed ordinary White mode')
    exe=Path(exe).resolve(strict=True);stage=Path(stage).resolve(strict=True)
    session_directory=Path(session_directory).resolve(strict=True)
    run_directory=Path(run_directory).resolve(strict=True)
    if not run_directory.is_relative_to(session_directory):
        raise ValueError('Owned private run/session required')
    if any((run_directory/name).exists() for name in ('native.log','xvfb.log','runtime-result.json')):
        raise ValueError('Fresh evidence directory required')
    validate_inputs(stage)
    manifest=json.loads((session_directory/'manifest.json').read_text())
    session=Session(manifest,session_directory)
    bootstrap=Path(bootstrap).resolve(strict=True)
    if bootstrap.name!='bootstrap.txt':raise ValueError('Exact native bootstrap input required')
    native=NativeRun.attach(session,bootstrap.parent)
    proof={'exe_sha256':digest(exe),'target':'pikmin_ci_fixture_white_campaign',
           'source':'tools/p2_white_campaign_runtime.cpp','root_pin':root_pin,'native_pin':native_pin,
           'source_sha256':source_sha,'development_test':True}
    env={k:v for k,v in os.environ.items() if (k=='PIKMIN_SHA' or not k.upper().startswith(('PIKMIN_','P2_','COOP_')))
         and k.upper() not in ('DISPLAY','XAUTHORITY','NECTAR_SAVE_DIR','NECTAR_EXECUTABLE_PATH')}
    runtime=runtime_evidence(exe,env=env,cwd=stage)
    if runtime['executable']['sha256']!=proof['exe_sha256']:raise ValueError('Executable changed after admission')
    env.update(SDL_AUDIODRIVER='dummy',PIKMIN_P2_ROOM_WINDOW='960x540',
               PIKMIN_RANDOMIZER_AUTOPLAY='0',PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',PIKMIN_RANDOMIZER_TEST_VISIBLE='1',
               SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS='1',NECTAR_EXECUTABLE_PATH=str(exe),
               NECTAR_SAVE_DIR=str(session_directory/'campaign'/'card'))
    modes={'ready':'P2_WHITE_CAMPAIGN_READY_ONLY','forced-down':'P2_WHITE_CAMPAIGN_FORCE_DOWN',
           'paused-down':'P2_WHITE_CAMPAIGN_PAUSED_DOWN','resume':'P2_WHITE_CAMPAIGN_RESUME'}
    if mode in modes:env[modes[mode]]='1'
    if mode=='resume':
        if type(expected_day) is not int or not 1<=expected_day<=10000:raise ValueError('Observed saved next day required')
        card=verify_native_card(session_directory/'campaign'/f'{saved_generation:020d}.sav',
            fingerprint=session.fingerprint,generation=saved_generation,stage=stage,check_count=len(session.names),
            expected_day=expected_day,expected_p1_stock=expected_p1_stock)
        resume_input=json.loads((native.directory/'resume-inputs.json').read_text())
        if (resume_input.get('paired_card')!=card or resume_input.get('token')!=native.token
                or resume_input.get('generation')!=saved_generation or resume_input.get('expected_day')!=expected_day):
            raise ValueError('Fresh resume inputs differ from actual producer card')
        env['P2_WHITE_CAMPAIGN_EXPECT_DAY']=str(expected_day)
        env['P2_WHITE_CAMPAIGN_EXPECT_P1_STOCK']=','.join(str(n) for n in expected_p1_stock)
    home=run_directory/'home';home.mkdir(exist_ok=False)
    temporary=run_directory/'tmp';temporary.mkdir(exist_ok=False)
    config=home/'config';config.mkdir();cache=home/'cache';cache.mkdir()
    env.update(HOME=str(home),TMPDIR=str(temporary),XDG_CONFIG_HOME=str(config),XDG_CACHE_HOME=str(cache))
    os.environ.update(HOME=str(home),TMPDIR=str(temporary),XDG_CONFIG_HOME=str(config),XDG_CACHE_HOME=str(cache),PYTHONDONTWRITEBYTECODE='1')
    os.environ.pop('XAUTHORITY',None);os.environ.pop('DISPLAY',None)
    display=None;display_read,display_write=os.pipe()
    processes=[];protocol=None;backend=None;native_process=None;started=phase_started
    total=0;pending=b'';timed_out=False;error=None;cleanup=[];raw=[]
    selector=selectors.DefaultSelector()
    native_log=(run_directory/'native.log').open('xb')
    xvfb_log=(run_directory/'xvfb.log').open('xb')
    try:
        phase_guard()
        xvfb=subprocess.Popen(['/usr/bin/Xvfb','-displayfd',str(display_write),'-screen','0','1280x720x24','-nolisten','tcp'],
             cwd=run_directory,env=env,stdout=xvfb_log,stderr=subprocess.STDOUT,pass_fds=(display_write,))
        processes.append((xvfb,OwnedX11Keys.process(xvfb.pid,live=False)[1]))
        os.close(display_write);display_write=None
        display=read_display_fd(display_read,deadline=min(work_deadline,time.monotonic()+3))
        os.close(display_read);display_read=None
        socket=Path('/tmp/.X11-unix')/('X'+display[1:]);env['DISPLAY']=display
        (run_directory/'runtime-inputs.json').write_text(json.dumps({'admission':proof,'runtime':runtime,
            'mode':mode,'bootstrap_sha256':digest(bootstrap),'stage':str(stage),'display':display,
            'phase_limit':phase_budget,'work_limit':work_budget,'cleanup_reserved':6},indent=2)+'\n')
        waiting=time.monotonic()
        while not socket.exists():
            phase_guard()
            if xvfb.poll() is not None or time.monotonic()-waiting>=3:raise ValueError('Owned Xvfb startup failed')
            time.sleep(.01)
        phase_guard()
        if digest(exe)!=proof['exe_sha256']:raise ValueError('Executable changed immediately before launch')
        phase_guard()
        native_process=subprocess.Popen([str(exe),'--randomizer-seed',str(bootstrap)],cwd=stage,env=env,
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        processes.append((native_process,OwnedX11Keys.process(native_process.pid,live=False)[1]))
        os.set_blocking(native_process.stdout.fileno(),False)
        selector.register(native_process.stdout,selectors.EVENT_READ)
        def line_received(line):
            nonlocal backend,protocol
            if line.startswith('P2_WHITE_NATIVE_KEY_REQUEST'):
                if mode not in ('positive','resume'):raise ValueError('Unexpected native key request in guard/ready')
                if backend is None:
                    backend=OwnedX11Client(native_pid=native_process.pid,xvfb_pid=xvfb.pid,display=display,
                        executable_sha256=proof['exe_sha256'],deadline=work_deadline,cleanup_deadline=cleanup_deadline,clock=time.monotonic,
                        diagnostic_path=Path(run_directory)/'x11-helper.log')
                    protocol=ShipKeyProtocol(backend,time.monotonic,resume=mode=='resume',started=started,phase_budget=phase_budget)
            if protocol:protocol.line(line)
        while selector.get_map():
            if time.monotonic()>=work_deadline:timed_out=True;raise ValueError('Phase work deadline; cleanup reserved within selected phase')
            if protocol:protocol.tick()
            if xvfb.poll() is not None:raise ValueError('Owned display ended before native')
            native.poll();native.write_state(True)
            for key,event in selector.select(.02):
                data=os.read(key.fileobj.fileno(),65536)
                if not data:
                    selector.unregister(key.fileobj);continue
                native_log.write(data);native_log.flush();total+=len(data)
                if total>16*1024*1024:raise ValueError('Bounded native raw log exceeded')
                pending+=data
                while b'\n' in pending:
                    line,pending=pending.split(b'\n',1)
                    if len(line)>8192:raise ValueError('Bounded native observation line exceeded')
                    text=line.decode('utf-8',errors='strict');raw.append(text);line_received(text)
                if len(pending)>8192:raise ValueError('Bounded native pending line exceeded')
        if pending:raise ValueError('Incomplete native observation line')
        remaining=max(0,work_deadline-time.monotonic())
        native_process.wait(timeout=remaining)
        native.poll()
        if not native.handshaken:raise ValueError('Actual native hello required')
        if protocol and protocol.pending:raise ValueError('Native ended before requested key effect')
    except Exception as exc:
        error=str(exc)
    finally:
        # Attempt EVERY owned release and process cleanup even if an earlier one
        # fails. Never signal a replaced PID or an unrelated process group.
        for object in (protocol,backend):
            if object:
                try:object.close()
                except Exception as exc:cleanup.append(str(exc))
        for process,start in reversed(processes):
            try:
                if process.poll() is None:
                    if OwnedX11Keys.process(process.pid)!=(os.getpid(),start):raise ValueError('Owned cleanup PID changed')
                    process.kill()
                process.wait(timeout=max(.001,min(.25,cleanup_deadline-time.monotonic())))
            except Exception as exc:cleanup.append(str(exc))
        for fd in (display_read,display_write):
            if fd is not None:
                try:os.close(fd)
                except Exception as exc:cleanup.append(str(exc))
        selector.close();native_log.close();xvfb_log.close()
    elapsed=time.monotonic()-started if started is not None else None
    result={'schema':1,'mode':mode,'launched':native_process is not None,
            'exit_code':native_process.returncode if native_process else None,
            'elapsed':elapsed,'phase_budget':phase_budget,'work_budget':work_budget,'cleanup_reserved':6,'timed_out':timed_out,'error':error,'cleanup_errors':cleanup,
            'native_log_sha256':digest(run_directory/'native.log'),
            'actual_ship_key_effects':protocol.effects if protocol else [],
            'source_proof':proof,'gameplay_accepted':False}
    (run_directory/'runtime-result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def phase_failure(result,mode):
    """Infrastructure and mode exit validation; required guard86 stays valid."""
    expected={'ready':0,'forced-down':86,'paused-down':86,'positive':0,'resume':0}
    if mode not in expected or not isinstance(result,dict) or result.get('mode')!=mode:
        return 'Exact selected phase result required'
    if result.get('error') is not None:return 'Inner phase error: '+str(result.get('error'))
    if not isinstance(result.get('cleanup_errors'),list) or result['cleanup_errors']:
        return 'Inner phase cleanup failed: '+str(result.get('cleanup_errors'))
    if result.get('timed_out') is not False:return 'Inner phase timed out or timeout evidence missing'
    if result.get('launched') is not True:return 'Actual native launch required'
    if type(result.get('exit_code')) is not int or result['exit_code']!=expected[mode]:
        return 'Unexpected selected-mode raw native exit'
    elapsed=result.get('elapsed')
    if type(elapsed) not in (float,int) or not math.isfinite(elapsed) or not 0<elapsed<phase_limit(mode):
        return 'Inner phase deadline evidence invalid'
    return None


def parse_execstart(value):
    """Exact stable systemctl ExecStart fields, with mutable observations apart.

    Prepared paths/argv are restricted to literal ASCII tokens without shell or
    systemd escaping. Unknown serialization fails closed; no substring binding.
    """
    if not isinstance(value,str) or len(value)>8192:raise ValueError('Bounded ExecStart required')
    match=re.fullmatch(r'\{ path=([^;]+) ; argv\[\]=([^;]+) ; ignore_errors=(yes|no) ; start_time=([^;{}\r\n]*) ; stop_time=([^;{}\r\n]*) ; pid=([0-9]+) ; code=([^;{}\r\n]+) ; status=([^;{}\r\n]+) \}',value)
    if not match:raise ValueError('Exact single ExecStart serialization required')
    path,arguments,ignored,start,stop,pid,code,status=match.groups()
    argv=arguments.split(' ')
    if ignored!='no' or not path.startswith('/') or not argv or argv[0]!=path or any(not re.fullmatch(r'[A-Za-z0-9_./:=+-]+',arg) for arg in argv):
        raise ValueError('Exact literal executable/full argv required')
    return {'path':path,'argv':argv,'ignore_errors':False}, {'start_time':start,'stop_time':stop,'pid':int(pid),'code':code,'status':status}


def process_source_identity(pid):
    """Actual same-UID kernel snapshot; PID0 is never a historical identity."""
    import os
    if type(pid) is not int or pid<2:raise ValueError('Actual nonzero process identity required')
    base=Path('/proc')/str(pid)
    if base.stat().st_uid!=1000:raise ValueError('Actual UID1000 process required')
    raw=(base/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
    if len(fields)<20 or not fields[19].isdecimal():raise ValueError('Actual PID birth required')
    command=(base/'cmdline').read_bytes()
    if not command.endswith(b'\0'):raise ValueError('Actual process argv required')
    argv=[part.decode('utf8','strict') for part in command[:-1].split(b'\0')]
    cgroups=[row[3:] for row in (base/'cgroup').read_text().splitlines() if row.startswith('0::')]
    if len(cgroups)!=1:raise ValueError('Actual process unified membership required')
    executable=(base/'exe').resolve(strict=True)
    proof={'pid':pid,'birth':fields[19],'uid':1000,'argv':argv,'executable':str(executable),
           'executable_sha256':digest(executable),'cgroup':cgroups[0]}
    # Snapshot refuses PID reuse during multi-file reads, rather than mixing two
    # processes into one command/membership certificate.
    again=(base/'stat').read_text();second=again[again.rfind(')')+2:].split()
    if len(second)<20 or second[19]!=fields[19] or base.stat().st_uid!=1000:
        raise ValueError('Process identity changed during observation')
    return proof


def bind_unit_identity(facts,expected,receipt,prior=None,live=None):
    """Stable unit binding plus actual live or source-issued historical snapshot."""
    command,observed=parse_execstart(facts.get('ExecStart'))
    if command!={'path':expected['argv'][0],'argv':expected['argv'],'ignore_errors':False}:
        raise ValueError('Exact unit executable/full argv changed')
    invocation=facts.get('InvocationID');group=facts.get('ControlGroup')
    if not isinstance(invocation,str) or not re.fullmatch('[0-9a-f]{32}',invocation):raise ValueError('Actual invocation required')
    if prior and (invocation!=prior['invocation'] or group not in ('',prior['cgroup'])):
        raise ValueError('Unit invocation/cgroup changed; foreign unit refused')
    for field in ('MainPID','ExecMainPID'):
        if not isinstance(facts.get(field),str) or not facts[field].isdecimal():raise ValueError('Actual manager PID observations required')
    main=int(facts['MainPID']);historic=int(facts['ExecMainPID'])
    if not prior and group!=expected['cgroup'] and not (group=='' and main==0 and receipt is not None):
        raise ValueError('Exact initial unit cgroup or genuine completed startup history required')
    if historic<2:raise ValueError('Actual nonzero ExecMainPID required')
    proof=live or receipt or (prior['process'] if prior else None)
    if not isinstance(proof,dict) or set(proof)!={'pid','birth','uid','argv','executable','executable_sha256','cgroup'}:
        raise ValueError('Genuine process snapshot required; MainPID0 not evidence')
    if (type(proof['pid']) is not int or proof['pid']!=historic or proof['uid']!=1000
        or not isinstance(proof['birth'],str) or not proof['birth'].isdecimal() or int(proof['birth'])<1
        or proof['argv']!=expected['argv'] or proof['executable']!=expected['executable']
        or proof['executable_sha256']!=expected['executable_sha256'] or proof['cgroup']!=expected['cgroup']):
        raise ValueError('Process source/birth/cgroup binding mismatch')
    if main not in (0,proof['pid']):raise ValueError('Current MainPID changed')
    if main and live is None:raise ValueError('Current process needs live kernel binding')
    if prior and proof!=prior['process']:raise ValueError('Actual process identity changed')
    # Historical receipt is emitted by the exact source before any test. Its
    # manager InvocationID is separately checked by caller, never supplied as PID0.
    return {'invocation':invocation,'cgroup':expected['cgroup'],'command':command,'process':proof,
            'mutable_observation':dict(observed,MainPID=main,ExecMainPID=historic)}


def phase_worker():
    """Direct child phase entry; fixed payload, one inherited absolute clock."""
    import os,time
    if sys.platform!='linux':raise ValueError('Linux private worker required')
    print(json.dumps({'white_control_startup28':True,'invocation':os.environ.get('INVOCATION_ID',''),
                      'process':process_source_identity(os.getpid())}),flush=True)
    line=sys.stdin.buffer.readline(8193)
    if not line or len(line)>8192 or not line.endswith(b'\n'):return 1
    try:
        request=strict_json(line)
        fields={'exe','stage','session_directory','run_directory','mode','root_pin','native_pin','source_sha',
                'bootstrap','expected_day','expected_p1_stock','saved_generation','phase_started','supervisor_pid'}
        if not isinstance(request,dict) or set(request)!=fields:
            raise ValueError('Exact owned phase request required')
        started=request.pop('phase_started');request.pop('supervisor_pid')
        if type(started) not in (float,int) or not math.isfinite(started) or not 0<=time.monotonic()-started<54:
            raise ValueError('Actual inherited phase clock required')
        result=_run_phase_worker(**request,phase_started=started)
        failure=phase_failure(result,request['mode'])
        print(json.dumps({'ok':failure is None,'result':result,'error':failure}),flush=True)
        return 0 if failure is None else 1
    except Exception as exc:
        print(json.dumps({'ok':False,'result':None,'error':str(exc)[:1024]}),flush=True)
        return 1


def cleanup_control29(mode):
    import os,subprocess,time,signal
    print(json.dumps({'white_control_startup28':True,'invocation':os.environ.get('INVOCATION_ID',''),
                      'process':process_source_identity(os.getpid())}),flush=True)
    child=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(120)'],start_new_session=True,
                           stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print(json.dumps({'cleanup_child29':True,'pid':child.pid,'group':os.getpgid(child.pid),'birth':OwnedX11Keys.process(child.pid)[1]}),flush=True)
    time.sleep(.75)
    if mode=='exit':raise SystemExit(23)
    if mode=='kill':os.kill(os.getpid(),signal.SIGKILL)
    if mode=='stall':time.sleep(120)
    raise ValueError('Fixed cleanup scenarios only')

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--cleanup-control' and sys.argv[2] in ('exit','kill','stall'):cleanup_control29(sys.argv[2]);raise SystemExit(1)
    if sys.argv[1:]==['--x11-helper']:raise SystemExit(x11_helper())
    if sys.argv[1:]==['--phase-worker']:raise SystemExit(phase_worker())
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True,type=Path)
    parser.add_argument('--session',required=True,type=Path)
    args=parser.parse_args()
    print(json.dumps(prepare_session(args.stage,args.session),indent=2))
