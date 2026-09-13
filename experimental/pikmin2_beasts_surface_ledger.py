"""Opt-in Beasts host persistence; no native launcher or save migration."""
from copy import deepcopy
from experimental.pikmin2_surface_ledger import SurfaceLedger, _hex, _surface
from experimental.pikmin2_beasts_checkpoint_reference import digest


class BeastsSurfaceLedger(SurfaceLedger):
    """Uses the same locked, atomic surface-ledger.json as the tutorial writer.

    Fresh sessions only. Caller-supplied handoffs are not authenticated here.
    Floor3 is durable but cannot launch or return to the surface.
    """
    def __init__(self,directory,content,campaign,adapter):
        super().__init__(directory,content,campaign)
        if adapter.profile['content']!=content or adapter.identity!=digest(adapter.profile):
            raise ValueError('Beasts profile/content differs')
        self.adapter=deepcopy(adapter)

    def _validate(self,state):
        if isinstance(state,dict) and type(state.get('schema')) is int and state['schema']==1:
            super()._validate(state)
            if state['phase']!='surface' or state['revision']!=0:
                raise ValueError('Beasts requires a fresh surface ledger; migration unsupported')
            return state
        if not isinstance(state,dict) or set(state)!={'schema','campaign','content','origin','revision','phase','surface','trip','events'}:
            raise ValueError('Invalid Beasts ledger fields')
        if (type(state['schema']) is not int or state['schema']!=2
                or not _hex(state['campaign'],32) or state['content']!=self.content or not _hex(state['origin'],64)):
            raise ValueError('Invalid Beasts ledger identity')
        _surface(state['surface'],state['content'])
        if state['phase'] not in ('cave','failed'):raise ValueError('Unsupported Beasts ledger phase')
        trip=state['trip']
        if (not isinstance(trip,dict) or set(trip)!={'id','cave','token','checkpoint'}
                or not _hex(trip['id'],32) or trip['cave']!='forest_1'):
            raise ValueError('Invalid Beasts trip')
        checkpoint=self.adapter.validate(trip['checkpoint'])
        if checkpoint['trip']!=trip['id'] or checkpoint['status']!=('active' if state['phase']=='cave' else 'failed'):
            raise ValueError('Beasts trip/checkpoint differs')
        expected_token=self.adapter.token(checkpoint) if state['phase']=='cave' else None
        if trip['token']!=expected_token:raise ValueError('Beasts boundary token differs')
        events=state['events']
        expected_keys={f'enter:{trip["id"]}'}|{f'floor:{token}' for token in checkpoint['events']}
        if (not isinstance(events,dict) or set(events)!=expected_keys or any(not _hex(v,64) for v in events.values())
                or type(state['revision']) is not int or state['revision']!=len(events)):
            raise ValueError('Beasts ledger history differs')
        for key,value in state['surface']['receipts'].items():
            if checkpoint['receipts'].get(key)!=value:raise ValueError('Suspended surface receipts regressed')
        return state

    def enter_beasts(self,expected_revision,trip_id):
        if not _hex(trip_id,32):raise ValueError('Invalid Beasts trip identity')
        def apply(state):
            if state['schema']!=1 or state['phase']!='surface' or state['revision']!=0:
                raise ValueError('Beasts requires a fresh surface ledger')
            surface=state['surface']
            checkpoint=self.adapter.initial(trip_id,surface['squad'],surface['health'],surface['receipts'])
            state.update(schema=2,phase='cave',trip=dict(id=trip_id,cave='forest_1',
                         token=self.adapter.token(checkpoint),checkpoint=checkpoint))
        return self._change(expected_revision,f'enter:{trip_id}',dict(trip=trip_id,profile=self.adapter.identity),apply)

    def apply_beasts_floor(self,expected_revision,token,*,squad,health,receipts,conversions,destination_context):
        if not _hex(token,64):raise ValueError('Invalid Beasts boundary token')
        payload=deepcopy(dict(squad=squad,health=health,receipts=receipts,conversions=conversions,destination_context=destination_context))
        def apply(state):
            trip=state['trip']
            if state['schema']!=2 or state['phase']!='cave' or trip['token']!=token:
                raise ValueError('Wrong or terminal Beasts boundary')
            checkpoint=self.adapter.apply(trip['checkpoint'],token,**payload)
            trip['checkpoint']=checkpoint
            state['phase']='failed' if checkpoint['status']=='failed' else 'cave'
            trip['token']=None if state['phase']=='failed' else self.adapter.token(checkpoint)
        return self._change(expected_revision,f'floor:{token}',payload,apply)

    def launch_requirement(self):
        state=self.read()
        if state['schema']!=2:raise ValueError('No Beasts trip')
        return self.adapter.launch_requirement(state['trip']['checkpoint'])

    def enter_cave(self,*args,**kwargs):
        raise ValueError('Use enter_beasts; tutorial entry is unsupported by this writer')

    def apply_floor(self,*args,**kwargs):
        raise ValueError('Use apply_beasts_floor; tutorial handoffs are unsupported by this writer')

    def return_to_surface(self,*args,**kwargs):
        raise ValueError('Beasts return is unsupported; retain the durable checkpoint')
