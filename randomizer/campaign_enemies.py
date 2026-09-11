"""Campaign-wide seeded compatibility pools, with explicit species coverage."""
from .campaign_data import CAMPAIGN_HASH, CAMPAIGN_SLOTS, CAMPAIGN_SOURCES


def resolve_campaign(seed, slot):
    from .seed import SeedRandom
    rng=SeedRandom(str(seed)+'/campaign-enemies-v1/'+slot)
    for attempt in range(256):
        actual={}
        for cohort in ('ground','frog','flying','dwarf','grub','aquatic'):
            rows=[r for r in CAMPAIGN_SLOTS if r['cohort']==cohort]
            if cohort=='ground':
                # The eleven Impact files are one alternating-day encounter, not
                # eleven independent heavy enemies. Keep its choice consistent.
                impact=rng.shuffle([4,32,15])[0]
                for r in rows:
                    actual[r['uid']]=impact if r['stage']==0 else (4,32,15)[rng.below(3)]
                # One heavy replacement in each large area, without consuming
                # Spring's two renewable adult sources merely to keep both species local.
                heavies=rng.shuffle([9,17,24])
                for stage,heavy in zip((1,2,3),heavies):
                    eligible=[r for r in rows if r['stage']==stage and r['first_day']==2 and 0<r['respawn_days']<=5 and (r['expires_after_day'] is None or r['expires_after_day']>=29)]
                    actual[rng.shuffle(eligible)[0]['uid']]=heavy
            else:
                choices=rows[0]['miniboss_allowed']
                values=rng.shuffle([choices[i%len(choices)] for i in range(len(rows))])
                actual.update((r['uid'],v) for r,v in zip(rows,values))
        # Retain renewable ground farming in both logic farming areas.
        early=lambda stage:{actual[r['uid']] for r in CAMPAIGN_SLOTS if r['stage']==stage and r['cohort']=='ground' and r['first_day']==2 and 0<r['respawn_days']<=5}
        if not ({4,32}<=early(1) and early(2)&{4,32,15}):continue
        if not all(any(r['stage']==stage and actual[r['uid']]!=r['original'] for r in CAMPAIGN_SLOTS) for stage in range(4)):continue
        layout=dict(version='campaign-enemies-v1',catalog_hash=CAMPAIGN_HASH,assignments=[dict(uid=r['uid'],actual=actual[r['uid']]) for r in CAMPAIGN_SLOTS])
        sources=campaign_sources(layout)
        # Guarantee every collectible bestiary species has a surviving source.
        from .catalog import BESTIARY_TARGETS
        from .enemies import sources_for
        if not all(sources_for(sources,species) for species,_ in BESTIARY_TARGETS.values()):continue
        return layout
    raise ValueError('cannot satisfy campaign enemy coverage and farming constraints')


def campaign_sources(layout):
    actual={r['uid']:r['actual'] for r in layout['assignments']}
    return dict(version='campaign-enemy-sources-v1',sources=[dict(stage=r['stage'],original=r['original'],actual=actual.get(r['uid'],r['original']),protected=r['protected'],first_day=r['first_day']) for r in CAMPAIGN_SOURCES])


def campaign_bootstrap(manifest):
    layout=manifest['campaign_layout']
    return 'ENEMY_CAMPAIGN 1 '+CAMPAIGN_HASH+' '+str(len(CAMPAIGN_SLOTS))+' 1 '+' '.join(str(r['uid'])+' '+str(r['actual']) for r in layout['assignments'])+'\n'
