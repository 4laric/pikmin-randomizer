"""Two ordinary mouth losses must match the actual production poison events."""
import math,re
CARD='d40f4089381645dad2a425e70bceea4a61d959e5e611dd7604fdfaf352b3268f'
def rows(text,marker):
    return [dict(re.findall(r'([A-Za-z_][A-Za-z_0-9]*)=([^\s]+)',line)) for line in text.splitlines() if line.startswith(marker+' ')]
def assess(text,*,exit_code,elapsed,timed_out,saved_card,current_card,**unused):
    if exit_code!=0 or timed_out or not math.isfinite(elapsed) or not 0<elapsed<180:raise ValueError('Bounded actual native0 required')
    if saved_card!=current_card or saved_card['sha256']!=CARD:raise ValueError('Unchanged original74 card required')
    checkpoint=rows(text,'P2_WHITE_ADULT_CHECKPOINT')
    if checkpoint!=[{'generation':str(saved_card['generation']),'sha256':CARD}]:raise ValueError('Actual loader card identity required')
    base=rows(text,'P2_WHITE_ADULT_BASELINE');end=rows(text,'P2_WHITE_ADULT_PASS')
    if len(base)!=1 or len(end)!=1:raise ValueError('Single actual baseline/final required')
    predator=base[0]['predator']
    if base[0]['predator_uid']!='436207616' or not 750<float(base[0]['native_hp'])<=1500:raise ValueError('Original adult native HP/source required')
    # Native following and throwing can both produce an ordinary mouth capture.
    # The captures, not a fixture-imposed throw count, identify the actual victims.
    kinds=['P2_WHITE_ADULT_THROW','P2_WHITE_ADULT_CAPTURE','P2_WHITE_ADULT_CASUALTY']
    throws,captures,losses=[rows(text,k) for k in kinds]
    if len(captures)!=2 or len(losses)!=2:raise ValueError('Two actual mouth/loss witnesses required')
    victims=[r['victim'] for r in captures]
    if len(set(victims))!=2 or [r['victim'] for r in losses]!=victims:raise ValueError('Actual two victim pointers/order required')
    if any(r['predator']!=predator for r in captures):raise ValueError('Actual source predator mouth required')
    thrown=[r['victim'] for r in throws]
    if len(throws)>2 or len(set(thrown))!=len(thrown) or any(v not in victims for v in thrown):raise ValueError('Every claimed throw must be a unique actual mouth victim')
    poison=rows(text,'P2_WHITE_POISON_CONSUMED')
    if len(poison)!=2 or [r['victim'] for r in poison]!=victims:raise ValueError('Exact once-per-actual-victim poison required')
    if any(r['predator']!=predator or r['damage']!='750.000' for r in poison):raise ValueError('Exact supported predator/750 callback required')
    lines=text.splitlines()
    for victim in victims:
        def at(marker):return next(i for i,l in enumerate(lines) if l.startswith(marker+' ') and f'victim={victim} ' in l+' ')
        if not at(kinds[1])<at('P2_WHITE_POISON_CONSUMED')<at(kinds[2]):raise ValueError('Actual capture/poison/casualty order required')
        if victim in thrown and not at(kinds[0])<at(kinds[1]):raise ValueError('Claimed actual throw must precede its capture')
    p=end[0]
    for key,value in dict(consumed='2',field_white='0',stored_white='13',original_red='5',remaining_total='18',native_dead_state='2',source_uid='436207616',actual_ordinary_inputs='1').items():
        if p.get(key)!=value:raise ValueError('Strict corpse/conservation final required')
    if p['predator']!=predator or float(p['native_health'])!=0 or p['corpse'] in ('0','0x0','(nil)'):raise ValueError('Native death/live-owned corpse required')
    return dict(mode_passed=True,gameplay_accepted=True,scope='native TEKI_Swallow adapter ordinary two White ingestion/death/corpse',damage_per_victim=750,consumed=2,remaining=18,actual_throws=len(throws),natural_following_captures=2-len(throws),full_P2_AI=False,card_unchanged=True)
