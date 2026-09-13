#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_PENDING = {
    "AutoResolveMission","StartMission",
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
    "test-m1-ufo-recovery-owner-extraction.py",
    "test-m1-alien-containment-owner-extraction.py",
    "test-m1-aircraft-configuration-owner-extraction.py",
    "test-m1-defence-owner-extraction.py",
    "test-m1-transfer-owner-extraction.py",
    "test-m1-save-owner-extraction.py",
    "test-m1-load-owner-extraction.py",
    "test-m1-load-last-save-owner-extraction.py",
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
    require(len(applied)==55, f"strategic applied count must be 55, got {len(applied)}")
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
    require(registry["ItemId"]["intent_status"]=="create_production_market_aircraft_equipment_defence_owners_qualified", "ItemId aircraft/defence-equipment status stale")
    require(registry["AircraftDefinitionKey"]["intent_status"]=="create_production_market_owner_qualified",
            "AircraftDefinitionKey Market status stale")
    require(registry["UgvDefinitionKey"]["intent_status"]=="market_owner_qualified", "UgvDefinitionKey Market status stale")
    require(registry["UfoRecoveryId"]["mapping_status"]=="runtime_mapping_implemented", "UfoRecoveryId mapping stale")
    require(registry["UfoRecoveryId"]["publication_status"]=="published", "UfoRecoveryId publication stale")
    require(registry["UfoSaleOfferId"]["mapping_status"]=="runtime_mapping_implemented", "UfoSaleOfferId mapping stale")
    require(registry["UfoSaleOfferId"]["publication_status"]=="published", "UfoSaleOfferId publication stale")
    require(registry["ContainedAlienSpecies"]["intent_status"]=="containment_owners_qualified", "containment aggregate owner status stale")
    require(registry["AircraftEquipmentSlot"]["intent_status"]=="aircraft_equipment_owners_qualified", "aircraft equipment structural owner status stale")
    require(registry["AircraftEquipmentSlot"]["mapping_status"]=="structural_tuple", "aircraft equipment slot must remain structural")
    require(registry["DefenceSlotId"]["classification"]=="runtime_direct", "DefenceSlotId classification stale")
    require(registry["DefenceSlotId"]["mapping_status"]=="runtime_mapping_implemented", "DefenceSlotId mapping stale")
    require(registry["DefenceSlotId"]["publication_status"]=="published", "DefenceSlotId publication stale")
    require(registry["DefenceSlotId"]["intent_status"]=="defence_owners_qualified", "DefenceSlotId owner status stale")
    require(registry["TransferManifestId"]["mapping_status"]=="bounded_submission_registry", "TransferManifestId mapping stale")
    require(registry["TransferManifestId"]["intent_status"]=="start_transfer_owner_qualified", "TransferManifestId owner status stale")
    require(registry["TransferId"]["mapping_status"]=="type_added_mapping_missing", "active TransferId debt changed")

    lifetime={r["identity"]:r for r in rows("tools/remaster/m1-canonical-identity-lifetime-registry.tsv")}
    require(lifetime["FacilityId"]["second_pass_status"]=="qualified_runtime_mapping",
            "FacilityId lifetime mapping not qualified")
    require("not serialized" in lifetime["FacilityId"]["save_semantics"],
            "FacilityId must remain explicitly runtime-only")
    require(lifetime["UfoRecoveryId"]["second_pass_status"]=="qualified_runtime_mapping", "UfoRecoveryId lifetime stale")
    require(lifetime["UfoSaleOfferId"]["second_pass_status"]=="qualified_runtime_mapping", "UfoSaleOfferId lifetime stale")
    require(lifetime["DefenceSlotId"]["second_pass_status"]=="qualified_runtime_mapping", "DefenceSlotId lifetime stale")
    require(lifetime["TransferManifestId"]["second_pass_status"]=="qualified_submission_mapping", "TransferManifestId lifetime stale")
    require(lifetime["TransferId"]["second_pass_status"]=="pending_mapping", "active TransferId lifetime debt changed")

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
        require("57" in doc and "55" in doc and "2" in doc and "46c6c3ca9fb808f7c5bdb8c665b79ef378a3cabf" in doc,
                docname+": current authority baseline/counts not synchronized")
    require("SDL3 3.4.16" in readme, "README does not reflect latest installed SDL3")
    require("8add4c8c8319111766d2ba9939e6fdcab8e08bd272fbadb068d198567bcaa218" in readme,
            "README canonical verification digest stale")
    require("ea6cb9ded6289b809ab22ae8fe2fb19e3ed8fb0ff8e71ec180f3c9a2710f6c35" in readme,
            "README M0.3 environment digest stale")

    print("PASS M1 authority bookkeeping synchronization")
    print("PASS strategic authority: 57 total / 55 applied / 2 fail-closed")
    print("PASS tactical authority: 15 total / 13 forwarded / 2 fail-closed")
    print("PASS DestroyAntimatterFacility reclassified as scripted canonical event; enum 20 tombstone retained")
    print("PASS FacilityId + Market + UFO recovery + containment + aircraft-equipment + DefenceSlotId + TransferManifestId registries synchronized")
    print("PASS cgame export surface is explicitly reviewed; MapClick remains classified")
    print("PASS family tests no longer own global historical authority totals")
    print("PASS save v4 / protocol 18 unchanged")

if __name__=="__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 authority bookkeeping synchronization: "+str(exc),file=sys.stderr)
        raise SystemExit(1)
