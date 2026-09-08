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
    BH=ROOT/'src/client/cgame/campaign/cp_base.h'
    BC=ROOT/'src/client/cgame/campaign/cp_base.cpp'
    BCB=ROOT/'src/client/cgame/campaign/cp_base_callbacks.cpp'
    AD=ROOT/'src/client/presentation/strategic_intent_legacy_adapter.cpp'

    header=BH.read_text(encoding='utf-8')
    require(header,[
        'facilityBuildResult_t','facilityDestroyResult_t','B_GetBuildingByIDXSafe(',
        'B_TryBuildFacility(','B_CheckDestroyFacility(','B_TryDestroyFacility(',
        'B_FACILITY_DESTROY_BASE_UNDER_ATTACK','B_FACILITY_DESTROY_BREAKS_CONNECTIVITY',
    ],'cp_base.h')

    low_build=body(BC,'B_BuildBuilding (')
    forbid(low_build,['Cmd_ExecuteString("base_init'],'B_BuildBuilding')
    require(low_build,['CP_UpdateCredits(','B_FireEvent('],'B_BuildBuilding')

    safe=body(BC,'B_GetBuildingByIDXSafe (')
    require(safe,['B_GetBaseByIDX(','ccs.numBuildings[baseIdx]','B_GetBuildingByIDX('],'B_GetBuildingByIDXSafe')

    build=body(BC,'B_TryBuildFacility (')
    require(build,[
        'B_GetBuildingTemplateSilent(','BASE_SIZE','CP_CheckCredits(','B_BuildBuilding(',
        'B_FACILITY_BUILD_INVALID_DEFINITION','B_FACILITY_BUILD_DOES_NOT_FIT','B_FACILITY_BUILD_APPLIED',
    ],'B_TryBuildFacility')
    forbid(build,['RS_IsResearched_ptr(','maxCount','Cmd_ExecuteString(','Cvar_Set(','UI_','CP_Popup('],'B_TryBuildFacility')

    check=body(BC,'B_CheckDestroyFacility (')
    require(check,[
        'B_GetBuildingByIDXSafe(','B_IsUnderAttack(','B_ENTRANCE','B_IsBuildingDestroyable(',
        'B_FACILITY_DESTROY_BASE_UNDER_ATTACK','B_FACILITY_DESTROY_BREAKS_CONNECTIVITY',
    ],'B_CheckDestroyFacility')
    forbid(check,['UI_','CP_Popup(','CAP_GetFreeCapacity('],'B_CheckDestroyFacility')

    destroy=body(BC,'B_TryDestroyFacility (')
    require(destroy,['B_CheckDestroyFacility(','B_GetBuildingByIDXSafe(','B_BuildingDestroy(','B_FACILITY_DESTROY_APPLIED'],'B_TryDestroyFacility')
    forbid(destroy,['UI_','CP_Popup(','Cmd_ExecuteString(','Cvar_Set('],'B_TryDestroyFacility')

    low_destroy=body(BC,'B_BuildingDestroy (')
    forbid(low_destroy,['Cmd_ExecuteString("base_init'],'B_BuildingDestroy')
    require(low_destroy,['CAP_CheckOverflow(','B_FireEvent('],'B_BuildingDestroy')

    legacy_build=body(BCB,'B_BuildBuilding_f (')
    require(legacy_build,['B_TryBuildFacility(','S_StartLocalSample(','Cmd_ExecuteString("base_init','Cmd_ExecuteString("ui_push bases'],'B_BuildBuilding_f')
    forbid(legacy_build,['B_BuildBuilding('],'B_BuildBuilding_f')

    legacy_destroy=body(BCB,'B_BuildingDestroy_f (')
    require(legacy_destroy,[
        'B_CheckDestroyFacility(','B_TryDestroyFacility(','CAP_GetFreeCapacity(',
        'Destroy Alien Containment','Destroy Hangar','Destroy Quarter','Destroy Storage',
        'Cmd_ExecuteString("base_init',
    ],'B_BuildingDestroy_f')
    forbid(legacy_destroy,['B_IsUnderAttack(','B_IsBuildingDestroyable(','B_BuildingDestroy('],'B_BuildingDestroy_f')

    adapter=AD.read_text(encoding='utf-8')
    require(adapter,[
        'case StrategicIntentKind::BuildFacility:','B_TryBuildFacility(',
        'case StrategicIntentKind::DestroyFacility:','B_TryDestroyFacility(',
        'resolveBase(','resolveBoundedText(',
    ],'strategic adapter')
    forbid(adapter,[
        'Cmd_ExecuteString(','Cbuf_AddText(','Cvar_Set(','Cvar_SetValue(',
        'B_BuildBuilding(','B_BuildingDestroy(','B_GetBuildingTemplateSilent(',
    ],'strategic adapter')

    rows=list(csv.DictReader((ROOT/'tools/remaster/m1-authoritative-intent-coverage.tsv').open(),delimiter='\t'))
    strategic={r['semantic_action']:r for r in rows if r['domain']=='strategic'}
    for name in {'BuildFacility','DestroyFacility'}:
        if strategic[name]['authority_bridge']!='canonical_applied':
            raise AssertionError(f'{name}: not canonical_applied')
    if strategic['DestroyAntimatterFacility']['authority_bridge']!='owner_extraction_pending_fail_closed':
        raise AssertionError('DestroyAntimatterFacility must remain fail-closed')
    if strategic['StartMission']['authority_bridge']!='owner_extraction_pending_fail_closed':
        raise AssertionError('StartMission must remain fail-closed')

    print('PASS M1 Facility owner extraction: BuildFacility + DestroyFacility canonical owners')
    print('PASS facility destruction eligibility is canonical; capacity-sensitive confirmation remains presentation-only')
    print('PASS low-level base facility mutation no longer dispatches legacy base_init refresh')
    print('PASS DestroyAntimatterFacility remains fail-closed as an internal breach-event contract mismatch')
except AssertionError as exc:
    print('FAIL M1 Facility owner extraction: '+str(exc),file=sys.stderr)
    raise SystemExit(1)
