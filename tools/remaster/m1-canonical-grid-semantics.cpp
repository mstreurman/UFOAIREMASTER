#include <cmath>
#include <cstdlib>
#include <iostream>

#include "../../src/common/grid_semantics.h"

namespace {

void require (const bool condition, const char* label)
{
	if (!condition) {
		std::cerr << "M1 canonical grid semantics: FAIL: " << label << '\n';
		std::exit(1);
	}
}

void requireFloat (const float actual, const float expected, const char* label)
{
	require(std::fabs(actual - expected) < 0.0001f, label);
}

} // namespace

int main ()
{
	/* Grid_MoveNext: zero/unreachable cells reject, reachable cells return areaFrom unchanged. */
	require(Grid_MoveNextSemantic(0, 0x0102) == ROUTING_UNREACHABLE, "MoveNext zero-length cell must reject");
	require(Grid_MoveNextSemantic(ROUTING_NOT_REACHABLE, 0x0102) == ROUTING_UNREACHABLE,
		"MoveNext ROUTING_NOT_REACHABLE cell must reject");
	require(Grid_MoveNextSemantic(2, 0x0603) == 0x0603, "MoveNext must preserve reachable areaFrom value");
	require(Grid_MoveNextSemantic(254, 0x0724) == 0x0724, "MoveNext must accept maximum reachable TU value");

	/* Grid_ShouldUseAutostand: strict saving after two crouch transitions. */
	require(Grid_ShouldUseAutostandSemantic(11, 4), "autostand should win when upright + transitions is cheaper");
	require(!Grid_ShouldUseAutostandSemantic(10, 4), "autostand equality must remain false");
	require(!Grid_ShouldUseAutostandSemantic(9, 4), "autostand must reject when crouched path is cheaper");
	require(!Grid_ShouldUseAutostandSemantic(ROUTING_NOT_REACHABLE, ROUTING_NOT_REACHABLE),
		"autostand must preserve legacy unreachable-value arithmetic");

	/* Grid_PosToVec: actor centering plus floor clamped to [0, UNIT_HEIGHT]. */
	{
		const pos3_t pos = {128, 128, 0};
		vec3_t vec;
		Grid_PosToVecSemantic(ACTOR_SIZE_NORMAL, pos, 0, vec);
		requireFloat(vec[0], 16.0f, "normal actor X center at grid origin");
		requireFloat(vec[1], 16.0f, "normal actor Y center at grid origin");
		requireFloat(vec[2], 32.0f, "normal actor Z center with zero floor");

		Grid_PosToVecSemantic(ACTOR_SIZE_NORMAL, pos, -12, vec);
		requireFloat(vec[2], 32.0f, "negative floor must clamp to zero");

		Grid_PosToVecSemantic(ACTOR_SIZE_NORMAL, pos, 12, vec);
		requireFloat(vec[2], 44.0f, "partial floor height must be added unchanged");

		Grid_PosToVecSemantic(ACTOR_SIZE_NORMAL, pos, 128, vec);
		requireFloat(vec[2], 96.0f, "floor above one level must clamp to UNIT_HEIGHT");
	}

	{
		const pos3_t pos = {128, 128, 0};
		vec3_t vec;
		Grid_PosToVecSemantic(ACTOR_SIZE_2x2, pos, 0, vec);
		requireFloat(vec[0], 32.0f, "2x2 actor X center");
		requireFloat(vec[1], 32.0f, "2x2 actor Y center");
	}

	{
		const pos3_t pos = {130, 127, 1};
		vec3_t vec;
		Grid_PosToVecSemantic(ACTOR_SIZE_NORMAL, pos, 4, vec);
		requireFloat(vec[0], 80.0f, "offset grid X conversion");
		requireFloat(vec[1], -16.0f, "offset grid Y conversion");
		requireFloat(vec[2], 100.0f, "level + floor Z conversion");
	}

	std::cout << "M1 canonical grid semantics: PASS\n";
	std::cout << "  services: MoveNext, GridShouldUseAutostand, GridPosToVec\n";
	std::cout << "  semantic cases: 15\n";
	std::cout << "  behavior: exact-result helpers used by production grid.cpp\n";
	return 0;
}
