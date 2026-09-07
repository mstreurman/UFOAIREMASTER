/**
 * @file
 * @brief Temporary legacy-client adapter for immutable tactical snapshot publication.
 */
#pragma once

#include "tactical_snapshot.h"

#include <cstddef>
#include <cstdint>

struct le_s;

namespace ufo {
namespace presentation {
namespace legacy {

bool tryProjectActor(const le_s& legacyActor, TacticalActorView& projected);
TacticalSnapshot buildSnapshot(uint64_t publicationSerial, const le_s* entities, std::size_t count);
TacticalSnapshot buildCurrentClientSnapshot(uint64_t publicationSerial);

} // namespace legacy
} // namespace presentation
} // namespace ufo
