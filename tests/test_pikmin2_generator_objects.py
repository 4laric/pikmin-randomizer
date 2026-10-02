from copy import deepcopy
import pytest
from experimental.pikmin2_generator_objects import enemy_object


def actor():
    return dict(kind='teki', object_version='0005', source_payload=[
        '16', '0', '2', '80.156250', '2', '70.000000', '0.000000',
        '841', '3', '5', '1', '8', '0.700000', ['0000'],
        '200.000000', '30.000000', [['_eof']]])


def test_named_original_fields_and_opaque_tail_preserved():
    source = actor()
    before = deepcopy(source)
    decoded = enemy_object(source)
    assert decoded['source_id'] == 16 and decoded['count'] == 2
    assert decoded['spawn_type'] == 2 and decoded['appear_radius'] == 70
    assert decoded['direction_degrees'] == 80.15625
    assert decoded['treasure_code'] == 841 and decoded['pellet_probability'] == .7
    assert decoded['generator_version'] == '0000'
    assert decoded['generator_tail'] == ['200.000000', '30.000000']
    decoded['generator_tail'].append('changed')
    assert source == before


@pytest.mark.parametrize('index,value', [(0,'-1'), (0,'65536'), (1,'256'),
    (2,'32768'), (2,'1.5'), (3,'nan'), (5,'inf'), (6,'-inf'), (7,'32768'), (7,'-32769'),
    (8,'256'), (9,'-1'), (10,'256'), (11,'-1'), (12,'nan'), (3,'1e100'), (0,True)])
def test_malformed_common_native_fields_refused(index, value):
    source = actor()
    source['source_payload'][index] = value
    with pytest.raises(ValueError):
        enemy_object(source)


@pytest.mark.parametrize('change', ['version', 'kind', 'truncated', 'terminator', 'special_version'])
def test_unsupported_or_incomplete_record_refused(change):
    source = actor()
    if change == 'version': source['object_version'] = '0004'
    if change == 'kind': source['kind'] = 'piki'
    if change == 'truncated': source['source_payload'] = source['source_payload'][:12]
    if change == 'terminator': source['source_payload'][-1] = ['_eof']
    if change == 'special_version': source['source_payload'][13] = ['0000', 'extra']
    with pytest.raises(ValueError):
        enemy_object(source)


@pytest.mark.parametrize('code', [-32768, -1, 0, 32767])
def test_signed_original_treasure_code_preserved(code):
    source = actor()
    source['source_payload'][7] = str(code)
    assert enemy_object(source)['treasure_code'] == code
