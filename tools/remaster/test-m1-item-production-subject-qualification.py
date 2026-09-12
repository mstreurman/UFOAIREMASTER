#!/usr/bin/env python3
from __future__ import annotations
import csv, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "128b8a8a95531e5d5a53b1e4b91efc71b425c9ca"

class GateError(RuntimeError):
    pass

def require(cond, msg):
    if not cond:
        raise GateError(msg)

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")

def run(args):
    p = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    if p.returncode != 0:
        raise GateError(f"command failed ({p.returncode}): {' '.join(args)}\n{p.stdout}")
    return p.stdout

def main():
    p = subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"],
                       cwd=ROOT, check=False)
    require(p.returncode == 0, "HEAD is not descended from ItemId qualification baseline")

    scripts = read("src/common/scripts.cpp")
    inv = read("src/game/inv_shared.cpp")
    produce = read("src/client/cgame/campaign/cp_produce.cpp")
    snapshot = read("src/client/presentation/strategic_snapshot.h")
    adapter = read("src/client/presentation/strategic_snapshot_legacy_adapter.cpp")
    intent = read("src/client/presentation/strategic_intent.h")
    intent_adapter = read("src/client/presentation/strategic_intent_legacy_adapter.cpp")

    require("od->idx = csi.numODs - 1;" in scripts, "objDef canonical ordinal assignment changed")
    require("INVSH_GetItemByIDX (int index)" in inv, "item ordinal resolver missing")
    require("INVSH_GetItemByIDSilent (const char* id)" in inv, "item script-key resolver missing")

    for token in (
        "SAVE_PRODUCE_ITEMID, prod->data.data.item->id",
        "SAVE_PRODUCE_AIRCRAFTID, prod->data.data.aircraft->id",
        "SAVE_PRODUCE_UFOIDX, prod->data.data.ufo->idx",
        "PR_SetData(&prod->data, PRODUCTION_TYPE_ITEM, INVSH_GetItemByID(s1));",
        "US_GetStoredUFOByIDX",
        "AIR_GetAircraft(s2)",
    ):
        require(token in produce, "production subject save/load changed: " + token)

    for token in (
        "struct StrategicItemDefinitionView",
        "struct StrategicAircraftDefinitionView",
        "const std::vector<StrategicItemDefinitionView>& itemDefinitions() const",
        "const std::vector<StrategicAircraftDefinitionView>& aircraftDefinitions() const",
        "canonical::ItemId item;",
        "canonical::StoredUfoId storedUfo;",
        "std::string aircraftDefinition;",
    ):
        require(token in snapshot, "public subject contract missing: " + token)

    for token in (
        "indexedId<canonical::ItemId>(item.idx)",
        "valueString(aircraft.id)",
        "cgi->csi->numODs",
        "ccs.numAircraftTemplates",
        "out.item = indexedId<canonical::ItemId>(production.data.data.item->idx);",
        "out.aircraftDefinition = valueString(production.data.data.aircraft->id);",
        "out.storedUfo = indexedId<canonical::StoredUfoId>(production.data.data.ufo->idx);",
    ):
        require(token in adapter, "legacy subject projection missing: " + token)

    require(
        "submitCreateProduction(canonical::BaseId base, int32_t subjectKind, canonical::ItemId item, canonical::StoredUfoId storedUfo, const char* aircraftDefinition, int32_t amount)" in intent,
        "typed CreateProduction signature changed",
    )
    fail = intent_adapter[intent_adapter.find("case StrategicIntentKind::AcceptUfoSaleOffer:"):]
    require("case StrategicIntentKind::CreateProduction:" not in fail,
            "CreateProduction must not remain fail-closed after owner extraction")

    with (ROOT/"tools/remaster/m1-canonical-identity-registry.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    by = {r["identity"]: r for r in rows}
    require(by["ItemId"]["mapping_status"] == "runtime_content_ordinal_qualified",
            "ItemId mapping is not qualified")
    require(by["ItemId"]["publication_status"] == "published_definition_catalog",
            "ItemId catalog not published")
    require(by["AircraftDefinitionKey"]["publication_status"] == "published_definition_catalog",
            "aircraft definition catalog not published")
    require(by["ItemId"]["intent_status"] == "create_production_market_aircraft_equipment_owners_qualified",
            "ItemId CreateProduction/Market/AircraftEquipment owner qualification missing")

    with (ROOT/"tools/remaster/m1-canonical-identity-lifetime-registry.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    life = {r["identity"]: r for r in rows}
    require(life["ItemId"]["second_pass_status"] == "qualified_runtime_content_ordinal",
            "ItemId lifetime qualification missing")

    cxx = shutil.which("g++")
    require(cxx is not None, "g++ not found")
    build = ROOT/".build/m1-item-production-subject"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)
    binary = build/"m1-item-production-subject-contract"
    run([cxx, "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-I", str(ROOT),
         str(ROOT/"tools/remaster/m1-item-production-subject-contract.cpp"),
         "-o", str(binary)])
    out = run([str(binary)])
    require("M1 ItemId + production subject public contract: PASS" in out,
            "focused C++11 public contract failed")

    print("M1 ItemId + production subject qualification: PASS")
    print("  ItemId: current-content objDef ordinal + stable script-key catalog")
    print("  aircraft subject: published script-definition key")
    print("  disassembly subject: StoredUfoId")
    print("  CreateProduction: canonical campaign owner qualified")
    print("  ItemId owner status includes CreateProduction, Market buy/sell and aircraft equipment; aggregate accounting is centralized")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print("M1 ItemId + production subject qualification: FAIL: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
