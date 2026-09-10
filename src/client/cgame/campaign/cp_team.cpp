/**
 * @file
 * @brief Team management for the campaign gametype
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

#include "../../cl_shared.h"
#include "../../cl_team.h"
#include "cp_campaign.h"
#include "cp_team.h"

/**
 * @brief Updates status of weapon (sets pointers, reloads, etc).
 * @param[in] ed Pointer to equipment definition.
 * @param[in] item An item to update.
 * @return Updated item in any case, even if there was no update.
 * @sa CP_CleanupAircraftCrew
 */
void CP_AddWeaponAmmo (equipDef_t* ed, Item* item)
{
	const objDef_t* type = item->def();

	assert(ed->numItems[type->idx] > 0);
	--ed->numItems[type->idx];
	if (type->isArmour())
		return;

	if (type->weapons[0]) {
		/* The given item is ammo or self-contained weapon (i.e. It has firedefinitions. */
		if (!type->isAmmo()) {
			/* "Recharge" the oneshot weapon. */
			item->setAmmoLeft(type->ammo);
			item->setAmmoDef(item->def()); /* Just in case this hasn't been done yet. */
			cgi->Com_DPrintf(DEBUG_CLIENT, "CL_AddWeaponAmmo: oneshot weapon '%s'.\n", type->id);
			return;
		} else {
			/* No change, nothing needs to be done to this item. */
			return;
		}
	} else if (item->getAmmoLeft()) {
		assert(item->ammoDef());
		/* The item is a weapon and it was reloaded one time. */
		if (item->getAmmoLeft() == type->ammo) {
			/* Fully loaded, no need to reload, but mark the ammo as used. */
			if (ed->numItems[item->ammoDef()->idx] > 0) {
				--ed->numItems[item->ammoDef()->idx];
			} else {
				/* Your clip has been sold; give it back. */
				item->setAmmoLeft(NONE_AMMO);
			}
			return;
		}
	}

	/* Check for complete clips of the same kind */
	if (item->ammoDef() && ed->numItems[item->ammoDef()->idx] > 0) {
		--ed->numItems[item->ammoDef()->idx];
		item->setAmmoLeft(type->ammo);
		return;
	}

	/* Search for any complete clips. */
	/** @todo We may want to change this to use the type->ammo[] info. */
	for (int i = 0; i < cgi->csi->numODs; i++) {
		const objDef_t* od = INVSH_GetItemByIDX(i);
		if (od->isLoadableInWeapon(type)) {
			if (ed->numItems[i] > 0) {
				--ed->numItems[i];
				item->setAmmoLeft(type->ammo);
				item->setAmmoDef(od);
				return;
			}
		}
	}

	/** @todo on return from a mission with no clips left
	 * and one weapon half-loaded wielded by soldier
	 * and one empty in equip, on the first opening of equip,
	 * the empty weapon will be in soldier hands, the half-full in equip;
	 * this should be the other way around. */

	/* Failed to find a complete clip - see if there's any loose ammo
	 * of the same kind; if so, gather it all in this weapon. */
	if (item->ammoDef() && ed->numItemsLoose[item->ammoDef()->idx] > 0) {
		item->setAmmoLeft(ed->numItemsLoose[item->ammoDef()->idx]);
		ed->numItemsLoose[item->ammoDef()->idx] = 0;
		return;
	}

	/* See if there's any loose ammo */
	/** @todo We may want to change this to use the type->ammo[] info. */
	item->setAmmoLeft(NONE_AMMO);
	for (int i = 0; i < cgi->csi->numODs; i++) {
		const objDef_t* od = INVSH_GetItemByIDX(i);
		if (od->isLoadableInWeapon(type) && ed->numItemsLoose[i] > item->getAmmoLeft()) {
			if (item->getAmmoLeft() > 0) {
				/* We previously found some ammo, but we've now found other
				 * loose ammo of a different (but appropriate) type with
				 * more bullets.  Put the previously found ammo back, so
				 * we'll take the new type. */
				assert(item->ammoDef());
				ed->numItemsLoose[item->ammoDef()->idx] = item->getAmmoLeft();
				/* We don't have to accumulate loose ammo into clips
				 * because we did it previously and we create no new ammo */
			}
			/* Found some loose ammo to load the weapon with */
			item->setAmmoLeft(ed->numItemsLoose[i]);
			ed->numItemsLoose[i] = 0;
			item->setAmmoDef(od);
		}
	}
}

