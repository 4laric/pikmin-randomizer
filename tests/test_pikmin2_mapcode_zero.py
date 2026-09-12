import pytest
from experimental.pikmin2_collision import translate_mapcode


def test_zero_surface_retains_independent_slip_and_bald_fields():
    for slip in range(4):
        for bald in (0,1):
            code=(slip<<4)|(bald<<6)
            native=translate_mapcode(code)
            assert native>>29==0  # ATTR_Solid, never Water or Hole
            assert (native>>27)&3==slip
            assert bool((native>>25)&1)==(not bald)
    assert translate_mapcode(0)==1<<25
    assert translate_mapcode(64)==0


def test_old_surface_codes_are_unchanged_and_unknowns_still_reject():
    old_attributes={1,2,5,6,7}
    for code in range(256):
        if code&15 in old_attributes:
            expected=(((code>>4)&3)<<27)|((not(code&64))<<25)
            assert translate_mapcode(code)==expected
        elif code&15!=0:
            with pytest.raises(ValueError,match='Unaudited P2 material'):translate_mapcode(code)
