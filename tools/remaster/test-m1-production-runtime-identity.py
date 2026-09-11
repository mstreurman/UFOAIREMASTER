#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def require(text, tokens, label):
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{label}: missing {token}")

def forbid(text, tokens, label):
    for token in tokens:
        if token in text:
            raise AssertionError(f"{label}: forbidden {token}")

def body(text, signature):
    pos = text.find(signature)
    if pos < 0:
        raise AssertionError(f"missing body signature: {signature}")
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

try:
    ph = (ROOT/"src/client/cgame/campaign/cp_produce.h").read_text(encoding="utf-8")
    pc = (ROOT/"src/client/cgame/campaign/cp_produce.cpp").read_text(encoding="utf-8")
    common = (ROOT/"src/common/common.h").read_text(encoding="utf-8")
    snapshot = (ROOT/"src/client/presentation/strategic_snapshot.h").read_text(encoding="utf-8")
    snap_adapter = (ROOT/"src/client/presentation/strategic_snapshot_legacy_adapter.cpp").read_text(encoding="utf-8")
    intent = (ROOT/"src/client/presentation/strategic_intent.h").read_text(encoding="utf-8")
    dispatch = (ROOT/"src/client/presentation/strategic_intent_dispatch.cpp").read_text(encoding="utf-8")

    require(ph, [
        "uint32_t runtimeId;",
        "uint32_t PR_GetProductionRuntimeId(const production_t* production);",
        "production_t* PR_GetProductionByRuntimeId(struct base_s* base, uint32_t runtimeId);",
        "const production_t* PR_GetProductionByRuntimeId(const struct base_s* base, uint32_t runtimeId);",
    ], "production header")

    require(pc, [
        "static uint32_t nextProductionRuntimeId = 0;",
        "static uint32_t PR_AllocateRuntimeId (void)",
        "std::numeric_limits<uint32_t>::max()",
    ], "production runtime allocator")

    queue_new = body(pc, "production_t* PR_QueueNew (")
    require(queue_new, ["prod->runtimeId = PR_AllocateRuntimeId();", "queue->numItems++;"], "PR_QueueNew")
    if queue_new.index("prod->runtimeId = PR_AllocateRuntimeId();") > queue_new.index("queue->numItems++;"):
        raise AssertionError("PR_QueueNew: runtime ID must be assigned before queue activation")

    queue_move = body(pc, "void PR_QueueMove (")
    require(queue_move, [
        "production_t saved = queue->items[index];",
        "queue->items[i] = queue->items[i + 1];",
        "queue->items[i] = queue->items[i - 1];",
        "queue->items[newIndex] = saved;",
    ], "PR_QueueMove")
    forbid(queue_move, ["runtimeId ="], "PR_QueueMove must preserve copied runtime identity")

    queue_delete = body(pc, "void PR_QueueDelete (")
    require(queue_delete, ["REMOVE_ELEM_ADJUST_IDX(queue->items, index, queue->numItems);"], "PR_QueueDelete")

    require(common, [
        "#define REMOVE_ELEM(array, index, n)",
        "memmove((array) + idx__, (array) + idx__ + 1",
        "#define REMOVE_ELEM_ADJUST_IDX(array, index, n)",
        "--(array)[i__].idx;",
    ], "queue compaction macro")

    resolver_const = body(pc, "const production_t* PR_GetProductionByRuntimeId (")
    require(resolver_const, [
        "runtimeId == std::numeric_limits<uint32_t>::max()",
        "PR_GetProductionForBase(base)",
        "queue->items[i].runtimeId == runtimeId",
    ], "production runtime resolver")

    save_body = body(pc, "bool PR_SaveXML (")
    forbid(save_body, ["runtimeId", "ProductionId"], "PR_SaveXML runtime-only identity")

    load_body = body(pc, "bool PR_LoadXML (")
    require(load_body, ["prod->runtimeId = PR_AllocateRuntimeId();", "pq->numItems++;"], "PR_LoadXML")
    if load_body.index("prod->runtimeId = PR_AllocateRuntimeId();") > load_body.index("pq->numItems++;"):
        raise AssertionError("PR_LoadXML: runtime ID must be assigned before loaded queue activation")

    prod_view = body(snapshot, "struct StrategicProductionView ")
    require(prod_view, ["canonical::ProductionId id;", "int32_t queueIndex;"], "StrategicProductionView")
    require(snap_adapter, [
        "out.id = canonical::ProductionId(PR_GetProductionRuntimeId(&production));",
        "out.queueIndex = production.idx;",
    ], "production publication mapping")

    signatures = [
        "submitDecreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount)",
        "submitIncreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount)",
        "submitCreateProduction(canonical::BaseId base, int32_t subjectKind, canonical::ItemId item, canonical::StoredUfoId storedUfo, const char* aircraftDefinition, int32_t amount)",
        "submitMoveProductionDown(canonical::BaseId base, canonical::ProductionId production)",
        "submitMoveProductionUp(canonical::BaseId base, canonical::ProductionId production)",
        "submitSetProductionAmount(canonical::BaseId base, canonical::ProductionId production, int32_t amount)",
        "submitStopProduction(canonical::BaseId base, canonical::ProductionId production)",
    ]
    require(intent, signatures, "typed production intent declarations")
    forbid(intent, [
        "submitDecreaseProduction(canonical::BaseId base, int32_t queueIndex",
        "submitMoveProductionDown(canonical::BaseId base, int32_t queueIndex",
        "submitMoveProductionUp(canonical::BaseId base, int32_t queueIndex",
        "submitSetProductionAmount(canonical::BaseId base, int32_t queueIndex",
        "submitStopProduction(canonical::BaseId base, int32_t queueIndex",
    ], "typed production intent declarations")

    for sig in [
        "submitDecreaseProduction(",
        "submitIncreaseProduction(",
        "submitMoveProductionDown(",
        "submitMoveProductionUp(",
        "submitSetProductionAmount(",
        "submitStopProduction(",
    ]:
        fn = body(dispatch, sig)
        require(fn, ["v.production = production;"], sig)
        if "queueIndex" in fn:
            raise AssertionError(f"{sig}: queueIndex must not be mutation identity")

    rows = list(csv.DictReader(
        (ROOT/"tools/remaster/m1-canonical-identity-registry.tsv").open(encoding="utf-8"),
        delimiter="\t"))
    by_id = {r["identity"]: r for r in rows}
    prod = by_id["ProductionId"]
    if prod["classification"] != "runtime_direct":
        raise AssertionError("ProductionId registry classification must be runtime_direct after implementation")
    if prod["mapping_status"] != "runtime_mapping_implemented":
        raise AssertionError("ProductionId registry mapping_status must be runtime_mapping_implemented")
    if prod["publication_status"] != "published":
        raise AssertionError("ProductionId registry must be published")
    if prod["intent_status"] != "production_owners_qualified":
        raise AssertionError("ProductionId intent status must reflect all production owners qualified")

    coverage = list(csv.DictReader(
        (ROOT/"tools/remaster/m1-authoritative-intent-coverage.tsv").open(encoding="utf-8"),
        delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in coverage if r["domain"] == "strategic"}
    for name in ("DecreaseProduction","MoveProductionDown","MoveProductionUp","StopProduction",
                 "IncreaseProduction","SetProductionAmount"):
        if strategic[name]["authority_bridge"] != "canonical_applied":
            raise AssertionError(f"{name}: existing-job production owner must be canonical_applied")
    if strategic["CreateProduction"]["authority_bridge"] != "canonical_applied":
        raise AssertionError("CreateProduction must be canonical_applied")

    print("PASS M1 stable ProductionId: runtime identity survives queue copy/compaction semantics")
    print("PASS ProductionId is published with queueIndex retained as order metadata")
    print("PASS production submit APIs use ProductionId rather than queueIndex identity")
    print("PASS ProductionId is runtime-only and regenerated on load; save schema unchanged")
    print("PASS ProductionId drives all six existing-job production owners; CreateProduction uses the qualified canonical create owner")
except AssertionError as exc:
    print("FAIL M1 stable ProductionId: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
