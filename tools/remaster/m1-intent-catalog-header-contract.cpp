#include "../../src/client/presentation/strategic_intent.h"
#include "../../src/client/presentation/tactical_intent.h"

#include <type_traits>

int main()
{
	using namespace ufo::presentation;

	static_assert(std::is_standard_layout<StrategicIntent>::value, "");
	static_assert(std::is_trivially_copyable<StrategicIntent>::value, "");
	static_assert(std::is_standard_layout<TacticalIntent>::value, "");
	static_assert(std::is_trivially_copyable<TacticalIntent>::value, "");

	StrategicIntent strategic = {};
	strategic.kind = StrategicIntentKind::SendAircraftToMission;
	strategic.aircraft = ufo::canonical::AircraftId(3u);
	strategic.mission = ufo::canonical::MissionId(7u);

	TacticalIntent tactical = {};
	tactical.kind = TacticalIntentKind::SetReactionFire;
	tactical.entity = ufo::canonical::EntityId(9u);
	tactical.value0 = 1;

	return strategic.aircraft.value == 3u
		&& strategic.mission.value == 7u
		&& tactical.entity.value == 9u ? 0 : 1;
}
