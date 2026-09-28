"""Private GL acceptance for the HikariKinoko camera-facing billboard (#429).

Builds a replacement-main fixture that loads the native Hikari MOD, renders it at
two world yaws with the real preview camera, and asserts the OGL backend took the
billboard path with a screen-aligned draw matrix. Never install as the player
executable.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

from scripts.build_pikmin2_fixture import build_fixture
from scripts.preview_pikmin2_room import overlay

APP = r'''
class MaterialApp final:public PlugPikiApp {
 int frames=0,ready=0;Shape* model=nullptr;
public:
 int idle()override{
  int result=PlugPikiApp::idle();require(++frames<1200,"startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++ready;
  if(!model){
   int heap=gsys->setHeap(SYSHEAP_App);
   model=gameflow.loadShape("courses/pikmin2room/hikari.mod",true);require(model,"model missing");
   for(int i=0;i<model->mTexAttrCount;++i)if(model->mTexAttrList[i].mTexture)model->mTexAttrList[i].mTexture->attach();
   gsys->setHeap(heap);
   std::printf("HIKARI_MODEL meshes=%d materials=%d\n",model->mMeshCount,model->mMaterialCount);
  }return result;
 }
 void draw(Graphics& gfx)override{
  PlugPikiApp::draw(gfx);if(ready<120||!model)return;require(gfx.mCamera,"camera");
  gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
  gfx.setDepth(true);gfx.useMaterial(nullptr);
  p2billboard::stats().draws=0;p2billboard::stats().max_offdiagonal=0.f;
  auto renderAt=[&](float yaw,const char* path){
   Matrix4f world,view;auto pos=naviMgr->getNavi()->mSRT.t+Vector3f(0,20,0);
   world.makeSRT(Vector3f(1,1,1),Vector3f(0,yaw,0),pos);
   gfx.calcViewMatrix(world,view);gfx.useMatrix(view,0);
   pc_gfx_flush_batch();glClearColor(0,0,0,1);glDepthMask(GL_TRUE);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
   model->updateAnim(gfx,view,nullptr,nullptr);
   model->drawshape(gfx,*gfx.mCamera,nullptr);gfx.useMaterial(nullptr);
   return capture(path);
  };
  auto y0=renderAt(0.f,"hikari-yaw0.ppm");
  auto y90=renderAt(1.5707963f,"hikari-yaw90.ppm");
  require(p2billboard::stats().draws>0,"billboard draw path not activated");
  require(p2billboard::stats().max_offdiagonal<1e-3f,"billboard draw matrix not screen aligned");
  std::size_t visible=0;for(std::size_t i=0;i<y0.size();++i)visible+=y0[i]>8;
  require(visible>100,"billboard invisible");
  std::printf("PASS HIKARI_BILLBOARD draws=%llu max_offdiagonal=%.6f visible=%zu\n",
              p2billboard::stats().draws,p2billboard::stats().max_offdiagonal,visible);
  std::fflush(nullptr);std::_Exit(0);
 }
};
'''


def build(native, build_dir, output, head):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = (Path(__file__).resolve().parents[1] / 'scripts/pikmin2_material_binding_fixture.cpp').read_text()
    start = source.index('class MaterialApp final:')
    end = source.index('int main(', start)
    source = '#include "pc_p2_billboard_draw.h"\n' + source[:start] + APP + source[end:]
    source = source.replace('960,720', '960,540')
    anchor = 'pc_settings_p2d_init();'
    assert source.count(anchor) == 1
    source = source.replace(anchor, anchor + '''auto* window=SDL_GL_GetCurrentWindow();SDL_SetWindowSize(window,960,540);SDL_Rect bounds;require(SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds)==0,"display bounds");SDL_SetWindowPosition(window,bounds.x+(bounds.w-960)/2,bounds.y+(bounds.h-540)/2);''')
    (output / 'fixture.cpp').write_text(source)
    return build_fixture(build_dir, native, output / 'fixture.cpp', output / 'build', head)


def stage(source, mod, output):
    source = Path(source).resolve()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    overrides = {'dataDir/courses/pikmin2room/hikari.mod': Path(mod).read_bytes()}
    overlay(source / 'assets', output / 'assets', overrides)
    shutil.copyfile(source / 'p2-pod.txt', output / 'p2-pod.txt')
    return output


def run(exe, directory):
    exe = Path(exe).resolve()
    provenance = json.loads((exe.parent / 'provenance.json').read_text())
    expected = provenance.get('artifacts', {}).get(str(exe), {}).get('sha256')
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    if provenance.get('status') != 'built' or digest != expected:
        raise ValueError('Require completed, unchanged isolated fixture build')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    with (directory / 'native.log').open('x') as log:
        result = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=directory, env=env,
                                stdout=log, stderr=subprocess.STDOUT, startupinfo=startup, timeout=180)
    text = (directory / 'native.log').read_text(errors='replace')
    report = dict(exit=result.returncode, exe_sha256=digest,
                  passed=result.returncode == 0 and 'PASS HIKARI_BILLBOARD' in text)
    (directory / 'result.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    b.add_argument('--native', type=Path, required=True)
    b.add_argument('--build-dir', type=Path, required=True)
    b.add_argument('--output', type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run')
    r.add_argument('--exe', type=Path, required=True)
    r.add_argument('--source', type=Path, required=True)
    r.add_argument('--mod', type=Path, required=True)
    r.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'build':
        print(json.dumps(build(args.native, args.build_dir, args.output, args.head), indent=2))
    else:
        directory = stage(args.source, args.mod, args.output)
        print(json.dumps(run(args.exe, directory), indent=2))
