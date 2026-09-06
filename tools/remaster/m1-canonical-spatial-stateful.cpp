/**
 * @file
 * @brief M1-only stateful canonical spatial boundary fixtures.
 *
 * This file is injected into ufotestall only when
 * UFOAI_M1_SPATIAL_STATEFUL_TESTS=ON.  It deliberately does not modify
 * src/tests/CMakeLists.txt or the sealed M0 regression sources.
 */

#include "../../src/tests/test_shared.h"
#include "../../src/shared/ufotypes.h"
#include "../../src/game/g_local.h"
#include "../../src/game/g_edicts.h"
#include "../../src/server/server.h"
#include "../../src/common/cmodel.h"
#include "../../src/common/grid.h"
#include "../../src/common/routing.h"
#include "../../src/common/tracing.h"
#include "../../src/client/renderer/r_state.h"

#include <cmath>

extern "C" trace_t M1_CanonicalServerTrace(const Line& traceLine, const AABB& box, int contentmask);

namespace {

static void ExpectAABBEqual (const AABB& actual, const AABB& expected)
{
	for (int axis = 0; axis < 3; ++axis) {
		EXPECT_FLOAT_EQ(actual.getMins()[axis], expected.getMins()[axis]);
		EXPECT_FLOAT_EQ(actual.getMaxs()[axis], expected.getMaxs()[axis]);
	}
}

static void ExpectTraceEqual (const trace_t& actual, const trace_t& expected)
{
	EXPECT_EQ(actual.allsolid, expected.allsolid);
	EXPECT_EQ(actual.startsolid, expected.startsolid);
	EXPECT_FLOAT_EQ(actual.fraction, expected.fraction);
	for (int axis = 0; axis < 3; ++axis)
		EXPECT_FLOAT_EQ(actual.endpos[axis], expected.endpos[axis]);
	EXPECT_EQ(actual.planenum, expected.planenum);
	EXPECT_EQ(actual.contentFlags, expected.contentFlags);
	EXPECT_EQ(actual.leafnum, expected.leafnum);
	EXPECT_EQ(actual.mapTile, expected.mapTile);
	EXPECT_EQ(actual.entNum, expected.entNum);
}

static Edict* FindLinkedInlineModelEdict ()
{
	Edict* ent = nullptr;
	while ((ent = G_EdictsGetNextInUse(ent))) {
		if (!ent->model || ent->model[0] != '*')
			continue;
		if (ent->solid != SOLID_BSP)
			continue;
		if (ent->number < 0 || ent->number >= MAX_EDICTS)
			continue;
		if (!sv->edicts[ent->number].linked)
			continue;
		return ent;
	}
	return nullptr;
}

class M1SpatialStatefulTest: public ::testing::Test {
protected:
	static void SetUpTestCase ()
	{
		TEST_Init();
		Com_ParseScripts(true);
		Cvar_Set("sv_threads", "0");
		sv_maxclients = Cvar_Get("sv_maxclients", "1", CVAR_SERVERINFO, "Max. connected clients for test");
		port = Cvar_Get("port", DOUBLEQUOTE(PORT_SERVER), CVAR_NOSET);
		masterserver_url = Cvar_Get("masterserver_url", MASTER_SERVER, CVAR_ARCHIVE, "URL of UFO:AI masterserver");
		sv_genericPool = Mem_CreatePool("server-m1-spatial-stateful");
		com_networkPool = Mem_CreatePool("server-m1-spatial-stateful-network");
		r_state.active_texunit = &r_state.texunits[0];
	}

	static void TearDownTestCase ()
	{
		TEST_Shutdown();
	}

	void SetUp () override
	{
		OBJZERO(*sv);
	}

	void TearDown () override
	{
		SV_ShutdownGameProgs();
	}

