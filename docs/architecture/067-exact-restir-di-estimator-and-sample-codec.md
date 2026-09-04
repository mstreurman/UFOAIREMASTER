# Exact ReSTIR DI Estimator and Sample Codec

**Status:** Exact implementation specification  
**Related ADR:** ADR-020, ADR-031

## 1. Domain

Baseline local direct lighting:

```text
resolution domain = HalfRenderExtent = ceil(RenderExtent / 2)
qualification example = 960x540 when RenderExtent = 1920x1080
8 fresh candidates per valid half-resolution shading pixel
one final RT visibility ray
```

Candidate visibility is not traced.

## 2. Reservoir semantics

The 32-byte `DirectReservoir` stores:

```text
lightId/lightGeneration
sampleParam0/sampleParam1
weightSum
selectedTarget
finalWeight
packed M/age/flags
```

Invalid if `M==0`, selectedTarget<=0, weightSum<=0, or validity flag is clear.

## 3. Scalar target

ACEScg/AP1 luminance:

```text
Y(rgb) =
    0.2722287168 * r +
    0.6740817658 * g +
    0.0536895174 * b
```

```text
target = max(0, Y(unshadowedRgbIntegrand))
```

Visibility is excluded.

## 4. Unshadowed RGB integrand

`EvaluateLocalLightIntegrand` includes light intensity, BRDF, surface NdotL, emitter cosine where applicable, distance/geometric factor, spot attenuation, range window and area/line measure geometry.

It excludes light-selection proposal probability, shape proposal PDF, RT visibility and reservoir weight.

## 5. Fresh light proposal

One frame-global alias table is built from active local lights ordered by ascending `lightId`, then generation.

Proposal proxy:

```text
Point:
    Y(color) * max(intensity,0) * 4*pi

Spot:
    outerSolidAngle = 2*pi*(1-cosOuter)
    Y(color) * max(intensity,0) * max(outerSolidAngle,1e-6)

Rect:
    area = 4*halfWidth*halfHeight
    Y(color) * max(emittedRadiance,0) * area*pi

Disk:
    area = pi*radius^2
    Y(color) * max(emittedRadiance,0) * area*pi

Line:
    length = 2*halfLength
    Y(color) * max(lineIntensityPerMeter,0) * length
```

Global ineligibility sets proxy zero. Per-pixel range/material response remains in the target.

If total proxy is zero but eligible lights exist, use uniform proposal.

## 6. Deterministic alias-table construction

Use IEEE-754 binary64 Vose construction.

```text
scaled[i] = proxy[i] * N / sum(proxy)

small = min-index priority queue of scaled<1
large = min-index priority queue of scaled>=1
```

Pop minimum indices deterministically, assign probability/alias, update/reinsert.

Quantize:

```text
thresholdU32[i] =
    floor(clamp(probability[i],0,1) * 2^32)
```

Clamp stored integer to [0,0xffffffff]. Self-alias selects itself unconditionally.

Sampling:

```text
column =
    high32(uint64(word0) * uint64(N))

selected =
    column if alias[column]==column
    column if word1 < thresholdU32[column]
    alias[column] otherwise
```

Actual branch probability:

```text
pColumn[c] =
    1                                          if alias[c]==c
    double(thresholdU32[c]) / 4294967296.0     otherwise
```

Actual selected-light probability:

```text
qLightActual[j] =
    sum_c (
        (1/N)*pColumn[c]                    if c==j
      + (1/N)*(1-pColumn[c])                if alias[c]==j && alias[c]!=c
    )
```

Estimator uses `qLightActual`, not the pre-quantized desired probability.

## 7. Shape proposal

```text
Point/Spot radius 0:
    DeltaCenter
    qShape = 1

Point/Spot finite radius:
    SphereDirection
    qShape = 1/(4*pi*r^2)

Rect:
    RectUv
    qShape = 1/area

Disk:
    DiskUv
    qShape = 1/area

Line:
    LineT
    qShape = 1/length
```

```text
qFresh = qLightActual * qShape
```

Finite Point/Spot radius preserves authored point/spot energy:

```text
A = 4*pi*r^2
EvaluateLocalLightIntegrand(area measure) = rgbCenterModel / A
qShape = 1/A
```

The sampled sphere still affects incident direction, NdotL, visibility endpoint and softness.

## 8. Fresh RIS weight

