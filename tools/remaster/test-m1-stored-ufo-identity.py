#!/usr/bin/env python3
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[2]

def body(text: str, signature: str) -> str:
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
                return text[start:i + 1]
    raise AssertionError(f"unterminated body: {signature}")

def require(text: str, tokens, label: str):
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{label}: missing {token}")

def forbid(text: str, tokens, label: str):
    for token in tokens:
        if token in text:
            raise AssertionError(f"{label}: forbidden {token}")

try:
    uh = (ROOT/"src/client/cgame/campaign/cp_uforecovery.h").read_text(encoding="utf-8")
    uc = (ROOT/"src/client/cgame/campaign/cp_uforecovery.cpp").read_text(encoding="utf-8")
    stats = (ROOT/"src/client/cgame/campaign/cp_statistics.cpp").read_text(encoding="utf-8")
    save = (ROOT/"src/client/cgame/campaign/cp_save.cpp").read_text(encoding="utf-8")
    snapshot = (ROOT/"src/client/presentation/strategic_snapshot.h").read_text(encoding="utf-8")
    adapter = (ROOT/"src/client/presentation/strategic_snapshot_legacy_adapter.cpp").read_text(encoding="utf-8")

    require(uh, [
        "typedef struct storedUFO_s {",
        "int idx;",
        "#define US_Foreach(var) LIST_Foreach(ccs.storedUFOs, storedUFO_t, var)",
        "storedUFO_t* US_GetStoredUFOByIDX(const int idx);",
    ], "stored UFO canonical type/API")

    lookup = body(uc, "storedUFO_t* US_GetStoredUFOByIDX (")
    require(lookup, ["US_Foreach(ufo)", "ufo->idx == idx"], "stored UFO identity lookup")

    store = body(uc, "storedUFO_t* US_StoreUFO (")
    require(store, [
        "ccs.campaignStats.ufosStored < 0",
        "std::numeric_limits<int>::max()",
        "ufo.idx = ccs.campaignStats.ufosStored++;",
        "LIST_Add(&ccs.storedUFOs, ufo)",
    ], "stored UFO allocation")
    if store.index("std::numeric_limits<int>::max()") > store.index("ufo.idx = ccs.campaignStats.ufosStored++;"):
        raise AssertionError("StoredUfoId exhaustion guard must precede allocation")

    remove = body(uc, "void US_RemoveStoredUFO (")
    require(remove, ["LIST_Remove(&ccs.storedUFOs, (void*)ufo)"], "stored UFO removal")
    forbid(remove, ["ufo->idx =", "ufosStored--"], "stored UFO removal identity stability")

    save_ufo = body(uc, "bool US_SaveXML (")
    require(save_ufo, [
        "SAVE_UFORECOVERY_UFOIDX",
        "ufo->idx",
    ], "stored UFO identity save")

    load_ufo = body(uc, "bool US_LoadXML (")
    require(load_ufo, [
        "ufo.idx = cgi->XML_GetInt(snode, SAVE_UFORECOVERY_UFOIDX, -1)",
        "US_GetStoredUFOByIDX(ufo.idx)",
        "Duplicate stored UFO IDX",
        "LIST_Add(&ccs.storedUFOs, ufo)",
    ], "stored UFO identity load")
    if load_ufo.index("US_GetStoredUFOByIDX(ufo.idx)") > load_ufo.index("LIST_Add(&ccs.storedUFOs, ufo)"):
        raise AssertionError("duplicate StoredUfoId check must happen before list insertion")

    save_stats = body(stats, "bool STATS_SaveXML (")
    require(save_stats, [
        "SAVE_STATS_UFOSSTORED",
        "ccs.campaignStats.ufosStored",
    ], "StoredUfoId allocator save")

    load_stats = body(stats, "bool STATS_LoadXML (")
    require(load_stats, [
        'ccs.campaignStats.ufosStored = cgi->XML_GetInt(stats, SAVE_STATS_UFOSSTORED, 0);',
        "US_Foreach(ufo)",
        "ufo->idx >= ccs.campaignStats.ufosStored",
        "std::numeric_limits<int>::max()",
        "ufo->idx + 1",
    ], "StoredUfoId allocator load reconciliation")
    if load_stats.index("US_Foreach(ufo)") < load_stats.index("SAVE_STATS_UFOSSTORED"):
        raise AssertionError("stored-UFO counter reconciliation must happen after stats counter restore")

    require(save, [
        "SAV_AddSubsystem(&us_subsystemXML);",
        "SAV_AddSubsystem(&stats_subsystemXML);",
    ], "save subsystem order")
    if save.index("SAV_AddSubsystem(&us_subsystemXML);") > save.index("SAV_AddSubsystem(&stats_subsystemXML);"):
        raise AssertionError("focused identity contract expects ufostores to load before stats reconciliation")

    view = body(snapshot, "struct StrategicStoredUfoView ")
    require(view, [
        "canonical::StoredUfoId id;",
        "canonical::InstallationId installation;",
        "int32_t status;",
        "float condition;",
        "bool disassembling;",
        "std::string ufoDefinition;",
    ], "stored UFO public view")
    forbid(view, ["storedUFO_t", "installation_t", "aircraft_t", "production_t", "*"], "stored UFO public view")
    require(snapshot, [
        "const std::vector<StrategicStoredUfoView>& storedUfos() const",
        "std::vector<StrategicStoredUfoView> storedUfos_;",
    ], "stored UFO snapshot publication")

    require(adapter, [
        '#include "../cgame/campaign/cp_uforecovery.h"',
        "StrategicStoredUfoView projectStoredUfo(",
        "indexedId<canonical::StoredUfoId>(ufo.idx)",
        "indexedId<canonical::InstallationId>(ufo.installation->idx)",
        "ufo.disassembly != nullptr",
        "valueString(ufo.id)",
        "std::vector<StrategicStoredUfoView> storedUfos;",
        "US_Foreach(ufo)",
        "storedUfos.push_back(projectStoredUfo(*ufo))",
    ], "stored UFO legacy projection")

    rows = list(csv.DictReader(
        (ROOT/"tools/remaster/m1-canonical-identity-registry.tsv").open(encoding="utf-8"),
        delimiter="\t"))
    by_id = {r["identity"]: r for r in rows}
    stored = by_id["StoredUfoId"]
    if stored["classification"] != "runtime_direct":
        raise AssertionError("StoredUfoId classification must remain runtime_direct")
    if stored["mapping_status"] != "direct_persisted_qualified":
        raise AssertionError("StoredUfoId mapping must be direct_persisted_qualified")
    if stored["publication_status"] != "published":
        raise AssertionError("StoredUfoId must be published")
    if stored["intent_status"] != "create_production_owner_qualified":
        raise AssertionError("StoredUfoId intent status must reflect the qualified CreateProduction owner")

    coverage = list(csv.DictReader(
        (ROOT/"tools/remaster/m1-authoritative-intent-coverage.tsv").open(encoding="utf-8"),
        delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in coverage if r["domain"] == "strategic"}
    if strategic["CreateProduction"]["authority_bridge"] != "canonical_applied":
        raise AssertionError("CreateProduction must be canonical_applied after owner extraction")
    if sum(r["authority_bridge"] == "canonical_applied" for r in strategic.values()) != 25:
        raise AssertionError("strategic applied accounting must be 25")
    if sum(r["authority_bridge"] == "owner_extraction_pending_fail_closed" for r in strategic.values()) != 33:
        raise AssertionError("strategic fail-closed accounting must be 33")

    print("PASS M1 StoredUfoId: monotonic linked-list identity with direct lookup and no removal compaction")
    print("PASS StoredUfoId save/load: object ID + allocator state persist; duplicate IDs reject; counter reconciles after load")
    print("PASS immutable stored-UFO publication: StoredUfoId + InstallationId + status/condition/definition, no raw pointers")
    print("PASS CreateProduction is canonical-applied with ItemId/aircraft/StoredUfoId subject qualification")
    print("PASS authority accounting current: strategic 25/33; tactical 13/2")
except AssertionError as exc:
    print("FAIL M1 StoredUfoId qualification: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
