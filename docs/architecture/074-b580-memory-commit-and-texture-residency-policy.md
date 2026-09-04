# B580 Memory Commitment and Texture Residency Policy

**Status:** Exact implementation specification  
**Related ADR:** ADR-032  
**Related architecture:** 030, 061, 070

## 1. Purpose

Make the custom Vulkan allocator's logical pool sizes compatible with the captured B580 memory budget and the immutable live persistent sampled-image heap contract.

## 2. Logical pool vs committed memory

A pool may have:

```text
base block size
growth policy
free-list/arena metadata
```

without owning a Vulkan memory block yet.

At renderer initialization:

```text
unused allocator pools commit 0 bytes
```

except memory needed by specifically documented bootstrap resources.

## 3. First allocation

On first real allocation for a pool:

```text
blockBytes =
    max(
        baseBlockSize,
        aligned required allocation size)
```

subject to Vulkan memory-type/alignment/dedicated-allocation requirements.

Subsequent growth uses the existing pool growth policy.

## 4. FrameContext arenas

Each FrameContext owns logically separate:

```text
FrameTransient
AccelerationStructureScratch
UploadStaging
Readback
```

storage.

Those arenas:

```text
allocate on demand
reuse committed blocks after retirement
do not eagerly commit every documented growth unit
```

## 5. Retained high-water behavior

After a representative workload, arenas may retain blocks for reuse to avoid allocation churn.

Retained capacity is:

```text
telemetry-visible
pressure-trimmable after safe retirement
not part of correctness
```

Do not automatically preserve pathological one-time peaks forever.

## 6. Baseline persistent sampled-image heap residency

Before publishing a texture slot:

```text
create image/view
upload baseline required mip set
complete transitions
reach SHADER_READ_ONLY_OPTIMAL
publish immutable descriptor/view identity
```

While referenced/live:

```text
the published view is not mip-stripped
the descriptor is not rewritten to a reduced view
the image is not repurposed for another asset
```

## 7. Pressure actions

### Normal

```text
allow accepted prefetch/residency behavior
```

### Constrained

```text
stop aggressive prefetch
defer speculative/low-value texture loads
avoid growth that is not needed for current frame/world
```

### High

```text
evict whole unreferenced texture assets after safe retirement
trim unreferenced staging/readback/transient cache blocks
delay optional residency
reduce/stop speculative asset prefetch
```

### Critical

```text
suspend optional uploads
evict lowest-priority unreferenced whole assets
trim safely retired allocator cache blocks
emit visible developer telemetry
preserve canonical game state
```

## 8. Forbidden baseline pressure behavior

Do not:

```text
strip mips from a live persistent sampled-image heap view
change a live persistent sampled-image heap view identity
rewrite a live descriptor to a different asset
depend on sparse residency that is not in the accepted baseline
```

## 9. Whole-texture eviction eligibility

A texture is eligible for whole-asset eviction only when:

```text
no strong asset/material reference requires it
replacement/fallback material state is already published if needed
all FrameContexts that may reference its descriptor retire
transfer/upload ownership is complete
descriptor slot retirement conditions are met
```

Architecture 061/070 descriptor retirement remains authority.

## 10. Future mip streaming

True partial mip streaming requires a later explicit contract covering at least:

```text
residency representation
view/descriptor publication
old-view retirement
history/material consistency
streaming priority
memory-pressure behavior
capture/replay diagnostics
```

Possible future mechanisms include:

```text
new immutable view + new descriptor slot publication
sparse residency where appropriate
```

Baseline 026 does not choose one.

## 11. Telemetry

Per pool record:

```text
logical base block size
VkDeviceMemory committed
suballocated live bytes
free bytes
cached/retained bytes
high-water committed
high-water live
allocation/growth count
trim count/bytes
```

Texture residency records:

```text
published texture count
committed bytes
unreferenced evictable bytes
pending retirement bytes
prefetch bytes
eviction count
```

## 12. Target principle

Use the current Vulkan memory budget as the pressure denominator.

Do not pre-consume a large fraction of budget merely to make every logical pool look initialized.
