"""Stage complete retail tutorial terrain for opt-in topology/controller evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from experimental.pikmin2_surface_import import verify_bundle
from experimental.pikmin2_surface_collision import attach_surface_collision
from experimental.pikmin2_convert import convert
from experimental.pikmin2_collision import route_ini
from scripts.stage_pikmin2_surface_boot import stage_table,starting_squad
from scripts.preview_pikmin2_room import overlay


def prepare(assets,bundle,identity,output):
    receipt=verify_bundle(bundle,identity)
    if receipt['course']!='tutorial':raise ValueError('Only tutorial is audited')
    if output.exists():raise ValueError('Refusing existing output')
    room=json.loads((bundle/'surface-geometry.json').read_text())
    output.mkdir(parents=True)
    convert(bundle/'arc/model.bmd',output/'surface-render.mod',approximate_materials=True)
    model,record=attach_surface_collision((output/'surface-render.mod').read_bytes(),room)
    stage=(assets/'dataDir/stages/chal0.ini').read_bytes()
    stage=re.sub(rb'(?m)^map_file[^\r\n]*',b'map_file courses/p2tutorial/full.mod',stage)
    stage=re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start -190.0 1160.0',stage)
    empty=b'1.0v'+struct.pack('>4fI',-190,80,1160,0,0)
    overrides={'dataDir/stages/stages.ini':stage_table((assets/'dataDir/stages/stages.ini').read_bytes()),
               'dataDir/stages/p2_tutorial.ini':stage,'dataDir/stages/p2_tutorial/default.gen':starting_squad(assets),
               'dataDir/courses/p2tutorial/full.mod':model,'dataDir/courses/p2tutorial/full.ini':route_ini(room['routes']).encode()}
    for name in ('init.gen','plants.gen','day.gen'):overrides['dataDir/stages/p2_tutorial/'+name]=empty
    run=output/'run';run.mkdir();overlay(assets,run/'assets',overrides)
    (run/'surface-water.json').write_bytes((bundle/'surface-water.json').read_bytes())
    record.update(schema=1,course='tutorial',receipt_identity=identity,starting_pikmin=20,
                  engineering_boundary=False,source_water_retained=True,native_water_consumer=False,
                  retail_generators_imported=False,routes_serialized=True,material_fidelity='approximate',
                  files={name:hashlib.sha256(data).hexdigest() for name,data in overrides.items()})
    (run/'full-surface-inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    return run


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','bundle','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--identity',required=True);a=p.parse_args()
    print(prepare(a.assets.resolve(),a.bundle.resolve(),a.identity,a.output.resolve()))
