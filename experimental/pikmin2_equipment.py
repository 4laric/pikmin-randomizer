"""Exploration Kit and Key audit: source-backed specification and a host-side data contract.

Mirrors ``OlimarData`` from ``include/Game/gamePlayData.h`` and the acquisition path in
``PelletGoalState::init``. It is a specification and validation model for #141; it is not
captain runtime state and it does not edit any actor or save interface.
"""
import json

SOURCE = 'native/pikmin2-research'
EXPLORATION_KIT_COUNT = 12   # ODII_FIRST_NON_EXPLORATION_KIT_ITEM
ITEM_COUNT = 13              # ODII_COUNT == PelletList::Mgr::getCount(PLK_Item)
KEY_INDEX = 12               # ODII_TheKey
# ogObjSMenuItem.cpp: Exploration Kit menu slot order, four rows of three ItemIndex values.
MENU_ROWS = ((2, 3, 4), (5, 6, 1), (7, 0, 8), (10, 11, 9))
# Persistence carried by the memory card image (gamePlayDataMemCard.cpp).
PERSISTENCE = dict(
    olimar_data='PlayData::write/read: OlimarData::write emits two "itemFlag" bytes per captain slot; only mOlimarData[0] gates effects.',
    find_item_flags='PlayData::mFindItemFlags: one bit per item config index (13); gates the s16_find_item_%02d cutscene.',
    journal='PelletFirstMemory::firstCarryPellet sets KCF_Earned (bit 1) in mItem[config_index]; completeAll() needs every otakara and item kind.',
    courses='PlayData::mBitfieldPerCourse[i]: PDCF_Open set by openCourse; written per course after the OlimarData block.')


def _item(index, symbol, config, dictionary, model, effect, triggers, kit=True, notes=()):
    return dict(index=index, symbol='ODII_' + symbol, config_name=config, dictionary=dictionary, model=model,
                exploration_kit=kit, effect=effect,
                triggers=[dict(file=f, symbol=s, behavior=b) for f, s, b in triggers], notes=list(notes))


