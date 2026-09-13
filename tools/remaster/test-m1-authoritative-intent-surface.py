#!/usr/bin/env python3
from pathlib import Path
import re, subprocess, tempfile, sys
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'src/client/presentation'
strategic=(P/'strategic_intent.h').read_text()
tactical=(P/'tactical_intent.h').read_text()
strict_s=[x.strip() for x in (ROOT/'tools/remaster/strict-strategic-actions.txt').read_text().splitlines() if x.strip()]
strict_t=[x.strip() for x in (ROOT/'tools/remaster/strict-tactical-actions.txt').read_text().splitlines() if x.strip()]
missing=[]
for name in strict_s:
    if not re.search(r'\b'+re.escape(name)+r'\s*=\s*\d+', strategic): missing.append('strategic enum '+name)
    if 'submit'+name+'(' not in strategic: missing.append('strategic submit '+name)
for name in strict_t:
    if not re.search(r'\b'+re.escape(name)+r'\s*=\s*\d+', tactical): missing.append('tactical enum '+name)
    if 'submit'+name+'(' not in tactical: missing.append('tactical submit '+name)
if missing:
    print('FAIL missing contract entries:'); print('\n'.join('  '+m for m in missing)); sys.exit(1)
# Authority guard: presentation adapter must not use legacy command/cvar dispatch for new intents.
for file in ['strategic_intent_legacy_adapter.cpp','tactical_intent_legacy_adapter.cpp']:
    text=(P/file).read_text()
    for banned in ['Cmd_ExecuteString(', 'Cbuf_AddText(', 'Cvar_Set(', 'Cvar_SetValue(']:
        if banned in text:
            print(f'FAIL {file}: banned presentation dispatch {banned}'); sys.exit(1)
# Existing ABI values stay stable. Value 20 remains a tombstone so later kinds do not renumber.
for token in ['SetCampaignTimeLapse = 1','SelectMission = 2','SelectAircraft = 3','SendAircraftToMission = 4','ReturnAircraftToBase = 5']:
    assert token in strategic, token
assert 'DestroyAntimatterFacility = 20' in strategic
if 'submitDestroyAntimatterFacility(' in strategic:
    print('FAIL deprecated DestroyAntimatterFacility tombstone must not expose a public submit helper'); sys.exit(1)
if len(strict_s) != 57:
    print(f'FAIL strict strategic authoritative inventory must be 57, got {len(strict_s)}'); sys.exit(1)
for token in ['SetReactionFire = 1','SetReservedTimeUnits = 2']:
    assert token in tactical, token
# Public strategic headers must coexist in one translation unit.
with tempfile.TemporaryDirectory(prefix='ufoai-m1-strategic-header-coexist-') as td:
    td_path=Path(td)
    source=td_path/'coexist.cpp'
    obj=td_path/'coexist.o'
    source.write_text(
        '#include "src/client/presentation/strategic_intent.h"\n'
        '#include "src/client/presentation/strategic_publication.h"\n'
        'int main() {\n'
        '  ufo::presentation::StrategicPosition p = {0.0f, 0.0f, 0.0f};\n'
        '  ufo::presentation::StrategicIntent i = {};\n'
        '  i.position = p;\n'
        '  return i.position.longitude == 0.0f ? 0 : 1;\n'
        '}\n',
        encoding='utf-8',
    )
    proc=subprocess.run(
        ['g++','-std=c++11','-Wall','-Wextra','-Werror','-pedantic',
         '-I',str(ROOT),'-c',str(source),'-o',str(obj)],
        cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False,
    )
    if proc.returncode != 0:
        print('FAIL strategic intent/publication header coexistence:\n'+proc.stdout)
        sys.exit(1)
print('PASS strategic intent/publication header coexistence: C++11')
print(f'PASS contract coverage: {len(strict_s)} strategic authoritative semantics, {len(strict_t)} tactical semantics')
print('PASS presentation authority guard: no command/cvar fallback in intent adapters')
# Coverage ledger must match the strict inventory and fail-closed bridge accounting.
import csv
coverage=list(csv.DictReader((ROOT/'tools/remaster/m1-authoritative-intent-coverage.tsv').open(), delimiter='\t'))
ledger_s={r['semantic_action']:r for r in coverage if r['domain']=='strategic'}
ledger_t={r['semantic_action']:r for r in coverage if r['domain']=='tactical'}
if set(ledger_s) != set(strict_s):
    print('FAIL strategic coverage ledger does not match strict inventory'); sys.exit(1)
if set(ledger_t) != set(strict_t):
    print('FAIL tactical coverage ledger does not match strict inventory'); sys.exit(1)
expected_applied={
    'SetCampaignTimeLapse','SendAircraftToMission','ReturnAircraftToBase',
    'StartAircraft','StopAircraft','SetAircraftDestination','PursueUfo','ChangeAircraftHomebase',
    'BuildBase','RenameBase','BuildInstallation','RenameInstallation','DestroyInstallation',
    'BuildFacility','DestroyFacility',
    'AssignResearch','MaxAssignResearch','StopResearch',
    'DecreaseProduction','MoveProductionDown','MoveProductionUp','StopProduction',
    'IncreaseProduction','SetProductionAmount','CreateProduction',
    'AssignEmployeeToAircraft','DeequipEmployee','DeleteEmployee','HireOrFireEmployee',
    'RenameEmployee','SetEmployeeSkin',
    'BuyAircraft','BuyItem','BuyUGV','SellAircraft','SellItem','SellUGV','SetAutoSellPolicy',
    'AcceptUfoSaleOffer','DestroyStoredUfo','StoreRecoveredUfo','TransferStoredUfo',
    'KillContainedAlien','KillContainedAliens',
    'EquipAircraftItem','RemoveAircraftItem','RenameAircraft',
    'EquipBaseDefenceItem','RemoveBaseDefenceItem','SetAirDefenceAutoFire','SetAirDefenceTarget',
    'StartTransfer','SaveGame','LoadGame','LoadLastSave','StartMission',
}
applied={name for name,row in ledger_s.items() if row['authority_bridge']=='canonical_applied'}
if applied != expected_applied:
    print('FAIL strategic applied-owner set mismatch: '+repr(sorted(applied))); sys.exit(1)
expected_pending={
    'AutoResolveMission',
}
pending={name for name,row in ledger_s.items() if row['authority_bridge']=='owner_extraction_pending_fail_closed'}
if pending != expected_pending:
    print('FAIL strategic pending-owner set mismatch: '+repr(sorted(pending))); sys.exit(1)
if len(ledger_s) != 57:
    print(f'FAIL strategic coverage ledger must contain 57 semantics, got {len(ledger_s)}'); sys.exit(1)
if sum(r['authority_bridge']=='server_request_forwarded' for r in ledger_t.values()) != 13:
    print('FAIL tactical v1 bridge accounting must be 13 forwarded / 2 pending'); sys.exit(1)
if sum(r['authority_bridge']=='client_request_helper_pending_fail_closed' for r in ledger_t.values()) != 2:
    print('FAIL tactical v1 pending-helper accounting must be 2'); sys.exit(1)
tactical_adapter=(P/'tactical_intent_legacy_adapter.cpp').read_text()
if 'CL_ActorReload(' in tactical_adapter:
    print('FAIL Reload must fail closed until request emission is observable'); sys.exit(1)
if 'NET_WriteByte(&msg,clc_endround)' not in tactical_adapter:
    print('FAIL EndTurn must emit the existing clc_endround protocol directly'); sys.exit(1)
print('PASS bridge accounting: strategic 56 applied / 1 fail-closed; tactical 13 forwarded / 2 fail-closed')
