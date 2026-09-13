"""Versioned byte identity for the bounded surface staging inputs."""
import hashlib
from pathlib import Path
import re


def surface_identity(cave_identity, treasure, source_import, pocket):
    if not re.fullmatch('[0-9a-f]{64}',cave_identity):raise ValueError('Invalid cave identity')
    source_import,pocket=Path(source_import),Path(pocket)
    files=[('treasure',Path(treasure)),('surface/render',source_import/'surface-render.mod')]
    files += [('pocket/'+name,pocket/name) for name in ('entrance-pocket.json','entrance-collision.json','surface-water.json')]
    digest=hashlib.sha256(b'P2_SURFACE_CONTENT_1\0'+bytes.fromhex(cave_identity))
    for label,path in files:
        digest.update(label.encode('ascii')+b'\0'+hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()
