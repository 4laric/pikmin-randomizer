"""Fixed Linux cave phase admission and ordinary X11 modal confirmation.

Output-only review candidate. A deployed fixed runtime recipe is required.
The unchanged common supervisor retains its raw exit and passed fields.
"""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import threading
import time

from scripts.fixture_platform import linux_admission, runtime_evidence

ROOT = Path(__file__).resolve().parents[1]
SUITE = 'cave-route-sdl-runtime'
TARGET = 'pikmin_ci_fixture_cave_route'
SOURCE = 'tools/p2_cave_route_runtime.cpp'
GUARD_SHA = 'ee2bfeaba96020f4f0ae310f9cf98dfabbd824353d20de6fb78fec17001f3ff9'
PREFIX = 'P2_CAVE_NATIVE_DIALOG '
ENV_KEYS = ('P2_CAVE_ROUTE_FULL_PARTY', 'P2_CAVE_ROUTE_ACQUIRE', 'P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN')
LABELS = {'enter': 'Enter cave', 'descend': 'Descend', 'leave': 'Leave cave'}
PHASES = ('surface', 'acquisition', 'floor1', 'floor2', 'guard')
MATRIX = {'surface': ('enter', 'White Flower Garden', 'forest_2/f_02', 0),
          'acquisition': ('leave', 'White Flower Garden', 'forest_2', 1),
          'floor1': ('descend', 'Emergence Cave', 'forest_1', 1),
          'floor2': ('leave', 'Emergence Cave', 'forest_1', 2)}
