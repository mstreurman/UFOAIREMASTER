# Reference — M1 Strategic Typed-Intent Dispatch Qualification

**Date:** 2026-09-07  
**Status:** PASS  
**Scope:** establish the typed presentation-intent dispatch mechanism with one representative strategic action  
**Reference compiler:** GCC 16.2.1  
**Reference OpenAL Soft discovery:** 1.25.2

## Qualified architecture

The first end-to-end typed strategic intent is:

```text
SetCampaignTimeLapse(int32 lapseIndex)
```

Qualified ownership:

```text
presentation / future retained UI
    |
    | submitSetCampaignTimeLapse()
    v
ufoai_remaster_intent_runtime
    strict C++26
    bounded FIFO transport
    monotonic sequence IDs
    |
    v
strategic_intent_legacy_adapter
    retained C++11 / Main ownership
    bounded drain
    |
    v
CP_TrySetGameTimeLapse()
    canonical validation + mutation/rejection
    |
    +--> StrategicIntentResult
    |
    v
CP_CampaignRun()
    |
    v
StrategicSnapshot publication
```

Presentation submission itself does not mutate canonical campaign state.

Canonical rules remain authoritative.

## Public contract

The shared intent contract remains C++11-compatible and exposes value-only records:

```text
StrategicIntentKind
StrategicIntentDisposition
StrategicIntent
StrategicIntentSubmission
StrategicIntentResult
```

Public intent/result records are standard-layout and trivially copyable.

No live canonical pointer crosses the intent boundary.

## Runtime transport contract

The C++26 runtime is bounded:

```text
pending intents: 256
result feedback: 256
Main drain budget: 64 intents/frame
```

Qualified behavior includes:

```text
FIFO ordering
bounded capacity
non-zero monotonic accepted sequence IDs
queue-full rejection
typed result correlation
campaign-lifetime reset
sequence monotonicity across reset
```

A transport-accepted intent is not equivalent to canonical acceptance.

## Canonical action owner

The first canonical helper is:

```cpp
bool CP_TrySetGameTimeLapse(int gameLapseValue);
```

It preserves canonical campaign ownership by requiring existing campaign/time-scale rules, validating the lapse range, mutating only on acceptance, and applying the existing canonical time update path.

Invalid values are rejected without mutation.

## Main-loop ordering

Qualified source ordering:

```text
CP_IsRunning()
    ->
applyPendingStrategicIntents()
    ->
CP_OnGeoscape()
    ->
CP_CampaignRun()
    ->
publishAfterCanonicalCampaignUpdate()
```

This satisfies the strategic presentation separation rule:

```text
typed intent
-> Main/campaign adapter
-> canonical validation/mutation or rejection
-> next immutable strategic publication
```

## Focused typed-intent qualification

Command:

```bash
python3 tools/remaster/test-m1-strategic-intent-dispatch.py
```

Result:

```text
M1 strategic typed intent dispatch lane: PASS
  C++11 public intent contract: PASS
  bounded C++26 intent/result runtime: PASS
  queue FIFO/capacity/reset/sequence contract: PASS
  Main-before-campaign-before-publication ordering audit: PASS
  canonical time-lapse validation/mutation audit: PASS
  strategic intent integration GoogleTests: 3/3
  sealed src/tests/CMakeLists.txt: unchanged
```

Integration tests:

```text
AcceptedIntentMutatesOnlyThroughCanonicalAdapter
CanonicalValidationRejectsInvalidLapse
CampaignResetDropsPendingPresentationIntentState
```

## Nearby preservation lanes

Strategic publication:

```text
M1 strategic publication focused lane: PASS
```

Tactical publication:

```text
M1.2 tactical publication lane: PASS
tactical publication GoogleTests: 3/3
```

The qualified C++26 intent runtime participates in the same production/test build graph as the already-qualified publication runtime.

## Canonical regression state

The OpenAL Soft 1.25.2 environment rotation resealed the current canonical evidence while preserving the canonical corpus:

```text
104/104 PASS
104/104 PASS
two-run trace repeatability: PASS
```

Current accepted environment identity:

```text
aa42dc88f980845c94fab1d6ff992657f935f25c13ac418c16aa25f3baa5d305
```

Current M0.5 evidence identity:

```text
33143dc7b737b6df7c2a1496500bf435b6563f259d60561c4db7f75c2f00bed2
```

Historical evidence identities remain historical and are not rewritten.

## Fresh production builds

Legacy production:

```bash
cmake --preset legacy-m0-f44 --fresh
cmake --build --preset legacy-m0-f44
```

Result:

```text
PASS
[389/389] Linking CXX executable ufo
```

Remaster production:

```bash
python3 tools/remaster/provision-m0-slang.py
cmake --preset remaster-m0-f44 --fresh
cmake --build --preset remaster-m0-f44
```

Result:

```text
Slang v2026.17 provisioning: PASS
M0 dependency discovery: PASS
OpenAL: 1.25.2
PASS
[37/37] Linking CXX executable ufo
```

Observed remaster dependency discovery also includes:

```text
Vulkan 1.4.341
SDL3 3.4.14
Slang 2026.17
Jolt v5.6.0
spirv-val found
b3sum found
ccache found
```

## M1 conclusion

The **typed presentation-intent dispatch mechanism is qualified**.

This does not mean every future strategic/tactical action has already been migrated.

The mechanism is now an implemented production rule:

```text
presentation input
-> typed value intent
-> bounded C++26 transport
-> C++11 canonical/Main adapter
-> canonical validation/mutation or rejection
-> immutable publication
```

Future strategic actions should extend this vocabulary/dispatch path rather than reintroduce direct UI mutation.

Tactical player actions may require their own server/canonical authority adapter, but must preserve the same ownership principle.

## Remaining M1 work

The remaining M1 work is primarily migration breadth and temporary-consumer containment:

```text
expand strategic typed intent vocabulary as presentation consumers migrate
introduce tactical/server-authority typed intents where needed
keep legacy consumers behind temporary adapters
prevent new presentation paths from depending on legacy UI/renderer internals
```

The typed-intent transport/dispatch architecture itself does not need to be redesigned for each new action.