/**
 * @brief Set up equip (floor) container for soldiers
 * @param[in,out] chr Pointer to soldiers character structure
 */
void CP_SetEquipContainer (character_t* chr)
{
	/* get the inventory the UI uses for all the work */
	Inventory* uiInv = *cgi->ui_inventory;
	/* if it was not already set to our character's inventory ... */
	if (uiInv && uiInv != &chr->inv) {
		/* ...use the UI equip cont for our character's equipment container */
		chr->inv.setContainer(CID_EQUIP, uiInv->getContainer2(CID_EQUIP));
		/* set 'old' CID_EQUIP to nullptr */
		uiInv->resetContainer(CID_EQUIP);
	}
	/* set the UI inventory to our char's (including the equip container we preserved.) */
	*cgi->ui_inventory = &chr->inv;
}

/**
 * @brief Reload or remove weapons in container
 */
static void CP_CleanupContainerWeapons (equipDef_t* ed, containerIndex_t container, character_t* chr)
{
	Item* ic, *next;

	for (ic = chr->inv.getContainer2(container); ic; ic = next) {
		next = ic->getNext();
		if (ed->numItems[ic->def()->idx] > 0) {
			CP_AddWeaponAmmo(ed, ic);
		} else {
			/* Drop ammo used for reloading and sold carried weapons. */
			if (!cgi->INV_RemoveFromInventory(&chr->inv, chr->inv.getContainer(container).def(), ic))
				cgi->Com_Error(ERR_DROP, "Could not remove item from inventory");
		}
	}
}

/**
 * @brief Reloads weapons, removes not assigned and resets defaults
 * @param[in] base Pointer to a base for given team.
 * @param[in] ed equipDef_t pointer to equipment
 * @sa CL_AddWeaponAmmo
 * @note Iterate through in container order (right hand, left hand, belt,
 * holster, backpack) at the top level, i.e. each squad member reloads
 * the right hand, then each reloads the left hand, etc. The effect
 * of this is that when things are tight, everyone has the opportunity
 * to get their preferred weapon(s) loaded before anyone is allowed
 * to keep her spares in the backpack or on the floor. We don't want
 * the first person in the squad filling their backpack with spare ammo
 * leaving others with unloaded guns in their hands...
 */
void CP_CleanupTeam (base_t* base, equipDef_t* ed)
{
	assert(base);

	/* Auto-assign weapons to UGVs/Robots if they have no weapon yet. */
	E_Foreach(EMPL_ROBOT, employee) {
		if (!employee->isHiredInBase(base))
			continue;
		if (employee->transfer)
			continue;

		character_t* chr = &employee->chr;

		/* This is an UGV */
		if (employee->getUGV()) {
			/* Check if there is a weapon and add it if there isn't. */
			Item* rightH = chr->inv.getRightHandContainer();
			if (!rightH || !rightH->def())
				cgi->INV_EquipActor(chr, nullptr, INVSH_GetItemByID(employee->getUGV()->weapon),
						cgi->GAME_GetChrMaxLoad(chr));
		}
	}

	for (containerIndex_t container = 0; container < CID_MAX; container++) {
		E_Foreach(EMPL_SOLDIER, employee) {
			if (!employee->isHiredInBase(base))
				continue;
			if (employee->transfer)
				continue;

			character_t* chr = &employee->chr;
#if 0
			/* ignore items linked from any temp container */
			if (INVDEF(container)->temp)
				continue;
#endif
			CP_CleanupContainerWeapons(ed, container, chr);
		}
	}
}

/**
 * @brief Reloads weapons, removes not assigned and resets defaults
 * @param[in] aircraft Pointer to an aircraft for given team.
 * @param[in] ed equipDef_t pointer to equipment
 * @sa CL_AddWeaponAmmo
 * @note Iterate through in container order (right hand, left hand, belt,
 * holster, backpack) at the top level, i.e. each squad member reloads
 * the right hand, then each reloads the left hand, etc. The effect
 * of this is that when things are tight, everyone has the opportunity
 * to get their preferred weapon(s) loaded before anyone is allowed
 * to keep her spares in the backpack or on the floor. We don't want
 * the first person in the squad filling their backpack with spare ammo
 * leaving others with unloaded guns in their hands...
 */
