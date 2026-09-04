# Audio Frame Schedule, Telemetry and Benchmarks

**Status:** Architecture baseline  
**Related ADR:** ADR-024

## 1. Main-frame production

During CPU frame presentation phases:

```text
PresentationEvent processing
    ->
audio event creation

Presentation finalization
    ->
listener/emitter/environment state
```

Workers may prepare exclusive ranges.

Main owns ordered publication.

## 2. Discrete audio commands

Canonical/presentation events create ordered commands such as:

```text
weapon one-shot
impact one-shot
actor vocal
door start/stop
loop state
music state transition
UI feedback
```

Main publishes to the SPSC command ring.

No worker completion order defines command ordering.

## 3. Continuous snapshot

After presentation finalization:

```text
AudioStateSnapshot::Seal()
```

Then publish latest immutable state to AudioControl.

Continuous fields include:

```text
listener
emitters
bus state
acoustic zone state
cutaway revision
presentation time/frame index
```

## 4. AudioControl service pass

On wake:

```text
consume ordered commands
consume newest state snapshot
update logical voices
run virtualization
service occlusion results
service stream queues
batch OpenAL property updates
check device/latency telemetry
sleep
```

## 5. Occlusion job scheduling

Acoustic queries are presentation CPU jobs.

Suggested lane:

```text
SmtFriendly
```

except when query volume/profile shows PrimaryOnly is beneficial.

AudioControl does not execute large BVH query batches itself.

Flow:

```text
AudioControl/state analysis
    ->
occlusion request batch
    ->
job system acoustic queries
    ->
result ring
    ->
AudioControl filter/send update
```

Results are tagged with:

```text
voice generation
source/emitter generation
snapshot/frame age
```

Stale results are discarded.

## 6. AudioControl and scheduler affinity

Reserve one worker-core SMT sibling.

Benchmark candidate mappings:

```text
WorkerCore[5].sibling
WorkerCore[4].sibling
unrestricted SCHED_OTHER
```

Production uses the placement with best sustained CPU-frame tails.

Do not place AudioControl on Main/Render sibling in baseline.

## 7. OpenAL internal threads

Do not attempt to set affinity or priority of OpenAL Soft internal backend/mixer threads initially.

Fedora/PipeWire/OpenAL Soft retain their normal scheduling behavior.

Only intervene after a reproducible profile demonstrates a problem.

## 8. CPU budgets

Starting targets, not measured results:

```text
Main-side audio snapshot/event preparation:
    <= 0.20 ms/frame

AudioControl normal service pass:
    <= 0.25 ms average
    <= 0.75 ms 99th percentile

acoustic occlusion jobs:
    <= 0.30 ms aggregate normal frame

stream decode:
    background; must not consume frame-critical physical work under pressure
```

OpenAL Soft's internal mixer CPU is measured separately.

## 9. Physical-source benchmark

Compare:

```text
64
96
128
```

physical OpenAL sources.

Scenarios:

```text
HRTF off
HRTF on
many simultaneous weapon impacts
dense ambience
large tactical map
```

Baseline remains:

```text
96
```

until target measurements favor another count.

## 10. Logical voice benchmark

Compare:

```text
256
512
1024
```

logical voices for:

```text
ranking cost
memory
virtual-clock update
promotion/thrash behavior
```

Baseline:

```text
512
```

## 11. HRTF benchmark

Measure:

```text
Off
Auto actual-off
Auto actual-on
On
```

and available HRTF profiles.

Record:

```text
OpenAL mixer CPU
total process CPU
underruns
source-count scaling
perceptual localization
```

Do not infer HRTF state solely from requested mode.


## 11.1 Device-selection benchmark/qualification

Audio qualification must cover at least:

```text
SystemDefault through PipeWire
one explicitly selected named OpenAL endpoint
device switch/reopen while the game is running
selected-device disconnect with fallback/recovery
```

On the current workstation, the 10:47 capture provides a Bluetooth A2DP/aptX-HD system-default case and an AE-7 analog endpoint as two concrete local test routes. Neither endpoint is hardcoded into production configuration.

## 12. EFX benchmark

Test:

```text
0
1
2
4
8
```

active effect slots with representative EAX Reverb/reverb parameters.

Record:

```text
mixer CPU
frame CPU interference
wet-path stability
```

Normal-play baseline targets no more than four expensive active wet effects.

## 13. Occlusion benchmark

Compare update frequencies:

```text
5 Hz
10 Hz
20 Hz
```

and ray budgets.

Scenes:

```text
open exterior
dense rooms
doors opening/closing
multiple floors
long corridors
RMA map
```

Evaluate:

```text
CPU cost
filter zippering
response latency
false occlusion/leaking
```

## 14. Stream benchmark

At 48 kHz compare queue shapes:

```text
4 x 1024 frames
4 x 2048 frames
6 x 1024 frames
```

Record:

```text
underruns
wake frequency
decode headroom
transition latency
```

Baseline:

```text
4 x 1024
```

## 15. Required telemetry

Expose:

```text
requested/actual device
actual sample rate
OpenAL renderer/vendor/version
AL/ALC extension list in diagnostics
HRTF requested state
HRTF actual status/profile
max auxiliary sends

logical voice count
physical source count
virtual voice count
source steals/frame
voice promotions/frame

active EFX slots
active filtered sources
active primary/secondary sends

occlusion queries/sec
occlusion result age
stream queued frames
stream underruns

AudioControl service time
command queue depth
command overflow/coalesce count
snapshot age
```

## 16. Audio debug view

Developer UI should permit inspection of a selected logical voice:

```text
AudioVoiceId
owner
asset
bus
logical cursor
physical/virtual state
priority score
gain stack
position/distance
occlusion
direct filter
aux sends
environment zone
OpenAL source ID internally
```

Raw OpenAL source ID remains diagnostic only.

## 17. Regression/replay

Presentation event capture should retain enough audio commands/state identity to replay:

```text
one-shot ordering
loop transitions
music state changes
environment transitions
```

Audio waveform bit-exactness is not a canonical regression requirement.

Regression checks focus on:

```text
same logical command ordering
same voice IDs/priorities
same source promotion decisions under fixed settings
no dropped critical commands
```

## 18. Failure policy

Audio subsystem failure:

```text
logs detailed error
enters silent presentation mode where possible
continues canonical game
```

It must never:

```text
abort canonical mission state
change simulation
change AI
change LOS
change damage
```

## Budget-accounting authority

Architecture 055 classifies AudioControl service time as an independent concurrent target.

Main-side audio preparation is inside the Main/presentation publication path.
