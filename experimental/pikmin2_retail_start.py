"""Original no-demo cave captain initialization, separate from World admission."""
import hashlib
import json

RULE = 'retail-story-no-demo-navi-init/1'
RULE_SOURCES = {'include/Game/Cave/Info.h': '8d7b76ef45810f1093dfb8ee19e89d8b6dc123ae3885609afa9f01476033aa4f',
 'include/Game/mapParts.h': '159445505a92e9ab604cbfdf888ed7ba36b57f64438854a8a1af9260bae3d3bb',
 'src/plugProjectKandoU/baseGameSection.cpp': 'ffc3063e1d088a2806cf391c66b30812af83414cd925e4a303e22244b26fa21f',
 'src/plugProjectKandoU/gameMapParts.cpp': '267df97dceba6034a657d728e38892c273790059b29e25ee60efac26d333fd49',
 'src/plugProjectKandoU/mapMgr.cpp': 'c59a737276448722efb47702d947944e1ff5767176a058668acd06fe99f127fc',
 'src/plugProjectNishimuraU/MapCreator.cpp': 'e33c58655016b23ecc617132df7653ef98483216163f19c2759c41c894327c0a',
 'src/plugProjectNishimuraU/MapNode.cpp': '0fd0279e351dc4bd99bedd52aa227a007ea23b9cd01a1d23ad04cb06ba253ca3',
 'src/plugProjectNishimuraU/RandMapMgr.cpp': 'ec28ff1b934e7e1a38f20e2f7820d0033b5109108b4c0ec064eb759fc47a183e',
 'src/plugProjectNishimuraU/RandMapScore.cpp': '9f721aa295878db4066fb1fb7a08f76feaf2c9c42658c3d14241f2138e0697de'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


RULE_SHA256 = hashlib.sha256(canonical(dict(rule=RULE, sources=RULE_SOURCES))).hexdigest()


def source_start(source, floor, pool_member, pool_sha, layout_member, layout_sha, selected):
    for member, digest in RULE_SOURCES.items():
        if hashlib.sha256((source/member).read_bytes()).hexdigest() != digest:
            raise ValueError('Original Navi initialization source differs: '+member)
    start = floor['pod']
    if start['source']['type'] != 7:
        raise ValueError('Selected start is not original CGT_Start')
    # Actual original rule: getStartPosition returns FIXNODE_Pod global XYZ +50Y.
    # initGenerators then queries ground at this point BEFORE applying X/Z offsets.
    position = start['position']
    record = dict(schema=1, rule=RULE, rule_sha256=RULE_SHA256, rule_sources=RULE_SOURCES,
                  cave=floor['cave'], floor=floor['floor'], layout_sha256=floor['layout_sha256'],
                  cave_source_sha256=floor['source_sha256'], catalog_sha256=floor['catalog_sha256'],
                  source_lines=dict(map_start='RandMapMgr.cpp:182-196',
                                    fixed_node='RandMapScore.cpp:116-122,381-412',
                                    transform='MapNode.cpp:483-527',
                                    storage='MapCreator.cpp:56-63; mapParts.h:260',
                                    captain0='baseGameSection.cpp:834-871',
                                    captain1='baseGameSection.cpp:882-916',
                                    facing='mapMgr.cpp:163-171'),
                  pool=dict(member=pool_member, sha256=pool_sha),
                  slot=dict(member=layout_member, sha256=layout_sha, unit=start['unit'],
                            index=start['index'], spawn_type=7, local=start['source'],
                            unit_definition=selected, transform=floor['layout'][start['unit']],
                            global_position=position, global_yaw_degrees=start['yaw']),
                  map_start=[position[0], position[1]+50.0, position[2]],
                  captains=[dict(id=0, x_offset=-4.526, z_offset=7.453, ground_y_offset=8.5),
                            dict(id=1, x_offset=18.082, z_offset=-11.482, ground_y_offset=8.5)],
                  ground_query='actual MapMgr getMinY at map_start, before horizontal offsets',
                  facing='roundAng(actual MapMgr getMapRotation), not Pod yaw',
                  prerequisites=['story non-versus', 'actual RoomMapMgr with null demo matrix',
                                 'actual zero-existing-Navi initialization branch'],
                  native_ready=False, gameplay_accepted=False)
    record['record_sha256'] = hashlib.sha256(canonical(record)).hexdigest()
    return record
