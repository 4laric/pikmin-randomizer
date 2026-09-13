from experimental.pikmin2_batch2_runtime import readings, validate


def test_readings_parse():
    text = (
        "P2_BATCH2_BIRTH id=346001 type=3 registered=1 x=-300.000 y=30.000 z=1850.000\n"
        "P2_BATCH2_BIND generator=346001 key=ground|Armor "
        "visual_only=1 native_fsm=unimplemented\n"
        "P2_BATCH2_DRAW corpse=0 key=ground|ElecBug clip=wait\n"
        "P2_BATCH2_MOVE id=346001 dx=12.500 dz=-3.000 dist=12.855\n")
    births, binds, draws, moves = readings(text)
    assert births == [('346001', '3', '1')]
    assert binds == [('346001', 'ground|Armor')]
    assert draws == [('0', 'ground|ElecBug', 'wait')]
    assert moves == [('346001', '12.500', '-3.000', '12.855')]


def _manifest():
    return {'control': 'P1 Chappy', 'actors': [
        dict(generator=346001, species='Armor', native_teki_type=3,
             expected_xyz=[-300.0, 30.0, 1850.0]),
        dict(generator=346002, species='ElecBug', native_teki_type=3,
             expected_xyz=[-180.0, 30.0, 1850.0]),
        dict(generator=346007, species='P1 Chappy', native_teki_type=3,
             expected_xyz=[240.0, 30.0, 1500.0]),
    ]}


def _log(dist):
    return (
        "P2_BATCH2_BIRTH id=346001 type=3 registered=1 x=-300.000 y=30.000 z=1850.000\n"
        "P2_BATCH2_BIRTH id=346002 type=3 registered=1 x=-180.000 y=30.000 z=1850.000\n"
        "P2_BATCH2_BIRTH id=346007 type=3 registered=0 x=240.000 y=30.000 z=1500.000\n"
        "P2_BATCH2_BIND generator=346001 key=ground|Armor visual_only=1\n"
        "P2_BATCH2_BIND generator=346002 key=ground|ElecBug visual_only=1\n"
        "P2_BATCH2_DRAW corpse=0 key=ground|Armor clip=wait\n"
        f"P2_BATCH2_MOVE id=346001 dx=0.000 dz=0.000 dist=0.000\n"
        f"P2_BATCH2_MOVE id=346002 dx={dist:.3f} dz=0.000 dist={dist:.3f}\n"
        "PASS P2_BATCH2_RUNTIME\n")


def test_validate_movement_gate_passes_when_an_actor_moves():
    evidence = validate(_log(12.0), 0, _manifest())
    assert evidence['passed'] is True
    assert evidence['checks']['movement'] is True
    assert evidence['moved_generators'] == ['346002']


def test_validate_movement_gate_fails_when_all_stationary():
    evidence = validate(_log(0.0), 0, _manifest())
    assert evidence['checks']['movement'] is False
    assert evidence['passed'] is False
