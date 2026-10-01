"""Private same-frame equal-depth Honeywisp material comparison, not gameplay."""
import re

def instrument(source):
    anchor='    for(Teki* actor:selected){'
    draw='    if(!actors.count(static_cast<PelletView*>(actor)))return false;'
    if source.count(anchor)!=1 or source.count(draw)!=1:raise ValueError('Unexpected copied family')
    source=source.replace('bool logged[2]', 'Shape* comparison=nullptr;\nbool logged[2]')
    source=source.replace(anchor,'    comparison=gameflow.loadShape("courses/pikmin2room/qurione_comparison.mod",true);if(!comparison)std::abort();\n'+anchor)
    block=r'''
    if(!corpse){Matrix4f view;view.makeLookat(Vector3f(0,80,300),Vector3f(0,20,0),nullptr);
     for(int corrected=0;corrected<2;++corrected){Shape* fixed=corrected?comparison:clips.at("waitl").front();
      Matrix4f world,modelView;world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),Vector3f(corrected?35:-35,0,0));view.multiplyTo(world,modelView);
      fixed->updateAnim(gfx,modelView,nullptr,actor);fixed->drawshape(gfx,*gfx.mCamera,nullptr);
      static bool shown[2]={false,false};if(!shown[corrected]){shown[corrected]=true;std::printf("P2_QURIONE_MATERIAL_COMPARE corrected=%d pose=waitl_0 x=%d y=0 z=0 scale=1 yaw=0 eye=0,80,300 target=0,20,0 ambient=%u,%u,%u fov=%.4f aspect=%.4f\n",corrected,corrected?35:-35,gfx.mAmbientColour.r,gfx.mAmbientColour.g,gfx.mAmbientColour.b,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio);}}
     return true;
    }
'''
    return source.replace(draw,draw+block)

def evidence(text):
    rows=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in text.splitlines() if line.startswith('P2_QURIONE_MATERIAL_COMPARE ')]
    if len(rows)!=2 or {r.get('corrected') for r in rows}!={'0','1'}:raise ValueError('Missing paired draw')
    for r in rows:
        expected=dict(pose='waitl_0',x='35' if r['corrected']=='1' else '-35',y='0',z='0',scale='1',yaw='0',eye='0,80,300',target='0,20,0')
        if any(r.get(k)!=v for k,v in expected.items()):raise ValueError('Unmatched transform')
    for k in ('ambient','fov','aspect'):
        if any(k not in r for r in rows) or len({r[k] for r in rows})!=1:raise ValueError('Unmatched light/projection')
    return dict(rows=rows,fixed_pose_equal_depth=True,shared_frame_light=True,live_behavior=False,source_lighting_parity=False)
