"""Bounded Linux production checkpoint with ordinary XTest controls on its own display.

Requires the frozen resume39 input package and reviewed OwnedX11Keys helper.
Only keyboard input and framebuffer reads touch the running game.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def screenshot(keys, target):
    import ctypes as c
    import struct
    import zlib
    keys.verify()
    class XImage(c.Structure):
        _fields_ = [('width', c.c_int), ('height', c.c_int), ('xoffset', c.c_int),
                    ('format', c.c_int), ('data', c.c_void_p), ('byte_order', c.c_int),
                    ('bitmap_unit', c.c_int), ('bitmap_bit_order', c.c_int),
                    ('bitmap_pad', c.c_int), ('depth', c.c_int), ('bytes_per_line', c.c_int),
                    ('bits_per_pixel', c.c_int), ('red_mask', c.c_ulong),
                    ('green_mask', c.c_ulong), ('blue_mask', c.c_ulong)]
    keys.x.XGetImage.argtypes = [c.c_void_p,c.c_ulong,c.c_int,c.c_int,c.c_uint,c.c_uint,c.c_ulong,c.c_int]
    keys.x.XGetImage.restype = c.POINTER(XImage)
    keys.x.XDestroyImage.argtypes = [c.POINTER(XImage)]
    picture = keys.x.XGetImage(keys.handle, keys.window, 0, 0, 960, 540, c.c_ulong(-1), 2)
    if not picture:
        raise ValueError('Owned framebuffer capture failed')
    try:
        p = picture.contents
        if (p.bits_per_pixel,p.byte_order,p.red_mask,p.green_mask,p.blue_mask) != (32,0,0xff0000,0xff00,0xff):
            raise ValueError('Unsupported framebuffer pixel layout')
        raw = c.string_at(p.data,p.bytes_per_line*p.height)
        rows = bytearray()
        for y in range(p.height):
            rows.append(0)
            row = raw[y*p.bytes_per_line:y*p.bytes_per_line+4*p.width]
            for x in range(0,len(row),4):
                rows.extend((row[x+2],row[x+1],row[x],255))
        def chunk(kind,data):
            return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data))
        png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',p.width,p.height,8,6,0,0,0))
        png += chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
        target.write_bytes(png)
    finally:
        keys.x.XDestroyImage(picture)


def helper(args):
    sys.path.insert(0,str(args.host_root))
    runtime = load(args.host_root/'scripts/run_p2_white_bank_campaign.py','owned_controls')
    class Controls(runtime.OwnedX11Keys):
        SYMBOLS = {'UP':0xff52,'ENTER':0xff0d,'SPACE':0x20,'X':ord('x'),
                   'W':ord('w'),'A':ord('a'),'S':ord('s'),'D':ord('d')}
    keys = Controls(native_pid=args.native_pid,xvfb_pid=args.xvfb_pid,display=args.display,
                    executable_sha256=args.exe_sha256,deadline=args.deadline,
                    clock=time.monotonic,supervisor_pid=os.getppid())
    evidence = []
    try:
        def press(key,seconds):
            keys.key(key,True)
            try: time.sleep(seconds)
            finally: keys.key(key,False)
            time.sleep(.3)
            evidence.append(dict(key=key,held_seconds=seconds))
        screenshot(keys,args.work/'before.png')
        press('ENTER',.25)
        time.sleep(2)
        press('ENTER',.25)
        time.sleep(2)
        press('SPACE',.25)
        time.sleep(2)
        screenshot(keys,args.work/'after-intro.png')
        time.sleep(6)
        press('UP',.25)
        screenshot(keys,args.work/'switched.png')
        press('D',1.0)
        screenshot(keys,args.work/'moved.png')
        press('UP',.25)
        press('ENTER',.25)
        screenshot(keys,args.work/'paused.png')
        (args.work/'ordinary-inputs.json').write_text(json.dumps(evidence,indent=2)+'\n')
    finally:
        keys.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','exe','work','host-root'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--exe-sha256',required=True)
    parser.add_argument('--host-sha256',required=True)
    parser.add_argument('--helper',action='store_true')
    parser.add_argument('--native-pid',type=int)
    parser.add_argument('--xvfb-pid',type=int)
    parser.add_argument('--display')
    parser.add_argument('--deadline',type=float)
    args = parser.parse_args()
    for name in ('inputs','exe','work','host_root'):
        setattr(args,name,getattr(args,name).resolve())
    if sha(args.host_root/'scripts/run_p2_white_bank_campaign.py') != args.host_sha256:
        raise ValueError('Owned input helper differs from reviewed pin')
    if args.helper:
        return helper(args)
    if sys.platform != 'linux' or sha(args.exe) != args.exe_sha256:
        raise ValueError('Exact qualified Linux production executable required')
    args.work.mkdir(exist_ok=False,parents=True)
    package = args.work/'inputs'
    shutil.copytree(args.inputs,package,ignore=shutil.ignore_patterns('__pycache__'))
    for name,expected in json.loads((package/'input-sha256.json').read_text()).items():
        if sha(package/name) != expected:
            raise ValueError('Frozen input differs: '+name)
    sys.path.insert(0,str(package))
    runtime = load(package/'linux-production-resume39.py','checkpoint_package')
    from randomizer.session import Session, SessionLock
    from randomizer.runner import NativeRun
    runtime.overlay(Path('/srv/game-ci/assets/pikmin/pikmin1/assets'),args.work/'assets',
        {f.relative_to(package/'asset-overrides').as_posix():f.read_bytes()
         for f in (package/'asset-overrides').rglob('*') if f.is_file()})
    shutil.copytree(package/'starting-session',args.work/'session')
    campaign=args.work/'session/campaign'
    cards={f.relative_to(campaign).as_posix():sha(f) for f in campaign.rglob('*')
           if f.is_file() and 'shader_cache' not in f.relative_to(campaign).parts}
    binary = args.work/'nectar'
    shutil.copy2(args.exe,binary)
    if sha(binary) != args.exe_sha256:
        raise ValueError('Private executable copy differs')
    processes = []
    result = dict(executable_sha256=args.exe_sha256,ordinary_keyboard_only=True,
                  full_campaign_accepted=False,work=str(args.work))
    (args.work/'input-pins.json').write_text(json.dumps(dict(
        executable_sha256=args.exe_sha256,host_sha256=args.host_sha256,
        package_input_index_sha256=sha(package/'input-sha256.json'),cards=cards),indent=2)+'\n')
    started = time.monotonic()
    try:
        with SessionLock(args.work/'session'):
            session = Session(json.loads((package/'manifest.json').read_text()),args.work/'session')
            native = NativeRun(session);session.save();native.write_state(True)
            (native.directory/'assets').symlink_to(args.work/'assets',target_is_directory=True)
            for f in (package/'sidecars').glob('p2-*.txt'):shutil.copy2(f,native.directory/f.name)
            env = {k:v for k,v in os.environ.items() if not k.startswith(('PIKMIN_','P2_','NECTAR_','SDL_'))}
            env.pop('XAUTHORITY',None);env.pop('DISPLAY',None)
            for name in ('HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','TMPDIR'):
                directory=args.work/'environment'/name;directory.mkdir(parents=True);env[name]=str(directory)
            env.update(PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',PIKMIN_RANDOMIZER_TEST_VISIBLE='1',
                PIKMIN_P2_ROOM_WINDOW='960x540',SDL_AUDIODRIVER='dummy',
                NECTAR_SAVE_DIR=str(args.work/'session/campaign'))
            read,write=os.pipe()
            with (args.work/'xvfb.log').open('wb') as xlog:
                display_process=subprocess.Popen(['/usr/bin/Xvfb','-displayfd',str(write),'-screen','0','1280x720x24','-nolisten','tcp'],env=env,pass_fds=(write,),stdout=xlog,stderr=subprocess.STDOUT)
                processes.append(display_process);os.close(write)
                display=runtime_helper_display(read,time.monotonic()+3,args)
                os.close(read);env['DISPLAY']=display
            with (args.work/'native.log').open('wb') as log:
                game=subprocess.Popen([str(binary),'--randomizer-seed',str(native.bootstrap)],cwd=native.directory,env=env,stdout=log,stderr=subprocess.STDOUT)
                processes.append(game);result.update(pid=game.pid,display=display)
                helper_process=None
                while game.poll() is None and time.monotonic()-started<70:
                    native.poll();native.write_state(True)
                    text=(args.work/'native.log').read_text(errors='replace')
                    if helper_process is None and 'P2_CAMPAIGN_SCENE_READY floor=0 restored_party=1' in text:
                        argv=[sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--helper',
                              '--native-pid',str(game.pid),'--xvfb-pid',str(display_process.pid),
                              '--display',display,'--deadline',str(started+70)]
                        helper_process=subprocess.Popen(argv,env=env,stdout=subprocess.DEVNULL,stderr=(args.work/'helper.stderr').open('wb'))
                        processes.append(helper_process)
                    if helper_process is not None and helper_process.poll() is not None:
                        result['input_helper_exit']=helper_process.returncode
                        break
                    time.sleep(.1)
                result.update(handshake=native.handshaken,native_exit_before_stop=game.poll())
    finally:
        for process in reversed(processes):
            if process.poll() is None:process.terminate()
            try:process.wait(timeout=3)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
        text=(args.work/'native.log').read_text(errors='replace') if (args.work/'native.log').exists() else ''
        result.update(seconds=time.monotonic()-started,owned_children_reaped=all(p.poll() is not None for p in processes),
                      captain_switches=[line for line in text.splitlines() if line.startswith('P2_CAPTAIN_SWITCH ')],
                      restored_bodies=text.count('P2_CAMPAIGN_BODY_RESTORE key='),
                      extinction_tutorial='tu_tx20.blo' in text)
        result['cards_unchanged']=cards=={f.relative_to(campaign).as_posix():sha(f)
            for f in campaign.rglob('*') if f.is_file() and 'shader_cache' not in f.relative_to(campaign).parts}
        (args.work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    return 0 if (result.get('input_helper_exit') == 0 and result.get('handshake')
                 and result.get('native_exit_before_stop') is None
                 and len(result['captain_switches']) >= 2 and result['cards_unchanged']
                 and result['owned_children_reaped']) else 1


def runtime_helper_display(fd,deadline,args):
    sys.path.insert(0,str(args.host_root))
    runtime=load(args.host_root/'scripts/run_p2_white_bank_campaign.py','display_helper')
    return runtime.read_display_fd(fd,deadline=deadline)


if __name__ == '__main__':
    raise SystemExit(main())
