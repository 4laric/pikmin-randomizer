# Reproduce ordinary White retail campaign acceptance (#1191)

Native companionPR135 provides opt-in target pikmin_ci_fixture_white_bank_campaign. This ROOT companion adds the reusable host assessment/card parser and isolated Xvfb/XTest input supervisor from actual74/75, plus a portable one-phase CLI. Ordinary input obtains15Whites from3Ivorybuds, physically hauls original dia_a_red weight180/min15/max25, records once180receipt, stores all15 through ship keys, completes real day3 SAVE, then a separate process loads the same unchanged card and withdraws/moves15Whites. All20 original population and full-color maturity stocks remain strict.

Use a fresh private stage/session from the normal White/Purple/P2/treasure seed staging API. Session manifest must be the actual source manifest; files/assets are never transplanted between fingerprints. Preserve the successful positive run's assessment.json and real campaign card for resume. CLI input hashes identify caller-supplied build/source provenance; they are not a cryptographic claim that an arbitrary executable was built from that source. Keep its real build receipt and qualified component/whole-build limitations separately.

`python3 scripts/run_p2_white_bank_campaign.py --help` lists input parameters. Without --run it validates exact executable/source hashes, original source stage and paired card only. --mode resume requires --saved-assessment PATH from the actual successful positive run; other modes reject it. --session is the existing private session directory containing manifest.json. --stage is the immutable staged run (assets plus p2-* descriptors and white-campaign-staging.json). --exe is the freshly built opt-in fixture, not the human production executable.

Run actual phases inside a fresh owned user service, retaining the foreground SSH connection:

```sh
unit=white-bank-unique-positive.service
systemd-run --user --collect --wait --pipe --unit="$unit" \
  --setenv=WHITE_BANK_UNIT="$unit" \
  -p RuntimeMaxSec=360 -p KillMode=control-group -p KillSignal=SIGKILL \
  -p TimeoutStopSec=1 -p CPUQuota=400% -p MemoryMax=8G -p TasksMax=512 \
  python3 -B scripts/run_p2_white_bank_campaign.py --mode positive \
  --exe /private/build/pikmin_ci_fixture_white_bank_campaign --exe-sha256 ACTUAL_ELF_SHA \
  --source /private/native/tools/p2_white_bank_campaign_runtime.cpp --source-sha256 ACTUAL_CPP_SHA \
  --native-pin ACTUAL_BUILD_COMMIT_OR_COMPONENT_QUALIFICATION --root-pin ACTUAL_ROOT_COMMIT \
  --stage /private/staged/run --session /private/session --run
```

Readiness, forced-down, paused-down and resume use RuntimeMaxSec=60; positive alone360. The CLI verifies actual own MainPID/InvocationID/kernel cgroup and whole-unit KillMode/SIGKILL/deadline. The actual Xlib backend is separately killable with bounded IPC; native work reserves6seconds cleanup. The service contains descendants even if Python dies. On any abrupt termination preserve logs then confirm actual child/process/kernel-cgroup absence before reuse; a missing final report is a failure, never fabricated acceptance. No global display/server/service is modified. Capacity checks and coordination remain practical; no Root issuer, workflow-registry or opaque admission chain is required.

Validation:31 engine-free Python controls (card checksum/version/stock/day/refusal, key ownership/acknowledgement/deadlines, service identity/profile policy); genuine74 unchanged card/stage preflightPASS with no game. The exact extracted service guard functions also passed against a real owned UID1000 Linux unit in230ms (7.5MB), with real MainPID/InvocationID/cgroup/RuntimeMax observations and final kernel-cgroup absence. This harmless control launched no engine; the full new canonical CLI subsequently passed actual native READY26.270s/exit0 with strict20Red/3buds/original cargo/receiver setup on the retained75 ELF, no timeout/cleanup errors and final actual service/kernel absence. Genuine74card stayed unchanged. Generic positive/resume modes were not repeated; their underlying actual74/75 witnesses remain component-qualified. Underlying component74 positive nativePASS294.011s, component75 same-card freshresumePASS36.374s. Their retained-core build receipts are qualified, not latest whole-main gameplay. NativePR includes real-header syntax and compiled fake world-map input controls. Prior failures remain ignored local evidence.

Separate Windows human76 package uses qualified production95bc, genuine74card and frozen asset/import closure. Hash/card preflight and harmless owned Windows Job cleanup passed; its new Windows gameplay is unobserved. Choose FoH on the map then ordinary ship Ctrl+F10/F10; no forged save or prefilled actor writes. Imported P2 map/cinematic compatibility, poison and online White support remain open.