SETTINGS = b'debugKeys=0\nwindowWidth=960\nwindowHeight=540\ndisplayMode=0\n'
MAPPED_ENV = {'PIKMIN_RANDOMIZER_TEST_BACKGROUND': '1', 'PIKMIN_RANDOMIZER_TEST_VISIBLE': '1', 'SDL_VIDEODRIVER': 'x11'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def phase_environment(env, phase, fresh_acquisition=False, guard_negative=False):
    if phase not in PHASES or guard_negative != (phase == 'guard'):
        raise ValueError('Unsupported fixed cave phase')
    if fresh_acquisition and phase != 'acquisition':
        raise ValueError('Fresh acquisition outside WFG phase')
    result = {k: v for k, v in env.items() if k not in ENV_KEYS}
    if guard_negative:
        result['P2_CAVE_ROUTE_FORCE_CAPTAIN_DOWN'] = '1'
    else:
        result['P2_CAVE_ROUTE_FULL_PARTY'] = '1'
        if fresh_acquisition:
            result['P2_CAVE_ROUTE_ACQUIRE'] = '1'
    return result


def recipe_admission(exe, root, session, run):
    """A package preflight proves job authority, never a launched native phase."""
    if sys.platform != 'linux':
        raise ValueError('Linux fixed recipe required')
    paths = [Path(p).absolute() for p in (exe, root, session, run)]
    for path in paths:
        if path.is_symlink() or path.resolve(strict=True) != path:
            raise ValueError('Redirected cave input path')
    exe, root, session, run = paths
    if root != ROOT.resolve(strict=True) or not session.is_relative_to(root / 'output') or not run.is_relative_to(session):
        raise ValueError('Foreign pinned cave session')
    if exe != run / 'nectar.exe':
        raise ValueError('Cave executable must be the exact private run copy')
    proof = linux_admission(exe, root, session, run)
    if (proof['pins']['FIXTURE_SUITE'] != SUITE or proof['target'] != TARGET or proof['source'] != SOURCE
            or proof['guard_sha256'] != GUARD_SHA):
        raise ValueError('Compile-only or foreign recipe cannot authorize cave runtime')
    if any(proof['pins'][key] != os.environ.get(key) for key in proof['pins']):
        raise ValueError('Controller source pins differ from the owned phase')
    job = Path(proof['job']).resolve(strict=True)
    if root != job / 'root':
        raise ValueError('Controller job/root mismatch')
    built = job / 'build' / 'fixtures' / TARGET
    if built.is_symlink() or not built.is_file() or digest(built) != proof['exe_sha256'] or digest(exe) != proof['exe_sha256']:
        raise ValueError('Private ELF differs from selected immutable build')
    evidence = runtime_evidence(exe, env=dict(os.environ), include_sdl=False, cwd=run)
    if evidence['executable']['sha256'] != proof['exe_sha256']:
        raise ValueError('ELF changed after broker admission')
    return proof


def native_context(record, proof, exe, run):
    """Bind the log PID to this common supervisor's actual owned native child."""
    pid = record.get('pid')
    if type(pid) is not int or pid <= 1:
        raise ValueError('Invalid native dialog PID')
    proc = Path('/proc') / str(pid)
    fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    if fields[0] == 'Z' or int(fields[1]) != os.getpid() or int(fields[2]) != pid or int(fields[3]) != pid:
        raise ValueError('Dialog PID is not this supervisor owned process group')
    if (proc / 'exe').resolve(strict=True) != exe or (proc / 'cwd').resolve(strict=True) != run:
        raise ValueError('Native dialog executable/cwd mismatch')
    groups = [line.split(':', 2)[2] for line in (proc / 'cgroup').read_text().splitlines() if line.startswith('0::')]
    if groups != [proof['cgroup']] or digest(exe) != proof['exe_sha256']:
        raise ValueError('Native dialog left its admitted cgroup/source')
    environ = dict(pair.split('=', 1) for pair in (proc / 'environ').read_bytes().decode().split('\0') if '=' in pair)
    if environ.get('DISPLAY') != os.environ.get('DISPLAY'):
        raise ValueError('Native dialog uses a foreign display')
    return (pid, fields[19])


def modal_owner_context(pid, native, proof, exe, run):
    """XRes server ownership, corroborated against the native SDL fork child."""
    if type(pid) is not int or pid <= 1:
        raise ValueError('Modal lacks server-observed local owner PID')
    if pid == native[0]:
        record = {'pid': pid}
        if native_context(record, proof, exe, run) != native:
            raise ValueError('Modal native owner PID reused')
        return native
    proc = Path('/proc') / str(pid)
    fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    if fields[0] == 'Z' or int(fields[1]) != native[0] or int(fields[2]) != native[0] or int(fields[3]) != native[0]:
        raise ValueError('Modal resource owner is not the native SDL child')
    if (proc / 'exe').resolve(strict=True) != exe or (proc / 'cwd').resolve(strict=True) != run:
        raise ValueError('Modal child executable/cwd mismatch')
    if [line.split(':', 2)[2] for line in (proc / 'cgroup').read_text().splitlines() if line.startswith('0::')] != [proof['cgroup']]:
        raise ValueError('Modal child left admitted cgroup')
    env = dict(pair.split('=', 1) for pair in (proc / 'environ').read_bytes().decode().split('\0') if '=' in pair)
    if env.get('DISPLAY') != os.environ.get('DISPLAY'):
        raise ValueError('Modal resource owner uses a foreign display')
    return (pid, fields[19])


def validate_launch_environment(env, phase, run, token):
    if phase == 'guard':
        if env.get(ENV_KEYS[2]) != '1' or any(key in env for key in ENV_KEYS[:2]):
            raise ValueError('Guard requires isolated negative phase switches')
        return
    if env.get(ENV_KEYS[0]) != '1' or ENV_KEYS[2] in env:
        raise ValueError('Normal phase requires full party and no forced captain down')
    if phase != 'acquisition':
        if ENV_KEYS[1] in env:raise ValueError('Acquisition switch outside fresh WFG phase')
        return
    # The controller also validates the complete Route proof chain. This
    # launch gate independently binds the switch to the actual pending journal.
    run = Path(run)
    session = run.parent.parent if run.parent.name == 'runs' else run.parent.parent.parent
    state = json.loads((session / 'route-state.json').read_text())
    pending = json.loads((session / 'route-pending.json').read_text())
    if (state.get('phase') != 'acquisition' or type(state.get('visit')) is not int or state['visit']<1
            or pending.get('run') != str(run) or pending.get('token') != token
            or pending.get('phase') != 'acquisition' or pending.get('revision') != state.get('revision')):
        raise ValueError('WFG launch lacks matching actual pending state')
    if state['visit']==1:
        if (state.get('wfg_white_boundary') is not None or state.get('entry',{}).get('health')!=1
                or state.get('entry',{}).get('squad')!=[[1,0]]*20 or env.get(ENV_KEYS[1])!='1'):
            raise ValueError('Fresh WFG requires ACQUIRE1 and actual 20 Red Leaf state')
    elif ENV_KEYS[1] in env:
        raise ValueError('Reentry must preserve party without acquisition switch')


def validate_mapped_runtime(env, run):
    if any(env.get(key)!=value for key,value in MAPPED_ENV.items()):
        raise ValueError('Fixed private Xvfb phase requires mapped background X11 window')
    settings=Path(run)/'pikmin_settings.conf'
    if settings.is_symlink() or not settings.is_file() or settings.read_bytes()!=SETTINGS:
        raise ValueError('Native startup settings differ from fixed 960x540 debugKeys0 policy')


def validate_begin(record, *, phase, token, action, title, ready):
    expected_phase = 'surface' if phase == 'surface' else 'floor'
    if (record.get('event') != 'begin' or record.get('phase') != expected_phase or record.get('token') != token
            or record.get('action') != action or record.get('title') != title or not ready):
        raise ValueError('Unexpected or uncorrelated native dialog')
    if (action, title, record.get('cave'), record.get('floor')) != MATRIX.get(phase):
        raise ValueError('Native dialog differs from fixed cave/floor/action matrix')
    if type(record.get('sequence')) is not int or record['sequence'] <= 0:
        raise ValueError('Invalid native dialog sequence')
    if record.get('video_driver') != 'x11' or type(record.get('parent_x11_window')) is not int or record['parent_x11_window'] <= 0:
        raise ValueError('Native dialog lacks actual X11 parent identity')
    if record.get('buttons') != [
        {'id': 0, 'flags': 2, 'text': 'Stay', 'return_default': False, 'escape_default': True},
        {'id': 1, 'flags': 1, 'text': LABELS[action], 'return_default': True, 'escape_default': False},
    ]:
        raise ValueError('Unexpected actual SDL button/default metadata')
    # SDL2 has no disabled flag for SDL_MessageBoxButtonData. This checks actual
    # source-bound defaults; it never claims OCR/accessibility button evidence.
    if record.get('button_disabled_state_supported') is not False:
        raise ValueError('Unsupported SDL button-state evidence')


def matching_modal(windows, begin, baseline):
    parent = begin['parent_x11_window']
    parents = [w for w in windows if w['window'] == parent]
    if len(parents) != 1 or parents[0]['pid'] != begin['pid'] or parents[0].get('owner_pid') != begin['pid'] or not parents[0]['mapped']:
        raise ValueError('Actual mapped parent/PID mismatch')
    matches = [w for w in windows if w['transient_for'] == parent and w['dialog'] and w['modal'] and w['mapped']]
    if len(matches) > 1:
        raise ValueError('Ambiguous actual native modal')
    if not matches:
        return None
    modal = matches[0]
    if modal['window'] in baseline or modal['title'] != begin['title']:
        raise ValueError('Stale or mismatched actual native modal')
    if type(modal.get('owner_pid')) is not int or modal['owner_pid'] <= 1:
        raise ValueError('Actual modal lacks XRes resource owner PID')
    return modal


def validate_end(record, begin, pressed):
    if not pressed or record.get('event') != 'end' or any(record.get(k) != begin.get(k) for k in ('pid', 'sequence', 'phase', 'action', 'token', 'title', 'cave', 'floor')):
        raise ValueError('Dialog completion lacks correlated ordinary OS action')
    if record.get('rc') != 0 or record.get('choice') != 1 or record.get('known_button_selected') is not True or record.get('selected_label') != LABELS[begin['action']]:
        raise ValueError('Native confirmation cancelled/refused/changed')


def validate_provider_lineage(raw, context):
    if type(raw.get('pid')) is not int or type(raw.get('owned_process_group')) is not int or raw['pid']!=context[0] or raw['owned_process_group']!=context[0]:
        raise ValueError('Native dialog is not the common provider launched child')


class WindowAttributes(ctypes.Structure):
    _fields_ = [(n, ctypes.c_int) for n in ('x', 'y', 'width', 'height', 'border_width', 'depth')] + [
        ('visual', ctypes.c_void_p), ('root', ctypes.c_ulong)] + [
        (n, ctypes.c_int) for n in ('class_', 'bit_gravity', 'win_gravity', 'backing_store')] + [
        ('backing_planes', ctypes.c_ulong), ('backing_pixel', ctypes.c_ulong), ('save_under', ctypes.c_int),
        ('colormap', ctypes.c_ulong), ('map_installed', ctypes.c_int), ('map_state', ctypes.c_int),
        ('all_event_masks', ctypes.c_long), ('your_event_mask', ctypes.c_long), ('do_not_propagate_mask', ctypes.c_long),
        ('override_redirect', ctypes.c_int), ('screen', ctypes.c_void_p)]


class ClientIdSpec(ctypes.Structure):
    _fields_ = [('client', ctypes.c_ulong), ('mask', ctypes.c_uint)]


class ClientIdValue(ctypes.Structure):
    _fields_ = [('spec', ClientIdSpec), ('length', ctypes.c_long), ('value', ctypes.c_void_p)]


def trusted_library(name):
    path = Path('/usr/lib/x86_64-linux-gnu') / name
    resolved = path.resolve(strict=True)
    for entry in {*resolved.parents, resolved, *path.parents}:
        info = entry.stat()
        if info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError('Untrusted X11 runtime library')
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError('X11 runtime library is not a regular file')
    return resolved


class X11Input:
    """Only fixed Return press/release; no command/coordinate/key caller input."""
    def __init__(self):
        if not re.fullmatch(r':\d+(?:\.\d+)?', os.environ.get('DISPLAY', '')):
            raise ValueError('Fixed local Xvfb display required')
        self.libraries = {name: str(trusted_library(name)) for name in ('libX11.so.6', 'libXtst.so.6', 'libXRes.so.1')}
        self.library_hashes = {name: digest(path) for name, path in self.libraries.items()}
        self.x = ctypes.CDLL(self.libraries['libX11.so.6'])
        self.xt = ctypes.CDLL(self.libraries['libXtst.so.6'])
        self.xr = ctypes.CDLL(self.libraries['libXRes.so.1'])
        P = ctypes.c_void_p; U = ctypes.c_ulong; I = ctypes.c_int
        specs = {
            'XOpenDisplay': ([ctypes.c_char_p], P), 'XCloseDisplay': ([P], I), 'XDefaultRootWindow': ([P], U),
            'XInternAtom': ([P, ctypes.c_char_p, I], U), 'XFree': ([P], I),
            'XQueryTree': ([P,U,ctypes.POINTER(U),ctypes.POINTER(U),ctypes.POINTER(ctypes.POINTER(U)),ctypes.POINTER(ctypes.c_uint)],I),
            'XGetWindowAttributes': ([P,U,ctypes.POINTER(WindowAttributes)],I),
            'XGetTransientForHint': ([P,U,ctypes.POINTER(U)],I), 'XFetchName': ([P,U,ctypes.POINTER(P)],I),
            'XGetWindowProperty': ([P,U,U,ctypes.c_long,ctypes.c_long,I,U,ctypes.POINTER(U),ctypes.POINTER(I),ctypes.POINTER(U),ctypes.POINTER(U),ctypes.POINTER(P)],I),
            'XSetInputFocus': ([P,U,I,U],I), 'XGetInputFocus': ([P,ctypes.POINTER(U),ctypes.POINTER(I)],I),
            'XKeysymToKeycode': ([P,U],ctypes.c_ubyte), 'XSync': ([P,I],I),
        }
        for name,(args,result) in specs.items():
            getattr(self.x,name).argtypes=args;getattr(self.x,name).restype=result
        self.xt.XTestQueryExtension.argtypes=[P,ctypes.POINTER(I),ctypes.POINTER(I),ctypes.POINTER(I),ctypes.POINTER(I)]
        self.xt.XTestQueryExtension.restype=I
        self.xt.XTestFakeKeyEvent.argtypes=[P,ctypes.c_uint,I,U];self.xt.XTestFakeKeyEvent.restype=I
        self.xr.XResQueryVersion.argtypes=[P,ctypes.POINTER(I),ctypes.POINTER(I)];self.xr.XResQueryVersion.restype=I
        self.xr.XResQueryClientIds.argtypes=[P,ctypes.c_long,ctypes.POINTER(ClientIdSpec),ctypes.POINTER(ctypes.c_long),ctypes.POINTER(ctypes.POINTER(ClientIdValue))]
        self.xr.XResQueryClientIds.restype=I
        self.xr.XResGetClientPid.argtypes=[ctypes.POINTER(ClientIdValue)];self.xr.XResGetClientPid.restype=I
        self.xr.XResClientIdsDestroy.argtypes=[ctypes.c_long,ctypes.POINTER(ClientIdValue)];self.xr.XResClientIdsDestroy.restype=None
        self.display=self.x.XOpenDisplay(None)
        if not self.display:
            raise ValueError('Cannot open fixed native X11 display')
        bases=[I() for _ in range(4)]
        if not self.xt.XTestQueryExtension(self.display,*[ctypes.byref(v) for v in bases]):
            self.close();raise ValueError('Ordinary XTest input extension unavailable')
        major=I();minor=I()
        if not self.xr.XResQueryVersion(self.display,ctypes.byref(major),ctypes.byref(minor)) or (major.value,minor.value)<(1,2):
            self.close();raise ValueError('XRes1.2 server-observed client ownership required')

    def close(self):
        if getattr(self,'display',None):self.x.XCloseDisplay(self.display);self.display=None

    def atom(self,name):return self.x.XInternAtom(self.display,name.encode('ascii'),False)

    def owner_pid(self,window):
        spec=ClientIdSpec(window,2);count=ctypes.c_long();values=ctypes.POINTER(ClientIdValue)()
        # Unlike QueryVersion, QueryClientIds returns X11 Success (zero).
        if self.xr.XResQueryClientIds(self.display,1,ctypes.byref(spec),ctypes.byref(count),ctypes.byref(values)) != 0:
            raise ValueError('XRes client ownership query failed')
        try:
            if count.value != 1 or not values:return None
            pid=self.xr.XResGetClientPid(ctypes.byref(values[0]))
            return pid if pid>1 else None
        finally:
            if values:self.xr.XResClientIdsDestroy(count.value,values)

    def property(self,window,name):
        U=ctypes.c_ulong;actual=U();fmt=ctypes.c_int();count=U();after=U();data=ctypes.c_void_p()
        if self.x.XGetWindowProperty(self.display,window,self.atom(name),0,64,False,0,ctypes.byref(actual),ctypes.byref(fmt),ctypes.byref(count),ctypes.byref(after),ctypes.byref(data))!=0:
            raise ValueError('X11 property query failed')
        try:
            if not data.value:return []
            if fmt.value!=32 or count.value>64 or after.value:return []
            return list(ctypes.cast(data,ctypes.POINTER(U))[:count.value])
        finally:
            if data.value:self.x.XFree(data)

    def title_property(self,window,name,encodings):
        # Bound the server read to 4096 bytes and require the entire 8-bit
        # property. XFetchName cannot decode SDL's observed WM_NAME UTF-8 atom.
        U=ctypes.c_ulong;actual=U();fmt=ctypes.c_int();count=U();after=U();data=ctypes.c_void_p()
        rc=self.x.XGetWindowProperty(self.display,window,self.atom(name),0,1024,False,0,ctypes.byref(actual),ctypes.byref(fmt),ctypes.byref(count),ctypes.byref(after),ctypes.byref(data))
        try:
            if rc!=0:raise ValueError('X11 title property query failed')
            if actual.value==0:
                if fmt.value or count.value or after.value:raise ValueError('Malformed absent X11 title property')
                return None
            encoding=next(((atom,codec) for atom,codec in encodings if actual.value==self.atom(atom)),None)
            if encoding is None or fmt.value!=8 or count.value>4096 or after.value or (count.value and not data.value):
                raise ValueError('Unsupported or truncated X11 title property: '+name)
            raw=ctypes.string_at(data.value,count.value) if count.value else b''
            if b'\0' in raw:raise ValueError('Embedded NUL in X11 title property')
            return raw.decode(encoding[1],errors='strict'),encoding[0]
        finally:
            if data.value:self.x.XFree(data)

    def window_title(self,window):
        title=self.title_property(window,'_NET_WM_NAME',[('UTF8_STRING','utf-8')])
        if title is not None:return title[0],'_NET_WM_NAME',title[1]
        title=self.title_property(window,'WM_NAME',[('STRING','latin-1'),('UTF8_STRING','utf-8'),('UTF-8','utf-8')])
        return (title[0],'WM_NAME',title[1]) if title is not None else ('','absent','absent')

    def windows(self):
        U=ctypes.c_ulong;root=U();parent=U();children=ctypes.POINTER(U)();count=ctypes.c_uint()
        if not self.x.XQueryTree(self.display,self.x.XDefaultRootWindow(self.display),ctypes.byref(root),ctypes.byref(parent),ctypes.byref(children),ctypes.byref(count)) or count.value>4096:
            raise ValueError('Cannot enumerate bounded X11 root windows')
        try:ids=list(children[:count.value])
        finally:
            if children:self.x.XFree(children)
        result=[]
        for window in ids:
            attrs=WindowAttributes()
            if not self.x.XGetWindowAttributes(self.display,window,ctypes.byref(attrs)):continue
            transient=U();self.x.XGetTransientForHint(self.display,window,ctypes.byref(transient))
            text,title_source,title_encoding=self.window_title(window)
            pids=self.property(window,'_NET_WM_PID')
            result.append(dict(window=window,title=text,title_source=title_source,title_encoding=title_encoding,transient_for=transient.value,pid=pids[0] if len(pids)==1 else None,owner_pid=self.owner_pid(window),
                mapped=attrs.map_state==2,dialog=self.atom('_NET_WM_WINDOW_TYPE_DIALOG') in self.property(window,'_NET_WM_WINDOW_TYPE'),
                modal=self.atom('_NET_WM_STATE_MODAL') in self.property(window,'_NET_WM_STATE')))
        return result

    def press_return(self,window):
        self.x.XSetInputFocus(self.display,window,2,0);self.x.XSync(self.display,False)
        focus=ctypes.c_ulong();revert=ctypes.c_int();self.x.XGetInputFocus(self.display,ctypes.byref(focus),ctypes.byref(revert))
        if focus.value!=window:raise ValueError('Actual modal did not receive OS focus')
        key=self.x.XKeysymToKeycode(self.display,0xff0d)
        if not key:raise ValueError('Return key not mapped')
        if not self.xt.XTestFakeKeyEvent(self.display,key,True,0):raise ValueError('OS Return press failed')
        try:self.x.XSync(self.display,False)
        finally:
            if not self.xt.XTestFakeKeyEvent(self.display,key,False,0):raise ValueError('OS Return release failed')
            self.x.XSync(self.display,False)


class DialogObserver:
    def __init__(self, backend, proof, exe, run, phase, token, action, title):
        self.backend=backend;self.proof=proof;self.exe=exe;self.run=run
        self.phase=phase;self.token=token;self.action=action;self.title=title
        self.baseline={w['window'] for w in backend.windows() if w['mapped'] and w['modal']}
        if self.baseline:raise ValueError('Foreign/stale modal exists before fresh native launch')
        self.begin=None;self.context=None;self.ready=False;self.pressed=False;self.ended=False;self.events=[]

    def line(self,line):
        ready_prefix='P2_CAVE_SURFACE_READY ' if self.phase=='surface' else 'P2_CAVE_ROUTE_FLOOR_READY '
        if line.startswith(ready_prefix):
            match=re.search(r'\btoken=([0-9a-f]{32})(?:\s|$)',line)
            if not match or match.group(1)!=self.token:raise ValueError('Foreign native ready token')
            self.ready=True
        if not line.startswith(PREFIX):return
        record=json.loads(line[len(PREFIX):])
        if record.get('event')=='begin':
            if self.begin is not None:raise ValueError('Duplicate native confirmation request')
            validate_begin(record,phase=self.phase,token=self.token,action=self.action,title=self.title,ready=self.ready)
            self.context=native_context(record,self.proof,self.exe,self.run);self.begin=record;self.events.append(record)
        elif record.get('event')=='end':
            if self.begin is None or self.ended:raise ValueError('Orphan/duplicate dialog completion')
            validate_end(record,self.begin,self.pressed);self.ended=True;self.events.append(record)
        else:raise ValueError('Unknown native dialog evidence')

    def tick(self):
        if self.begin is None or self.pressed or self.ended:return
        if native_context(self.begin,self.proof,self.exe,self.run)!=self.context:raise ValueError('Native PID reused before OS confirmation')
        modal=matching_modal(self.backend.windows(),self.begin,self.baseline)
        if modal is None:return
        # Corroborate a second observation immediately before the sole fixed key.
        if matching_modal(self.backend.windows(),self.begin,self.baseline)!=modal:raise ValueError('Actual modal changed before OS action')
        owner=modal_owner_context(modal['owner_pid'],self.context,self.proof,self.exe,self.run)
        # Recheck the resource owner and its start time before the sole key.
        if matching_modal(self.backend.windows(),self.begin,self.baseline)!=modal or modal_owner_context(modal['owner_pid'],self.context,self.proof,self.exe,self.run)!=owner:
            raise ValueError('Actual modal resource owner changed before OS action')
        self.backend.press_return(modal['window']);self.pressed=True
        self.events.append(dict(event='os-return',pid=self.context[0],native_start=self.context[1],window=modal['window'],
            parent=self.begin['parent_x11_window'],title=modal['title'],transient_for=modal['transient_for'],mapped=True,modal=True,
            resource_owner_pid=owner[0],resource_owner_start=owner[1]))


def _provider_launch(exe,run,args,marker,root,session):
    # Bare imports inside the unchanged provider resolve only this pinned scripts directory.
    sys.path.insert(0,str(ROOT/'scripts'))
    from run_pikmin2_fixture import launch
    return launch(exe,run,args,[marker],60,canonical_root=root,session_root=session)


def launch_linux_fixture(exe,run,args,marker,root,session,phase,token,action,title):
    exe,run,root,session=(Path(p).resolve(strict=True) for p in (exe,run,root,session))
    if phase not in PHASES or not re.fullmatch('[0-9a-f]{32}',token):raise ValueError('Invalid fixed phase/token')
    expected_args=['--experimental-pikmin2-surface','tutorial'] if phase in ('surface','guard') else ['--experimental-pikmin2-room']
    if list(args)!=expected_args:raise ValueError('Unexpected native arguments for fixed phase')
    if phase!='guard' and (action not in LABELS or title not in ('White Flower Garden','Emergence Cave')):raise ValueError('Unexpected fixed confirmation')
    if phase!='guard' and (action,title)!=MATRIX[phase][:2]:raise ValueError('Wrong fixed phase confirmation')
    validate_launch_environment(dict(os.environ),phase,run,token)
    validate_mapped_runtime(dict(os.environ),run)
    proof=recipe_admission(exe,root,session,run)
    receipt=run/'cave-linux-runtime-result.json'
    if receipt.exists():raise ValueError('Preserve existing Linux cave receipt')
    record=dict(schema=1,phase=phase,token=token,run=str(run),exe=str(exe),source_sha256=proof['pins']['FIXTURE_SOURCE_SHA256'],
        linux_route_phase_accepted=False,gameplay_accepted=False,dialogs=[])
    backend=None;observer=None;stop=threading.Event();errors=[];thread=None;raw=None
    def observe():
        consumed=0;partial=b'';deadline=time.monotonic()+60
        try:
            while not stop.is_set():
                if time.monotonic()>deadline:raise ValueError('Native modal observation exceeded phase bound')
                path=run/'native.log'
                if path.exists():
                    size=path.stat().st_size
                    if size<consumed or size>32*1024*1024:raise ValueError('Native evidence log reset/too large')
                    with path.open('rb') as stream:stream.seek(consumed);chunk=stream.read();consumed+=len(chunk)
                    lines=(partial+chunk).split(b'\n');partial=lines.pop()
                    for line in lines:observer.line(line.decode('utf-8',errors='replace'))
                    observer.tick()
                stop.wait(.02)
            # Completion may be logged immediately before provider exit; drain once more.
            if (run/'native.log').exists():
                with (run/'native.log').open('rb') as stream:stream.seek(consumed);chunk=stream.read()
                for line in (partial+chunk).splitlines():observer.line(line.decode('utf-8',errors='replace'))
        except BaseException as error:errors.append(str(error))
    try:
        if phase!='guard':
            backend=X11Input();observer=DialogObserver(backend,proof,exe,run,phase,token,action,title)
            record['x11_libraries_sha256']=backend.library_hashes
            thread=threading.Thread(target=observe,daemon=True);thread.start()
        raw=_provider_launch(exe,run,args,marker,root,session)
        stop.set()
        if thread:thread.join(timeout=2)
        if thread and thread.is_alive():raise ValueError('Native dialog observer did not stop')
        if errors:raise ValueError(errors[0])
        text=(run/'native.log').read_text()
        if raw.get('timed_out') or raw.get('elapsed_seconds',61)>60:raise ValueError('Native phase timed out')
        if phase=='guard':
            if raw.get('exit_code')!=86 or not raw.get('captain_down') or 'P2_CAVE_ROUTE_NEGATIVE_INITIALIZED ' not in text or 'PASS' in text or PREFIX in text:
                raise ValueError('Initialized captain-down guard did not refuse before actions')
            if any((run/p).exists() for p in ('p2-cave-transfer.txt','p2-cave-surface-transfer.txt')):raise ValueError('Guard emitted an unexpected boundary')
        else:
            if raw.get('exit_code')!=42 or raw.get('captain_down') or not observer.ended or not observer.pressed:raise ValueError('Actual native/OS confirmation phase failed')
            validate_provider_lineage(raw,observer.context)
        record['linux_route_phase_accepted']=True
        return dict(raw,linux_route_phase_accepted=True)
    except BaseException as error:
        record['error']=str(error)
        raise
    finally:
        stop.set()
        if thread:thread.join(timeout=2)
        if observer:record['dialogs']=observer.events
        # Xlib calls belong to the observer thread while it is alive. Never
        # close its display concurrently; a stuck observer refuses acceptance
        # and the fixed wrapper exits after writing this failure receipt.
        if backend and (thread is None or not thread.is_alive()):backend.close()
        if (run/'admission.json').exists():record['admission_sha256']=digest(run/'admission.json')
        if (run/'run-result.json').exists():record['raw_result_sha256']=digest(run/'run-result.json')
        receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
