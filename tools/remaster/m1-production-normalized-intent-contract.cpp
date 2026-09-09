#include "src/client/presentation/strategic_intent.h"

#include <cstdint>
#include <type_traits>

using namespace ufo::presentation;

static_assert(static_cast<uint8_t>(StrategicIntentKind::CreateProduction) == 60,
              "CreateProduction must append without renumbering existing ABI values");
static_assert(static_cast<uint8_t>(StrategicIntentKind::TransferStoredUfo) == 59,
              "existing strategic intent ABI must remain stable");

using IncreaseFn = StrategicIntentSubmission (*)(
    ufo::canonical::BaseId,
    ufo::canonical::ProductionId,
    int32_t);

using SetAmountFn = StrategicIntentSubmission (*)(
    ufo::canonical::BaseId,
    ufo::canonical::ProductionId,
    int32_t);

using CreateFn = StrategicIntentSubmission (*)(
    ufo::canonical::BaseId,
    int32_t,
    ufo::canonical::ItemId,
    ufo::canonical::StoredUfoId,
    const char*,
    int32_t);

static_assert(std::is_same<
    decltype(&ufo::presentation::intent::submitIncreaseProduction),
    IncreaseFn>::value,
    "IncreaseProduction must target an existing ProductionId only");

static_assert(std::is_same<
    decltype(&ufo::presentation::intent::submitSetProductionAmount),
    SetAmountFn>::value,
    "SetProductionAmount must remain explicit absolute target transport");

static_assert(std::is_same<
    decltype(&ufo::presentation::intent::submitCreateProduction),
    CreateFn>::value,
    "CreateProduction must carry subject identity separately");

int main()
{
    return 0;
}
