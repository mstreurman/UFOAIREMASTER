#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_PENDING = {
    "AcceptUfoSaleOffer","AutoResolveMission","DestroyStoredUfo","EquipAircraftItem",
    "EquipBaseDefenceItem","KillContainedAlien","KillContainedAliens","LoadGame","LoadLastSave",
    "RemoveAircraftItem","RemoveBaseDefenceItem","RenameAircraft","SaveGame",
    "SetAirDefenceAutoFire","SetAirDefenceTarget","StartMission","StartTransfer",
    "StoreRecoveredUfo","TransferStoredUfo",
}
FAMILY_TESTS = (
    "test-m1-research-owner-extraction.py",
    "test-m1-production-owner-extraction.py",
    "test-m1-production-contract-normalization.py",
    "test-m1-create-production-owner-extraction.py",
    "test-m1-employee-team-owner-extraction.py",
    "test-m1-production-runtime-identity.py",
    "test-m1-stored-ufo-identity.py",
    "test-m1-item-production-subject-qualification.py",
    "test-m1-market-owner-extraction.py",
    "test-m1-canonical-identity-completeness.py",
)

class GateError(RuntimeError):
    pass

def require(cond, msg):
    if not cond:
        raise GateError(msg)

def rows(rel):
    with (ROOT/rel).open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def text(rel):
    return (ROOT/rel).read_text(encoding="utf-8")

