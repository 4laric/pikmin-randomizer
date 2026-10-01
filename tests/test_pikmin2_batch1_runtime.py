from experimental.pikmin2_batch1_runtime import readings


def test_readings_parse():
    text = (
        "P2_BATCH1_BIRTH id=374001 type=30 species=Catfish "
        "x=-240.000 y=30.000 z=1850.000\n"
        "P2_BATCH3_BIND generator=374001 key=aquatic|Catfish "
        "visual_only=1 native_fsm=unimplemented\n"
        "P2_BATCH3_DRAW corpse=0 key=aquatic|Catfish clip=wait1\n"
        "P2_BATCH3_DRAW corpse=1 key=aquatic|Catfish clip=dead\n"
        "P2_BATCH1_MOVE id=374001 dx=12.500 dz=-3.000 dist=12.855\n"
        "P2_BATCH1_CLEANUP actors=0 banks=0 reentry_actors=4 reentry_banks=4\n"
        "P2_BATCH1_CORPSE_OK\n")
    births, draws, binds, moves, cleanup, corpse_ok = readings(text)
    assert births == [('374001', '30', 'Catfish', '-240.000', '30.000', '1850.000')]
    assert binds == [('374001', 'aquatic|Catfish')]
    assert draws == [('0', 'aquatic|Catfish', 'wait1'), ('1', 'aquatic|Catfish', 'dead')]
    assert moves == [('374001', '12.500', '-3.000', '12.855')]
    assert cleanup.groups() == ('0', '0', '4', '4')
    assert corpse_ok is True
