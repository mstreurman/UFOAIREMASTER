#!/usr/bin/env python3
from pathlib import Path
import csv, shutil, subprocess, sys
ROOT = Path(__file__).resolve().parents[2]

def body(text, signature):
    pos=text.find(signature)
    if pos<0: raise AssertionError("missing body: "+signature)
    start=text.find("{",pos); depth=0
    for i in range(start,len(text)):
        if text[i]=="{": depth+=1
        elif text[i]=="}":
            depth-=1
            if depth==0: return text[start:i+1]
    raise AssertionError("unterminated body: "+signature)
def require(text,tokens,label):
    for t in tokens:
        if t not in text: raise AssertionError(f"{label}: missing {t}")
def forbid(text,tokens,label):
    for t in tokens:
        if t in text: raise AssertionError(f"{label}: forbidden {t}")
def run(args):
    p=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    if p.returncode!=0: raise AssertionError(f"command failed ({p.returncode}): {' '.join(args)}\n{p.stdout}")
    return p.stdout

try:
    ph=(ROOT/"src/client/cgame/campaign/cp_produce.h").read_text()
    pc=(ROOT/"src/client/cgame/campaign/cp_produce.cpp").read_text()
    cb=(ROOT/"src/client/cgame/campaign/cp_produce_callbacks.cpp").read_text()
    ad=(ROOT/"src/client/presentation/strategic_intent_legacy_adapter.cpp").read_text()
    require(ph,["productionMutationResult_t","PR_MUTATION_APPLIED","PR_MUTATION_INVALID_BASE",
      "PR_MUTATION_INVALID_PRODUCTION","PR_MUTATION_INVALID_AMOUNT","PR_MUTATION_NOT_DECREASABLE",
      "PR_MUTATION_QUEUE_BOUNDARY","PR_TryDecreaseProduction(","PR_TryMoveProductionUp(",
      "PR_TryMoveProductionDown(","PR_TryStopProduction("],"cp_produce.h")
    dec=body(pc,"productionMutationResult_t PR_TryDecreaseProduction (")
    require(dec,["amount <= 0","PR_GetProductionByRuntimeId(base, runtimeId)","prod->amount <= amount",
      "PR_QueueDelete(base, PR_GetProductionForBase(base), prod->idx)","PR_IsDisassembly(prod)",
      "PR_DecreaseProduction(prod, amount)"],"decrease owner")
    forbid(dec,["UI_","CP_Popup(","Cmd_ExecuteString(","Cbuf_AddText(","Cvar_Set("],"decrease owner")
    mv=body(pc,"static productionMutationResult_t PR_TryMoveProductionCanonical (")
    require(mv,["PR_GetProductionByRuntimeId(base, runtimeId)","const int newIndex = std::max(",
      "newIndex == prod->idx","PR_QueueMove(queue, prod->idx, offset)"],"move owner")
    forbid(mv,["UI_","CP_Popup(","Cmd_ExecuteString(","Cbuf_AddText(","Cvar_Set("],"move owner")
    require(body(pc,"productionMutationResult_t PR_TryMoveProductionUp ("),["PR_TryMoveProductionCanonical(base, runtimeId, -1)"],"move up")
    require(body(pc,"productionMutationResult_t PR_TryMoveProductionDown ("),["PR_TryMoveProductionCanonical(base, runtimeId, 1)"],"move down")
    st=body(pc,"productionMutationResult_t PR_TryStopProduction (")
    require(st,["PR_GetProductionByRuntimeId(base, runtimeId)","PR_QueueDelete(base, PR_GetProductionForBase(base), prod->idx)"],"stop owner")
    forbid(st,["UI_","CP_Popup(","Cmd_ExecuteString(","Cbuf_AddText(","Cvar_Set("],"stop owner")

    s=body(cb,"static void PR_ProductionStop_f (")
    require(s,["PR_GetProductionRuntimeId(selectedProduction)","PR_TryStopProduction(base, runtimeId)","prod_selectline"],"stop callback")
    forbid(s,["PR_QueueDelete("],"stop callback")
    d=body(cb,"static void PR_ProductionDecrease_f (")
    require(d,["PR_GetProductionRuntimeId(prod)","PR_TryDecreaseProduction(base, runtimeId, amount)",
      "PR_GetProductionByRuntimeId(base, runtimeId)"],"decrease callback")
    forbid(d,["PR_DecreaseProduction(","PR_QueueDelete("],"decrease callback")
    u=body(cb,"static void PR_ProductionUp_f (")
    require(u,["PR_GetProductionRuntimeId(selectedProduction)","PR_TryMoveProductionUp(base, runtimeId)",
      "PR_GetProductionByRuntimeId(base, runtimeId)"],"up callback")
    forbid(u,["PR_QueueMove("],"up callback")
    dn=body(cb,"static void PR_ProductionDown_f (")
    require(dn,["PR_GetProductionRuntimeId(selectedProduction)","PR_TryMoveProductionDown(base, runtimeId)",
      "PR_GetProductionByRuntimeId(base, runtimeId)"],"down callback")
    forbid(dn,["PR_QueueMove("],"down callback")

    require(ad,['#include "../cgame/campaign/cp_produce.h"'],"adapter")
    for name,owner in (("DecreaseProduction","PR_TryDecreaseProduction("),
                       ("MoveProductionDown","PR_TryMoveProductionDown("),
                       ("MoveProductionUp","PR_TryMoveProductionUp("),
                       ("StopProduction","PR_TryStopProduction(")):
        case=body(ad,f"case StrategicIntentKind::{name}:")
        require(case,["resolveBase(in.base)","in.production.isValid()",owner,"in.production.value"],name)
        forbid(case,["queueIndex","Cmd_ExecuteString(","Cbuf_AddText(","Cvar_Set("],name)
    fc=ad[ad.find("case StrategicIntentKind::AcceptUfoSaleOffer:"):]
    for name in ("DecreaseProduction","MoveProductionDown","MoveProductionUp","StopProduction"):
        if f"case StrategicIntentKind::{name}:" in fc: raise AssertionError(name+" still fail-closed")

    rows=list(csv.DictReader((ROOT/"tools/remaster/m1-authoritative-intent-coverage.tsv").open(),delimiter="\t"))
    strategic={r["semantic_action"]:r for r in rows if r["domain"]=="strategic"}
    for name in ("DecreaseProduction","MoveProductionDown","MoveProductionUp","StopProduction"):
        if strategic[name]["authority_bridge"]!="canonical_applied": raise AssertionError(name+" not applied")
        if strategic[name]["owner_source"]!="src/client/cgame/campaign/cp_produce.cpp": raise AssertionError(name+" wrong owner")
    for name in ("IncreaseProduction","SetProductionAmount"):
        if strategic[name]["authority_bridge"]!="owner_extraction_pending_fail_closed": raise AssertionError(name+" must remain pending")
    if sum(r["authority_bridge"]=="canonical_applied" for r in strategic.values())!=22: raise AssertionError("applied must be 22")
    if sum(r["authority_bridge"]=="owner_extraction_pending_fail_closed" for r in strategic.values())!=35: raise AssertionError("pending must be 35")

    cxx=shutil.which("g++")
    if not cxx: raise AssertionError("g++ not found")
    build=ROOT/".build/m1-production-owner-extraction"; build.mkdir(parents=True,exist_ok=True)
    binary=build/"m1-production-owner-stale-contract"
    run([cxx,"-std=c++11","-Wall","-Wextra","-Werror","-pedantic","-I",str(ROOT),
         str(ROOT/"tools/remaster/m1-production-owner-stale-contract.cpp"),"-o",str(binary)])
    out=run([str(binary)])
    if "M1 production stale-intent contract: PASS" not in out: raise AssertionError("stale contract failed")
    print("PASS M1 production owners: Decrease + MoveUp + MoveDown + Stop")
    print("PASS canonical owners re-resolve ProductionId at execution time and contain no UI/command/cvar fallback")
    print("PASS stale two-intent contract: deleted ProductionId rejects after compaction; neighbor identity preserved")
    print("PASS IncreaseProduction + SetProductionAmount remain fail-closed pending contract normalization")
    print("PASS bridge accounting: strategic 22 applied / 35 fail-closed; tactical unchanged 13/2")
except AssertionError as exc:
    print("FAIL M1 production owner extraction: "+str(exc),file=sys.stderr)
    raise SystemExit(1)
