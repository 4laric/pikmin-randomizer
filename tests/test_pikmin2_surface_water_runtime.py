import pytest
from experimental.pikmin2_surface_water_runtime import serialize


SOURCE = '0 { 3 -140 -55 350 960 45 1150 -1210 -30 -650 -410 70 150 -140 -60 1250 960 40 2150 }'


def test_exact_source_order_bounds_and_heights():
    assert serialize(SOURCE).decode().splitlines() == [
        'P2_SURFACE_WATER_1 tutorial 3',
        '0 -140 -55 350 960 45 1150 45 0',
        '1 -1210 -30 -650 -410 70 150 70 0',
        '2 -140 -60 1250 960 40 2150 40 0']


@pytest.mark.parametrize('text', [SOURCE[:-2], SOURCE.replace('3 -140', '2 -140'),
                                 SOURCE.replace('-55', 'nan'), SOURCE.replace('960 45', '-140 45')])
def test_refuses_bad_source(text):
    with pytest.raises((ValueError, IndexError)):
        serialize(text)
