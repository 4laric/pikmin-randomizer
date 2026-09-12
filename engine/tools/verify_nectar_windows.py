import argparse
from pathlib import Path
import shlex
import subprocess

parser = argparse.ArgumentParser(description='Build the live nectar regression fixture against a completed Windows Ninja game build.')
parser.add_argument('--build', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
build, output = args.build.resolve(), args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
cache = dict(line.split('=',1) for line in (build/'CMakeCache.txt').read_text(encoding='utf-8').splitlines() if '=' in line and not line.startswith(('#','//')))
ninja = next(v for k,v in cache.items() if k.startswith('CMAKE_MAKE_PROGRAM:'))
source = Path(next(v for k,v in cache.items() if k.startswith('CMAKE_HOME_DIRECTORY:')))
commands = subprocess.check_output([ninja,'-t','commands','pikmin_pc'],cwd=build,text=True).splitlines()
main_obj = 'CMakeFiles/pikmin_pc.dir/pc_port/pc_main.cpp.obj'
compile_args = shlex.split(next(c for c in commands if main_obj in c and ' -c ' in c).replace('\\','/'))
name = 'preview_nectar'
obj = output/(name+'.obj')
exe = output/(name+'.exe')
compile_args[compile_args.index('-o')+1] = str(obj)
compile_args[compile_args.index('-c')+1] = str(source/'tools'/(name+'.cpp'))
for flag in ('-MF','-MT'):
    if flag in compile_args:
        i=compile_args.index(flag); del compile_args[i:i+2]
compile_args = [a for a in compile_args if a != '-MD' and not a.startswith('-flto')]
link_args = shlex.split(commands[-1].split(' && ')[1].replace('\\','/'))
link_args = [str(obj) if a == main_obj else a for a in link_args if not a.startswith(('-flto','-Wl,--out-implib'))]
link_args[link_args.index('-o')+1] = str(exe)
link_args.append('-flto=4')
with (output/'build.log').open('w', encoding='utf-8') as log:
    subprocess.run(compile_args,cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run(link_args,cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
print(exe)
