/**
 * @file
 * @brief M1-only tactical identity/snapshot/publication integration fixtures.
 *
 * Injected into ufotestall only with UFOAI_M1_TACTICAL_PUBLICATION_TESTS=ON.
 * The sealed src/tests/CMakeLists.txt remains untouched.
 */

#include "../../src/tests/test_shared.h"
#include "../../src/client/client.h"
#include "../../src/client/presentation/canonical_identity.h"
#include "../../src/client/presentation/tactical_presentation_event.h"
#include "../../src/client/presentation/tactical_publication.h"
#include "../../src/client/presentation/tactical_snapshot_legacy_adapter.h"

#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace {

void ConfigureActor(le_t& actor, int entnum, entity_type_t type)
{
	actor.init();
	actor.inuse = true;
	actor.type = type;
	actor.entnum = entnum;
}

TEST(M1TacticalPublicationTest, ProjectsOnlyCanonicalActorValues)
{
	le_t entities[5];
	for (le_t& entity : entities)
		entity.init();

	ConfigureActor(entities[0], 37, ET_ACTOR);
	entities[0].pos[0] = 4;
	entities[0].pos[1] = 5;
	entities[0].pos[2] = 2;
	entities[0].oldPos[0] = 3;
	entities[0].oldPos[1] = 5;
	entities[0].oldPos[2] = 2;
	entities[0].team = 2;
	entities[0].pnum = 7;
	entities[0].ucn = 1234;
	entities[0].TU = 41;
	entities[0].maxTU = 52;
	entities[0].HP = 31;
	entities[0].maxHP = 40;
	entities[0].STUN = 3;
	entities[0].morale = 66;
	entities[0].maxMorale = 100;
	entities[0].state = STATE_CROUCHED | STATE_SHAKEN;
	entities[0].fieldSize = ACTOR_SIZE_NORMAL;

	ConfigureActor(entities[1], 38, ET_ACTORHIDDEN);
	entities[1].HP = 17;
	entities[1].maxHP = 20;

	entities[2].inuse = true;
	entities[2].type = ET_ITEM;
	entities[2].entnum = 39;

	ConfigureActor(entities[3], MAX_EDICTS, ET_ACTOR);
	entities[3].HP = 999;
	ConfigureActor(entities[4], -1, ET_ACTOR);
	entities[4].HP = 998;

	ufo::presentation::TacticalActorView invalidProjection = {};
	EXPECT_FALSE(ufo::presentation::legacy::tryProjectActor(entities[3], invalidProjection));
	EXPECT_FALSE(ufo::presentation::legacy::tryProjectActor(entities[4], invalidProjection));

	const ufo::presentation::TacticalSnapshot snapshot =
		ufo::presentation::legacy::buildSnapshot(77, entities, 5);
	ASSERT_EQ(77u, snapshot.publicationSerial());
	ASSERT_EQ(2u, snapshot.actors().size());

	const ufo::presentation::TacticalActorView& actor = snapshot.actors()[0];
	EXPECT_EQ(ufo::canonical::EntityId(37), actor.entity);
	EXPECT_EQ(4, actor.gridPosition.x);
	EXPECT_EQ(5, actor.gridPosition.y);
	EXPECT_EQ(2, actor.gridPosition.z);
	EXPECT_EQ(3, actor.previousGridPosition.x);
	EXPECT_EQ(5, actor.previousGridPosition.y);
	EXPECT_EQ(2, actor.previousGridPosition.z);
	EXPECT_EQ(2, actor.team);
	EXPECT_EQ(7, actor.playerNumber);
	EXPECT_EQ(1234, actor.characterUcn);
	EXPECT_EQ(41, actor.timeUnits);
	EXPECT_EQ(52, actor.maxTimeUnits);
	EXPECT_EQ(31, actor.hitPoints);
	EXPECT_EQ(40, actor.maxHitPoints);
	EXPECT_EQ(3, actor.stun);
	EXPECT_EQ(66, actor.morale);
	EXPECT_EQ(100, actor.maxMorale);
	EXPECT_EQ(static_cast<uint16_t>(STATE_CROUCHED | STATE_SHAKEN), actor.stateFlags);
	EXPECT_EQ(ACTOR_SIZE_NORMAL, actor.fieldSize);

	EXPECT_EQ(ufo::canonical::EntityId(38), snapshot.actors()[1].entity);
	EXPECT_EQ(17, snapshot.actors()[1].hitPoints);
}