	void LoadTrackedMap (const char* mapName)
	{
		ASSERT_NE(-1, FS_CheckFile("maps/%s.bsp", mapName))
			<< "Map resource '" << mapName << ".bsp' for M1 stateful spatial test is missing.";
		SV_Map(true, mapName, nullptr);
	}
};

TEST_F(M1SpatialStatefulTest, RoutingQueriesMatchCanonicalState)
{
	LoadTrackedMap("test_routing");

	vec3_t world;
	pos3_t from;
	pos3_t reachable;
	pos3_t blocked;
	VectorSet(world, 80, 80, 32);
	VecToPos(world, from);
	VectorSet(world, 80, 48, 32);
	VecToPos(world, reachable);
	VectorSet(world, 80, 176, 32);
	VecToPos(world, blocked);

	pathing_t* directReachablePath = Mem_AllocType(pathing_t);
	pathing_t* importReachablePath = Mem_AllocType(pathing_t);
	const bool directReachable = Grid_FindPath(
		sv->mapData.routing, ACTOR_SIZE_NORMAL, directReachablePath, from, reachable,
		0, MAX_ROUTE_TUS, nullptr);
	const bool importReachable = gi.GridFindPath(
		ACTOR_SIZE_NORMAL, importReachablePath, from, reachable, 0, MAX_ROUTE_TUS, nullptr);
	EXPECT_TRUE(directReachable);
	EXPECT_EQ(importReachable, directReachable);

	pathing_t* directBlockedPath = Mem_AllocType(pathing_t);
	pathing_t* importBlockedPath = Mem_AllocType(pathing_t);
	const bool directBlocked = Grid_FindPath(
		sv->mapData.routing, ACTOR_SIZE_NORMAL, directBlockedPath, from, blocked,
		0, MAX_ROUTE_TUS, nullptr);
	const bool importBlocked = gi.GridFindPath(
		ACTOR_SIZE_NORMAL, importBlockedPath, from, blocked, 0, MAX_ROUTE_TUS, nullptr);
	EXPECT_FALSE(directBlocked);
	EXPECT_EQ(importBlocked, directBlocked);

	const bool directStand = RT_CanActorStandHere(sv->mapData.routing, ACTOR_SIZE_NORMAL, from);
	EXPECT_TRUE(directStand);
	EXPECT_EQ(gi.CanActorStandHere(ACTOR_SIZE_NORMAL, from), directStand);

	const float directVisibility = CM_GetVisibility(&sv->mapTiles, from);
	const float importVisibility = gi.GetVisibility(from);
	EXPECT_TRUE(std::isfinite(directVisibility));
	EXPECT_FLOAT_EQ(importVisibility, directVisibility);
}

TEST_F(M1SpatialStatefulTest, WorldTraceLineAndContentsMatchCanonicalState)
{
	LoadTrackedMap("test_routing");

	vec3_t start;
	vec3_t stop;
	VectorSet(start, 80, 80, 64);
	VectorSet(stop, 80, 176, 64);

	const bool directLine = TR_TestLine(&sv->mapTiles, start, stop, TRACE_ALL_LEVELS);
	const bool importLine = gi.TestLine(start, stop, TRACE_ALL_LEVELS);
	EXPECT_EQ(importLine, directLine);

	AABB traceBox;
	traceBox.reset();
	const Line line(start, stop);
	const trace_t directTrace = M1_CanonicalServerTrace(line, traceBox, MASK_ALL);
	const trace_t importTrace = gi.Trace(line, traceBox, nullptr, MASK_ALL);
	EXPECT_TRUE(std::isfinite(directTrace.fraction));
	EXPECT_GE(directTrace.fraction, 0.0f);
	EXPECT_LE(directTrace.fraction, 1.0f);
	ExpectTraceEqual(importTrace, directTrace);

	const vec3_t points[] = {
		{80.0f, 80.0f, 32.0f},
		{80.0f, 176.0f, 32.0f},
		{0.0f, 0.0f, 0.0f},
	};
	for (const auto& point : points)
		EXPECT_EQ(gi.PointContents(point), SV_PointContents(point));
}

TEST_F(M1SpatialStatefulTest, LinkAndUnlinkMutateCanonicalWorldMembership)
{
	LoadTrackedMap("test_game");

	Edict* ent = FindLinkedInlineModelEdict();
	ASSERT_NE(ent, nullptr) << "test_game must expose at least one linked SOLID_BSP inline-model edict";
	ASSERT_TRUE(sv->edicts[ent->number].linked);
	const int linkcountBefore = ent->linkcount;

	gi.UnlinkEdict(ent);
	EXPECT_FALSE(sv->edicts[ent->number].linked);

	gi.LinkEdict(ent);
	EXPECT_TRUE(sv->edicts[ent->number].linked);
	EXPECT_EQ(ent->linkcount, linkcountBefore + 1);
}

TEST_F(M1SpatialStatefulTest, InlineModelOrientationAndBoundsMatchCanonicalState)
{
	LoadTrackedMap("test_game");

	Edict* ent = FindLinkedInlineModelEdict();
	ASSERT_NE(ent, nullptr) << "test_game must expose at least one linked SOLID_BSP inline-model edict";

	AABB importInitial;
	AABB directInitial;
	gi.GetInlineModelAABB(ent->model, importInitial);
	CM_GetInlineModelAABB(&sv->mapTiles, ent->model, directInitial);
	ExpectAABBEqual(importInitial, directInitial);

	vec3_t rotatedAngles;
	VectorCopy(ent->angles, rotatedAngles);
	rotatedAngles[1] += 90.0f;
	gi.SetInlineModelOrientation(ent->model, ent->origin, rotatedAngles);

	AABB importRotated;
	AABB directRotated;
	gi.GetInlineModelAABB(ent->model, importRotated);
	CM_GetInlineModelAABB(&sv->mapTiles, ent->model, directRotated);
	ExpectAABBEqual(importRotated, directRotated);

	/* Restore the canonical model state directly after the import-side mutation. */
	CM_SetInlineModelOrientation(&sv->mapTiles, ent->model, ent->origin, ent->angles);
}

TEST_F(M1SpatialStatefulTest, GrenadeTargetMatchesCanonicalSolver)
{
	LoadTrackedMap("test_game");

	vec3_t from;
	vec3_t at;
	VectorSet(from, 0, 0, 32);
	VectorSet(at, 128, 64, 48);

	const float speeds[] = {300.0f, 1.0f};
	for (const float speed : speeds) {
		vec3_t directV0;
		vec3_t importV0;
		VectorClear(directV0);
		VectorClear(importV0);
		const float directResult = Com_GrenadeTarget(from, at, speed, false, false, directV0);
		const float importResult = gi.GrenadeTarget(from, at, speed, false, false, importV0);
		EXPECT_FLOAT_EQ(importResult, directResult);
		for (int axis = 0; axis < 3; ++axis)
			EXPECT_FLOAT_EQ(importV0[axis], directV0[axis]);
	}
}

TEST_F(M1SpatialStatefulTest, LoadedModelAABBMatchesCanonicalLoader)
{
	LoadTrackedMap("test_game");

	const char* model = "models/objects/abrams/abrams.md2";
	ASSERT_NE(-1, FS_CheckFile("%s", model))
		<< "tracked MD2 fixture required for positive LoadModelAABB coverage is missing";

	AABB importBounds;
	ASSERT_TRUE(gi.LoadModelAABB(model, 0, importBounds));
	EXPECT_GT(importBounds.getWidthX(), 0.0f);
	EXPECT_GT(importBounds.getWidthY(), 0.0f);
	EXPECT_GT(importBounds.getWidthZ(), 0.0f);

	AABB directCachedBounds;
	ASSERT_TRUE(SV_LoadModelAABB(model, 0, directCachedBounds));
	ExpectAABBEqual(importBounds, directCachedBounds);
}

} /* namespace */
