"""Bundle a private Windows fixture and its explicitly resolved runtime DLLs."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pe_imports(path, objdump):
    text = subprocess.check_output([str(objdump), '-p', str(path)], text=True)
    if not re.search(r'file format pei-(?:x86-64|i386)', text):
        raise ValueError(f'Not a recognized Windows PE image: {path}')
    return re.findall(r'DLL Name:\s*(\S+)', text)


def plan(executable, dll_roots, system_directory, imports):
    executable = Path(executable).resolve(strict=True)
    roots = list(dict.fromkeys(Path(p).resolve(strict=True) for p in dll_roots))
    system_directory = Path(system_directory).resolve(strict=True)
    if not executable.is_file() or not all(p.is_dir() for p in roots + [system_directory]):
        raise ValueError('Expected executable file and DLL directories')
    indexes = []
    for root in roots + [system_directory]:
        index = {}
        for path in root.iterdir():
            if path.is_file():
                index.setdefault(path.name.lower(), []).append(path.resolve(strict=True))
        indexes.append(index)
    queue = [executable]
    files, system = {}, set()
    while queue:
        path = queue.pop(0)
        key = path.name.lower()
        if key in files:
            if files[key]['source'] != str(path):
                raise ValueError(f'Conflicting output name: {path.name}')
            continue
        before = sha256(path)
        dependencies = imports(path)
        if sha256(path) != before:
            raise ValueError(f'Input changed during inspection: {path}')
        files[key] = dict(name=path.name, source=str(path), sha256=before,
                          imports=sorted(set(dependencies), key=str.lower))
        for name in dependencies:
            if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.dll', name, re.IGNORECASE):
                raise ValueError(f'Unsafe import name: {name}')
            lower = name.lower()
            candidates = set(p for index in indexes[:-1] for p in index.get(lower, []))
            is_system = lower in indexes[-1] or lower.startswith(('api-ms-win-', 'ext-ms-win-'))
            if is_system:
                if candidates:
                    raise ValueError(f'System DLL shadowed by supplied root: {name}')
                system.add(name)
                continue
            if len(candidates) != 1:
                raise ValueError(f'Missing or ambiguous DLL: {name} ({len(candidates)} candidates)')
            queue.append(next(iter(candidates)))
    return dict(schema=1, executable=executable.name,
                system_directory=str(system_directory), system_imports=sorted(system),
                files=sorted(files.values(), key=lambda f: f['name'].lower()))


def bundle(executable, dll_roots, system_directory, output, imports):
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing existing output')
    result = plan(executable, dll_roots, system_directory, imports)
    if output.parent.resolve() != output.parent or not output.parent.is_dir():
        raise ValueError('Expected existing non-linked output parent')
    output.mkdir()
    # Exclusive writes; a failed copy leaves a visibly incomplete private directory,
    # without a provenance manifest. Never delete or reuse it automatically.
    for entry in result['files']:
        data = Path(entry['source']).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('Input changed before copy')
        with (output / entry['name']).open('xb') as stream:
            stream.write(data)
    with (output / 'runtime-provenance.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', required=True, type=Path)
    parser.add_argument('--dll-root', required=True, action='append', type=Path)
    parser.add_argument('--system-directory', required=True, type=Path)
    parser.add_argument('--objdump', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = bundle(args.executable, args.dll_root, args.system_directory, args.output,
                    lambda path: pe_imports(path, args.objdump))
    print(json.dumps(dict(files=len(result['files']), output=str(args.output))))


if __name__ == '__main__':
    main()
