#!/usr/bin/env python3
from pathlib import Path
import csv
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def body(text, signature):
    pos = text.find(signature)
    if pos < 0:
        raise AssertionError(f"missing body: {signature}")
    start = text.find("{", pos)
    if start < 0:
        raise AssertionError(f"missing body opener: {signature}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise AssertionError(f"unterminated body: {signature}")

def require(text, tokens, label):
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{label}: missing {token}")

def forbid(text, tokens, label):
    for token in tokens:
        if token in text:
            raise AssertionError(f"{label}: forbidden {token}")

def run(args):
    p = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    if p.returncode != 0:
        raise AssertionError(f"command failed ({p.returncode}): {' '.join(args)}\n{p.stdout}")
    return p.stdout

try:
    ph = (ROOT/"src/client/cgame/campaign/cp_produce.h").read_text(encoding="utf-8")
    pc = (ROOT/"src/client/cgame/campaign/cp_produce.cpp").read_text(encoding="utf-8")
    cb = (ROOT/"src/client/cgame/campaign/cp_produce_callbacks.cpp").read_text(encoding="utf-8")
    ih = (ROOT/"src/client/presentation/strategic_intent.h").read_text(encoding="utf-8")
    dispatch = (ROOT/"src/client/presentation/strategic_intent_dispatch.cpp").read_text(encoding="utf-8")
    adapter = (ROOT/"src/client/presentation/strategic_intent_legacy_adapter.cpp").read_text(encoding="utf-8")
    strict = [x.strip() for x in
              (ROOT/"tools/remaster/strict-strategic-actions.txt").read_text().splitlines()
              if x.strip()]

    if len(strict) != 58 or strict.count("CreateProduction") != 1:
        raise AssertionError("strict strategic semantic inventory must be 58 with one CreateProduction")

    require(ih, [
        "CreateProduction = 60",
        "TransferStoredUfo = 59",
        "submitIncreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount)",
        "submitSetProductionAmount(canonical::BaseId base, canonical::ProductionId production, int32_t amount)",
        "submitCreateProduction(canonical::BaseId base, int32_t subjectKind, canonical::ItemId item, canonical::StoredUfoId storedUfo, const char* aircraftDefinition, int32_t amount)",
    ], "normalized strategic intent contract")
    forbid(ih, [
        "submitIncreaseProduction(canonical::BaseId base, int32_t subjectKind",
    ], "IncreaseProduction contract")

    inc_dispatch = body(dispatch, "StrategicIntentSubmission submitIncreaseProduction(")
    require(inc_dispatch, [
        "StrategicIntentKind::IncreaseProduction",
        "v.production = production",
        "v.value0 = amount",
    ], "increase dispatch")
    forbid(inc_dispatch, ["subjectKind", "storedUfo", "aircraftDefinition"], "increase dispatch")

    create_dispatch = body(dispatch, "StrategicIntentSubmission submitCreateProduction(")
    require(create_dispatch, [
        "StrategicIntentKind::CreateProduction",
        "v.value0 = subjectKind",
        "v.item = item",
        "v.storedUfo = storedUfo",
        "v.value1 = amount",
        "copyBounded(v.key0, aircraftDefinition)",
    ], "create dispatch")

    require(ph, [
        "PR_MUTATION_APPLIED_PARTIAL",
        "PR_MUTATION_NOT_INCREASABLE",
        "PR_MUTATION_NO_HANGAR_CAPACITY",
        "PR_MUTATION_NO_MATERIALS",
        "PR_MUTATION_NO_CHANGE",
        "PR_IsMutationApplied(",
        "PR_TryIncreaseProduction(",
        "PR_TrySetProductionAmount(",
    ], "production owner header")

    increase = body(pc, "productionMutationResult_t PR_TryIncreaseProduction (")
    require(increase, [
        "PR_GetProductionByRuntimeId(base, runtimeId)",
        "PR_IsDisassembly(prod)",
        "CAP_GetFreeCapacity(base, AIR_GetHangarCapacityType(prod->data.data.aircraft))",
        "MAX_PRODUCTION_AMOUNT - prod->amount",
        "PR_RequirementsMet(amount, &tech->requireForProduction, base)",
        "PR_IncreaseProduction(prod, producibleAmount)",
        "PR_MUTATION_APPLIED_PARTIAL",
    ], "PR_TryIncreaseProduction")
    forbid(increase, ["UI_", "CP_Popup(", "Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set("],
           "PR_TryIncreaseProduction")

    set_amount = body(pc, "productionMutationResult_t PR_TrySetProductionAmount (")
    require(set_amount, [
        "targetAmount < 0",
        "targetAmount == prod->amount",
        "targetAmount == 0",
        "PR_TryStopProduction(base, runtimeId)",
        "PR_TryDecreaseProduction(base, runtimeId, prod->amount - targetAmount)",
        "PR_TryIncreaseProduction(base, runtimeId, targetAmount - prod->amount)",
    ], "PR_TrySetProductionAmount")
    forbid(set_amount, ["queueIndex", "UI_", "Cmd_ExecuteString(", "Cbuf_AddText("],
           "PR_TrySetProductionAmount")

    inc_cb = body(cb, "static void PR_ProductionIncrease_f (")
    require(inc_cb, [
        "if (selectedProduction)",
        "PR_GetProductionRuntimeId(prod)",
        "PR_TryIncreaseProduction(base, runtimeId, amount)",
        "PR_MUTATION_NO_HANGAR_CAPACITY",
        "PR_MUTATION_NO_MATERIALS",
        "PR_MUTATION_APPLIED_PARTIAL",
        "PR_TryCreateProduction(base, selectedData.type,",
    ], "legacy increase callback")
    # Creation and existing-job mutation both route through campaign-owned production helpers.
    selected = inc_cb[inc_cb.find("if (selectedProduction)"):inc_cb.find("} else {")]
    forbid(selected, ["PR_IncreaseProduction("], "legacy selected-job increase branch")

    for name, owner in (
        ("IncreaseProduction", "PR_TryIncreaseProduction("),
        ("SetProductionAmount", "PR_TrySetProductionAmount("),
    ):
        case = body(adapter, f"case StrategicIntentKind::{name}:")
        require(case, [
            "resolveBase(in.base)",
            "in.production.isValid()",
            owner,
            "in.production.value",
        ], f"adapter {name}")
        forbid(case, ["queueIndex", "Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set("],
               f"adapter {name}")

    fail_start = adapter.find("case StrategicIntentKind::AcceptUfoSaleOffer:")
    if fail_start < 0:
        raise AssertionError("fail-closed block missing")
    fail = adapter[fail_start:]
    if "case StrategicIntentKind::CreateProduction:" in fail:
        raise AssertionError("CreateProduction must not remain fail-closed")
    for name in ("IncreaseProduction", "SetProductionAmount"):
        if f"case StrategicIntentKind::{name}:" in fail:
            raise AssertionError(f"{name}: must not remain in fail-closed block")

    rows = list(csv.DictReader(
        (ROOT/"tools/remaster/m1-authoritative-intent-coverage.tsv").open(encoding="utf-8"),
        delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in rows if r["domain"] == "strategic"}
    if len(strategic) != 58:
        raise AssertionError("coverage ledger must contain 58 strategic semantics")
    for name in ("IncreaseProduction", "SetProductionAmount"):
        if strategic[name]["authority_bridge"] != "canonical_applied":
            raise AssertionError(f"{name}: must be canonical_applied")
        if strategic[name]["owner_source"] != "src/client/cgame/campaign/cp_produce.cpp":
            raise AssertionError(f"{name}: wrong owner source")
    if strategic["CreateProduction"]["authority_bridge"] != "canonical_applied":
        raise AssertionError("CreateProduction must be canonical_applied")
    if strategic["CreateProduction"]["owner_source"] != "src/client/cgame/campaign/cp_produce.cpp":
        raise AssertionError("CreateProduction must be owned by cp_produce.cpp")

    if sum(r["authority_bridge"] == "canonical_applied" for r in strategic.values()) != 25:
        raise AssertionError("strategic applied accounting must be 25")
    if sum(r["authority_bridge"] == "owner_extraction_pending_fail_closed" for r in strategic.values()) != 33:
        raise AssertionError("strategic pending accounting must be 33")

    cxx = shutil.which("g++")
    if not cxx:
        raise AssertionError("g++ not found")
    build = ROOT/".build/m1-production-contract-normalization"
    build.mkdir(parents=True, exist_ok=True)
    source = ROOT/"tools/remaster/m1-production-normalized-intent-contract.cpp"
    obj = build/"m1-production-normalized-intent-contract.o"
    run([
        cxx, "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(ROOT), "-c", str(source), "-o", str(obj),
    ])

    print("PASS M1 production contract normalization: Increase existing + absolute SetAmount")
    print("PASS legacy prod_inc semantic split: CreateProduction action 60 now routes through its canonical campaign owner")
    print("PASS normalized C++11 intent signatures compile without renumbering existing ABI values")
    print("PASS canonical increase/set owners re-resolve ProductionId and contain no UI/command/cvar dispatch")
    print("PASS bridge accounting: 58 strategic semantics; 25 applied / 33 fail-closed; tactical 13/2")
except AssertionError as exc:
    print("FAIL M1 production contract normalization: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
