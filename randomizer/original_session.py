"""Explicit original P2 source sessions, independent of AP inventory and days."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import struct
import subprocess
import time
import importlib.util
import sys

from .session import SessionLock, atomic_write

COURSES = ('tutorial', 'forest', 'yakushima', 'last')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
MAX_DESCRIPTOR = 16 * 1024 * 1024
MAX_FILE = 128 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_identity(bundles, calendar):
    selected = {}
    for directory in bundles:
        directory = Path(directory).resolve(strict=True)
        receipt = json.loads((directory / 'surface-receipt.json').read_text(encoding='utf-8'))
        if receipt.get('schema') != 'p2-surface-source-1' or not isinstance(receipt.get('files'), dict) or not receipt['files']:
            raise ValueError('Unsupported or empty original surface receipt')
        actual = set()
        for file in directory.rglob('*'):
            if file.is_symlink() or file.is_junction():
                raise ValueError('Redirected original source bundle')
            if file.is_file():
                actual.add(file.relative_to(directory).as_posix())
        if actual != set(receipt['files']) | {'surface-receipt.json'}:
            raise ValueError('Original source bundle inventory changed')
        for name, record in receipt['files'].items():
            path = PurePosixPath(name)
            if path.is_absolute() or str(path) != name or any(part in ('.', '..') for part in path.parts) or re.fullmatch(r'[A-Za-z0-9_./-]+', name) is None:
                raise ValueError('Unsafe original source bundle path')
            data = (directory / name).read_bytes()
            if len(data) != record['size'] or sha(data) != record['sha256']:
                raise ValueError('Original source bundle member changed: ' + name)
        course = receipt['course']
        if course not in COURSES or course in selected:
            raise ValueError('Select exactly one verified bundle for each original course')
        # The source identity includes all original members, including schedules.
        selected[course] = receipt
    if set(selected) != set(COURSES):
        raise ValueError('Four verified original course bundles are required')
    calendar = Path(calendar).resolve(strict=True)
    receipt = json.loads((calendar / 'receipt.json').read_text(encoding='utf-8'))
    stages = (calendar / 'stages.txt').read_bytes()
    if (receipt.get('contract') != 'p2-original-calendar-source-v1' or receipt.get('member') != 'user/Abe/stages.txt'
            or len(stages) != receipt.get('size') or sha(stages) != receipt.get('sha256')):
        raise ValueError('Original calendar source changed or is unsupported')
    if any(bundle.get('disc') != receipt['disc'] for bundle in selected.values()):
        raise ValueError('Original generator bundles and calendar belong to different discs')
    from .original_calendar import course_schedule, validate_members
    for course, bundle in selected.items():
        schedule = course_schedule(stages.decode('cp932'), course)
        members = {name.removeprefix('generators/') for name in bundle['files'] if name.startswith('generators/') and name.endswith('.txt')}
        validate_members(schedule, members)
    canonical = json.dumps({'contract': 'original-p2-source-v2', 'courses': selected, 'calendar': receipt}, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return sha(canonical), canonical


def safe_path(name):
    if name in ('p2-treasure-placements.txt', 'p2-treasure-catalog.txt'):
        return True
    path = PurePosixPath(name)
    return (len(name) <= 512 and name.startswith(('assets/', 'p2-original/'))
            and not path.is_absolute() and str(path) == name
            and all(part not in ('.', '..') for part in path.parts)
            and re.fullmatch(r'[A-Za-z0-9_./-]+', name) is not None)


def manifest_campaign(data, magic):
    if not 45 <= len(data) <= 4 * 1024 * 1024 or data[:5] != magic or hashlib.sha256(data[:-32]).digest() != data[-32:]:
        raise ValueError('Damaged original manifest')
    offset = 5
    if magic == b'P2OC1':
        if struct.unpack_from('<I', data, offset)[0] != 64:
            raise ValueError('Invalid original campaign identity length')
        offset += 4
    campaign = data[offset:offset + 64].decode('ascii')
    if not DIGEST.fullmatch(campaign):
        raise ValueError('Invalid original manifest campaign')
    return campaign


def validate_prepared(prepared, bundles, calendar, native_source, campaign):
    """Compare typed manifests with the actual raw literal source translation."""
    bundles = tuple(bundles)
    if source_identity(bundles, calendar)[0] != campaign:
        raise ValueError('Literal source selection changed before translation')
    from .original_calendar import tree, stage_calendar
    tools = Path(native_source).resolve(strict=True) / 'tools'
    names = ('p2_original_source_inventory', 'p2_original_enemy_manifest', 'p2_original_piki_manifest')
    previous = {name: sys.modules.get(name) for name in names}
    modules = {}
    try:
        for name in names:
            spec = importlib.util.spec_from_file_location(name, tools / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
            spec.loader.exec_module(module)
            modules[name] = module
        courses = [modules[names[0]].inventory(bundle, tree, True) for bundle in bundles]
        courses.sort(key=lambda value: COURSES.index(value[0]))
        for course, members in courses:
            expected, _, _ = modules[names[1]].stage(members, course, campaign)
            if (Path(prepared) / 'p2-original' / (course + '.p2c')).read_bytes() != expected:
                raise ValueError('Prepared P2OC manifest differs from actual literal source: ' + course)
        expected, _, _ = modules[names[2]].stage(courses, campaign)
        if (Path(prepared) / 'p2-original/campaign.p2pk').read_bytes() != expected:
            raise ValueError('Prepared Piki atlas differs from actual all-calendar source')
        stages = (Path(calendar) / 'stages.txt').read_bytes()
        expected = stage_calendar(courses, stages, campaign)
        if (Path(prepared) / 'p2-original/calendar.p2sc').read_bytes() != expected or (Path(prepared) / 'p2-original/stages.txt').read_bytes() != stages:
            raise ValueError('Prepared native calendar differs from actual original declarations')
        if source_identity(bundles, calendar)[0] != campaign:
            raise ValueError('Literal source selection changed during translation')
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def descriptor(prepared, campaign):
    prepared = Path(prepared).resolve(strict=True)
    if not DIGEST.fullmatch(campaign):
        raise ValueError('Invalid verified source identity')
    for course in COURSES:
        data = (prepared / 'p2-original' / (course + '.p2c')).read_bytes()
        if manifest_campaign(data, b'P2OC1') != campaign:
            raise ValueError('P2OC source manifest does not match actual selected source campaign')
    if manifest_campaign((prepared / 'p2-original/campaign.p2pk').read_bytes(), b'P2PK1') != campaign:
        raise ValueError('Piki catalog belongs to a different original campaign')
    raw_stages = (prepared / 'p2-original/stages.txt').read_bytes()
    calendar = (prepared / 'p2-original/calendar.p2sc').read_bytes()
    fields = calendar.decode('ascii').split()
    if not raw_stages or len(raw_stages) > MAX_FILE or len(calendar) > 16 * 1024 * 1024 or fields[:4] != ['P2_SOURCE_CALENDAR', '1', campaign, sha(raw_stages)] or fields[-1:] != ['END']:
        raise ValueError('Original calendar is missing or belongs to different literal stages/source inputs')
    files = {}
    for prefix in ('assets', 'p2-original'):
        root = prepared / prefix
        if not root.is_dir():
            raise ValueError('Missing prepared original runtime directory')
        for file in root.rglob('*'):
            if not file.is_file():
                continue
            name = file.relative_to(prepared).as_posix()
            if not safe_path(name) or not file.resolve().is_relative_to(prepared):
                raise ValueError('Unsafe prepared runtime member')
            data = file.read_bytes()
            if not data or len(data) > MAX_FILE:
                raise ValueError('Prepared runtime file exceeds native verification bounds: ' + name)
            files[name] = sha(data)
    for name in ('p2-treasure-placements.txt', 'p2-treasure-catalog.txt'):
        if (prepared / name).exists():
            data = (prepared / name).read_bytes()
            if not data or len(data) > MAX_FILE:
                raise ValueError('Invalid prepared treasure descriptor')
            files[name] = sha(data)
    if not 5 <= len(files) <= 65536:
        raise ValueError('Prepared original input inventory exceeds bounds')
    data = (f'P2_ORIGINAL_SESSION 1 {campaign} {len(files)}\n' + ''.join(f'{name} {files[name]}\n' for name in sorted(files)) + 'END\n').encode('ascii')
    if len(data) > MAX_DESCRIPTOR:
        raise ValueError('Prepared original descriptor exceeds bounds')
    return data


class OriginalSession:
    def __init__(self, directory, descriptor_bytes):
        self.directory = Path(directory)
        self.identity = sha(descriptor_bytes)
        self.campaign = descriptor_bytes.decode('ascii').split()[2]
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / 'p2-original-session.txt'
        if path.exists() and path.read_bytes() != descriptor_bytes:
            raise ValueError('Original session physical inputs changed; preserve existing cards')
        atomic_write(path, descriptor_bytes.decode('ascii'))


class OriginalRun:
    def __init__(self, session, prepared, course='tutorial', treasure_source=''):
        if course not in COURSES or (treasure_source and not DIGEST.fullmatch(treasure_source)):
            raise ValueError('Invalid explicit original launch selection')
        self.session = session
        self.token = secrets.token_hex(32)
        self.directory = session.directory / 'runs' / self.token
        self.directory.mkdir(parents=True)
        prepared = Path(prepared).resolve(strict=True)
        # Private copies keep maintained assets and other running sessions intact.
        for name in ('assets', 'p2-original'):
            shutil.copytree(prepared / name, self.directory / name)
        for name in ('p2-treasure-placements.txt', 'p2-treasure-catalog.txt'):
            if (prepared / name).exists():
                shutil.copy2(prepared / name, self.directory / name)
        if treasure_source and (not (self.directory / 'p2-treasure-placements.txt').exists() or sha((self.directory / 'p2-treasure-placements.txt').read_bytes()) != treasure_source):
            raise ValueError('Explicit treasure source differs from staged descriptor')
        copied = descriptor(self.directory, session.campaign)
        if copied != (session.directory / 'p2-original-session.txt').read_bytes():
            raise ValueError('Copied original runtime differs from selected session; preserve run for diagnosis')
        shutil.copy2(session.directory / 'p2-original-session.txt', self.directory / 'p2-original-session.txt')
        self.bootstrap = self.directory / 'bootstrap.txt'
        atomic_write(self.bootstrap, f'ORIGINAL_P2_CAMPAIGN 1\nSESSION {self.token}\nFINGERPRINT {session.identity}\nORIGINAL_SOURCE {session.campaign}\nCOURSE {course}\nCAPTAINS 2\n' + (f'TREASURE_SOURCE {treasure_source}\n' if treasure_source else '') + 'END\n')
        self.capabilities = ['original-campaign-state-v1', 'p2-second-captain-v1'] + (['source-treasure-state-v1'] if treasure_source else [])
        self.handshaken = False
        self.write_state(False)

    def write_state(self, ready):
        atomic_write(self.directory / 'state.txt', f'ORIGINAL_P2_STATE 1 {self.token} {self.session.identity} {int(ready)} END\n')

    def poll(self):
        hello = self.directory / 'hello.txt'
        if not self.handshaken and hello.exists():
            expected = ['ORIGINAL_P2_HELLO', '1', self.token, self.session.identity, *self.capabilities, 'END']
            if hello.read_text(encoding='ascii').split() != expected:
                raise ValueError('Original native session handshake mismatch')
            self.handshaken = True


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--bundle', action='append', required=True, type=Path)
    cli.add_argument('--source-identity', action='store_true')
    cli.add_argument('--calendar', required=True, type=Path)
    cli.add_argument('--native-source', type=Path)
    cli.add_argument('--prepared', type=Path)
    cli.add_argument('--session', type=Path)
    cli.add_argument('--exe', type=Path)
    cli.add_argument('--course', choices=COURSES, default='tutorial')
    cli.add_argument('--treasure-source', default='')
    args = cli.parse_args()
    campaign, _ = source_identity(args.bundle, args.calendar)
    if args.source_identity:
        print(campaign)
        return
    if args.prepared is None or args.session is None or args.native_source is None:
        cli.error('--prepared, --session and --native-source are required for session preparation')
    validate_prepared(args.prepared, args.bundle, args.calendar, args.native_source, campaign)
    image = descriptor(args.prepared, campaign)
    with SessionLock(args.session):
        session = OriginalSession(args.session, image)
        run = OriginalRun(session, args.prepared, args.course, args.treasure_source)
        print(json.dumps({'campaign': campaign, 'fingerprint': session.identity, 'bootstrap': str(run.bootstrap.resolve()), 'gameplay_accepted': False}))
        if args.exe is None:
            return
        env = dict(os.environ)
        for key in list(env):
            if key.startswith(('PIKMIN_', 'BBFT_', 'SDL_')):
                env.pop(key)
        env['PIKMIN_P2_ORIGINAL_CATALOG'] = str((run.directory / 'p2-original').resolve())
        env['PIKMIN_P2_SURFACE_SAVE'] = '1'
        startup = None
        if os.name == 'nt':
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
        with (run.directory / 'native.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([str(args.exe.resolve(strict=True)), '--experimental-pikmin2-campaign', args.course, '--randomizer-seed', str(run.bootstrap.resolve())], cwd=run.directory, env=env, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup)
            try:
                while process.poll() is None:
                    run.poll()
                    run.write_state(run.handshaken)
                    time.sleep(.1)
                run.poll()
                if process.returncode:
                    raise RuntimeError(f'Original native launch exited {process.returncode}; retain native.log')
            finally:
                run.write_state(False)
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


if __name__ == '__main__':
    main()