def main():
    strict=[x.strip() for x in text("tools/remaster/strict-strategic-actions.txt").splitlines() if x.strip()]
    require(len(strict)==57, f"strict strategic count must be 57, got {len(strict)}")
    require("DestroyAntimatterFacility" not in strict, "antimatter breach remains in strict presentation action inventory")

    coverage=rows("tools/remaster/m1-authoritative-intent-coverage.tsv")
    strategic={r["semantic_action"]:r for r in coverage if r["domain"]=="strategic"}
    tactical={r["semantic_action"]:r for r in coverage if r["domain"]=="tactical"}
    require(set(strategic)==set(strict), "coverage ledger and strict strategic inventory differ")
    applied={n for n,r in strategic.items() if r["authority_bridge"]=="canonical_applied"}
    pending={n for n,r in strategic.items() if r["authority_bridge"]=="owner_extraction_pending_fail_closed"}
    require(len(applied)==38, f"strategic applied count must be 38, got {len(applied)}")
    require(pending==EXPECTED_PENDING, "strategic pending set mismatch: "+repr(sorted(pending)))
    require(len(tactical)==15, f"tactical total must remain 15, got {len(tactical)}")
    require(sum(r["authority_bridge"]=="server_request_forwarded" for r in tactical.values())==13,
            "tactical forwarded count must remain 13")
    require(sum(r["authority_bridge"]=="client_request_helper_pending_fail_closed" for r in tactical.values())==2,
            "tactical pending count must remain 2")

    ih=text("src/client/presentation/strategic_intent.h")
    dispatch=text("src/client/presentation/strategic_intent_dispatch.cpp")
    require("DestroyAntimatterFacility = 20" in ih, "enum tombstone 20 moved or disappeared")
    require("submitDestroyAntimatterFacility(" not in ih, "public antimatter submit helper remains")
    require("submitDestroyAntimatterFacility(" not in dispatch, "dispatch antimatter submit helper remains")

    seed=rows("tools/remaster/m1-presentation-authority-seed.tsv")
    breach=[r for r in seed if r["name"]=="building_amdestroy"]
    require(len(breach)==1, "building_amdestroy seed row must be unique")
    breach=breach[0]
    require(breach["scope"]=="SCRIPTED_CANONICAL_EVENT", "building_amdestroy scope must be SCRIPTED_CANONICAL_EVENT")
    require(not breach["authority"] and not breach["semantic_action"] and breach["api_relevance"]=="no",
            "building_amdestroy must not expose presentation authority/API relevance")

    registry={r["identity"]:r for r in rows("tools/remaster/m1-canonical-identity-registry.tsv")}
    facility=registry["FacilityId"]
    require(facility["classification"]=="runtime_direct", "FacilityId classification not synchronized")
    require(facility["mapping_status"]=="runtime_mapping_implemented", "FacilityId runtime mapping not recorded")
    require(facility["publication_status"]=="published", "FacilityId publication not recorded")
    require(facility["intent_status"]=="destroy_owner_qualified", "FacilityId destroy owner not recorded")
    require(registry["ItemId"]["intent_status"]=="create_production_market_owners_qualified", "ItemId Market status stale")
    require(registry["AircraftDefinitionKey"]["intent_status"]=="create_production_market_owner_qualified",
            "AircraftDefinitionKey Market status stale")
    require(registry["UgvDefinitionKey"]["intent_status"]=="market_owner_qualified", "UgvDefinitionKey Market status stale")

    lifetime={r["identity"]:r for r in rows("tools/remaster/m1-canonical-identity-lifetime-registry.tsv")}
    require(lifetime["FacilityId"]["second_pass_status"]=="qualified_runtime_mapping",
            "FacilityId lifetime mapping not qualified")
    require("not serialized" in lifetime["FacilityId"]["save_semantics"],
            "FacilityId must remain explicitly runtime-only")

    scanner=text("tools/remaster/capture-m1-presentation-authority-inventory.py")
    for token in ("CGAME_EXPORT_RE","REVIEWED_CGAME_EXPORT_FIELDS","DIRECT_PRESENTATION_INPUT_EXPORTS",
                  'rel == "src/client/cgame/campaign/cl_game_campaign.cpp"'):
        require(token in scanner, "scanner export-surface guard missing: "+token)
    require("CGAME_MAPCLICK_RE" not in scanner, "MapClick-only scanner special case remains")
    require('"MapClick"' in scanner, "MapClick must remain a reviewed direct presentation input")

    snapshot_adapter=text("src/client/presentation/strategic_snapshot_legacy_adapter.cpp")
    require("RS_GetTechForItem(&item)" not in snapshot_adapter,
            "item-definition publication must not use throwing RS_GetTechForItem lookup")
    require("ccs.objDefTechs[item.idx]" in snapshot_adapter,
            "item-definition publication must use nullable canonical item->technology mapping")

    stale_accounting = (
        "strategic 31/27", "31 applied / 27", "58 strategic semantics; 31 applied / 27",
        "strategic applied accounting must be 31", "strategic pending accounting must be 27",
        "strategic fail-closed accounting must be 27", "strategic canonical-applied accounting must be 31",
        "applied must be 31", "pending must be 27", "strategic 38/20",
        "strategic fail-closed accounting must be 20", "authority accounting: strategic 38/20",
    )
    for name in FAMILY_TESTS:
        family=text("tools/remaster/"+name)
        for stale in stale_accounting:
            require(stale not in family, name+": stale aggregate authority accounting remains: "+stale)

    common=text("src/common/common.h")
    save=text("src/client/cgame/campaign/cp_save.h")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b",common) is not None, "protocol version changed")
    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b",save) is not None, "save version changed")

    readme=text("README.md")
    docs=text("docs/README.md")
    arch=text("docs/architecture/093-presentation-action-authority-and-intent-completeness-contract.md")
    for docname,doc in (("README.md",readme),("docs/README.md",docs),("architecture 093",arch)):
        require("57" in doc and "19" in doc and "7a1b9568a41b5b61a0820c4d67174f134d4445f9" in doc,
                docname+": current authority baseline/counts not synchronized")
    require("SDL3 3.4.16" in readme, "README does not reflect latest installed SDL3")
    require("b3349db1064514536cff0ffd5cb6837cefca12b8435bc41c27220f5650da845f" in readme,
            "README canonical verification digest stale")

    print("PASS M1 authority bookkeeping synchronization")
    print("PASS strategic authority: 57 total / 38 applied / 19 fail-closed")
    print("PASS tactical authority: 15 total / 13 forwarded / 2 fail-closed")
    print("PASS DestroyAntimatterFacility reclassified as scripted canonical event; enum 20 tombstone retained")
    print("PASS FacilityId + Market identity registries synchronized")
    print("PASS cgame export surface is explicitly reviewed; MapClick remains classified")
    print("PASS family tests no longer own global historical authority totals")
    print("PASS save v4 / protocol 18 unchanged")

if __name__=="__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 authority bookkeeping synchronization: "+str(exc),file=sys.stderr)
        raise SystemExit(1)