```text
rgb = EvaluateLocalLightIntegrand(x,y)
target = max(0,Y(rgb))
wFresh = target / qFresh
```

Nonpositive/nonfinite target or proposal yields zero weight.

## 9. Weighted reservoir update

For candidate represented by `m` source samples and weight `w`:

```text
newWeightSum = oldWeightSum + w
newM = oldM + m

select if:
    u * newWeightSum < w
```

`u` comes from architecture 068, never execution order.

Fresh candidate:

```text
m=1
w=wFresh
```

If selected, copy identity/sample params and set `selectedTarget = target at current target pixel`.

## 10. M saturation

If M>65535:

```text
scale = 65535 / float(M)
weightSum *= scale
M = 65535
```

## 11. Final reservoir weight

```text
finalWeight =
    weightSum / (float(M) * selectedTarget)
```

Invalid/nonpositive denominator invalidates reservoir.

## 12. Temporal combine

After surface/light validation:

```text
sourceMeff =
    min(source.M,
        20 * max(currentFresh.M,1))

targetCurrent =
    max(0,Y(EvaluateLocalLightIntegrand(currentSurface,sourceSample)))

wTemporal =
    targetCurrent *
    source.finalWeight *
    sourceMeff
```

Combine as candidate with `m=sourceMeff`, `w=wTemporal`, target=`targetCurrent`.

Previous visibility is not reused as weight.

## 13. Spatial pattern

Eight radius-8 half-resolution offsets:

```text
(+8,0) (+6,+6) (0,+8) (-6,+6)
(-8,0) (-6,-6) (0,-8) (+6,-6)
```

```text
rotation = RestirSpatialRotation(frame,pixel) & 7
neighbors = rotation + {0,2,4,6} mod 8
```

Out-of-bounds neighbors skipped without renumbering stream ordinals.

## 14. Spatial combine

For each compatible source:

```text
sourceMeff = source.M

targetCurrent =
    max(0,Y(EvaluateLocalLightIntegrand(targetSurface,sourceSample)))

wSpatial =
    targetCurrent *
    source.finalWeight *
    sourceMeff
```

Combine with `m=sourceMeff`, `w=wSpatial`.

## 15. Final visibility/RGB

```text
rgbUnshadowed =
    EvaluateLocalLightIntegrand(targetSurface,selectedSample)

V = one RT local visibility result, 0 or 1

directRgb =
    rgbUnshadowed *
    finalWeight *
    V
```

## 16. Age

Fresh-only selected reservoir age=0.

Selected temporal/spatial reuse:

```text
age=min(255,sourceAge+1)
```

## 17. UNORM16

```cpp
DecodeUnorm16(q) =
    float(q) * (1/65535)
```

Fresh Rect/Disk/Line params use Philox U16 lanes directly.

## 18. SNORM16

```text
-32768 -> -1
otherwise q/32767
then clamp [-1,1]
```

## 19. Octahedral direction codec

Decode:

```text
x=DecodeSnorm16(qx)
y=DecodeSnorm16(qy)
n=(x,y,1-abs(x)-abs(y))

if n.z<0:
    oldX=n.x
    n.x=(1-abs(n.y))*signNotZero(oldX)
    n.y=(1-abs(oldX))*signNotZero(n.y)

normalize(n)
```

`signNotZero(v)=-1 if v<0 else +1`.

Encode uses standard oct projection, then:

```text
scaled=clamp(p,-1,1)*32767
round nearest, ties away from zero
clamp integer [-32767,32767]
```

Encoder never emits -32768.

## 20. Concentric disk mapping

Shirley-Chiu:

```text
sx=2*u-1
sy=2*v-1

if sx==0 && sy==0: disk=(0,0)
else if abs(sx)>abs(sy):
    r=sx
    theta=(pi/4)*(sy/sx)
else:
    r=sy
    theta=(pi/2)-(pi/4)*(sx/sy)

disk=r*(cos(theta),sin(theta))
```

## 21. Known-answer tests

CPU/Slang tests cover:

```text
UNORM/SNORM endpoints
oct axes/diagonals
disk mapping
alias thresholds/aliases/qLightActual
fresh update
temporal combine
spatial combine
M saturation
finalWeight
final RGB estimator
```

## 22. Debug output

Expose:

```text
qLight
qShape
qFresh
target
candidate weight
weightSum
M
selectedTarget
finalWeight
source class/effective M
visibility
rgbUnshadowed
directRgb
```
