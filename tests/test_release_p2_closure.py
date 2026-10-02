import importlib.util
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("p2_package", ROOT / "scripts/package_release.py")
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def test_extracted_player_dependency_closure(tmp_path):
    stage = tmp_path / "fresh package"
    exe = tmp_path / "nectar.exe"
    exe.write_bytes(b"MZ package assembly test, not a game executable")
    archive, _, _ = package.package("1153-source-test", exe, dlls=[], repo=ROOT,
                                    output_dir=tmp_path / "candidate")
    with zipfile.ZipFile(archive) as zip_file:
        zip_file.extractall(stage)
    package.audit(stage)
    assert not any(p.suffix in (".mod", ".bti", ".bca", ".szs") for p in stage.rglob("*"))
    code = '''
import sys, importlib
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from experimental.pikmin2_enemy_roster import load_and_validate, admitted_ids
from experimental import pikmin2_family_install as families
from randomizer.seed import generate, PLAYABLE_P2_SPECIES
assert set(admitted_ids(load_and_validate())) == set(PLAYABLE_P2_SPECIES)
assert len(PLAYABLE_P2_SPECIES) == 42
for identity in PLAYABLE_P2_SPECIES:
    family = families.resolve_family(identity)
    assert callable(families._installer(family))
for path in Path(sys.argv[1]).rglob('*.py'):
    if path.name == '__main__.py': continue
    if path.relative_to(sys.argv[1]).parts[0] == 'launcher': continue
    module = '.'.join(path.relative_to(sys.argv[1]).with_suffix('').parts)
    if module.endswith('.__init__'): module = module[:-9]
    importlib.import_module(module)
one = generate('isolated-p2-package', p2_enemies=True, p2_checks=True, p2_species='playable')
assert one == generate('isolated-p2-package', p2_enemies=True, p2_checks=True, p2_species='playable')
assert one['p2_layout']
assert 'p2_layout' not in generate('isolated-p1-package')
print('admitted42 imports/families/deterministic generation PASS')
'''
    result = subprocess.run([sys.executable, "-I", "-c", code, str(stage)], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_apworld_zip_core_resources_without_checkout(tmp_path):
    output = tmp_path / "world.apworld"
    subprocess.run([sys.executable, str(ROOT / "scripts/build_apworld.py"), "--output", str(output)], check=True)
    code = '''
import sys, types
sys.path.insert(0,sys.argv[1])
world=types.ModuleType('pikmin_randomizer'); world.__path__=[sys.argv[1]+'/pikmin_randomizer']
sys.modules['pikmin_randomizer']=world
from pikmin_randomizer.core.seed import generate, PLAYABLE_P2_SPECIES
from pikmin_randomizer.experimental.pikmin2_enemy_roster import load_and_validate,admitted_ids
assert set(admitted_ids(load_and_validate()))==set(PLAYABLE_P2_SPECIES)
assert len(PLAYABLE_P2_SPECIES)==42
for pool,tier in [('playable',None),(None,None),('full','proven')]:
    one=generate('zip-p2',p2_enemies=True,p2_checks=True,p2_species=pool,p2_proxy_tier=tier)
    assert one==generate('zip-p2',p2_enemies=True,p2_checks=True,p2_species=pool,p2_proxy_tier=tier)
    assert one['p2_layout']
print('APworld zip core admitted42 generation PASS')
'''
    result = subprocess.run([sys.executable, "-I", "-c", code, str(output)], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
