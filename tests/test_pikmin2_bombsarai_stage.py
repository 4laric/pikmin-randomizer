"""#244 OWN: BombSarai native staging (bank grammar, teki row, adapter wiring)."""
import struct

import pytest

from experimental import pikmin2_bombsarai_stage as stage
from experimental import pikmin2_family_install as family


def _clip(anim, name, frames=60, events=((10, 0), (49, 1)), poses=((0, 0, (1.0, -22.5, 19.5)),)):
    return dict(anim_id=anim, name=name, frames=frames, events=list(events), poses=list(poses))


def test_bank_round_trip_matches_native_grammar():
    clips = [_clip(12, 'wait1'), _clip(8, 'supli1', frames=60, events=(), poses=())]
    bombs = [dict(name='hit_loop', frames=8, poses=[(0, 0), (4, 3)])]
    data = stage.bank_text(clips, bombs)
    text = data.decode('ascii')
    assert text.startswith('P2_BOMBSARAI_OWN_BANK_1 2\n')
    assert 'clip 12 wait1 60 2 10 0 49 1 1 0 0 1 -22.5 19.5' in text
    assert 'bomb hit_loop 8 2 0 0 4 3' in text
    parsed = stage.parse_bank(data)
    assert parsed['clips'][12]['poses'] == [(0, 0, (1.0, -22.5, 19.5))]
    assert parsed['clips'][8]['poses'] == []
    assert parsed['bombs'][0]['poses'] == [(0, 0), (4, 3)]


@pytest.mark.parametrize('bad', [
    _clip(14, 'wait1'),                                   # anim id out of range
    _clip(12, 'wait1', events=((70, 2),)),                # event past the clip
    _clip(12, 'wait1', poses=((5, 0, (0, 0, 0)), (5, 1, (0, 0, 0)))),  # non-increasing pose frames
    _clip(12, 'wait1', poses=((5, 100, (0, 0, 0)),)),     # file index beyond the native bound
    _clip(12, 'wait1', poses=((5, 0, (float('nan'), 0, 0)),)),
])
def test_bank_refuses_what_native_refuses(bad):
    with pytest.raises(stage.BombSaraiStageError):
        stage.bank_text([bad], [])


def test_parse_bank_fails_closed():
    with pytest.raises(stage.BombSaraiStageError):
        stage.parse_bank(b'P2_BOMBSARAI_OWN_BANK_1 1\nclip 12 wait1 60 0 0\n')
    with pytest.raises(stage.BombSaraiStageError):
        stage.parse_bank(b'P2_GROINK_BANK_1 1\nEND\n')


def test_bca_frames_reads_anf1_header():
    raw = bytearray(0x40)
    raw[0x20:0x24] = b'ANF1'
    struct.pack_into('>H', raw, 0x2A, 60)
    assert stage.bca_frames(bytes(raw)) == 60
    with pytest.raises(stage.BombSaraiStageError):
        stage.bca_frames(b'\0' * 0x40)


def test_teki_row_is_campaign_napkid_form():
    assert stage.teki_text(1945764764) == b'P2_BOMBSARAI_TEKI_1 1 1945764764 11\n'
    with pytest.raises(stage.BombSaraiStageError):
        stage.teki_text(0)


def test_family_adapter_routes_58_to_bombsarai_own_staging():
    assert family.IDENTITY_FAMILY[58] == 'bombsarai'
    assert family.ADAPTERS['bombsarai']['install'] is family._adapt_bombsarai
    assert family.ADAPTERS['bombsarai']['validate'] is family._validate_bombsarai


def test_prepare_content_wires_the_58_extractor():
    from scripts import p2_prepare_content as prepare
    assert prepare.EXTRACTORS[58] == 'extract_bombsarai'
    assert callable(prepare.extract_bombsarai)
