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
    for i in range(start,len(text)):
        if text[i]=='{':
            depth+=1
        elif text[i]=='}':
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
    RH=ROOT/'src/client/cgame/campaign/cp_research.h'
    RC=ROOT/'src/client/cgame/campaign/cp_research.cpp'
    RCB=ROOT/'src/client/cgame/campaign/cp_research_callbacks.cpp'
    AD=ROOT/'src/client/presentation/strategic_intent_legacy_adapter.cpp'

    header=RH.read_text(encoding='utf-8')
    require(header,[
        'researchChangeResult_t',
        'RS_CHANGE_APPLIED',
        'RS_CHANGE_WRONG_BASE',
        'RS_CHANGE_INVALID_DELTA',
        'RS_CHANGE_NO_LAB_SPACE',
        'RS_TryChangeScientists(',
        'RS_TryMaxAssignScientists(',
        'RS_TryStopResearch(',
    ],'cp_research.h')

    core=RC.read_text(encoding='utf-8')
    forbid(core,['CP_Popup('],'cp_research.cpp canonical research core')

    low=body(RC,'RS_TryAssignScientistCanonical (')
    require(low,[
        'E_GetUnassignedEmployee(',
        'tech->statusResearchable',
        'CAP_GetFreeCapacity(base, CAP_LABSPACE)',
        'tech->scientists++',
        'tech->base = base',
        'CAP_AddCurrent(base, CAP_LABSPACE, 1)',
        'employee->setAssigned(true)',
        'tech->statusResearch = RS_RUNNING',
    ],'RS_TryAssignScientistCanonical')
    forbid(low,['CP_Popup(','UI_','Cmd_ExecuteString(','Cvar_Set('],
           'RS_TryAssignScientistCanonical')

    wrapper=body(RC,'RS_AssignScientist (')
    require(wrapper,['RS_TryAssignScientistCanonical('],'RS_AssignScientist')
    forbid(wrapper,['CP_Popup('],'RS_AssignScientist')

    change=body(RC,'RS_TryChangeScientists (')
    require(change,[
        'tech->base && tech->base != base',
        'scientistDelta != 1 && scientistDelta != -1',
        'RS_TryAssignScientistCanonical(',
        'RS_RemoveScientist(tech, nullptr)',
        'RS_CHANGE_NO_ACTIVE_RESEARCH',
    ],'RS_TryChangeScientists')
    forbid(change,['CP_Popup(','UI_','Cmd_ExecuteString(','Cvar_Set('],
           'RS_TryChangeScientists')

    max_owner=body(RC,'RS_TryMaxAssignScientists (')
    require(max_owner,[
        'CAP_GetFreeCapacity(base, CAP_LABSPACE) > 0',
        'E_GetUnassignedEmployee(base, EMPL_SCIENTIST)',
        'RS_TryAssignScientistCanonical(',
        'RS_CHANGE_APPLIED',
    ],'RS_TryMaxAssignScientists')
    forbid(max_owner,['CP_Popup(','UI_','Cmd_ExecuteString(','Cvar_Set('],
           'RS_TryMaxAssignScientists')

    stop_owner=body(RC,'RS_TryStopResearch (')
    require(stop_owner,[
        'tech->base && tech->base != base',
        'RS_CHANGE_NO_ACTIVE_RESEARCH',
        'RS_StopResearch(tech)',
        'RS_CHANGE_APPLIED',
    ],'RS_TryStopResearch')
    forbid(stop_owner,['CP_Popup(','UI_','Cmd_ExecuteString(','Cvar_Set('],
           'RS_TryStopResearch')

    change_cb=body(RCB,'RS_Change_f (')
    require(change_cb,[
        'RS_TryChangeScientists(',
        'diff > 0 ? 1 : (diff < 0 ? -1 : 0)',
        'RS_CHANGE_WRONG_BASE',
        'RS_CHANGE_NO_LAB_SPACE',
        'CP_Popup(_(',
        'ui_research_update_topic',
        'ui_research_update_caps',
    ],'RS_Change_f')
    forbid(change_cb,['RS_AssignScientist(','RS_RemoveScientist('],'RS_Change_f')

    max_cb=body(RCB,'RS_Max_f (')
    require(max_cb,['RS_TryMaxAssignScientists(','RS_CHANGE_WRONG_BASE',
                    'ui_research_update_topic','ui_research_update_caps'],'RS_Max_f')
    forbid(max_cb,['RS_AssignScientist('],'RS_Max_f')

    stop_cb=body(RCB,'RS_Stop_f (')
    require(stop_cb,['RS_TryStopResearch(','RS_CHANGE_WRONG_BASE',
                     'ui_research_update_topic','ui_research_update_caps'],'RS_Stop_f')
    forbid(stop_cb,['RS_StopResearch('],'RS_Stop_f')

    adapter=AD.read_text(encoding='utf-8')
    require(adapter,[
        '#include "../cgame/campaign/cp_research.h"',
        'technology_t* resolveTechnology(',
        'RS_GetTechByIDX(',
        'case StrategicIntentKind::AssignResearch:',
        'RS_TryChangeScientists(',
        'case StrategicIntentKind::MaxAssignResearch:',
        'RS_TryMaxAssignScientists(',
        'case StrategicIntentKind::StopResearch:',
        'RS_TryStopResearch(',
    ],'strategic adapter')
    forbid(adapter,[
        'Cmd_ExecuteString(','Cbuf_AddText(','Cvar_Set(','Cvar_SetValue(',
        'RS_AssignScientist(','RS_RemoveScientist(','RS_StopResearch(',
    ],'strategic adapter')

    rows=list(csv.DictReader(
        (ROOT/'tools/remaster/m1-authoritative-intent-coverage.tsv').open(),
        delimiter='\t'))
    strategic={r['semantic_action']:r for r in rows if r['domain']=='strategic'}
    for name in ('AssignResearch','MaxAssignResearch','StopResearch'):
        if strategic[name]['authority_bridge']!='canonical_applied':
            raise AssertionError(f'{name}: not canonical_applied')
        if strategic[name]['owner_source']!='src/client/cgame/campaign/cp_research.cpp':
            raise AssertionError(f'{name}: wrong owner_source')

    if sum(r['authority_bridge']=='canonical_applied' for r in strategic.values()) != 25:
        raise AssertionError('strategic applied accounting must be 25')
    if sum(r['authority_bridge']=='owner_extraction_pending_fail_closed'
           for r in strategic.values()) != 33:
        raise AssertionError('strategic pending accounting must be 33')

    for name in ('DecreaseProduction','MoveProductionDown','MoveProductionUp','StopProduction',
                 'IncreaseProduction','SetProductionAmount'):
        if strategic[name]['authority_bridge']!='canonical_applied':
            raise AssertionError(f'{name}: existing-job production owner must be canonical_applied')
    if strategic['CreateProduction']['authority_bridge']!='canonical_applied':
        raise AssertionError('CreateProduction must be canonical_applied')

    print('PASS M1 Research owner extraction: AssignResearch + MaxAssignResearch + StopResearch')
    print('PASS typed AssignResearch accepts exactly one-scientist +/-1 mutations; legacy callback preserves sign-only behavior')
    print('PASS research canonical owners contain no UI/popup/command/cvar dispatch; no-lab popup remains legacy-callback-only')
    print('PASS bridge accounting: strategic 25 applied / 33 fail-closed; research and all production owners qualified')
except AssertionError as exc:
    print('FAIL M1 Research owner extraction: '+str(exc),file=sys.stderr)
    raise SystemExit(1)
