"""Retail per-species texture swaps applied before baking P2 poses (issue #895).

Several Pikmin 2 species share one ``enemy.bmd`` whose texture slots hold
8x8 placeholder images. At runtime each species manager loads its own BTI
files and ``Obj::changeMaterial`` swaps them into the model with
``J3DTexture::changeImage(texture, slot)``. Baking the model without that swap
shows the placeholder, a flat grey intensity texture, instead of the species'
colouring (e.g. Chappy renders pale grey instead of red-and-spotted).

``CHANGE_TEXTURES`` lists the swaps baked through this module, keyed by the P2
enemy name, with its disc path and slot. It is not every swap the decomp
performs. ``apply`` returns the model with the swap done (same TEX1 rewrite as
``pikmin2_enemy.replace_texture_zero``, generalised to any slot) plus a
provenance record.

Decomp ``changeMaterial`` swaps handled elsewhere, not through this table:

* Ftank/Wtank: ``pikmin2_tank_assets``.
* The Kochappy trio: the Kochappy/dwarf profiles.
* Koganemushi, Wealthy and Fart: ``pikmin2_kogane_assets`` (``change_texture``).
* Fire/Water/Gas/ElecOtakara: tinted by the native draw path instead
  (``pc_p2_batch2.h`` ``p2batch2tint``); see ``RUNTIME_TINTED``.
* BombOtakara: baked by ``pikmin2_dweevil_assets`` from the shared dweevil
  model. The native tint deliberately skips it, so its entry here is applied
  by that extractor (``BombOtakaraMgr.cpp`` ``otakara_bomb_s3tc.bti``, slot 0,
  ``BombOtakara.cpp`` ``Obj::changeMaterial``).

Remaining ``changeImage`` swaps in the decomp are outside the enemy pool:
blackMan (Waterwraith) and ``pelletOtakara`` (treasure pellets). Other
``changeMaterial`` overrides (e.g. FireChappy, DangoMushi, UmiMushi,
BigTreasure) animate material/TEV colours at runtime rather than swap an image.
"""
import hashlib
import struct

from experimental.pikmin2_convert import blocks, texture_layout, u16, u32

# name -> [(slot, disc path)]; decomp: src/plugProjectYamashitaU/{chappy,
# YellowChappy,BlueChappy}{,Mgr}.cpp, src/plugProjectNishimuraU/{Green,Red,
# Fix}Kabuto{,Mgr}.cpp. generalEnemyMgr.cpp maps Kabuto -> GreenKabuto::Mgr,
# Rkabuto -> RedKabuto::Mgr and Fkabuto -> FixKabuto::Mgr.
CHANGE_TEXTURES = {
    'Chappy': [(0, 'enemy/data/Chappy/moyou_565.1.bti'),
               (1, 'enemy/data/Chappy/swallow_565.1.bti')],
    'YellowChappy': [(0, 'enemy/data/YellowChappy/moyou_565.2.bti'),
                     (1, 'enemy/data/YellowChappy/swallow_565.2.bti')],
    'BlueChappy': [(0, 'enemy/data/BlueChappy/moyou_565.3.bti'),
                   (1, 'enemy/data/BlueChappy/swallow_565.3.bti')],
    'Kabuto': [(0, 'enemy/data/Kabuto/babykabuto_green_s3tc.bti')],
    'Fkabuto': [(0, 'enemy/data/Kabuto/babykabuto_green_s3tc.bti')],
    'Rkabuto': [(0, 'enemy/data/Rkabuto/babykabuto_red_s3tc.bti')],
    # plugProjectNishimuraU/BombOtakara{,Mgr}.cpp: changeImage(texture, 0).
    # Applied by pikmin2_dweevil_assets (not tinted natively, unlike the four
    # RUNTIME_TINTED dweevils).
    'BombOtakara': [(0, 'enemy/data/BombOtakara/otakara_bomb_s3tc.bti')],
}

# Species whose swap the native draw path approximates with a flat tint over
# the placeholder (pc_port/pc_p2_batch2.h p2batch2tint). Baking the real
# texture here would double-tint until that native tint is retired.
RUNTIME_TINTED = ('FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara')


def replace_texture(model, slot, texture):
    """Swap one TEX1 image (header + data), like J3DTexture::changeImage."""
    if len(texture) < 32 or texture[8]:
        raise ValueError('Expected non-paletted BTI')
    _, size = texture_layout(texture[0], u16(texture, 2), u16(texture, 4))
    start = u32(texture, 28)
    if start < 32 or start + size > len(texture):
        raise ValueError('Truncated BTI')
    b = blocks(model)
    t = bytearray(b['TEX1'])
    if not 0 <= slot < u16(t, 8):
        raise ValueError('Missing image slot %d' % slot)
    header = u32(t, 12) + 32 * slot
    if header < 20 or header + 32 > len(t):
        raise ValueError('Invalid texture header')
    at = len(t)
    t[header:header + 32] = texture[:32]
    struct.pack_into('>I', t, header + 28, at - header)
    t.extend(texture[start:start + size])
    t.extend(bytes((-len(t)) % 32))
    struct.pack_into('>I', t, 4, len(t))
    b['TEX1'] = bytes(t)
    result = bytearray(model[:32] + b''.join(b.values()))
    struct.pack_into('>I', result, 8, len(result))
    return bytes(result)


def apply(model, species, read):
    """(model with the retail swaps for ``species``, provenance list).

    ``read(path)`` returns disc bytes. Species without a swap return the
    model unchanged and an empty list.
    """
    records = []
    for slot, path in CHANGE_TEXTURES.get(species, ()):
        texture = read(path)
        model = replace_texture(model, slot, texture)
        records.append(dict(slot=slot, path=path, sha256=hashlib.sha256(texture).hexdigest()))
    return model, records
