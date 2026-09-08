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
    IH=ROOT/'src/client/cgame/campaign/cp_installation.h'
    IC=ROOT/'src/client/cgame/campaign/cp_installation.cpp'
    ICB=ROOT/'src/client/cgame/campaign/cp_installation_callbacks.cpp'
    GH=ROOT/'src/client/cgame/campaign/cp_geoscape.h'
    GC=ROOT/'src/client/cgame/campaign/cp_geoscape.cpp'
    AD=ROOT/'src/client/presentation/strategic_intent_legacy_adapter.cpp'

    geoh=GH.read_text(encoding='utf-8')
    require(geoh,['GEO_IsValidLandPosition('],'cp_geoscape.h')
    land=body(GC,'GEO_IsValidLandPosition (')
    require(land,['std::isfinite(','-180.0f','180.0f','-90.0f','90.0f','MapIsWater(','GEO_GetColor('],'GEO_IsValidLandPosition')
    geo_click=body(GC,'GEO_Click (')
    if geo_click.count('GEO_IsValidLandPosition(') < 2:
        raise AssertionError('GEO_Click must use shared land validation for base and installation placement')

    baseh=BH.read_text(encoding='utf-8')
    require(baseh,['baseBuildResult_t','B_TryBuildBase(','B_TrySetName(','B_BUILD_INSUFFICIENT_CREDITS'],'cp_base.h')
    buildbase=body(BC,'B_TryBuildBase (')
    require(buildbase,[
        'ccs.curCampaign','B_GetCount()','B_GetFirstUnfoundedBase()','GEO_IsValidLandPosition(',
        'ccs.credits - campaign->basecost <= 0','Com_IsValidName(','B_Build(','CP_UpdateCredits(',
        'GEO_GetNation(','MS_AddNewMessage(','B_SetUpFirstBase(',
    ],'B_TryBuildBase')
    forbid(buildbase,['CP_Popup(','UI_','Cmd_ExecuteString(','Cvar_Set(','Cvar_SetValue('],'B_TryBuildBase')
    renamebase=body(BC,'B_TrySetName (')
    require(renamebase,['Com_IsValidName(','B_SetName('],'B_TrySetName')

    legacy_build_base=body(BCB,'B_BuildBase_f (')
    require(legacy_build_base,['B_TryBuildBase('],'B_BuildBase_f')
    forbid(legacy_build_base,['B_Build('],'B_BuildBase_f')
    legacy_rename_base=body(BCB,'B_ChangeBaseName_f (')
    require(legacy_rename_base,['B_TrySetName('],'B_ChangeBaseName_f')
    forbid(legacy_rename_base,['B_SetName(','Com_IsValidName('],'B_ChangeBaseName_f')

    insh=IH.read_text(encoding='utf-8')
    require(insh,['installationBuildResult_t','INS_TryBuildInstallation(','INS_TrySetName(','INS_TryDestroyInstallation('],'cp_installation.h')
    buildins=body(IC,'INS_TryBuildInstallation (')
    require(buildins,[
        'B_GetInstallationLimit()','INS_GetCount()','RS_IsResearched_ptr(','installationTemplate->once',
        'INS_HasType(','GEO_IsValidLandPosition(','ccs.credits - installationTemplate->cost <= 0',
        'INS_Build(','CP_UpdateCredits(','GEO_GetNation(','MSO_CheckAddNewMessage(',
    ],'INS_TryBuildInstallation')
    forbid(buildins,['CP_Popup(','UI_','Cmd_ExecuteString(','Cvar_Set(','Cvar_SetValue('],'INS_TryBuildInstallation')
    renameins=body(IC,'INS_TrySetName (')
    require(renameins,['Q_strncpyz('],'INS_TrySetName')
    destroyins=body(IC,'INS_TryDestroyInstallation (')
    require(destroyins,['INS_DestroyInstallation('],'INS_TryDestroyInstallation')

    legacy_build_ins=body(ICB,'INS_BuildInstallation_f (')
    require(legacy_build_ins,['INS_TryBuildInstallation('],'INS_BuildInstallation_f')
    forbid(legacy_build_ins,['INS_Build('],'INS_BuildInstallation_f')
    legacy_rename_ins=body(ICB,'INS_ChangeInstallationName_f (')
    require(legacy_rename_ins,['INS_TrySetName('],'INS_ChangeInstallationName_f')
    forbid(legacy_rename_ins,['Q_strncpyz('],'INS_ChangeInstallationName_f')
    legacy_destroy_ins=body(ICB,'INS_DestroyInstallation_f (')
    require(legacy_destroy_ins,['INS_TryDestroyInstallation('],'INS_DestroyInstallation_f')
    forbid(legacy_destroy_ins,['INS_DestroyInstallation('],'INS_DestroyInstallation_f')

    adapter=AD.read_text(encoding='utf-8')
    require(adapter,[
        'resolveInstallation(','resolveBoundedText(','resolveStrategicPosition2(',
        'case StrategicIntentKind::BuildBase:','B_TryBuildBase(',
        'case StrategicIntentKind::RenameBase:','B_TrySetName(',
        'case StrategicIntentKind::BuildInstallation:','INS_TryBuildInstallation(',
        'case StrategicIntentKind::RenameInstallation:','INS_TrySetName(',
        'case StrategicIntentKind::DestroyInstallation:','INS_TryDestroyInstallation(',
    ],'strategic adapter')
    forbid(adapter,[
        'Cmd_ExecuteString(','Cbuf_AddText(','Cvar_Set(','Cvar_SetValue(',
        'B_Build(','INS_Build(','INS_DestroyInstallation(','B_SetName(','Q_strncpyz(',
    ],'strategic adapter')

    rows=list(csv.DictReader((ROOT/'tools/remaster/m1-authoritative-intent-coverage.tsv').open(),delimiter='\t'))
    strategic={r['semantic_action']:r for r in rows if r['domain']=='strategic'}
    expected={'BuildBase','RenameBase','BuildInstallation','RenameInstallation','DestroyInstallation'}
    for name in expected:
        if strategic[name]['authority_bridge']!='canonical_applied':
            raise AssertionError(f'{name}: not canonical_applied')
    for name in {'DestroyAntimatterFacility','StartMission'}:
        if strategic[name]['authority_bridge']!='owner_extraction_pending_fail_closed':
            raise AssertionError(f'{name}: must remain fail-closed')

    print('PASS M1 Base + Installation lifecycle extraction: five canonical owners')
    print('PASS shared geoscape land placement rule is canonical and consumed by legacy + typed paths')
    print('PASS legacy callbacks retain presentation/confirmation only; adapter has no command/cvar fallback')
    print('PASS Base + Installation owner subset remains qualified; facility lifecycle is checked by its dedicated lane')
except AssertionError as exc:
    print('FAIL M1 Base + Installation lifecycle extraction: '+str(exc),file=sys.stderr)
    raise SystemExit(1)
