"""Bounded private White development phase under direct coordination #1195.

A fresh owned user-manager service contains every native/display/helper child.

"""

import time

started=time.monotonic()

import argparse,json,os,re,selectors,signal,subprocess,sys,uuid

from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

sys.path.insert(0,str(ROOT))

from scripts.run_p2_white_campaign import phase_limit,bind_unit_identity,process_source_identity,digest



def command(args,deadline):

    if time.monotonic()>=deadline:raise ValueError('User-manager operation deadline')

    child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    try:

        out,err=child.communicate(timeout=min(.3,max(.001,deadline-time.monotonic())))

        if child.returncode or len(out)>8192 or len(err)>8192:raise ValueError('Bounded manager operation refused')

        return out.decode('utf8')

    finally:

        if child.poll() is None:child.kill()

        child.wait(timeout=.15)



def properties(unit,deadline):

    text=command(['/usr/bin/systemctl','--user','show',unit,'--property=LoadState,ActiveState,SubState,ControlGroup,InvocationID,ExecStart,MainPID,ExecMainPID'],deadline)

    facts={}

    for row in text.splitlines():

        key,sep,value=row.partition('=')

        if not sep or key in facts:raise ValueError('Malformed actual unit evidence')

        facts[key]=value

    # systemd omits ExecStart for an actual nonexistent service.

    if facts.get('LoadState')=='not-found' and 'ExecStart' not in facts:facts['ExecStart']=''

    if set(facts)!={'LoadState','ActiveState','SubState','ControlGroup','InvocationID','ExecStart','MainPID','ExecMainPID'}:raise ValueError('Exact manager properties required')

    return facts



def bound_observation(unit,expected,startup,prior,deadline):

    """Requery stale manager PID after observed exit; never invent a birth."""

    while True:

        facts=properties(unit,deadline)

        if facts['LoadState']!='loaded':return facts,None

        if facts['InvocationID']!=startup['invocation']:raise ValueError('Actual startup invocation changed')

        pid=int(facts['MainPID']);live=None

        if pid>0:

            try:live=process_source_identity(pid)

            except (ProcessLookupError,FileNotFoundError):pass

            except ValueError as exc:

                proc=Path('/proc')/str(pid)

                try:

                    stat=(proc/'stat').read_text();fields=stat[stat.rfind(')')+2:].split();state=fields[0]

                    captured=prior['process'] if prior else startup['process']

                    empty_exit=(str(exc)=='Actual process argv required' and (proc/'cmdline').read_bytes()==b''

                                and len(fields)>=20 and fields[19]==captured['birth']

                                and pid==captured['pid'] and proc.stat().st_uid==captured['uid'])

                except FileNotFoundError:state='absent';empty_exit=False

                if state not in ('Z','X','absent') and not empty_exit:raise

            if live is None:

                if time.monotonic()>=deadline:raise ValueError('Exited manager PID did not retire within observation deadline')

                time.sleep(.005);continue

        return facts,bind_unit_identity(facts,expected,startup['process'],prior=prior,live=live)



def cgroup_empty(path):

    if not re.fullmatch(r'/user.slice/user-1000.slice/user@1000.service/(?:[A-Za-z0-9_.@:-]+/)*white1191-29-[0-9a-f]{32}\.service',path):

        raise ValueError('Exact own user-manager service cgroup required')

    current=Path('/sys/fs/cgroup')

    for part in path.lstrip('/').split('/'):

        current=current/part

        if current.is_symlink():raise ValueError('Cgroup symlink refused')

        if not current.exists():return {'path':path,'absent':True,'populated':0,'method':'actual kernel cgroup path absent'}

    values={}

    for row in (current/'cgroup.events').read_text().splitlines():

        key,value=row.split()

        if key in values:raise ValueError('Duplicate cgroup state')

        values[key]=value

    procs=(current/'cgroup.procs').read_text().split()

    if values.get('populated')!='0' or procs:raise ValueError('Actual user unit descendants still present')

    return {'path':path,'absent':False,'populated':0,'direct_pids':[],'method':'actual cgroup.events/procs empty'}



