# UFO: Alien Invasion Remaster — Scope and Preservation Contract

**Status:** Accepted baseline  
**Purpose:** Define what the remaster is allowed to change and what remains canonical.

## 1. Project intent

The UFO: Alien Invasion remaster modernizes the game's presentation and sound while preserving the game itself.

The project is not a gameplay redesign. The existing UFO: Alien Invasion gameplay is the canonical behavioral reference.

A returning player should encounter the same underlying game decisions, rules, tactical outcomes, strategic outcomes, progression, balance, and content behavior, presented through a modern audiovisual runtime.

## 2. Core rule

> The canonical game decides what happens. The remaster decides how it is presented.

The presentation runtime may consume canonical state and canonical events. Presentation systems must not feed simulation results back into gameplay-authoritative systems.

## 3. Canonical gameplay domain

Unless explicitly changed by a future project-level decision, the following are treated as canonical gameplay:

- campaign mechanics;
- Geoscape behavior;
- tactical combat rules;
- Time Unit behavior;
- reaction fire;
- weapon and equipment behavior;
- damage calculations;
- soldier statistics and progression;
- alien behavior;
- gameplay AI;
- research;
- production;
- base management;
- aircraft and interception mechanics;
- economy;
- mission generation;
- campaign progression;
- victory and failure conditions;
- multiplayer gameplay rules where applicable;
- gameplay-affecting content data;
- line-of-sight, pathfinding, cover, collision, movement, and other gameplay-authoritative spatial results.

## 4. Remaster domain

The remaster may substantially modernize presentation, including:

### 4.1 Rendering

- Vulkan 1.4 renderer;
- physically based material presentation;
- modern lighting;
- hardware ray tracing;
- shadows;
- reflections;
- indirect-lighting presentation;
- volumetric and atmospheric effects;
- particles;
- post-processing;
- HDR rendering and output;
- modern display handling.

### 4.2 Animation

- modern skeletal animation;
- animation blending;
- inverse kinematics where appropriate;
- higher-quality action presentation;
- death animation and ragdoll transitions;
- secondary motion.

Animation represents canonical gameplay events. It does not redefine them.

### 4.3 Presentation physics

Presentation-only physics may drive:

- ragdolls;
- debris;
- shell casings;
- particles;
- loose visual props;
- secondary motion;
- cloth-like effects;
- visually simulated destruction aftermath.

Presentation physics is never authoritative for gameplay.

### 4.4 User-interface presentation

The UI may be visually and technically modernized while preserving the meaning and gameplay effect of player decisions.

Modernization may include:

- scalable high-resolution UI;
- improved typography;
- improved layout;
- improved information hierarchy;
- modern input presentation;
- better visual feedback;
- HDR-aware presentation.

### 4.5 Audio

The audio presentation may be substantially replaced or modernized:

- positional audio;
- environmental acoustics;
- weapon and impact sound;
- ambient sound;
- UI sound;
- voice;
- music;
- mixing;
- filters;
- reverberation;
- HRTF-capable headphone presentation.

OpenAL Soft + EFX is the chosen baseline.

## 5. Presentation physics boundary

Presentation physics may visually simulate the consequences of canonical events but cannot decide those consequences.

Examples:

- A canonical death event may trigger a ragdoll. The ragdoll cannot alter cover, pathfinding, damage, AI decisions, or other canonical state.
- A canonical explosion may trigger physically simulated debris. Debris cannot injure units or modify canonical collision.
- A canonical projectile hit may produce physically simulated fragments or impact effects. Physics cannot turn a canonical miss into a hit, or vice versa.
- A canonical door state may drive a physical or animated door presentation. Physics cannot decide whether the canonical door is open or closed.

There is no presentation-physics feedback path into canonical gameplay state.

## 6. Performance/qualification target and runtime configurability

The primary performance/qualification profile is:

- **GPU:** Intel Arc B580 / Battlemage / Xe2;
- **CPU:** Intel Core i9-9900K;
- **scene/render resolution:** 1920×1080;
- **target refresh/frame rate:** 60 Hz / sustained close to 60 FPS;
- **frame-budget reference:** 16.667 ms;
- **display-quality target:** VESA DisplayHDR 600-class output when HDR is enabled;
- **API:** Vulkan 1.4;
- **ray tracing:** Vulkan KHR ray-tracing pipeline extensions.

These values define the machine/profile against which performance and quality are optimized. They are **not hardcoded user-facing runtime settings**.

The runtime must allow the player to select, subject to actual platform/device support:

- output display/monitor;
- window/fullscreen mode;
- output resolution;
- refresh rate;
- HDR on/off (with actual capability/result reported);
- render resolution or native-output rendering mode;
- OpenAL playback device or system default;
- HRTF mode/profile.

The project prioritizes presentation quality and RT effectiveness at the 1080p60 B580/i9-9900K qualification profile. Higher/lower resolutions and different refresh rates remain valid runtime configurations and are not required to meet the same performance number.

Upscaling or reconstruction may be offered as optional modes, but the qualification profile must not depend on upscaling to remain near 60 FPS at a 1920×1080 RenderExtent on the Arc B580.

## 7. Gameplay-preservation test

Before accepting a presentation change, ask:

> Can this change cause the same canonical game state and the same player action to produce a different gameplay-authoritative result?

If the answer is yes, the change is outside the normal remaster presentation scope and requires an explicit scope decision.

## 8. Gameplay bug fixes

A gameplay-affecting bug fix is not automatically in scope merely because it is a bug fix.

Changes that alter canonical results must be tracked separately from presentation work and approved explicitly.

## 9. Success criterion

The project succeeds when UFO: Alien Invasion remains recognizably and behaviorally the same game while its graphics, animation, physical presentation, user-interface presentation, and sound meet the remaster's modern presentation target.
