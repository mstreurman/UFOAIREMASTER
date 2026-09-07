/**
 * @file
 * @brief Temporary adapter from the legacy tactical client mirror into value-only snapshots.
 */

#include "../client.h"
#include "tactical_snapshot_legacy_adapter.h"

#include <algorithm>
#include <vector>

namespace {

bool isTacticalActorType(const entity_type_t type)
{
	return type == ET_ACTOR || type == ET_ACTOR2x2 || type == ET_ACTORHIDDEN;
}

ufo::presentation::GridPosition projectGridPosition(const pos3_t pos)
{
	ufo::presentation::GridPosition projected = {};
	projected.x = pos[0];
	projected.y = pos[1];
	projected.z = pos[2];
	return projected;
}

} // namespace

namespace ufo {
namespace presentation {
namespace legacy {

bool tryProjectActor(const le_s& legacyActor, TacticalActorView& projected)
{
	if (!legacyActor.inuse || !isTacticalActorType(legacyActor.type))
		return false;
	if (legacyActor.entnum < 0 || legacyActor.entnum >= MAX_EDICTS)
		return false;

	TacticalActorView value = {};
	value.entity = canonical::EntityId(static_cast<uint32_t>(legacyActor.entnum));
	value.gridPosition = projectGridPosition(legacyActor.pos);
	value.previousGridPosition = projectGridPosition(legacyActor.oldPos);
	value.team = legacyActor.team;
	value.playerNumber = legacyActor.pnum;
	value.characterUcn = legacyActor.ucn;
	value.timeUnits = legacyActor.TU;
	value.maxTimeUnits = legacyActor.maxTU;
	value.hitPoints = legacyActor.HP;
	value.maxHitPoints = legacyActor.maxHP;
	value.stun = legacyActor.STUN;
	value.morale = legacyActor.morale;
	value.maxMorale = legacyActor.maxMorale;
	value.stateFlags = static_cast<uint16_t>(legacyActor.state);
	value.fieldSize = legacyActor.fieldSize;
	projected = value;
	return true;
}

TacticalSnapshot buildSnapshot(uint64_t publicationSerial, const le_s* entities, std::size_t count)
{
	std::vector<TacticalActorView> actors;
	if (entities != nullptr && count != 0) {
		actors.reserve(count);
		for (std::size_t i = 0; i < count; ++i) {
			TacticalActorView projected = {};
			if (tryProjectActor(entities[i], projected))
				actors.push_back(projected);
		}
	}
	return TacticalSnapshot(publicationSerial, std::move(actors));
}

TacticalSnapshot buildCurrentClientSnapshot(uint64_t publicationSerial)
{
	const int boundedCount = std::max(0, std::min(cl.numLEs, MAX_EDICTS));
	return buildSnapshot(publicationSerial, cl.LEs, static_cast<std::size_t>(boundedCount));
}

} // namespace legacy
} // namespace presentation
} // namespace ufo
