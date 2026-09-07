/**
 * @file
 * @brief Client-Main adapter from typed tactical intents to the existing server protocol.
 */
#pragma once

namespace ufo {
namespace presentation {
namespace legacy {

/**
 * Drain a bounded batch of tactical presentation intents.
 *
 * Successful local translation is only "ForwardedToServer"; authoritative
 * acceptance remains on the tactical game server.
 */
void applyPendingTacticalIntents();

/** Clear pending/result transport state at tactical client-state boundaries. */
void resetTacticalIntentAdapter();

} // namespace legacy
} // namespace presentation
} // namespace ufo
