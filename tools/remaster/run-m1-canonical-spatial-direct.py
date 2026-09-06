#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DIRECT_SCOPE_REL = Path("tools/remaster/m1-canonical-spatial-direct-scope.json")
EXPECTED_SERVICES = {
    "Trace", "LinkEdict", "UnlinkEdict", "TestLine", "TestLineWithEnt",
    "GrenadeTarget", "GridCalcPathing", "GridFindPath", "MoveStore", "MoveLength",
    "MoveNext", "GetTUsForDirection", "GridFall", "GridPosToVec", "isOnMap",
    "GridRecalcRouting", "CanActorStandHere", "GridShouldUseAutostand", "GetVisibility",
    "PointContents", "SetInlineModelOrientation", "GetInlineModelAABB", "LoadModelAABB",
}
EXPECTED_M0_EVIDENCE = "b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e"


class GateError(RuntimeError):
    pass


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GateError(f"cannot parse {path}: {exc}") from exc


def run_streaming(args: list[str], root: Path, label: str) -> str:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.Popen(
        args,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )
    assert proc.stdout is not None
    chunks: list[str] = []
    for line in proc.stdout:
        chunks.append(line)
        print(line, end="", flush=True)
    rc = proc.wait()
    if rc != 0:
        raise GateError(f"{label} failed with exit code {rc}")
    return "".join(chunks)


def validate(root: Path) -> tuple[dict, list[dict], set[str], set[str]]:
    direct_path = root / DIRECT_SCOPE_REL
    if not direct_path.is_file():
        raise GateError(f"missing direct scope: {DIRECT_SCOPE_REL}")
    direct = load_json(direct_path)
    if direct.get("schema") != 1:
        raise GateError("unsupported direct-scope schema")
    if direct.get("sealed_regression_evidence_b3") != EXPECTED_M0_EVIDENCE:
        raise GateError("direct scope does not pin the sealed M0 evidence identity")

    sentinel_rel = Path(direct.get("sentinel_scope", ""))
    sentinel_path = root / sentinel_rel
    if not sentinel_path.is_file():
        raise GateError(f"missing sentinel scope: {sentinel_rel}")
    sentinel = load_json(sentinel_path)

    sentinel_services: set[str] = set()
    for case in sentinel.get("selected_cases", []):
        services = case.get("services", [])
        if not isinstance(services, list):
            raise GateError("sentinel selected case has invalid services")
        sentinel_services.update(services)

    cases = direct.get("direct_cases")
    if not isinstance(cases, list) or not cases:
        raise GateError("direct_cases must be a non-empty list")

    ids: set[str] = set()
    direct_services: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise GateError("each direct case must be an object")
        case_id = case.get("id")
        service = case.get("service")
        claim = case.get("claim")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise GateError(f"invalid or duplicate direct case id: {case_id!r}")
        ids.add(case_id)
        if service not in EXPECTED_SERVICES:
            raise GateError(f"direct case {case_id} references unknown service: {service!r}")
        if service in direct_services:
            raise GateError(f"duplicate direct service: {service}")
        direct_services.add(service)
        if not isinstance(claim, str) or not claim:
            raise GateError(f"direct case {case_id} requires a claim")
        for key in ("gate", "probe", "production_helper", "production_consumer"):
            rel = case.get(key)
            if not isinstance(rel, str) or not rel or not (root / rel).is_file():
                raise GateError(f"direct case {case_id} missing {key}: {rel!r}")

    overlap = sorted(sentinel_services & direct_services)
    if overlap:
        raise GateError(f"direct coverage duplicates sentinel coverage: {overlap}")

    remaining = direct.get("remaining_direct_services")
    if not isinstance(remaining, list) or not all(isinstance(x, str) for x in remaining):
        raise GateError("remaining_direct_services must be a string list")
    remaining_services = set(remaining)
    unknown = sorted(remaining_services - EXPECTED_SERVICES)
    if unknown:
        raise GateError(f"remaining list contains unknown services: {unknown}")
    if direct_services & remaining_services:
        raise GateError("directly covered services must not remain listed as uncovered")

    represented = sentinel_services | direct_services | remaining_services
    if represented != EXPECTED_SERVICES:
        raise GateError(
            "M1 direct scope must partition all Architecture-075 services; "
            f"missing={sorted(EXPECTED_SERVICES - represented)} extra={sorted(represented - EXPECTED_SERVICES)}"
        )

    return direct, cases, sentinel_services, direct_services


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/verify accumulated M1 direct canonical spatial fixtures.")
    parser.add_argument("--audit-only", action="store_true", help="Validate direct/sentinel scope partition only.")
    args = parser.parse_args()

    root = repo_root()
    direct, cases, sentinel_services, direct_services = validate(root)

    if not args.audit_only:
        for case in cases:
            gate = root / case["gate"]
            run_streaming([sys.executable, str(gate)], root, f"direct fixture {case['id']}")

        sentinel_gate = root / direct["sentinel_gate"]
        sentinel_text = run_streaming([sys.executable, str(sentinel_gate)], root, "M1 sentinel + sealed regression lane")
        if EXPECTED_M0_EVIDENCE not in sentinel_text:
            raise GateError("sentinel lane passed without the expected sealed M0 evidence identity")

    aggregate = sentinel_services | direct_services
    remaining = set(direct["remaining_direct_services"])
    print("M1 canonical spatial direct-fixture lane: PASS")
    print(f"  sentinel services: {len(sentinel_services)}/23")
    print(f"  direct services: {len(direct_services)}/23")
    print(f"  aggregate services represented: {len(aggregate)}/23")
    print(f"  services still requiring direct fixtures: {len(remaining)}")
    if args.audit_only:
        print("  runtime gates: skipped (--audit-only)")
    else:
        print("  focused direct fixtures: PASS")
        print("  M1.1a binding + sealed M0 regression: PASS")
        print(f"  sealed evidence: {EXPECTED_M0_EVIDENCE}")
    print("  M1.1b parent: remains open")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 canonical spatial direct-fixture lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
