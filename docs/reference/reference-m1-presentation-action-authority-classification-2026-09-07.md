# Reference — M1 Presentation Action Authority Classification v3

**Date:** 2026-09-07  
**Status:** observed v2 surface fully classified; local strict verification pending  
**Source baseline:** `1dd974017f25d5bda5cc5b82b48d2590e574e50f`

## Measured v2 state

```text
active commands discovered: 301
direct presentation input entries: 1
direct protocol request callsites: 13
unresolved entries: 119
presentation source-guard violations: 0
```

## v3 coverage

Every one of the 119 unresolved v2 rows is now accounted for by:

```text
resolved non-presentation scope
final five-way PRESENTATION_ACTION authority
protocol semantic mapping
or tracked semantic decomposition
```

Coverage:

```text
119 / 119
```

The protocol naming defect is fixed:

```text
PA_REACT_SELECT -> SelectReactionFireMode
```

## Scope exclusions added

Examples:

```text
CANONICAL_MAINTENANCE
    add_battery
    remove_battery
    basedef_updatebatteries
    update_base_radar_coverage

SCRIPTED_CANONICAL_EVENT
    cp_add_researchable
    cp_add_item
    cp_changehappiness
    cp_endgame
    cp_start_xvi_spreading
    cp_spawn_ufocarrier
    cp_attack_ufocarrier

CANONICAL_LIFECYCLE
    cp_results

APPLICATION_PERSISTENCE
    game_listsaves
    game_delete
    game_quickloadinit
```

These remain inventoried but do not become gameplay intents.

## Newly resolved strategic action families

```text
StartMission
SetCampaignTimeLapse
BuildInstallation
RenameInstallation
DestroyInstallation
EquipAircraftItem
RemoveAircraftItem
EquipBaseDefenceItem
RemoveBaseDefenceItem
SetAirDefenceAutoFire
StartTransfer
SaveGame
LoadGame
StoreRecoveredUfo
AcceptUfoSaleOffer
DestroyStoredUfo
TransferStoredUfo
SetAircraftDestination
PursueUfo
BuyItem / SellItem
BuyAircraft / SellAircraft
BuyUGV / SellUGV
```

## Newly resolved tactical action families

```text
UseHeadgear
SetShotReservation
SelectReactionFireMode
EndTurn
Reload
MoveActor
Shoot
ClearShotReservation
```

## Recovered-UFO sale authority rule

The legacy sell flow generates a price for presentation and later accepts a price back from the UI.

The remaster must instead use canonical offer identity/revalidation:

```text
canonical sale-offer publication
AcceptUfoSaleOffer(OfferId)
canonical offer lookup/revalidation
```

Presentation-supplied price is not authoritative.

## Local closure command

```bash
python3 tools/remaster/capture-m1-presentation-authority-inventory.py --strict
```

Expected on the captured source surface:

```text
unresolved entries: 0
presentation source-guard violations: 0
M1 presentation authority classification: COMPLETE
```

The run also creates:

```text
.build/m1-presentation-authority/semantic-actions.tsv
.build/m1-presentation-authority/intent-candidates.tsv
```

No gameplay source is changed by this classification slice.
