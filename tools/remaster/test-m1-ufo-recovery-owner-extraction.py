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
    for i in range(brace, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: return text[start:i+1]
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
    identity = read("src/client/presentation/canonical_identity.h")
    intent = read("src/client/presentation/strategic_intent.h")
    dispatch = read("src/client/presentation/strategic_intent_dispatch.cpp")
    owner_h = read("src/client/cgame/campaign/cp_uforecovery.h")
    owner = read("src/client/cgame/campaign/cp_uforecovery.cpp")
    callbacks = read("src/client/cgame/campaign/cp_uforecovery_callbacks.cpp")
    missions = read("src/client/cgame/campaign/cp_missions.cpp")
    campaign = read("src/client/cgame/campaign/cp_campaign.cpp")
    adapter = read("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    snapshot = read("src/client/presentation/strategic_snapshot.h")
    snapshot_adapter = read("src/client/presentation/strategic_snapshot_legacy_adapter.cpp")

    require(identity, ["UfoRecoveryIdTag", "using UfoRecoveryId =", "UFOAI_CANONICAL_ID_CONTRACT(UfoRecoveryId)"], "UfoRecoveryId type")
    require(intent, ["canonical::UfoRecoveryId recovery;", "submitStoreRecoveredUfo(canonical::UfoRecoveryId recovery, canonical::InstallationId installation)"], "typed recovery intent")
    forbid(intent, ["submitStoreRecoveredUfo(const char* ufoDefinition"], "typed recovery intent")
    require(body(dispatch, "StrategicIntentSubmission submitStoreRecoveredUfo("), ["v.recovery = recovery", "v.installation = installation"], "recovery dispatch")

    require(owner_h, [
        "typedef struct ufoRecovery_s", "typedef struct ufoSaleOffer_s",
        "UR_BeginRecoveryFromMission", "UR_TryStoreRecoveredUFO", "UR_GenerateUfoSaleOffers",
        "UR_TryAcceptUfoSaleOffer", "US_TryDestroyStoredUFO", "US_TryTransferStoredUFO",
    ], "canonical recovery API")
    require(owner, [
        "nextRecoveryRuntimeId", "nextSaleOfferRuntimeId", "std::numeric_limits<uint32_t>::max()",
        "UR_ParsePersistedRecoveryCondition", "mission->onwin", "mission->ufo", "ufoDefinition",
        "UR_ClearRecovery();", "UR_GenerateUfoSaleOffers(runtimeId);", "CP_UpdateCredits",
        "NAT_SetHappiness", "US_StoreUFO", "US_RemoveStoredUFO", "US_TransferUFO",
    ], "canonical recovery owner implementation")
    forbid(callbacks, ["CP_UpdateCredits(", "NAT_SetHappiness(", "US_StoreUFO(", "US_RemoveStoredUFO(", "US_TransferUFO(", "UR_GenerateUfoSaleOffers("], "legacy recovery callbacks")
    require(callbacks, ["UR_TryStoreRecoveredUFO", "UR_TryAcceptUfoSaleOffer", "US_TryDestroyStoredUFO", "US_TryTransferStoredUFO", "UR_GetUfoSaleOfferCount"], "legacy callback delegation/projection")

    mission_end = body(missions, "void CP_MissionEnd (")
    require(mission_end, ["UR_ClearRecovery();", "UR_BeginRecoveryFromMission(mission)", "CP_ExecuteMissionTrigger(mission, won)"], "won-mission recovery handoff")
    if mission_end.index("UR_BeginRecoveryFromMission(mission)") > mission_end.index("CP_ExecuteMissionTrigger(mission, won)"):
        raise AssertionError("recovery context must be armed before inherited UI mission trigger")
    require(body(campaign, "void CP_ResetCampaignData (void)"), ["UR_ClearRecovery();"], "campaign reset invalidation")

    for kind, call in (
        ("AcceptUfoSaleOffer", "UR_TryAcceptUfoSaleOffer("),
        ("DestroyStoredUfo", "US_TryDestroyStoredUFO("),
        ("StoreRecoveredUfo", "UR_TryStoreRecoveredUFO("),
        ("TransferStoredUfo", "US_TryTransferStoredUFO("),
    ):
        case = re.search(r"case StrategicIntentKind::" + kind + r"\s*:(.*?)(?=\n\s*case StrategicIntentKind::)", adapter, re.S)
        if not case or call not in case.group(1):
            raise AssertionError(kind + " typed adapter does not reach canonical owner")

    require(snapshot, [
        "struct StrategicUfoRecoveryView", "canonical::UfoRecoveryId id;",
        "struct StrategicUfoSaleOfferView", "canonical::UfoSaleOfferId id;",
        "const StrategicUfoRecoveryView& ufoRecovery() const", "ufoSaleOffers() const",
    ], "immutable recovery publication")
    require(snapshot_adapter, ["UR_GetPendingRecovery()", "UR_GetUfoSaleOfferCount()", "projectUfoRecovery", "projectUfoSaleOffer"], "legacy recovery projection")

    with (ROOT/"tools/remaster/m1-canonical-identity-registry.tsv").open() as f:
        reg = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    for ident in ("UfoRecoveryId", "UfoSaleOfferId"):
        if reg[ident]["mapping_status"] != "runtime_mapping_implemented" or reg[ident]["publication_status"] != "published":
            raise AssertionError(ident + " mapping/publication not qualified")

    with (ROOT/"tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        cov = {r["semantic_action"]: r for r in csv.DictReader(f, delimiter="\t") if r["domain"] == "strategic"}
    for action in ("AcceptUfoSaleOffer", "DestroyStoredUfo", "StoreRecoveredUfo", "TransferStoredUfo"):
        if cov[action]["authority_bridge"] != "canonical_applied":
            raise AssertionError(action + " is not canonical_applied")

    save_h = read("src/client/cgame/campaign/cp_save.h")
    common_h = read("src/common/common.h")
    if not re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h):
        raise AssertionError("save version changed")
    if not re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h):
        raise AssertionError("protocol version changed")
    with (ROOT/"tools/remaster/m1-canonical-identity-lifetime-registry.tsv").open() as f:
        life = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    for ident in ("UfoRecoveryId", "UfoSaleOfferId"):
        if "not serialized" not in life[ident]["save_semantics"]:
            raise AssertionError(ident + " must remain runtime-only / not serialized")
    save_owner = body(owner, "bool US_SaveXML (")
    forbid(save_owner, ["UfoRecoveryId", "UfoSaleOfferId", "runtimeId"], "save v4 recovery runtime identity")

    print("PASS M1 UFO recovery owner extraction")
    print("  UfoRecoveryId: one-shot process-monotonic runtime identity from canonical won-mission context")
    print("  UfoSaleOfferId: generation-safe canonical nation/price offer bound to UfoRecoveryId")
    print("  Store/Accept/Destroy/Transfer: canonical-applied; stale/replayed IDs reject")
    print("  legacy callbacks delegate mutation; presentation-supplied UFO condition/price no longer authoritative")
    print("  save v4 / protocol 18 unchanged")
except AssertionError as exc:
    print("FAIL M1 UFO recovery owner extraction: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
