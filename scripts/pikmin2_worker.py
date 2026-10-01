"""Mac worker pilot: doctor, register, run one job, or retry a saved submission."""
import argparse
import json
from pathlib import Path
import platform
import sys
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from workflow.remote_worker import Client,doctor,run_one,retry_submission
from workflow.runner import write
from workflow.handoff import require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['doctor','register','work','retry-result'])
    p.add_argument('--credentials',type=Path)
    p.add_argument('--model',default='opencode-go/muse-spark-1.3-contributor')
    p.add_argument('--attempt',type=Path)
    args=p.parse_args()
    if args.command=='doctor':print(json.dumps(doctor(),indent=2));return
    require(args.credentials is not None,'Private credential file required')
    client=Client(json.loads(args.credentials.read_text(encoding='utf-8-sig')))
    state=Path(__file__).resolve().parents[1]/'output/remote-worker';state.mkdir(parents=True,exist_ok=True)
    instance_path=state/'instance.json'
    if not instance_path.exists():write(instance_path,{'instance':uuid.uuid4().hex})
    instance=json.loads(instance_path.read_text())['instance']
    if args.command=='retry-result':
        require(args.attempt is not None and args.attempt.resolve().is_relative_to(state.resolve()),'Attempt must be under local output/remote-worker')
        print(json.dumps(retry_submission(client,args.attempt)));return
    client.call('register',instance=instance,platform=platform.system(),capabilities=client.credential['capabilities'])
    if args.command=='register':print('Worker registered. No job claimed.');return
    # Exclusive process gate survives crashes; never infer that old children died.
    lock=state/'work.lock'
    with lock.open('x') as stream:stream.write(str(__import__('os').getpid()))
    try:run_one(client,state,instance,args.model)
    finally:lock.unlink()


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError) as exc:
        print(str(exc),file=sys.stderr);sys.exit(2)
