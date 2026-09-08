#!/usr/bin/env python3
from pathlib import Path
import csv
import sys

ROOT=Path(__file__).resolve().parents[2]

def body(path: Path, signature: str) -> str:
    text=path.read_text(encoding='utf-8')
    pos=text.find(signature)
    if pos < 0:
        raise AssertionError(f'missing {signature} in {path.relative_to(ROOT)}')
    start=text.find('{', pos)
    if start < 0:
        raise AssertionError(f'missing body for {signature}')
    depth=0
    for i in range(start, len(text)):
        ch=text[i]
        if ch=='{': depth+=1
        elif ch=='}':
            depth-=1
            if depth==0:
                return text[start:i+1]
    raise AssertionError(f'unterminated body for {signature}')

def require(text: str, tokens, label: str):
    for token in tokens:
        if token not in text:
            raise AssertionError(f'{label}: missing {token}')

def forbid(text: str, tokens, label: str):
    for token in tokens:
        if token in text:
            raise AssertionError(f'{label}: forbidden {token}')

try:
    H=ROOT/'src/client/cgame/campaign/cp_aircraft.h'
    C=ROOT/'src/client/cgame/campaign/cp_aircraft.cpp'
    CB=ROOT/'src/client/cgame/campaign/cp_aircraft_callbacks.cpp'
    GEO=ROOT/'src/client/cgame/campaign/cp_geoscape.cpp'
    POP=ROOT/'src/client/cgame/campaign/cp_popup.cpp'
    AD=ROOT/'src/client/presentation/strategic_intent_legacy_adapter.cpp'

    header=H.read_text(encoding='utf-8')
    require(header,[
        'AIR_TryStartAircraft(', 'AIR_TryStopAircraft(', 'AIR_TrySetAircraftDestination(',
        'AIR_TryPursueUFO(', 'AIR_TryChangeHomebase(',
        'AIR_START_NO_COMMAND_CENTRE', 'AIR_START_NO_PILOT', 'AIR_PURSUIT_NO_COMMAND_CENTRE',
    ],'cp_aircraft.h')

    start=body(C,'AIR_TryStartAircraft (')
    require(start,['B_GetBuildingStatus(','AIR_GetPilot(','AII_ReloadAircraftWeapons(','aircraft->status = AIR_IDLE'],'AIR_TryStartAircraft')
    forbid(start,['CP_Popup(','UI_'],'AIR_TryStartAircraft')

    stop=body(C,'AIR_TryStopAircraft (')
    require(stop,['aircraft->status = AIR_IDLE'],'AIR_TryStopAircraft')

    destination=body(C,'AIR_TrySetAircraftDestination (')
    require(destination,['AIR_IsAircraftOnGeoscape(','AIR_AircraftHasEnoughFuel(','GEO_CalcLine(','AIR_TRANSIT','aircraft->aircraftTarget = nullptr','aircraft->time = 0','aircraft->point = 0'],'AIR_TrySetAircraftDestination')

    pursuit=body(C,'AIR_TryPursueUFO (')
    require(pursuit,['AIR_IsUFO(','B_GetBuildingStatus(','AIR_SendAircraftPursuingUFO('],'AIR_TryPursueUFO')

    home=body(C,'AIR_TryChangeHomebase (')
    require(home,['AIR_CheckMoveIntoNewHomebase(','AIR_MoveAircraftIntoNewHomebase('],'AIR_TryChangeHomebase')

    legacy_start=body(CB,'AIM_AircraftStart_f (')
    require(legacy_start,['AIR_TryStartAircraft('],'AIM_AircraftStart_f')
    forbid(legacy_start,['AII_ReloadAircraftWeapons(','aircraft->status = AIR_IDLE'],'AIM_AircraftStart_f')
    legacy_stop=body(CB,'AIR_StopAircraft_f (')
    require(legacy_stop,['AIR_TryStopAircraft('],'AIR_StopAircraft_f')
    forbid(legacy_stop,['aircraft->status = AIR_IDLE'],'AIR_StopAircraft_f')

    geo_click=body(GEO,'GEO_Click (')
    require(geo_click,['AIR_TrySetAircraftDestination('],'GEO_Click')
    forbid(geo_click,['aircraft->status = AIR_TRANSIT'],'GEO_Click')

    popup_home=body(POP,'CL_PopupChangeHomebase_f (')
    require(popup_home,['AIR_TryChangeHomebase('],'CL_PopupChangeHomebase_f')
    forbid(popup_home,['AIR_MoveAircraftIntoNewHomebase('],'CL_PopupChangeHomebase_f')
    popup_intercept=body(POP,'CL_PopupInterceptClick_f (')
    require(popup_intercept,['AIR_TryPursueUFO(','AIR_SendAircraftToMission('],'CL_PopupInterceptClick_f')
    forbid(popup_intercept,['AIR_SendAircraftPursuingUFO('],'CL_PopupInterceptClick_f')

    adapter=AD.read_text(encoding='utf-8')
    require(adapter,[
        'case StrategicIntentKind::StartAircraft:', 'AIR_TryStartAircraft(',
        'case StrategicIntentKind::StopAircraft:', 'AIR_TryStopAircraft(',
        'case StrategicIntentKind::SetAircraftDestination:', 'AIR_TrySetAircraftDestination(',
        'case StrategicIntentKind::PursueUfo:', 'AIR_TryPursueUFO(',
        'case StrategicIntentKind::ChangeAircraftHomebase:', 'AIR_TryChangeHomebase(',
        'idx >= static_cast<uint32_t>(ccs.numUFOs)',
        'std::isfinite(position.longitude)', 'position.longitude < -180.0f', 'position.latitude < -90.0f',
    ],'strategic adapter')
    forbid(adapter,['Cmd_ExecuteString(','Cbuf_AddText(','Cvar_Set(','Cvar_SetValue(','GEO_CalcLine(','->status = AIR_'],'strategic adapter')

    rows=list(csv.DictReader((ROOT/'tools/remaster/m1-authoritative-intent-coverage.tsv').open(),delimiter='\t'))
    strategic={r['semantic_action']:r for r in rows if r['domain']=='strategic'}
    expected={'StartAircraft','StopAircraft','SetAircraftDestination','PursueUfo','ChangeAircraftHomebase'}
    for name in expected:
        if strategic[name]['authority_bridge']!='canonical_applied':
            raise AssertionError(f'{name}: not canonical_applied')
    if strategic['StartMission']['authority_bridge']!='owner_extraction_pending_fail_closed':
        raise AssertionError('StartMission must remain fail-closed in this slice')
    if sum(r['authority_bridge']=='canonical_applied' for r in strategic.values()) != 8:
        raise AssertionError('strategic applied count must be 8')
    if sum(r['authority_bridge']=='owner_extraction_pending_fail_closed' for r in strategic.values()) != 49:
        raise AssertionError('strategic pending count must be 49')

    print('PASS M1 Aircraft + Geoscape owner extraction: five canonical owners')
    print('PASS legacy UI paths consume canonical owners; UI feedback remains presentation-only')
    print('PASS typed adapter resolves/bounds IDs and destination without command/cvar fallback')
    print('PASS bridge accounting: strategic 8 applied / 49 fail-closed; StartMission remains pending')
except AssertionError as exc:
    print('FAIL M1 Aircraft + Geoscape owner extraction: '+str(exc),file=sys.stderr)
    raise SystemExit(1)