void CP_CleanupAircraftTeam (aircraft_t* aircraft, equipDef_t* ed)
{
	assert(aircraft);

	for (containerIndex_t container = 0; container < CID_MAX; container++) {
		LIST_Foreach(aircraft->acTeam, Employee, employee) {
			character_t* chr = &employee->chr;

			/* Auto-assign weapons to UGVs/Robots if they have no weapon yet. */
			if (employee->getUGV()) {
				/* Check if there is a weapon and add it if there isn't. */
				Item* rightH = chr->inv.getRightHandContainer();
				if (!rightH || !rightH->def())
					cgi->INV_EquipActor(chr, nullptr, INVSH_GetItemByID(employee->getUGV()->weapon),
							cgi->GAME_GetChrMaxLoad(chr));
				continue;
			}

#if 0
			/* ignore items linked from any temp container */
			if (INVDEF(container)->temp)
				continue;
#endif
			CP_CleanupContainerWeapons(ed, container, chr);
		}
	}
}

/**
 * @brief Clears all containers that are temp containers (see script definition).
 * @sa GAME_SaveTeamInfo
 * @sa GAME_SendCurrentTeamSpawningInfo
 */
void CP_CleanTempInventory (base_t* base)
{
	E_Foreach(EMPL_SOLDIER, employee) {
		employee->chr.inv.resetTempContainers();
	}

	E_Foreach(EMPL_ROBOT, employee) {
		employee->chr.inv.resetTempContainers();
	}

	if (!base)
		return;

	cgi->INV_DestroyInventory(&base->bEquipment);
}

/**
 * @brief Updates data about teams in aircraft.
 * @param[in] aircraft Pointer to an aircraft for a desired team.
 * @param[in] employeeType Type of employee for which data is being updated.
 * @returns the number of employees that are in the aircraft and were added to
 * the character list
 */
void CP_UpdateActorAircraftVar (aircraft_t* aircraft, employeeType_t employeeType)
{
	int numOnAircraft;
	const Employee* pilot = AIR_GetPilot(aircraft);

	assert(aircraft);

	numOnAircraft = AIR_GetTeamSize(aircraft);
	cgi->Cvar_Set("mn_hired", _("%i of %i"), numOnAircraft, aircraft->maxTeamSize);
	cgi->Cvar_Set("mn_hirable_count", "%i", aircraft->maxTeamSize - numOnAircraft);
	cgi->Cvar_Set("mn_hired_count", "%i", numOnAircraft);

	if (pilot) {
		cgi->Cvar_Set("mn_pilotassigned", "1");
		cgi->Cvar_Set("mn_pilot_name", "%s", pilot->chr.name);
		cgi->Cvar_Set("mn_pilot_body", "%s", CHRSH_CharGetBody(&pilot->chr));
		cgi->Cvar_Set("mn_pilot_head", "%s", CHRSH_CharGetHead(&pilot->chr));
		cgi->Cvar_Set("mn_pilot_body_skin", "%i", pilot->chr.bodySkin);
		cgi->Cvar_Set("mn_pilot_head_skin", "%i", pilot->chr.headSkin);
	} else {
		cgi->Cvar_Set("mn_pilotassigned", "0");
		cgi->Cvar_Set("mn_pilot_name", "");
		cgi->Cvar_Set("mn_pilot_body", "");
		cgi->Cvar_Set("mn_pilot_head", "");
		cgi->Cvar_Set("mn_pilot_body_skin", "");
		cgi->Cvar_Set("mn_pilot_head_skin", "");
	}
}

/**
 * @brief Report whether a team owner accepted the requested canonical state.
 */
bool CP_TEAM_IsMutationAccepted (teamMutationResult_t result)
{
	return result == TEAM_MUTATION_APPLIED || result == TEAM_MUTATION_NO_CHANGE;
}

/**
 * @brief Set desired soldier/pilot membership on a PHALANX aircraft.
 *
 * Both EmployeeId/UCN and aircraft index are re-resolved at execution time.
 * Assignment to a different aircraft remains rejected instead of silently moving
 * the employee, matching the legacy team-list eligibility contract.
 */
