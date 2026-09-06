/**
 * @file
 * @brief Small testable helpers for gameplay-authoritative server spatial adapters.
 */
#pragma once

#include "../shared/ufotypes.h"

/**
 * @brief Canonical inclusive map-bounds predicate used by game_import_t::isOnMap.
 *
 * The server map box is canonical state.  Keep this helper independent from
 * presentation collision, renderer bounds, Jolt, Vulkan, or other mirror data.
 */
inline bool SV_CanonicalPointWithinMapBounds (const vec3_t mins, const vec3_t maxs, const vec3_t point)
{
    return point[0] >= mins[0] && point[0] <= maxs[0]
        && point[1] >= mins[1] && point[1] <= maxs[1]
        && point[2] >= mins[2] && point[2] <= maxs[2];
}
