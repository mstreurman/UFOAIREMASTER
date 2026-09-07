/**
 * @file
 * @brief Main-thread legacy campaign adapter for typed strategic intents.
 */
#pragma once

namespace ufo {
namespace presentation {
namespace legacy {

/** Apply a bounded batch of queued presentation intents on canonical Main ownership. */
void applyPendingStrategicIntents();

/** Reset pending intent/result state at campaign lifetime boundaries. */
void resetStrategicIntentAdapter();

} // namespace legacy
} // namespace presentation
} // namespace ufo
