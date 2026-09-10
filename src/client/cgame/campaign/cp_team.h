/**
 * @file
 * @brief Team management for the campaign gametype headers
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

See the GNU General Public License for more details.m

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/

#pragma once

void CP_CleanTempInventory(base_t* base);
void CP_UpdateActorAircraftVar(aircraft_t* aircraft, employeeType_t employeeType);
void CP_CleanupAircraftTeam(aircraft_t* aircraft, equipDef_t* ed);
void CP_CleanupTeam(base_t* base, equipDef_t* ed);
void CP_SetEquipContainer(character_t* chr);
void CP_AddWeaponAmmo(equipDef_t* ed, Item* item);

typedef enum teamMutationResult_s {
	TEAM_MUTATION_APPLIED = 0,
	TEAM_MUTATION_NO_CHANGE,
	TEAM_MUTATION_INVALID_EMPLOYEE,
	TEAM_MUTATION_INVALID_AIRCRAFT,
	TEAM_MUTATION_INVALID_BASE,
	TEAM_MUTATION_WRONG_EMPLOYEE_TYPE,
	TEAM_MUTATION_NOT_HIRED_AT_BASE,
	TEAM_MUTATION_TRANSFER_ACTIVE,
	TEAM_MUTATION_AWAY_FROM_BASE,
	TEAM_MUTATION_AIRCRAFT_NOT_IN_BASE,
	TEAM_MUTATION_ASSIGNED_ELSEWHERE,
	TEAM_MUTATION_AIRCRAFT_FULL,
	TEAM_MUTATION_REJECTED
} teamMutationResult_t;

bool CP_TEAM_IsMutationAccepted(teamMutationResult_t result);
teamMutationResult_t CP_TEAM_TrySetAircraftAssignment(int employeeUcn, int aircraftIdx, bool assigned);
teamMutationResult_t CP_TEAM_TryDeequipEmployee(base_t* base, int employeeUcn, equipDef_t* unusedEquipment);
teamMutationResult_t CP_TEAM_TrySetEmployeeSkin(int employeeUcn, int bodySkin);
