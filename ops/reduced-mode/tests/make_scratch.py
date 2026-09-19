"""TEST FIXTURE ONLY: fresh scratch registry (copy of the pristine backup) re-rooted at scratch/root."""
import json, shutil, sqlite3, sys
from pathlib import Path
S = Path(__file__).resolve().parents[1] / 'scratch'
root = (S / 'root').resolve()
out = root / 'output/workflow'; (out / 'controller').mkdir(parents=True, exist_ok=True)
db = out / 'registry.sqlite3'
for f in out.glob('registry*'): f.unlink()
src = sqlite3.connect(S / 'pristine.sqlite3'); dst = sqlite3.connect(db); src.backup(dst); src.close()
meta = json.loads(dst.execute("select body from registry_documents where section='' and key=''").fetchone()[0])
meta['root'] = str(root)
dst.execute("update registry_documents set body=? where section='' and key=''", (json.dumps(meta),))
trig = dst.execute("select sql from sqlite_master where name='registry_legacy_write_guard'").fetchone()[0]
dst.execute('drop trigger registry_legacy_write_guard')
d = json.loads(dst.execute('select body from registry').fetchone()[0]); d['root'] = str(root)
dst.execute('update registry set body=?', (json.dumps(d),)); dst.execute(trig); dst.commit(); dst.close()
shutil.copy(r'C:\Users\alari\pikmin-randomizer\output\workflow\controller\config.json', out / 'controller/config.json')
(out / 'controller/STOP').write_text('scratch')
# the one pending intent has an empty launch dir live; mirror that
(out / 'controller/launches/00ee93d764d986470f5730678453ab1af184e0adb0f9e6ca986a2bee65db352e').mkdir(parents=True, exist_ok=True)
for f in (out / 'controller').glob('config.before-*'): f.unlink()
print('scratch registry', db)
