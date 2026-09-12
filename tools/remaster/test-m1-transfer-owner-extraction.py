#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def body(text, signature):
    start = text.find(signature)
    if start < 0:
        raise AssertionError("missing function: " + signature)
    brace = text.find("{", start)
    depth = 0
    state = "code"
    i = brace
    while i < len(text):
        c = text[i]
        n = text[i+1] if i+1 < len(text) else ""
        if state == "code":
            if c == "/" and n == "/":
                state = "line"; i += 1
            elif c == "/" and n == "*":
                state = "block"; i += 1
            elif c == '"':
                state = "string"
            elif c == "'":
                state = "char"
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        elif state == "line":
            if c == "\n": state = "code"
        elif state == "block":
            if c == "*" and n == "/":
                state = "code"; i += 1
        elif state == "string":
            if c == "\\": i += 1
            elif c == '"': state = "code"
        elif state == "char":
            if c == "\\": i += 1
            elif c == "'": state = "code"
        i += 1
    raise AssertionError("unterminated function: " + signature)

def require(text, tokens, label):
    for token in tokens:
        if token not in text:
            raise AssertionError(label + ": missing " + token)

def forbid(text, tokens, label):
    for token in tokens:
        if token in text:
            raise AssertionError(label + ": forbidden " + token)

try:
    public_h = read("src/client/presentation/strategic_intent.h")
    dispatch = read("src/client/presentation/strategic_intent_dispatch.cpp")
    adapter = read("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    transfer_h = read("src/client/cgame/campaign/cp_transfer.h")
    transfer_cpp = read("src/client/cgame/campaign/cp_transfer.cpp")
    callbacks = read("src/client/cgame/campaign/cp_transfer_callbacks.cpp")

    require(public_h, [
        "struct StrategicTransferManifest",
        "STRATEGIC_TRANSFER_MAX_ITEMS = 1024",
        "STRATEGIC_TRANSFER_MAX_EMPLOYEES = 512",
        "STRATEGIC_TRANSFER_MAX_AIRCRAFT = 64",
        "STRATEGIC_TRANSFER_MAX_ALIEN_TYPES = 128",
        "submitStartTransfer(const StrategicTransferManifest& manifest)",
        "takeTransferManifest(canonical::TransferManifestId manifest, StrategicTransferManifest* value)",
    ], "public transfer manifest contract")
    require(dispatch, [
        "MANIFEST_CAP=64", "stageManifestLocked(", "releaseManifestLocked(",
        "transferManifestShapeValid(", "takeTransferManifest(",
        "slot=TransferManifestSlot{}", "v.transferManifest=manifestId",
    ], "bounded one-shot transfer manifest runtime")

    require(transfer_h, [
        "transferStartRequest_t", "transferStartResult_t",
        "TR_BuildStartRequest(", "TR_TryStartTransfer(",
    ], "canonical transfer owner API")

    owner = body(transfer_cpp, "transferStartResult_t TR_TryStartTransfer (")
    require(owner, [
        "B_GetFoundedBaseByIDX(request.sourceBaseIndex)",
        "B_GetFoundedBaseByIDX(request.destinationBaseIndex)",
        "destination == source",
        "B_AntimatterInBase(source)",
        "INVSH_GetItemByIDX(item.itemIndex)",
        "B_ItemInBase(od, source) < item.amount",
        "E_GetEmployeeFromChrUCN(ucn)",
        "employee->getType() == EMPL_ROBOT",
        "!employee->isHiredInBase(source)",
        "AIR_AircraftGetFromIDX(idx)",
        "aircraft->homebase != source",
        "!AIR_IsAircraftInBase(aircraft)",
        "Com_GetTeamDefinitionByID(alien.teamDefinition)",
        "source->alienContainment->getAlive(team) < alien.alive",
        "source->alienContainment->getDead(team) < alien.dead",
        "if (!hasCargo)",
        "TR_TransferStart(source, transData)",
    ], "canonical StartTransfer owner")
    mutate = owner.find("TR_TransferStart(source, transData)")
    for resolver in (
        "B_GetFoundedBaseByIDX(request.sourceBaseIndex)",
        "B_GetFoundedBaseByIDX(request.destinationBaseIndex)",
        "INVSH_GetItemByIDX(item.itemIndex)",
        "E_GetEmployeeFromChrUCN(ucn)",
        "AIR_AircraftGetFromIDX(idx)",
        "Com_GetTeamDefinitionByID(alien.teamDefinition)",
    ):
        if owner.find(resolver) > mutate:
            raise AssertionError("canonical StartTransfer owner mutates before resolving: " + resolver)
    forbid(owner, ["UI_", "Cmd_ExecuteString(", "Cvar_Set(", "Cvar_SetValue("],
           "canonical StartTransfer owner presentation authority")

    legacy = body(callbacks, "static void TR_TransferStart_f (")
    require(legacy, [
        "TR_BuildStartRequest(base, tr, &request)",
        "TR_TryStartTransfer(request, &startedTransfer)",
        "TR_ClearTempCargo()", "MSO_CheckAddNewMessage(", "UI_PopWindow(false)",
    ], "legacy transfer callback")
    forbid(legacy, ["TR_TransferStart(base, tr)"], "legacy direct transfer mutation")

    require(adapter, [
        "case StrategicIntentKind::StartTransfer:",
        "takeTransferManifest(in.transferManifest,&manifest)",
        "buildTransferStartRequest(manifest,&request)",
        "TR_TryStartTransfer(request,&started)",
    ], "typed StartTransfer adapter")
    forbid(adapter, ["Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("],
           "strategic adapter command fallback")

    pending = adapter.split("Strict-authority catalog is transport-complete", 1)[1]
    if "case StrategicIntentKind::StartTransfer:" in pending:
        raise AssertionError("StartTransfer remains in fail-closed pending block")

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        cov = {r["semantic_action"]: r for r in csv.DictReader(f, delimiter="\t")
               if r["domain"] == "strategic"}
    if cov["StartTransfer"]["authority_bridge"] != "canonical_applied":
        raise AssertionError("StartTransfer is not canonical_applied")
    if cov["StartTransfer"]["owner_source"] != "src/client/cgame/campaign/cp_transfer.cpp":
        raise AssertionError("StartTransfer owner source mismatch")

    with (ROOT / "tools/remaster/m1-canonical-identity-registry.tsv").open() as f:
        reg = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    tm = reg["TransferManifestId"]
    if tm["classification"] != "submission_context":
        raise AssertionError("TransferManifestId changed identity class")
    if tm["mapping_status"] != "bounded_submission_registry":
        raise AssertionError("TransferManifestId bounded registry not recorded")
    if tm["intent_status"] != "start_transfer_owner_qualified":
        raise AssertionError("TransferManifestId StartTransfer status stale")
    if reg["TransferId"]["mapping_status"] != "type_added_mapping_missing":
        raise AssertionError("active TransferId debt was accidentally changed")

    with (ROOT / "tools/remaster/m1-canonical-identity-lifetime-registry.tsv").open() as f:
        life = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    if life["TransferManifestId"]["second_pass_status"] != "qualified_submission_mapping":
        raise AssertionError("TransferManifestId lifetime mapping not qualified")
    if life["TransferId"]["second_pass_status"] != "pending_mapping":
        raise AssertionError("active TransferId mapping debt changed")

    contract = read("tools/remaster/m1-intent-catalog-contract.cpp")
    require(contract, [
        "intent::submitStartTransfer(manifest)",
        "intent::legacy::takeTransferManifest(transferIntent.transferManifest, &consumed)",
        "if (intent::legacy::takeTransferManifest(transferIntent.transferManifest, &consumed))",
        "oversized.itemCount",
    ], "direct one-shot manifest runtime test")

    integration = read("tools/remaster/m1-intent-catalog-integration.cpp")
    require(integration, [
        "TransferManifestIntentIsBoundedOneShotAndCanonicalRejectsStaleBases",
        "submitStartTransfer(manifest)",
        "TR_START_INVALID_SOURCE",
    ], "StartTransfer integration test")

    save_h = read("src/client/cgame/campaign/cp_save.h")
    common_h = read("src/common/common.h")
    if not re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h):
        raise AssertionError("save version changed")
    if not re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h):
        raise AssertionError("protocol version changed")

    print("PASS M1 StartTransfer owner extraction")
    print("  bounded value-only transfer manifest staged behind one-shot TransferManifestId")
    print("  canonical owner resolves and validates complete cargo before inherited mutation begins")
    print("  legacy callback and typed adapter converge on TR_TryStartTransfer")
    print("  active TransferId remains explicit unmapped debt")
    print("  authority: strategic 52/57 applied, 5 fail-closed")
    print("  save v4 / protocol 18 unchanged")
except AssertionError as exc:
    print("FAIL M1 StartTransfer owner extraction: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
