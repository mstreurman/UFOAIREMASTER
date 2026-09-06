/**
 * @file
 * @brief Small exact-result helpers for canonical grid/path semantics.
 */
#pragma once

#include <cassert>

#include "../shared/defines.h"
#include "../shared/ufotypes.h"

/**
 * @brief Preserve Grid_MoveNext's canonical reachability/result rule.
 */
inline int Grid_MoveNextSemantic (const pos_t moveLen, const int areaFrom)
{
	if (!moveLen || moveLen == ROUTING_NOT_REACHABLE)
		return ROUTING_UNREACHABLE;
	return areaFrom;
}

/**
 * @brief Preserve Grid_ShouldUseAutostand's strict TU-saving rule.
 */
inline bool Grid_ShouldUseAutostandSemantic (const int tusCrouched, const int tusUpright)
{
	return tusUpright + 2 * TU_CROUCH < tusCrouched;
}

/**
 * @brief Preserve Grid_PosToVec's actor centering and floor-clamp arithmetic.
 *
 * The caller remains responsible for retrieving the canonical routing floor.
 */
inline void Grid_PosToVecSemantic (const actorSizeEnum_t actorSize, const pos3_t pos, const int gridFloor, vec3_t vec)
{
	assert(actorSize > ACTOR_SIZE_INVALID);
	assert(actorSize <= ACTOR_MAX_SIZE);

	vec[0] = ((int)pos[0] - 128) * UNIT_SIZE + (UNIT_SIZE * actorSize) / 2;
	vec[1] = ((int)pos[1] - 128) * UNIT_SIZE + (UNIT_SIZE * actorSize) / 2;
	vec[2] = (int)pos[2] * UNIT_HEIGHT + UNIT_HEIGHT / 2;

	const int clampedFloor = gridFloor < 0 ? 0 : (gridFloor > UNIT_HEIGHT ? UNIT_HEIGHT : gridFloor);
	vec[2] += clampedFloor;
}
