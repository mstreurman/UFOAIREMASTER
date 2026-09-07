/**
 * @file
 * @brief Legacy campaign projection confined behind the strategic snapshot boundary.
 */
#pragma once

#include "strategic_snapshot.h"

#include <cstdint>

namespace ufo {
namespace presentation {
namespace legacy {

StrategicSnapshot buildCurrentStrategicSnapshot(uint64_t publicationSerial);
void resetStrategicSnapshotAdapter();

} // namespace legacy
} // namespace presentation
} // namespace ufo
