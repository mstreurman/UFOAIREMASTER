# RT False-Color Visualizer and Frame-Wide Debug Modes

**Status:** Implementation specification baseline  
**Related ADR:** ADR-027

## 1. Purpose

RT debug visualization must answer two distinct questions:

```text
Where did hardware RT execute?
Where is the resolved final image influenced by RT-derived data?
```

Temporal reconstruction means those are not equivalent.

## 2. Named mode

Primary diagnostic:

```text
RT Isolation
```

Invariant:

```text
NON-RT = exact pure-red hue at output reference white

HDR display-linear:
    (203, 0, 0) nits

SDR display-linear:
    (100, 0, 0) nits
```

Normal raster/material/beauty appearance is intentionally removed.

No beauty-image tinting in this mode.

If RT stops globally, the screen should become unmistakably solid red.

## 3. Isolation submodes

Required:

```text
Current-Ray Activity
Resolved RT Influence
RT Contribution Strength
```

### Current-Ray Activity

Shows where a fresh hardware ray attributable to the displayed screen pixel/sample was launched this frame.

Included:

```text
directional shadow
local visibility/ReSTIR visibility
reflection
```

DDGI rays originate at probes and are excluded from this per-pixel classification.

Use a separate `DDGI Probe Update Activity` view for probe provenance.

### Resolved RT Influence

Shows pixels whose resolved presentation result contains RT-derived information, including:

```text
current ray
temporal RT history
RT reconstruction
reflection upsample
DDGI interpolation from RT-traced probes
```

### RT Contribution Strength

Hue identifies RT subsystem.

Intensity indicates magnitude of final influence/contribution.

Zero influence remains exact red.

## 4. Base false-color palette

Starting semantic palette:

```text
RED:
    no RT

YELLOW:
    directional RT shadow/visibility

ORANGE:
    local-light RT visibility / ReSTIR DI

CYAN:
    RT reflection

GREEN:
    DDGI / RT-derived indirect

MAGENTA:
    multiple major RT classes overlap

WHITE:
    high/multi-effect RT diagnostic overlap
```

Exact display shades may be adjusted for readability while retaining pure red as the non-RT invariant.

## 5. Effect-isolation modes

Provide:

```text
All RT
Directional Shadow
Local Visibility / ReSTIR
Reflection
DDGI
```

In an effect-isolation view:

```text
selected effect present/influential -> diagnostic color
anything else -> pure red
```

Other RT effects do not appear unless the selected combined mode requests them.

## 6. Directional-shadow encoding

Shadow RT is visibility, not radiance.

Starting encoding:

```text
bright yellow:
    directional RT says visible

dark yellow/ochre:
    directional RT says blocked

red:
    no directional-RT result/influence
```

## 7. Reflection debug views

Provide:

```text
Reflection eligibility
Current reflection ray activity
Raw reflection radiance
Reflection hit distance
Reflection hit object ID
Reflection direction
Temporal reflection result
Reflection variance
Atrous stage 1
Atrous stage 2
Atrous stage 4
Final reflection
Reflection contribution strength
```

## 8. ReSTIR DI debug views

Provide:

```text
selected light ID
reservoir age
reservoir M
fresh candidate count
temporal reuse accepted
spatial reuse accepted/count
final visibility
final contribution
```

Selected-light ID uses stable false-color hashing so instability appears as visible color flicker.

## 9. Directional shadow debug views

Provide:

```text
raw checkerboard visibility
resolved visibility
penumbra/blocker distance
temporal result
filtered result
blocker object ID
history age
```

## 10. DDGI debug views

Provide:

```text
nearest/selected probe ID
probe irradiance
probe distance moments
probe classification
probe relocation magnitude
probe update age
probe weight/contribution
final DDGI contribution
```

## 11. Acceleration-structure visualization

World-overlay toggles:

```text
TLAS instance bounds
BLAS bounds
BLAS partitions
static vs dynamic
opaque vs alpha-test
tactical level
instance masks
```

Starting classification colors:

```text
static opaque:
    blue

static alpha-test:
    yellow

rigid reusable:
    green

dynamic deforming:
    magenta
```

Mask visualization may map:

```text
Shadow 0x01      -> red channel
Reflection 0x02  -> green channel
GI 0x04          -> blue channel
```

Thus 0x07 appears white.

## 12. Temporal rejection view

Encode rejection reasons into a bitmask.

Conceptual:

```cpp
enum TemporalRejectReason : uint32_t {
    None              = 0,
    Offscreen         = 1u << 0,
    NoHistory         = 1u << 1,
    ObjectMismatch    = 1u << 2,
    NormalMismatch    = 1u << 3,
    PlaneMismatch     = 1u << 4,
    RoughnessMismatch = 1u << 5,
    HitIdMismatch     = 1u << 6,
    Disocclusion      = 1u << 7
};
```

Full-frame mode maps dominant/selected reason to stable false colors.

## 13. Ray-count/RT-cost visualization

Provide:

```text
ray count heatmap
any-hit/alpha-test heatmap
history length
history rejection frequency
reconstruction confidence
```

Heatmap units and scaling are displayed in legend.

## 14. Difference views

Provide diagnostic comparison modes:

```text
Final - NoRT
Final - NoReflections
Final - NoDDGI
Final - NoRTShadows
```

These are separate from strict RT Isolation.

Difference views may use signed/absolute heatmaps.

## 15. Split-screen comparison

Support:

```text
beauty | RT debug
```

with a movable divider.

This does not alter the strict RT debug colors on the debug side.

## 16. Diagnostic buffer policy

Do not permanently burden production shaders with all debug writes.

Use:

```text
Production
Visualization
Probe
```

shader/pipeline variants from shared Slang modules.

Shared ray/material functions preserve production-equivalent behavior.

## 17. RT debug mode overhead

When debug visualizers are disabled:

```text
production payload sizes
production RT shader paths
production transient memory
```

must remain unaffected except for minimal Basic instrumentation required by architecture.

Visualization cost is explicitly measured and excluded from normal performance baselines.

## Diagnostic output-space authority

Architecture 055 owns false-color output/provenance semantics.

RT Isolation is generated in the active display-linear output space after scene tone mapping/color transform and before PQ/sRGB transfer encoding.

```text
NON-RT = (outputReferenceWhiteNits, 0, 0)
```

The palette bypasses scene exposure, bloom and creative grading.