TEST(M1TacticalPublicationTest, PublishesOrderedSnapshotAndEventAfterMirrorMutation)
{
	const ufo::presentation::TacticalPublicationPtr previousPublication =
		ufo::presentation::latestTacticalPublication();
	const uint64_t previousSequence = previousPublication ? previousPublication->event().sequence : 0;

	cl.numLEs = 1;
	ConfigureActor(cl.LEs[0], 73, ET_ACTOR);
	cl.LEs[0].HP = 25;
	cl.LEs[0].maxHP = 30;

	ufo::presentation::legacy::publishAfterCanonicalEvent(static_cast<uint16_t>(EV_ACTOR_STATS), 4000);
	const uint64_t firstSequence = previousSequence + 1;
	const ufo::presentation::TacticalPublicationPtr firstPublication =
		ufo::presentation::latestTacticalPublication();
	ASSERT_TRUE(firstPublication);
	ASSERT_EQ(firstSequence, firstPublication->event().sequence);
	ASSERT_EQ(firstSequence, firstPublication->snapshot().publicationSerial());
	ASSERT_EQ(1u, firstPublication->snapshot().actors().size());
	EXPECT_EQ(25, firstPublication->snapshot().actors()[0].hitPoints);
	EXPECT_EQ(4000u, firstPublication->event().scheduledPresentationTime);
	EXPECT_EQ(ufo::presentation::TacticalPresentationEventKind::CanonicalMirrorUpdated, firstPublication->event().kind);
	EXPECT_EQ(static_cast<uint16_t>(EV_ACTOR_STATS), firstPublication->event().canonicalType.value);

	cl.LEs[0].HP = 19;
	ufo::presentation::legacy::publishAfterCanonicalEvent(static_cast<uint16_t>(EV_ACTOR_STATECHANGE), 4050);
	const uint64_t secondSequence = firstSequence + 1;
	const ufo::presentation::TacticalPublicationPtr secondPublication =
		ufo::presentation::latestTacticalPublication();
	ASSERT_TRUE(secondPublication);
	ASSERT_NE(firstPublication.get(), secondPublication.get());
	ASSERT_EQ(secondSequence, secondPublication->event().sequence);
	ASSERT_EQ(secondSequence, secondPublication->snapshot().publicationSerial());
	ASSERT_EQ(1u, secondPublication->snapshot().actors().size());
	EXPECT_EQ(19, secondPublication->snapshot().actors()[0].hitPoints);
	EXPECT_EQ(4050u, secondPublication->event().scheduledPresentationTime);
	EXPECT_EQ(ufo::presentation::TacticalPresentationEventKind::CanonicalMirrorUpdated, secondPublication->event().kind);
	EXPECT_EQ(static_cast<uint16_t>(EV_ACTOR_STATECHANGE), secondPublication->event().canonicalType.value);

	/* A held immutable publication must retain the earlier canonical mirror values. */
	EXPECT_EQ(firstSequence, firstPublication->event().sequence);
	EXPECT_EQ(25, firstPublication->snapshot().actors()[0].hitPoints);

	cl.LEs[0].init();
	cl.numLEs = 0;
}

TEST(M1TacticalPublicationTest, PublicValueTypesStayPointerFreeAndCopyable)
{
	EXPECT_EQ(sizeof(uint32_t), sizeof(ufo::canonical::EntityId));
	EXPECT_EQ(3u, sizeof(ufo::presentation::GridPosition));
	EXPECT_EQ(sizeof(uint16_t), sizeof(decltype(ufo::presentation::TacticalActorView::stateFlags)));
	EXPECT_TRUE(std::is_standard_layout<ufo::presentation::TacticalActorView>::value);
	EXPECT_TRUE(std::is_trivially_copyable<ufo::presentation::TacticalActorView>::value);
	EXPECT_TRUE(std::is_standard_layout<ufo::presentation::TacticalPresentationEventHeader>::value);
	EXPECT_TRUE(std::is_trivially_copyable<ufo::presentation::TacticalPresentationEventHeader>::value);
}

} // namespace
