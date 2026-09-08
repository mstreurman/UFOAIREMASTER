#include "../../src/client/presentation/strategic_intent.h"
#include "../../src/client/presentation/tactical_intent.h"
#include <type_traits>
using namespace ufo;
static_assert(std::is_standard_layout<presentation::StrategicIntent>::value, "strategic pod");
static_assert(std::is_trivially_copyable<presentation::StrategicIntent>::value, "strategic trivial");
static_assert(std::is_standard_layout<presentation::TacticalIntent>::value, "tactical pod");
static_assert(std::is_trivially_copyable<presentation::TacticalIntent>::value, "tactical trivial");
int main(){
    presentation::StrategicPosition p={1.0f,2.0f,0.0f};
    auto a=presentation::intent::submitBuildBase(p,"Alpha");
    auto b=presentation::tactical_intent::submitTurnActor(canonical::EntityId(7),3);
    return (a.accepted && b.accepted) ? 0 : 1;
}
