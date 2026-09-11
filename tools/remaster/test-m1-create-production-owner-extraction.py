#!/usr/bin/env python3
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]


def body(text, signature):
    pos = text.find(signature)
    if pos < 0:
        raise AssertionError("missing body: " + signature)
    start = text.find("{", pos)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: return text[start:i + 1]
    raise AssertionError("unterminated body: " + signature)


def require(text, tokens, label):
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{label}: missing {token}")


def forbid(text, tokens, label):
    for token in tokens:
        if token in text:
            raise AssertionError(f"{label}: forbidden {token}")


try:
    ph = (ROOT / "src/client/cgame/campaign/cp_produce.h").read_text()
    pc = (ROOT / "src/client/cgame/campaign/cp_produce.cpp").read_text()
    cb = (ROOT / "src/client/cgame/campaign/cp_produce_callbacks.cpp").read_text()
    adapter = (ROOT / "src/client/presentation/strategic_intent_legacy_adapter.cpp").read_text()

    require(ph, [
        "PR_TryCreateProduction(", "PR_MUTATION_INVALID_SUBJECT",
        "PR_MUTATION_UNSUPPORTED_SUBJECT", "PR_MUTATION_NOT_PRODUCIBLE",
        "PR_MUTATION_ALREADY_DISASSEMBLING", "PR_MUTATION_QUEUE_FULL",
    ], "production owner header")

    owner = body(pc, "productionMutationResult_t PR_TryCreateProduction (")
    require(owner, [
        "amount <= 0", "cgi->csi->numODs", "INVSH_GetItemByIDX(itemIndex)",
        "item->idx != itemIndex", "item->isVirtual", "RS_IsResearched_ptr(tech)",
        "PR_ItemIsProduceable(item)", "AIR_GetAircraftSilent(aircraftDefinition)",
        "AIR_IsUFO(aircraft)", "AIR_GetHangarCapacityType(aircraft)",
        "US_GetStoredUFOByIDX(storedUfoIndex)", "ufo->status != SUFO_STORED",
        "ufo->disassembly", "PR_RequirementsMet(queueAmount, &tech->requireForProduction, base)",
        "PR_GetProductionForBase(base)->numItems >= MAX_PRODUCTIONS",
        "PR_QueueNew(base, &data, producibleAmount)", "PR_MUTATION_APPLIED_PARTIAL",
    ], "CreateProduction owner")
    forbid(owner, ["UI_", "CP_Popup(", "Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set("],
           "CreateProduction owner")

    callback = body(cb, "static void PR_ProductionIncrease_f (")
    require(callback, ["PR_TryCreateProduction(base, selectedData.type,", "PR_IsMutationApplied(result)",
                       "PR_GetTech(&prod->data)", "PR_GetName(&prod->data)"], "legacy create adapter")
    create_branch = callback[callback.find("} else {"):]
    forbid(create_branch, ["PR_QueueNew(", "PR_RequirementsMet("], "legacy create adapter")

    case = body(adapter, "case StrategicIntentKind::CreateProduction:")
    require(case, ["resolveBase(in.base)", "resolveBoundedText(in.key0)", "in.item.isValid()",
                   "in.storedUfo.isValid()", "PR_TryCreateProduction(", "PR_IsMutationApplied(result)"],
            "typed CreateProduction adapter")
    forbid(case, ["PR_QueueNew(", "Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set("],
           "typed CreateProduction adapter")
    fail = adapter[adapter.find("case StrategicIntentKind::AcceptUfoSaleOffer:"):]
    if "case StrategicIntentKind::CreateProduction:" in fail:
        raise AssertionError("CreateProduction remains in fail-closed block")

    rows = list(csv.DictReader((ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open(), delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in rows if r["domain"] == "strategic"}
    if strategic["CreateProduction"]["authority_bridge"] != "canonical_applied":
        raise AssertionError("CreateProduction ledger not canonical_applied")
    if strategic["CreateProduction"]["owner_source"] != "src/client/cgame/campaign/cp_produce.cpp":
        raise AssertionError("CreateProduction ledger owner is not cp_produce.cpp")
    print("PASS M1 CreateProduction canonical owner extraction")
    print("PASS item/aircraft/stored-UFO subjects are re-resolved and canonically requalified")
    print("PASS legacy prod_inc and typed remaster intent converge on PR_TryCreateProduction")
    print("PASS CreateProduction family remains qualified; aggregate authority accounting is centralized")
except AssertionError as exc:
    print("FAIL M1 CreateProduction canonical owner extraction: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