def main():

    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--request',type=Path);group.add_argument('--cleanup-control',choices=('exit','kill','stall'))

    options=parser.parse_args()

    if sys.platform!='linux' or os.getuid()!=1000:raise ValueError('SoleRunner UID1000 user-manager controls only')

    directory=Path.cwd().resolve()

    if not directory.name.startswith('white1191-phase29-'):raise ValueError('New exclusive namespace required')

    result_path=directory/'phase-result.json'

    if result_path.exists():raise ValueError('Prior wrapper evidence preserved')

    script=ROOT/'scripts/run_p2_white_campaign.py'

    request=json.loads(options.request.read_text()) if options.request else {}

    whole_limit=phase_limit(request['mode']) if options.request else 60
    request['phase_started']=started;request['supervisor_pid']=os.getpid()

    payload=(json.dumps(request,separators=(',',':'))+'\n').encode()

    if len(payload)>8192:raise ValueError('Bounded private worker request required')

    unit='white1191-29-'+uuid.uuid4().hex+'.service'

    client=None;selector=selectors.DefaultSelector();output=bytearray();pending=b'';startup=None;identity=None;retirement=None;error=None;cleanup=[];returncode=None;observations=[]

    try:

        if properties(unit,started+2)['LoadState']!='not-found':raise ValueError('Fresh own unit required')

        # The script creates home/tmp itself. Distinct wrapper dirs avoid collisions.

        wrapper_home=directory/'wrapper-home';wrapper_tmp=directory/'wrapper-tmp'

        wrapper_home.mkdir();wrapper_tmp.mkdir()

        arguments=['/usr/bin/systemd-run','--user','--unit='+unit,'--wait','--pipe',

                   '--property=KillMode=control-group','--property=RuntimeMaxSec='+str(whole_limit-4)+'s',

                   '--property=Type=exec','--property=TimeoutStartSec=2s',

                   '--property=TimeoutStopSec=1s','--property=KillSignal=SIGKILL',

                   '--property=CPUQuota=600%','--property=MemoryMax=2G','--property=TasksMax=256',

                   '--working-directory='+str(directory),'--setenv=HOME='+str(wrapper_home),

                   '--setenv=TMPDIR='+str(wrapper_tmp),'--setenv=LP_NUM_THREADS=4','--setenv=PYTHONDONTWRITEBYTECODE=1',

                   '/usr/bin/python3','-I','-B',str(script),'--phase-worker']

        expected_argv=['/usr/bin/python3','-I','-B',str(script),'--phase-worker']

        if options.cleanup_control:

            arguments=arguments[:-1]+['--cleanup-control',options.cleanup_control]

            expected_argv=expected_argv[:-1]+['--cleanup-control',options.cleanup_control]

            arguments=[arg.replace('RuntimeMaxSec=56s','RuntimeMaxSec=3s') for arg in arguments]

        expected={'argv':expected_argv,'executable':str(Path('/usr/bin/python3').resolve(strict=True)),

                  'executable_sha256':digest(Path('/usr/bin/python3').resolve(strict=True)),'cgroup':None}

        client=subprocess.Popen(arguments,stdin=subprocess.DEVNULL if options.cleanup_control else subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

        sent=0

        os.set_blocking(client.stdout.fileno(),False)

        if client.stdin:

            os.set_blocking(client.stdin.fileno(),False);selector.register(client.stdin,selectors.EVENT_WRITE)

        selector.register(client.stdout,selectors.EVENT_READ)

        while selector.get_map():

            if time.monotonic()>=started+whole_limit-3:raise ValueError('Selected work/cleanup-report observation deadline')

            facts=properties(unit,min(started+whole_limit-3,time.monotonic()+.45))

            if facts['LoadState']=='loaded' and startup is not None:

                if facts['InvocationID']!=startup['invocation']:raise ValueError('Actual startup invocation changed')

                if expected['cgroup'] is None:

                    group=facts['ControlGroup'] or startup['process']['cgroup']

                    if not re.fullmatch(r'/user.slice/user-1000.slice/user@1000.service/(?:[A-Za-z0-9_.@:-]+/)*'+re.escape(unit),group):

                        raise ValueError('Exact own user-manager cgroup required')

                    expected['cgroup']=group

                facts,observed=bound_observation(unit,expected,startup,identity,min(started+whole_limit-3,time.monotonic()+.45))

                if observed is None:continue

                identity=observed

                identity['unit']=unit;observations.append(identity['mutable_observation'])

            elif facts['LoadState'] not in ('loaded','not-found'):raise ValueError('Unknown unit state')

            for key,event in selector.select(.02):

                if key.fileobj is client.stdin:

                    try:count=os.write(key.fileobj.fileno(),payload[sent:])

                    except BlockingIOError:continue

                    if count<=0:raise ValueError('Private worker input closed')

                    sent+=count

                    if sent==len(payload):selector.unregister(client.stdin);client.stdin.close()

                    continue

                data=os.read(key.fileobj.fileno(),8192)

                if not data:selector.unregister(key.fileobj);break

                output.extend(data);pending+=data

                while b'\n' in pending:

                    row,pending=pending.split(b'\n',1)

                    try:message=json.loads(row)

                    except json.JSONDecodeError:continue

                    if isinstance(message,dict) and message.get('white_control_startup28') is True:

                        if startup is not None or set(message)!={'white_control_startup28','invocation','process'}:

                            raise ValueError('Exact once actual startup receipt required')

                        startup=message

                if len(pending)>16384:raise ValueError('Bounded startup observation exceeded')

                if len(output)>65536:raise ValueError('Bounded wrapper output exceeded')

        if identity is None:

            if startup is None:raise ValueError('Source-issued actual startup snapshot missing')

            facts=properties(unit,min(started+whole_limit-3,time.monotonic()+.45))

            if facts['LoadState']!='loaded':raise ValueError('Unobserved early completion has no manager history')

            if facts['InvocationID']!=startup['invocation']:raise ValueError('Startup invocation mismatch')

            expected['cgroup']=facts['ControlGroup'] or startup['process']['cgroup']

            if not re.fullmatch(r'/user.slice/user-1000.slice/user@1000.service/(?:[A-Za-z0-9_.@:-]+/)*'+re.escape(unit),expected['cgroup']):

                raise ValueError('Exact historical unit cgroup required')

            facts,identity=bound_observation(unit,expected,startup,None,min(started+whole_limit-3,time.monotonic()+.45))

            if identity is None:raise ValueError('Unobserved completion lacks retained manager identity')

            identity['unit']=unit;observations.append(identity['mutable_observation'])

    except Exception as exc:error=str(exc)

    finally:

        # User manager survives abrupt script/client death. Never signal a unit

        # unless its actual invocation/source was captured as our new invocation.

        if identity:

            try:

                facts=properties(unit,min(started+whole_limit-3,time.monotonic()+.45))

                if facts['LoadState']=='loaded':

                    facts,current=bound_observation(unit,expected,startup,identity,min(started+whole_limit-3,time.monotonic()+.45))

                    if current:observations.append(current['mutable_observation'])

                    try:command(['/usr/bin/systemctl','--user','stop',unit],started+whole_limit-2)

                    except Exception as exc:observations.append({'stop_client_error':str(exc),'kernel_retirement_still_required':True})

                elif facts['LoadState']!='not-found':raise ValueError('Unknown unit state')

                while True:

                    try:retirement=cgroup_empty(identity['cgroup']);break

                    except ValueError as exc:

                        if 'descendants still present' not in str(exc) or time.monotonic()>=started+whole_limit-2:raise

                        time.sleep(.01)

            except Exception as exc:cleanup.append(str(exc))

        if client:

            try:

                if client.poll() is None:client.kill()

                returncode=client.wait(timeout=max(.001,min(.3,started+whole_limit-1-time.monotonic())))

            except Exception as exc:cleanup.append(str(exc))

            for stream in (client.stdin,client.stdout):

                if stream:stream.close()

        selector.close()

    if retirement is None or cleanup:error=error or 'Whole user containment retirement unconfirmed; no acceptance'

    worker=None;control_proof=None

    try:

        answers=[];children=[]

        for row in output.decode('utf8','strict').splitlines():

            try:message=json.loads(row)

            except json.JSONDecodeError:continue

            if isinstance(message,dict) and set(message)=={'ok','result','error'}:answers.append(message)

            if isinstance(message,dict) and message.get('cleanup_child29') is True:children.append(message)

        if options.cleanup_control:

            if len(children)!=1 or returncode in (None,0) or not retirement:raise ValueError('Actual abnormal child and unit cleanup required')

            child=children[0]

            if type(child.get('group')) is not int or child['group']!=child.get('pid') or not str(child.get('birth','')).isdecimal():raise ValueError('Actual child birth/group required')

            while True:

                try:os.killpg(child['group'],0)

                except ProcessLookupError:break

                if time.monotonic()>=started+whole_limit-2:raise ValueError('Own control child group remains')

                time.sleep(.01)

            control_proof={'scenario':options.cleanup_control,'actual_child':child,'group_ESRCH':True,'retirement':retirement}

        else:

            if len(answers)!=1:raise ValueError('Exactly one private worker result required')

            worker=answers[0]

            if worker['ok'] is not True or worker['error'] is not None:raise ValueError('Worker phase failed: '+str(worker['error']))

    except Exception as exc:error=error or str(exc)

    result={'schema':1,'engine_free':bool(options.cleanup_control),'native_development_test':not bool(options.cleanup_control),'direct_coordination1195':True,

            'uid':os.getuid(),'elapsed':time.monotonic()-started,'whole_limit':whole_limit,'cutoff':whole_limit-2,'error':error,

            'cleanup_errors':cleanup,'client_returncode':returncode,'unit_identity':identity,'mutable_unit_observations':observations,'actual_startup':startup,'containment_retirement':retirement,

            'controls_stdout':output.decode('utf8','replace'),'worker':worker,'cleanup_control':control_proof,'accepted':False,'gameplay_accepted':False}

    result_path.write_text(json.dumps(result,indent=2)+'\n')

    if time.monotonic()-started>=whole_limit:raise ValueError('Whole reporting deadline exceeded')

    print(json.dumps(result),flush=True)

    return 0 if error is None and (control_proof is not None if options.cleanup_control else returncode==0) else 1



if __name__=='__main__':raise SystemExit(main())

