/**
 * @file
 * @brief Header file for Alien Containment stuff.
 */

/*
Copyright (C) 2002-2025 UFO: Alien Invasion.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
*/

#pragma once

struct base_s;
struct technology_s;

/** @brief Result of presentation-facing canonical alien-containment mutations. */
typedef enum alienContainmentMutationResult_s {
	AC_CONTAINMENT_MUTATION_APPLIED,
	AC_CONTAINMENT_MUTATION_INVALID_BASE,
	AC_CONTAINMENT_MUTATION_INVALID_TECHNOLOGY,
	AC_CONTAINMENT_MUTATION_NO_CONTAINMENT,
	AC_CONTAINMENT_MUTATION_NO_LIVE_ALIENS
} alienContainmentMutationResult_t;

alienContainmentMutationResult_t AC_TryKillContainedAlien(struct base_s* base, const struct technology_s* technology);
alienContainmentMutationResult_t AC_TryKillContainedAliens(struct base_s* base);

/**
 * Collecting aliens functions.
 */

void AL_AddAliens(struct aircraft_s* aircraft);
bool AL_AddAlienTypeToAircraftCargo(struct aircraft_s* aircraft, const teamDef_t* teamDef, int amount, bool dead);

int AL_CountAll(void);
void AC_InitStartup(void);
