"""Extract only genuine GPVE01 Watage JPA/TEX1 into private output.

No game installation writes; exact raw bytes are verified before output.
The importer intentionally does not claim other JPAC resources.
"""
import argparse, hashlib, json
from pathlib import Path
from experimental.pikmin2_assets import disc_files
ARCHIVE = 'user/Ebisawa/effect/game.jpc'
ARCHIVE_SHA = 'ebf889b4e5df0391662bd531e220b93d148ab56fdec96362386b9cd1e734302c'
RESOURCES = (
 ('watage-01e4.jpa', 256660, 496, 'e94cd58a680c0cb2b04d1e3a88be0338bb0cea7cbf70ec0f1cefea17456aac6d'),
 ('IP2_watage2_ia.tex1', 551104, 1088, 'c5e7489de8993f0fffc977d3fc60e143dc06ceced4e8ddd7cf30df60cf114775'),
)
def extract(iso, out):
 index=disc_files(iso); offset,size=index[ARCHIVE]
 with iso.open('rb') as f:
  f.seek(offset);raw=f.read(size)
 if len(raw)!=size or hashlib.sha256(raw).hexdigest()!=ARCHIVE_SHA:
  raise ValueError('GPVE01 game.jpc source digest mismatch')
 checked={}
 for name,start,length,digest in RESOURCES:
  data=raw[start:start+length]
  if len(data)!=length or hashlib.sha256(data).hexdigest()!=digest:
   raise ValueError('Watage source member digest mismatch: '+name)
  checked[name]=data
 out.mkdir(parents=True,exist_ok=True)
 for name,data in checked.items():
  target=out/name
  if target.exists() and target.read_bytes()!=data:raise ValueError('Existing output changed: '+name)
  target.write_bytes(data)
 receipt={'disc_id':'GPVE01','source_archive':ARCHIVE,'archive_sha256':ARCHIVE_SHA,
  'effect':484,'texture':'IP2_watage2_ia','fields':['Drag','Random','Air'],
  'files':{name:hashlib.sha256(data).hexdigest() for name,data in checked.items()},'gameplay':False}
 (out/'watage-source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--iso',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();print(json.dumps(extract(a.iso,a.out)))
