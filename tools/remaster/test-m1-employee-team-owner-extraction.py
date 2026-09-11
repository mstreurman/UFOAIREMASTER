#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]

class GateError(RuntimeError):
    pass

def require(cond, message):
    if not cond:
        raise GateError(message)

def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def function_body(source, signature):
    start = source.find(signature)
    require(start >= 0, "missing function: " + signature)
    brace = source.find("{", start)
    require(brace >= 0, "missing function body: " + signature)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise GateError("unterminated function: " + signature)

def main():
    employee_h = text("src/client/cgame/campaign/cp_employee.h")
    employee_cpp = text("src/client/cgame/campaign/cp_employee.cpp")
    employee_cb = text("src/client/cgame/campaign/cp_employee_callbacks.cpp")
    team_h = text("src/client/cgame/campaign/cp_team.h")
    team_cpp = text("src/client/cgame/campaign/cp_team.cpp")
    team_cb = text("src/client/cgame/campaign/cp_team_callbacks.cpp")
    adapter = text("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    snapshot = text("src/client/presentation/strategic_snapshot.h")
    snapshot_adapter = text("src/client/presentation/strategic_snapshot_legacy_adapter.cpp")

    for token in ("E_TrySetHired", "E_TryDeleteEmployee", "E_TryRenameEmployee", "E_IsMutationAccepted"):
        require(token in employee_h and token in employee_cpp, "employee owner missing: " + token)
    for token in ("CP_TEAM_TrySetAircraftAssignment", "CP_TEAM_TryDeequipEmployee", "CP_TEAM_TrySetEmployeeSkin", "CP_TEAM_IsMutationAccepted"):
        require(token in team_h and token in team_cpp, "team owner missing: " + token)

    for signature, source in (
        ("employeeMutationResult_t E_TrySetHired", employee_cpp),
        ("employeeMutationResult_t E_TryDeleteEmployee", employee_cpp),
        ("employeeMutationResult_t E_TryRenameEmployee", employee_cpp),
        ("teamMutationResult_t CP_TEAM_TrySetAircraftAssignment", team_cpp),
        ("teamMutationResult_t CP_TEAM_TryDeequipEmployee", team_cpp),
        ("teamMutationResult_t CP_TEAM_TrySetEmployeeSkin", team_cpp),
    ):
        owner = function_body(source, signature)
        for banned in ("UI_", "Cvar_", "Cbuf_", "Cmd_"):
            require(banned not in owner, signature + ": presentation dispatch leaked into owner: " + banned)

    hire = function_body(employee_cpp, "employeeMutationResult_t E_TrySetHired")
    require("E_GetEmployeeFromChrUCN(employeeUcn)" in hire, "hire owner must re-resolve EmployeeId")
    require("CAP_GetFreeCapacity(base, CAP_EMPLOYEES) <= 0" in hire, "hire owner must preserve inherited quarters gate")
    require("employee->isAwayFromBase()" in hire, "fire path must preserve away-from-base UI eligibility")
    require("E_HireEmployee(base, employee)" in hire, "hire owner must retain low-level canonical mutation")

    delete = function_body(employee_cpp, "employeeMutationResult_t E_TryDeleteEmployee")
    require(delete.index("employee->transfer") < delete.index("E_DeleteEmployee(employee)"), "delete owner must reject transfer before low-level deletion")
    require("employee->isAwayFromBase()" in delete, "delete owner must preserve away-from-base UI eligibility")

    rename = function_body(employee_cpp, "employeeMutationResult_t E_TryRenameEmployee")
    require("employee->transfer" not in rename, "rename owner must not invent a transfer-state restriction absent from the legacy rename callback")

    assign = function_body(team_cpp, "teamMutationResult_t CP_TEAM_TrySetAircraftAssignment")
    for token in (
        "E_GetEmployeeFromChrUCN(employeeUcn)", "AIR_AircraftGetFromIDX(aircraftIdx)",
        "AIR_IsAircraftInBase(aircraft)",
        "employee->isHiredInBase(aircraft->homebase)", "AIR_IsEmployeeInAircraft(employee, nullptr)",
        "AIR_SetPilot(aircraft, employee)", "AIR_AddToAircraftTeam(aircraft, employee)",
        "AIR_RemoveEmployee(employee, aircraft)",
    ):
        require(token in assign, "assignment owner contract missing: " + token)

    deequip = function_body(team_cpp, "teamMutationResult_t CP_TEAM_TryDeequipEmployee")
    for token in (
        "INV_DestroyInventory(&employee->chr.inv)", "CP_CleanTempInventory(nullptr)",
        "equipDef_t unused = base->storage", "CP_CleanupTeam(base, &unused)",
    ):
        require(token in deequip, "de-equip owner lost legacy cleanup semantic: " + token)
    require("UI_ContainerNodeUpdateEquipment" not in deequip, "de-equip widget refresh must remain callback-only")
    require("employee->isAwayFromBase()" in deequip, "de-equip owner must preserve away-from-base UI eligibility")
    require("INV_DestroyInventory(&base->bEquipment)" not in deequip, "legacy base equipment scratch mutation must remain outside canonical de-equip owner")
    require("INV_DestroyInventory(&base->bEquipment)" in team_cb, "legacy callback must retain base equipment scratch cleanup")

    skin = function_body(team_cpp, "teamMutationResult_t CP_TEAM_TrySetEmployeeSkin")
    require("employee->isSoldier()" in skin, "skin owner must preserve soldier-only contract")
    require("bodySkin <" not in skin and "bodySkin >" not in skin, "skin owner must not invent range validation")

    for token in ("E_TryRenameEmployee(", "E_TryDeleteEmployee(", "E_TrySetHired("):
        require(token in employee_cb, "legacy employee callback does not converge on owner: " + token)
    for token in ("CP_TEAM_TrySetAircraftAssignment(", "CP_TEAM_TryDeequipEmployee(", "CP_TEAM_TrySetEmployeeSkin("):
        require(token in team_cb, "legacy team callback does not converge on owner: " + token)

    actions = (
        "AssignEmployeeToAircraft", "DeequipEmployee", "DeleteEmployee",
        "HireOrFireEmployee", "RenameEmployee", "SetEmployeeSkin",
    )
    fail_block = adapter[adapter.index("/* Strict-authority catalog is transport-complete"):]
    for action in actions:
        require("case StrategicIntentKind::" + action + ":" in adapter, "typed owner case missing: " + action)
        require("case StrategicIntentKind::" + action + ":" not in fail_block, action + " remains fail-closed")
    require("in.flag0" not in adapter, "nonexistent StrategicIntent::flag0 was introduced")
    require("in.value0!=0" in adapter, "employee boolean intents must use existing value0 transport")
    for banned in ("Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("):
        require(banned not in adapter, "typed strategic adapter contains banned fallback: " + banned)

    for token in (
        "struct StrategicEmployeeView", "canonical::EmployeeId id;",
        "const std::vector<StrategicEmployeeView>& employees() const noexcept",
        "std::vector<StrategicEmployeeView> employees_;",
    ):
        require(token in snapshot, "immutable employee publication missing: " + token)
    for token in (
        "projectEmployee(const Employee& employee)",
        "indexedId<canonical::EmployeeId>(employee.chr.ucn)",
        "E_Foreach(type, employee)", "employees.push_back(projectEmployee(*employee))",
    ):
        require(token in snapshot_adapter, "legacy employee projection missing: " + token)

    with tempfile.TemporaryDirectory(prefix="ufoai-m1-employee-snapshot-") as td:
        source = Path(td) / "contract.cpp"
        obj = Path(td) / "contract.o"
        source.write_text(
            '#include "src/client/presentation/strategic_snapshot.h"\n'
            '#include <type_traits>\n#include <utility>\n#include <vector>\n'
            'static_assert(std::is_same<decltype(std::declval<const ufo::presentation::StrategicSnapshot&>().employees()), '
            'const std::vector<ufo::presentation::StrategicEmployeeView>&>::value, "employee snapshot must be const-only");\n'
            'int main(){return 0;}\n', encoding="utf-8")
        proc = subprocess.run(
            ["g++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-I", str(ROOT), "-c", str(source), "-o", str(obj)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        require(proc.returncode == 0, "C++11 employee snapshot contract failed:\n" + proc.stdout)

    registry = list(csv.DictReader((ROOT / "tools/remaster/m1-canonical-identity-registry.tsv").open(encoding="utf-8"), delimiter="\t"))
    employee = {r["identity"]: r for r in registry}["EmployeeId"]
    require(employee["mapping_status"] == "direct_reconciled_persisted_qualified", "EmployeeId mapping qualification regressed")
    require(employee["publication_status"] == "published", "EmployeeId is not published")
    require(employee["intent_status"] == "employee_team_owners_qualified", "EmployeeId owner status is not qualified")

    coverage = list(csv.DictReader((ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open(encoding="utf-8"), delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in coverage if r["domain"] == "strategic"}
    for action in actions:
        require(strategic[action]["authority_bridge"] == "canonical_applied", action + " is not canonical_applied")
    common_h = text("src/common/common.h")
    save_h = text("src/client/cgame/campaign/cp_save.h")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h) is not None, "protocol version changed from 18")
    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h) is not None, "save version changed from 4")

    print("PASS M1 Employee + Team canonical owner extraction")
    print("PASS EmployeeId immutable publication from persisted chr.ucn")
    print("PASS six legacy/typed paths converge on campaign owners")
    print("PASS preservation guards: quarters, away-fire/delete/de-equip, in-base crew assignment, transfer delete, transfer-agnostic rename, skin integer semantics, de-equip cleanup")
    print("PASS Employee/Team family remains qualified; aggregate authority accounting is centralized")
    print("PASS save v4 and protocol 18 unchanged")

if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 Employee + Team owner extraction: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