K = 'src/plugProjectKandoU/'
ITEMS = (
    _item(0, 'BruteKnuckles', 'fue_a', 188, 'eq_pwr_punch.bmd',
          'Punch combo: after a landed punch the next press chains PUNCH2 then a stronger PUNCH3.',
          [(K + 'naviState.cpp', 'ODII_BruteKnuckles', 'NaviPunchState KEYEVENT_END advances mComboCounter and starts PUNCH2/PUNCH3.')]),
    _item(1, 'DreamMaterial', 'fue_b', 192, 'eq_elec_helmet.bmd',
          'Electricity immunity: electric enemies and electric gates no longer flick the captain.',
          [(K + 'interactNavi.cpp', 'ODII_DreamMaterial', 'InteractDenki::actNavi returns false without the flick transition.'),
           (K + 'navi.cpp', 'ODII_DreamMaterial', 'Navi::platCallback skips the elec platform flick.')]),
    _item(2, 'AmplifiedAmplifier', 'fue_wide', 194, 'eq_wide_pipe.bmd',
          'Whistle grows to mWideWhistleRadius instead of mPikiCallMaxRadius.',
          [(K + 'naviWhistle.cpp', 'ODII_AmplifiedAmplifier', 'NaviWhistle::update WS_Active picks the wide maximum radius.')]),
    _item(3, 'ProfessionalNoisemaker', 'fue_pullout', 195, 'eq_pull_pipe.bmd',
          'Whistle plucks planted sprouts (Versus mode: only sprouts of the other colour).',
          [(K + 'itemPikihead.cpp', 'ODII_ProfessionalNoisemaker', 'ItemPikihead::Item::interactFue refuses the pluck without it.')]),
    _item(4, 'StellarOrb', 'light_a', 190, 'eq_flashlight.bmd',
          'Cave lighting: mStellarIncrement ramps to 1 and blends the stellar light colours in.',
          [('src/plugProjectYamashitaU/gameLightMgr.cpp', 'ODII_StellarOrb', 'GameLightMgr::updateSpotType ramps mStellarIncrement up (down without it).')]),
    _item(5, 'JusticeAlloy', 'suit_powerup', 193, 'eq_pwr_helmet.bmd',
          'Damage taken is multiplied by mShieldDamageReductionRate.',
          [(K + 'navi.cpp', 'ODII_JusticeAlloy', 'Navi::startDamage and Navi::addDamage scale damage before applying it.')],
          notes=('item_config code=2: model loads with J3DMLF_UsePostTexMtx.',)),
    _item(6, 'ForgedCourage', 'suit_fire', 191, 'eq_fire_helmet.bmd',
          'Fire immunity: fire interactions return before any burn state.',
          [(K + 'interactNavi.cpp', 'ODII_ForgedCourage', 'InteractFire::actNavi returns false; reads mOlimarData[0] explicitly.')],
          notes=('item_config code=2: model loads with J3DMLF_UsePostTexMtx.',)),
    _item(7, 'RepugnantAppendage', 'dashboots', 189, 'eq_dashboots.bmd',
          'Rush boots: mRushBootSpeed movement, wind immunity, faster steep-slope slipping.',
          [(K + 'navi.cpp', 'ODII_RepugnantAppendage', 'Navi::makeVelocity uses mRushBootSpeed instead of mMoveSpeed.'),
           (K + 'naviState.cpp', 'ODII_RepugnantAppendage', 'NaviFollowState uses mRushBootSpeed for the following captain.'),
           (K + 'interactNavi.cpp', 'ODII_RepugnantAppendage', 'InteractWind::actNavi returns false (no wind flick).'),
           (K + 'fakePiki.cpp', 'ODII_RepugnantAppendage', 'Steep SlipCode slip factor 4.0 instead of 2.5.')]),
    _item(8, 'PrototypeDetector', 'radar_a', 186, 'eq_rader_a.bmd',
          'Treasure radar HUD in caves and treasure markers on the map.',
          [(K + 'singleGameSection.cpp', 'ODII_PrototypeDetector', 'Sets DEMO_RADAR_ENABLED on first cave HUD update, draws the sensor, feeds getDetectorFlags.')]),
    _item(9, 'FiveManNapsack', 'radar_b', 187, 'eq_rader_b.bmd',
          'Holding X for 35+ frames lies down so Pikmin carry the captain; also a map detector flag.',
          [(K + 'naviState.cpp', 'ODII_FiveManNapsack', 'NaviWalkState transitions to NSID_Pellet in story mode only with the napsack.'),
           (K + 'singleGameSection.cpp', 'ODII_FiveManNapsack', 'OlimarData::getDetectorFlags map type input.')]),
    _item(10, 'SphericalAtlas', 'map01', 184, 'us_eq_map01.bmd',
          'Opens course 1 (Awakening Wood); its find cutscene ignores distance; g32_get_map plays at the first return day end.',
          [(K + 'gamePlayData.cpp', 'ODII_SphericalAtlas', 'OlimarData::getItem calls playData->openCourse(1).'),
           (K + 'navi_demoCheck.cpp', 'ODII_SphericalAtlas', 'Find-item demo skips the proximity check.'),
           (K + 'singleGS_MainGame.cpp', 'ODII_SphericalAtlas', 'g08_first_return then g32_get_map once (DEMO_First_Globe_Day_End).')],
          notes=('item_config min=max=101: carrying behaviour is a runtime question, not asserted here.',)),
    _item(11, 'GeographicProjection', 'map02', 185, 'us_eq_map02.bmd',
          'Opens course 2 (Perplexing Pool); its find cutscene ignores distance.',
          [(K + 'gamePlayData.cpp', 'ODII_GeographicProjection', 'OlimarData::getItem calls playData->openCourse(2).'),
           (K + 'navi_demoCheck.cpp', 'ODII_GeographicProjection', 'Find-item demo skips the proximity check.')],
          notes=('item_config min=max=101: carrying behaviour is a runtime question, not asserted here.',
                 'Wistful Wild (course 3) opens from singleGS_Ending/singleGS_WorldMap after the debt is paid, only if course 2 is open.')),
    _item(12, 'TheKey', 'key', 196, 'test_key.bmd',
          'Never stored in OlimarData. Story delivery enables Challenge Mode; Challenge delivery opens the floor exit.',
          [(K + 'pelletState.cpp', '"key"', 'PelletGoalState: story mode enableChallengeGame + option save; Challenge skips the pollution-up SE.'),
           (K + 'onyonMgr.cpp', '"key"', 'Challenge mode InteractGotKey stimulates every ItemBigFountain and ItemHole.'),
           (K + 'itemHole.cpp', 'interactGotKey', 'Closed hole plays g2F_appear_hole.'),
           (K + 'itemBigFountain.cpp', 'interactGotKey', 'Closed geyser plays g30_appear_fountain.'),
           (K + 'pelletItem.cpp', '"key"', 'PelletItem::Object::onBounce plays PSSE_EV_KEY_BOUND.')],
          kit=False,
          notes=('item_config code=1: no shadow while resting and Breadbugs cannot carry it (panmodokiCarryable).',
                 'PelletGoalState::init only calls getItem for config index < 12, so the Key never sets an OlimarData bit.',
                 'Story placement: held by Damagumo in yakushima_1; also loose/held in many Challenge caves.')),
)


