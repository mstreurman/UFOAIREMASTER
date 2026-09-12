/**
 * @file
 * @brief Header file for Transfer stuff.
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

#include "../../DateTime.h"

#include <cstdint>

/** @brief Default transfer time for cases with no source/dest base */
#define DEFAULT_TRANSFER_TIME 2.0f

#define TRANSFER_REQUEST_MAX_ITEMS 1024
#define TRANSFER_REQUEST_MAX_EMPLOYEES 512
#define TRANSFER_REQUEST_MAX_AIRCRAFT 64
#define TRANSFER_REQUEST_MAX_ALIEN_TYPES 128
#define TRANSFER_REQUEST_TEAM_KEY_BYTES 96

typedef struct transferStartItem_s {
	int itemIndex;
	int amount;
} transferStartItem_t;

typedef struct transferStartAlien_s {
	char teamDefinition[TRANSFER_REQUEST_TEAM_KEY_BYTES];
	int alive;
	int dead;
} transferStartAlien_t;

typedef struct transferStartRequest_s {
	int sourceBaseIndex;
	int destinationBaseIndex;
	int antimatter;
	uint32_t itemCount;
	transferStartItem_t items[TRANSFER_REQUEST_MAX_ITEMS];
	uint32_t employeeCount;
	int employeeUcn[TRANSFER_REQUEST_MAX_EMPLOYEES];
	uint32_t aircraftCount;
	int aircraftIndex[TRANSFER_REQUEST_MAX_AIRCRAFT];
	uint32_t alienCount;
	transferStartAlien_t aliens[TRANSFER_REQUEST_MAX_ALIEN_TYPES];
} transferStartRequest_t;

typedef enum transferStartResult_s {
	TR_START_APPLIED = 0,
	TR_START_INVALID_REQUEST,
	TR_START_INVALID_SOURCE,
	TR_START_INVALID_DESTINATION,
	TR_START_EMPTY,
	TR_START_INVALID_ITEM,
	TR_START_INSUFFICIENT_ITEM,
	TR_START_INVALID_EMPLOYEE,
	TR_START_INVALID_AIRCRAFT,
	TR_START_INVALID_ALIEN,
	TR_START_REJECTED
} transferStartResult_t;

/** @brief Transfer information (they are being stored in ccs.transfers). */
typedef struct transfer_s {
	base_t* destBase;				/**< Pointer to destination base. May not be nullptr if active is true. */
	base_t* srcBase;				/**< Pointer to source base. May be nullptr if transfer comes from a mission (alien body recovery). */
	class DateTime event;				/**< When the transfer finish process should start. */

	int antimatter;
	class ItemCargo* itemCargo;
	class AlienCargo* alienCargo;
	linkedList_t* employees[MAX_EMPL];
	linkedList_t* aircraft;

	bool hasItems;				/**< Transfer of items. */
	bool hasEmployees;			/**< Transfer of employees. */
} transfer_t;

#define TR_Foreach(var) LIST_Foreach(ccs.transfers, transfer_t, var)
#define TR_ForeachEmployee(var, transfer, employeeType) LIST_Foreach(transfer->employees[employeeType], Employee, var)
#define TR_ForeachAircraft(var, transfer) LIST_Foreach(transfer->aircraft, aircraft_t, var)

void TR_TransferRun(void);
void TR_NotifyAircraftRemoved(const aircraft_t* aircraft);

transfer_t* TR_TransferStart(base_t* srcBase, transfer_t& transData);
bool TR_BuildStartRequest(const base_t* srcBase, const transfer_t& transData, transferStartRequest_t* request);
transferStartResult_t TR_TryStartTransfer(const transferStartRequest_t& request, transfer_t** startedTransfer);

void TR_InitStartup(void);
void TR_Shutdown(void);