teamMutationResult_t CP_TEAM_TrySetAircraftAssignment (int employeeUcn, int aircraftIdx, bool assigned)
{
	Employee* employee = E_GetEmployeeFromChrUCN(employeeUcn);
	if (!employee)
		return TEAM_MUTATION_INVALID_EMPLOYEE;

	aircraft_t* aircraft = AIR_AircraftGetFromIDX(aircraftIdx);
	if (!aircraft || !aircraft->homebase || AIR_IsUFO(aircraft))
		return TEAM_MUTATION_INVALID_AIRCRAFT;
	if (!AIR_IsAircraftInBase(aircraft))
		return TEAM_MUTATION_AIRCRAFT_NOT_IN_BASE;
	if (!employee->isSoldier() && !employee->isPilot())
		return TEAM_MUTATION_WRONG_EMPLOYEE_TYPE;
	if (employee->transfer)
		return TEAM_MUTATION_TRANSFER_ACTIVE;
	if (!employee->isHiredInBase(aircraft->homebase))
		return TEAM_MUTATION_NOT_HIRED_AT_BASE;

	const aircraft_t* assignedAircraft = AIR_IsEmployeeInAircraft(employee, nullptr);
	if (assigned) {
		if (assignedAircraft == aircraft)
			return TEAM_MUTATION_NO_CHANGE;
		if (assignedAircraft)
			return TEAM_MUTATION_ASSIGNED_ELSEWHERE;

		if (employee->isPilot()) {
			if (AIR_GetPilot(aircraft))
				return TEAM_MUTATION_AIRCRAFT_FULL;
			return AIR_SetPilot(aircraft, employee)
				? TEAM_MUTATION_APPLIED
				: TEAM_MUTATION_REJECTED;
		}
		if (AIR_GetTeamSize(aircraft) >= aircraft->maxTeamSize)
			return TEAM_MUTATION_AIRCRAFT_FULL;
		return AIR_AddToAircraftTeam(aircraft, employee)
			? TEAM_MUTATION_APPLIED
			: TEAM_MUTATION_REJECTED;
	}

	if (assignedAircraft != aircraft)
		return TEAM_MUTATION_NO_CHANGE;
	return AIR_RemoveEmployee(employee, aircraft)
		? TEAM_MUTATION_APPLIED
		: TEAM_MUTATION_REJECTED;
}

/**
 * @brief De-equip an employee and perform the same base/team cleanup as legacy UI.
 *
 * The optional returned equipment value exists only so the legacy callback can
 * refresh its equipment widget with the same post-cleanup value. Typed presentation
 * callers pass nullptr and receive no mutable campaign object.
 */
teamMutationResult_t CP_TEAM_TryDeequipEmployee (base_t* base, int employeeUcn, equipDef_t* unusedEquipment)
{
	if (!base)
		return TEAM_MUTATION_INVALID_BASE;

	Employee* employee = E_GetEmployeeFromChrUCN(employeeUcn);
	if (!employee)
		return TEAM_MUTATION_INVALID_EMPLOYEE;
	if (employee->transfer)
		return TEAM_MUTATION_TRANSFER_ACTIVE;
	if (!employee->isHiredInBase(base))
		return TEAM_MUTATION_NOT_HIRED_AT_BASE;
	if (employee->isAwayFromBase())
		return TEAM_MUTATION_AWAY_FROM_BASE;

	cgi->INV_DestroyInventory(&employee->chr.inv);
	/* Character temp containers affect canonical loadout cleanup. base->bEquipment
	 * is legacy equipment-screen scratch and remains callback-owned. */
	CP_CleanTempInventory(nullptr);
	equipDef_t unused = base->storage;
	CP_CleanupTeam(base, &unused);
	if (unusedEquipment)
		*unusedEquipment = unused;
	return TEAM_MUTATION_APPLIED;
}

/**
 * @brief Set a soldier body skin after re-resolving EmployeeId/UCN.
 *
 * No new range validation is introduced: the legacy callback accepted the parsed
 * integer verbatim once the employee was known to be a soldier.
 */
teamMutationResult_t CP_TEAM_TrySetEmployeeSkin (int employeeUcn, int bodySkin)
{
	Employee* employee = E_GetEmployeeFromChrUCN(employeeUcn);
	if (!employee)
		return TEAM_MUTATION_INVALID_EMPLOYEE;
	if (!employee->isSoldier())
		return TEAM_MUTATION_WRONG_EMPLOYEE_TYPE;

	employee->chr.bodySkin = bodySkin;
	return TEAM_MUTATION_APPLIED;
}