def item(index):
    if type(index) is not int or not 0 <= index < ITEM_COUNT:
        raise ValueError('Unknown ItemIndex')
    return ITEMS[index]


def by_config_name(name):
    for record in ITEMS:
        if record['config_name'] == name:
            return record
    raise ValueError('Unknown item config name')


def detector_map_type(has_prototype_detector, has_napsack):
    """OlimarData::getDetectorFlags: 0 none, 1 detector, 2 napsack, 3 both."""
    if has_prototype_detector and has_napsack:
        return 3
    if has_prototype_detector:
        return 1
    return 2 if has_napsack else 0


def find_item_cutscene(index):
    """navi_demoCheck.cpp: cutscene name and whether the proximity check is skipped."""
    record = item(index)
    return dict(movie='s16_find_item_%02d' % index, skip_distance_check=index in (10, 11), item=record['symbol'])


class OlimarData:
    """Two flag bytes with the exact bit placement of OlimarData::hasItem/getItem."""

    def __init__(self, flags=(0, 0)):
        flags = tuple(flags)
        if len(flags) != 2 or any(type(f) is not int or not 0 <= f <= 255 for f in flags):
            raise ValueError('OlimarData holds two bytes')
        self.flags = list(flags)

    @staticmethod
    def _slot(index):
        data_idx = index >> 3
        return 1 - data_idx, 1 << (index - (data_idx << 3))

    def has_item(self, index):
        # P2ASSERTBOUNDSLINE(588, ODII_BruteKnuckles, index, ODII_LAST_NON_EXPLORATION_KIT_ITEM): upper bound exclusive.
        if type(index) is not int or not 0 <= index < KEY_INDEX:
            raise ValueError('hasItem index outside the Exploration Kit range')
        slot, bit = self._slot(index)
        return bool(self.flags[slot] & bit)

    def get_item(self, index):
        """Set the flag and return the source side effects (course unlocks)."""
        if type(index) is not int or not 0 <= index < KEY_INDEX:
            raise ValueError('getItem asserts item < ODII_LAST_NON_EXPLORATION_KIT_ITEM')
        slot, bit = self._slot(index)
        self.flags[slot] |= bit
        if index == 10:
            return [('open_course', 1)]
        if index == 11:
            return [('open_course', 2)]
        return []

    def inventory(self):
        """singleGameSection.cpp: the twelve Exploration Kit booleans shown by the menu."""
        return [self.has_item(i) for i in range(EXPLORATION_KIT_COUNT)]

    def to_bytes(self):
        return bytes(self.flags)

    @classmethod
    def from_bytes(cls, data):
        if not isinstance(data, (bytes, bytearray)) or len(data) != 2:
            raise ValueError('OlimarData image is two bytes')
        return cls(tuple(data))

    def clear(self):
        self.flags = [0, 0]


def deliver_upgrade(state, config_name, mode='story'):
    """PelletGoalState::init acquisition for an item-kind pellet reaching the Onion or ship.

    Returns the ordered list of source events. ``state`` is the mutable OlimarData.
    """
    if mode not in ('story', 'challenge', 'versus'):
        raise ValueError('Unknown game mode')
    record = by_config_name(config_name)
    index = record['index']
    events = []
    if mode == 'story' and index < KEY_INDEX:
        already = state.has_item(index)
        events.extend(('side_effect',) + effect for effect in state.get_item(index))
        events.append(('flag_set', record['symbol'], 'repeat' if already else 'first'))
    if config_name == 'key':
        # checkMovie only runs in story and Challenge; onyonMgr only reacts to the Key in Challenge.
        if mode == 'challenge':
            events.append(('interact_got_key', 'ItemBigFountain+ItemHole'))
        elif mode == 'story':
            events.append(('enable_challenge_game', 'PlayCommonData::enableChallengeGame'))
    return events


def course_unlocks(state, debt_paid):
    """Courses opened by equipment and story flags: 0 always, 1 atlas, 2 projection, 3 after debt if 2 is open."""
    opened = {0}
    if state.has_item(10):
        opened.add(1)
    if state.has_item(11):
        opened.add(2)
    if debt_paid and 2 in opened:
        opened.add(3)
    return opened


def specification():
    """Serializable audit table for the issue record."""
    return dict(schema=1, source=SOURCE, exploration_kit_count=EXPLORATION_KIT_COUNT, item_count=ITEM_COUNT,
                menu_rows=[list(r) for r in MENU_ROWS], persistence=PERSISTENCE, items=[dict(i) for i in ITEMS])


if __name__ == '__main__':
    print(json.dumps(specification(), indent=2))
