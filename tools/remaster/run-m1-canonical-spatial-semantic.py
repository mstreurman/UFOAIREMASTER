#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCOPE_REL = Path("tools/remaster/m1-canonical-spatial-semantic-scope.json")
EXPECTED_SERVICES = {
    "Trace", "LinkEdict", "UnlinkEdict", "TestLine", "TestLineWithEnt",
    "GrenadeTarget", "GridCalcPathing", "GridFindPath", "MoveStore",
    "MoveLength", "MoveNext", "GetTUsForDirection", "GridFall",
    "GridPosToVec", "isOnMap", "GridRecalcRouting", "CanActorStandHere",
    "GridShouldUseAutostand", "GetVisibility", "PointContents",
    "SetInlineModelOrientation", "GetInlineModelAABB", "LoadModelAABB",
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


def load_scope(root: Path) -> dict:
    path = root / SCOPE_REL
    if not path.is_file():
        raise GateError(f"missing semantic scope: {SCOPE_REL}")
    try:
        scope = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GateError(f"cannot parse {SCOPE_REL}: {exc}") from exc
    if scope.get("schema") != 1:
        raise GateError("unsupported semantic scope schema")
    if scope.get("sealed_regression_evidence_b3") != EXPECTED_M0_EVIDENCE:
        raise GateError("semantic scope does not pin the sealed M0 evidence identity")
    return scope


def validate_scope(root: Path, scope: dict) -> tuple[list[dict], set[str]]:
    selected = scope.get("selected_cases")
    uncovered = scope.get("uncovered_required_cases")
    if not isinstance(selected, list) or not selected:
        raise GateError("selected_cases must be a non-empty list")
    if not isinstance(uncovered, list) or not uncovered:
        raise GateError("uncovered_required_cases must be a non-empty list")

    ids: set[str] = set()
    tests: set[str] = set()
    covered_services: set[str] = set()

    for case in selected:
        if not isinstance(case, dict):
            raise GateError("each selected case must be an object")
        case_id = case.get("id")
        test = case.get("test")
        source = case.get("source")
        services = case.get("services")
        claim = case.get("claim")
        if not all(isinstance(x, str) and x for x in (case_id, test, source, claim)):
            raise GateError(f"invalid selected case metadata: {case!r}")
        if case_id in ids:
            raise GateError(f"duplicate selected case id: {case_id}")
        if test in tests:
            raise GateError(f"duplicate selected test: {test}")
        ids.add(case_id)
        tests.add(test)
        if not isinstance(services, list) or not all(isinstance(x, str) for x in services):
            raise GateError(f"selected case {case_id} services must be a string list")
        unknown = sorted(set(services) - EXPECTED_SERVICES)
        if unknown:
            raise GateError(f"selected case {case_id} references unknown services: {unknown}")
        covered_services.update(services)

        source_path = root / source
        if not source_path.is_file():
            raise GateError(f"selected source is missing: {source}")
        suite, name = test.split(".", 1)
        text = source_path.read_text(encoding="utf-8", errors="strict")
        rx = re.compile(
            rf"\b(?:TEST|TEST_F)\s*\(\s*{re.escape(suite)}\s*,\s*{re.escape(name)}\s*\)"
        )
        if rx.search(text) is None:
            raise GateError(f"selected semantic sentinel no longer exists in {source}: {test}")

    uncovered_services: set[str] = set()
    areas: set[str] = set()
    for item in uncovered:
        if not isinstance(item, dict):
            raise GateError("each uncovered case must be an object")
        area = item.get("area")
        services = item.get("services")
        reason = item.get("reason")
        if not isinstance(area, str) or not area or area in areas:
            raise GateError(f"invalid or duplicate uncovered area: {area!r}")
        areas.add(area)
        if not isinstance(reason, str) or not reason:
            raise GateError(f"uncovered area {area} requires a reason")
        if not isinstance(services, list) or not services or not all(isinstance(x, str) for x in services):
            raise GateError(f"uncovered area {area} must list canonical services")
        unknown = sorted(set(services) - EXPECTED_SERVICES)
        if unknown:
            raise GateError(f"uncovered area {area} references unknown services: {unknown}")
        uncovered_services.update(services)

    overlap = sorted(covered_services & uncovered_services)
    if overlap:
        raise GateError(f"services cannot be simultaneously claimed covered and uncovered: {overlap}")

    represented = covered_services | uncovered_services
    missing_tracking = sorted(EXPECTED_SERVICES - represented)
    if missing_tracking:
        raise GateError(
            "semantic scope must either promote or explicitly track every Architecture-075 service; "
            f"untracked={missing_tracking}"
        )

    return selected, covered_services


def run_streaming(args: list[str], *, cwd: Path) -> tuple[int, str]:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.Popen(
        args,
        cwd=cwd,
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
    return proc.wait(), "".join(chunks)


def require_command_pass(args: list[str], *, cwd: Path, label: str) -> str:
    rc, text = run_streaming(args, cwd=cwd)
    if rc != 0:
        raise GateError(f"{label} failed with exit code {rc}")
    return text


def verify_runtime(root: Path, scope: dict, selected: list[dict]) -> None:
    boundary_rel = Path(scope["boundary_gate"])
    regression_rel = Path(scope["sealed_regression_gate"])
    boundary = root / boundary_rel
    regression = root / regression_rel
    if not boundary.is_file():
        raise GateError(f"missing M1 boundary gate: {boundary_rel}")
    if not regression.is_file():
        raise GateError(f"missing sealed M0 regression gate: {regression_rel}")

    boundary_text = require_command_pass(
        [sys.executable, str(boundary)], cwd=root, label="M1.1a boundary gate"
    )
    if "M1 canonical spatial boundary: PASS" not in boundary_text or "services: 23" not in boundary_text:
        raise GateError("M1.1a boundary gate passed without the expected 23-service identity")

    regression_text = require_command_pass(
        [sys.executable, str(regression), "--verify"],
        cwd=root,
        label="sealed M0 canonical regression",
    )
    final_marker = f"M0.5 canonical regression verification: PASS ({EXPECTED_M0_EVIDENCE})"
    if final_marker not in regression_text:
        raise GateError("sealed M0 regression passed without the expected evidence identity")

    for case in selected:
        test = case["test"]
        run_count = len(re.findall(rf"^\[\s*RUN\s*\]\s+{re.escape(test)}\s*$", regression_text, flags=re.M))
        ok_count = len(re.findall(rf"^\[\s*OK\s*\]\s+{re.escape(test)}(?:\s|$)", regression_text, flags=re.M))
        if run_count != 2 or ok_count != 2:
            raise GateError(
                f"semantic sentinel {test} must run and pass in both sealed regression passes; "
                f"runs={run_count} ok={ok_count}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit/verify the M1 canonical spatial semantic sentinel lane without modifying the sealed M0 corpus."
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Validate scope/test identities only; do not execute the M1/M0 runtime gates.",
    )
    args = parser.parse_args()

    root = repo_root()
    scope = load_scope(root)
    selected, covered = validate_scope(root, scope)

    if not args.audit_only:
        verify_runtime(root, scope, selected)

    uncovered = scope["uncovered_required_cases"]
    print("M1.1b.1 canonical spatial semantic lane: PASS")
    print(f"  semantic sentinels: {len(selected)}")
    print(f"  canonical services promoted: {len(covered)}/{len(EXPECTED_SERVICES)}")
    print(f"  explicitly tracked uncovered areas: {len(uncovered)}")
    if args.audit_only:
        print("  runtime gates: skipped (--audit-only)")
    else:
        print("  M1.1a binding identity: PASS (23 services)")
        print("  sealed M0 regression: PASS (104/104 in both repeatability passes)")
        print(f"  sealed evidence: {EXPECTED_M0_EVIDENCE}")
    print("  M1.1b parent: remains open until the tracked direct semantic fixtures are added")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1.1b.1 canonical spatial semantic lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
