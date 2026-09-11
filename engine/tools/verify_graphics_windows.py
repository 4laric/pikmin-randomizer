"""Run real OpenGL graphics fixtures against a completed Windows Ninja build.

Uses that build's compiler flags and objects; never replaces the game binary.
All settings, captures, logs and temporary executables stay in --output.
"""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import threading
import uuid


def check_scene_capture(output):
    from PIL import Image, ImageChops
    for path in output.glob('*.ppm'):
        with Image.open(path) as img:
            img.save(path.with_suffix('.png'))
    with Image.open(output / 'original.png') as original, \
         Image.open(output / 'enhanced.png') as enhanced, \
         Image.open(output / 'cancelled.png') as cancelled:
        if original.size != enhanced.size or original.size != cancelled.size:
            raise AssertionError('Scene capture dimensions changed')
        # The HUD sun animates independently even while simulation is held.
        # Compare the rest of the image, including the captain and bottom HUD.
        width, height = original.size
        scene = (0, height // 5, width, height)
        before = original.crop(scene)
        if not ImageChops.difference(before, enhanced.crop(scene)).getbbox():
            raise AssertionError('Enhanced preset did not change the scene')
        if ImageChops.difference(before, cancelled.crop(scene)).getbbox():
            raise AssertionError('Cancelling did not restore the original scene')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture', choices=('menus', 'post', 'scene'), required=True)
    parser.add_argument('--area', choices=('forest', 'navel', 'spring'), default='forest')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This wrapper uses the Windows Ninja toolchain.')
    build, output = args.build.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = dict(line.split('=', 1) for line in
                 (build / 'CMakeCache.txt').read_text().splitlines()
                 if '=' in line and not line.startswith(('#', '//')))
    ninja = next(v for k, v in cache.items() if k.startswith('CMAKE_MAKE_PROGRAM:'))
    source = Path(next(v for k, v in cache.items() if k.startswith('CMAKE_HOME_DIRECTORY:')))
    commands = subprocess.check_output([ninja, '-t', 'commands', 'pikmin_pc'],
                                       cwd=build, text=True).splitlines()
    replaced = 'gl/pc_gfx.cpp' if args.fixture == 'post' else 'settings/pc_settings.cpp'
    object_name = 'CMakeFiles/pikmin_pc.dir/pc_port/' + replaced + '.obj'
    compile_line = next(c for c in commands if ' -c ' in c and object_name in c)
    # CMake emits forward-slash source/include paths. Normalise the executable
    # spelling too before POSIX tokenisation so Windows backslashes survive.
    compile_args = shlex.split(compile_line.replace('\\', '/'))
    fixture_name = {'menus': 'preview_port_menus', 'post': 'verify_postprocess_gl',
                    'scene': 'preview_graphics_scene'}[args.fixture]
    obj = output / (fixture_name + '.obj')
    exe = output / (fixture_name + '.exe')
    compile_args[compile_args.index('-o') + 1] = str(obj)
    compile_args[compile_args.index('-c') + 1] = str(source / 'tools' / (fixture_name + '.cpp'))
    for flag in ('-MF', '-MT'):
        if flag in compile_args:
            index = compile_args.index(flag)
            del compile_args[index:index + 2]
    if '-MD' in compile_args:
        compile_args.remove('-MD')
    # Bounded LTO concurrency for a fixture sharing the game's static library.
    compile_args = [a for a in compile_args if not a.startswith('-flto')]
    link_line = commands[-1]
    if ' && ' not in link_line:
        raise RuntimeError('Expected CMake Windows Ninja linker wrapper')
    link_args = shlex.split(link_line.split(' && ')[1].replace('\\', '/'))
    main_obj = 'CMakeFiles/pikmin_pc.dir/pc_port/pc_main.cpp.obj'
    if main_obj not in link_args or object_name not in link_args:
        raise RuntimeError('Expected main and renderer/settings objects in linker command')
    link_args = [str(obj) if a == main_obj else a for a in link_args
                 if a != object_name and not a.startswith(('-flto', '-Wl,--out-implib'))]
    link_args[link_args.index('-o') + 1] = str(exe)
    link_args.append('-flto=4')
    with (output / 'build.log').open('w') as log:
        subprocess.run(compile_args, cwd=build, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(link_args, cwd=build, stdout=log, stderr=subprocess.STDOUT, check=True)
    assets = output / 'assets'
    if assets.exists():
        if assets.resolve() != args.assets.resolve():
            raise RuntimeError('Output assets points at a different directory')
    else:
        import _winapi
        _winapi.CreateJunction(str(args.assets.resolve()), str(assets))
    env = dict(os.environ, SDL_AUDIODRIVER='dummy', PIKMIN_RENDER_SCALE='1')
    env.pop('BBFT_PORT', None)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    argv = [str(exe)]
    heartbeat_done = threading.Event()
    heartbeat = None
    if args.fixture == 'menus':
        argv += [str(output), str(args.width), str(args.height)]
    elif args.fixture == 'scene':
        # Direct area boot, isolated from user saves and any active AP session.
        run = output / ('run-' + uuid.uuid4().hex)
        run.mkdir()
        token = uuid.uuid4().hex + uuid.uuid4().hex
        profile = {'forest': 'foh-day2', 'navel': 'navel-day2', 'spring': 'spring-day2'}[args.area]
        bootstrap = run / 'boot.txt'
        bootstrap.write_text(f'PIKMIN_RANDOMIZER 5\nSESSION {token}\nFINGERPRINT {token}\n'
                             f'PROFILE {profile}\nCATALOG gameplay-checks-v5\n'
                             'PLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\n'
                             'COLOR red\nSTARTING_FLARLIC 10\nEND\n')
        def refresh():
            while not heartbeat_done.is_set():
                pending = run / 'state.tmp'
                pending.write_text(f'PIKMIN_STATE 5 {token} 1 0 127 0 0 END\n')
                os.replace(pending, run / 'state.txt')
                heartbeat_done.wait(0.1)
        heartbeat = threading.Thread(target=refresh, daemon=True)
        heartbeat.start()
        env.update(PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',
                   PIKMIN_GRAPHICS_CAPTURE_DIR=str(output),
                   PIKMIN_GRAPHICS_CAPTURE_WIDTH=str(args.width),
                   PIKMIN_GRAPHICS_CAPTURE_HEIGHT=str(args.height))
        argv += ['--randomizer-seed', str(bootstrap)]
    try:
        with (output / 'run.log').open('w') as log:
            subprocess.run(argv, cwd=output, env=env, startupinfo=startup,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    finally:
        heartbeat_done.set()
        if heartbeat:
            heartbeat.join(timeout=2)
    if args.fixture == 'menus':
        from PIL import Image, ImageChops
        for path in output.glob('page-*.ppm'):
            with Image.open(path) as img:
                img.save(path.with_suffix('.png'))
        with Image.open(output / 'page-00.ppm') as initial, Image.open(output / 'page-16.ppm') as reopened:
            if ImageChops.difference(initial, reopened).getbbox():
                raise AssertionError('Reopening F1 left stale menu state')
        with Image.open(output / 'page-15.ppm') as closed:
            if closed.getcolors(maxcolors=2) is None or len(closed.getcolors(maxcolors=2)) != 1:
                raise AssertionError('Closed F1 still drew over the background')
    elif args.fixture == 'scene':
        check_scene_capture(output)
    print(f'PASS {args.fixture}: {output}')


if __name__ == '__main__':
    main()
