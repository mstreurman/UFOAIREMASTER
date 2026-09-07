/**
 * @file
 * @brief Immutable strategic snapshot publication seam.
 */
#pragma once

#include "strategic_snapshot.h"

#include <memory>

namespace ufo {
namespace presentation {

using StrategicSnapshotPtr = std::shared_ptr<const StrategicSnapshot>;

StrategicSnapshotPtr latestStrategicSnapshot();

namespace legacy {

void publishAfterCanonicalCampaignUpdate();
void resetStrategicPublication();

} // namespace legacy
} // namespace presentation
} // namespace ufo
