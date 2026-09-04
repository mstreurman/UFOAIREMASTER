# Pipeline Cache, Capacity Overflow, GPU Time and Audio ID Cleanup

**Status:** Exact supporting specification  
**Related ADR:** ADR-030

## 1. Shader binding identity

Architecture 061 `ShaderBindingAbiHash256` is mandatory input to:

```text
.rshader package identity
shader binding/cache key
pipeline description hash
VK_KHR_pipeline_binary persistent cache key
```

A cache entry with a different shader-binding hash is never reused.

## 2. Descriptor-heap overflow

Persistent logical handle capacities are ABI limits. Transient physical heap capacity is implementation state and may be tuned between builds, but no heap allocation grows or remaps silently during a submitted frame.

Telemetry records:

```text
used
capacity
peak
overflow attempt
requesting pass/asset
```

Capacity pressure may trigger content/quality diagnostics, but not shader-binding ABI mutation.

## 3. AudioVoiceId

```cpp
struct AudioVoiceId {
    uint32_t slot;
    uint32_t generation;
};

static_assert(sizeof(AudioVoiceId) == 8);
```

Invalid:

```text
slot = 0xffffffff
generation = 0
```

New slot generation starts at 1.

Reuse increments generation.

If generation would wrap to zero:

```text
retire slot permanently
```

Stale generation commands are rejected by AudioControl.

## 4. AudioEmitterId

`AudioEmitterId` follows the exact same invalid/start/reuse/wrap policy as `AudioVoiceId`.

## 5. Presentation-time authority

Architecture 071 supersedes the old modulo-4096 GPU-time rule.

CPU uses monotonic double time.

GPU uses `presentationTimeHighSeconds` and `presentationTimeLowSeconds`.

Periodic effects use split-time phase helpers; non-periodic continuous effects use local epochs.

Presentation time is not identity, replay order or RNG state.

## 6. BDA alignment telemetry/validation

The allocator validates the architecture-061 minimum 16-byte structured/root-record alignment.

Debug telemetry may report stronger device-required alignments separately.

A misaligned root/array address is a developer validation failure before submission.
