#!/usr/bin/env python3
"""Capture/verify the M0.8 public clean-checkout reproducibility proof."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

BASELINE_REVISION = "e611ca139e38dc246535f9536b8f6c2eda77a5f3"
PUBLIC_REPOSITORY = "https://github.com/mstreurman/UFOAIREMASTER.git"
BUILD_REL = Path("build-m0-clean-bootstrap-f44")
CHECKOUT_NAME = "checkout"
LOGS_NAME = "logs"
EVIDENCE_REL = Path("docs/reference/reference-m0-clean-bootstrap.txt")
SIDECAR_REL = Path("docs/reference/reference-m0-clean-bootstrap.b3")
REFERENCE_DOC_REL = Path("docs/reference/reference-m0-clean-bootstrap.md")
RUNNER_REL = Path("tools/remaster/run-m0-clean-bootstrap.py")
PROVISIONER_REL = Path("tools/remaster/provision-m0-slang.py")

EXPECTED_SIDECARS = {
    "environment": (
        "docs/reference/reference-m0-environment-manifest.txt",
        "docs/reference/reference-m0-environment-manifest.b3",
        "4b319f96f5674b3d39108fdd327b2e04143b1f4eaeaa88469eac364071f756b5",
    ),
    "legacy_committed": (
        "docs/reference/reference-m0-legacy-build-launch-smoke.txt",
        "docs/reference/reference-m0-legacy-build-launch-smoke.b3",
        "0bcf17b95ab6cccffab75f059c9ff919fe098e424fb02a8f579af7b1b0617d8e",
    ),
    "canonical": (
        "docs/reference/reference-m0-canonical-regression.txt",
        "docs/reference/reference-m0-canonical-regression.b3",
        "b5a6178ef17c3eb9f8957307ef94dc9d367ca2495d970f5c747170fe435b6a7e",
    ),
    "feature_selection": (
        "docs/reference/reference-m0-feature-selection.txt",
        "docs/reference/reference-m0-feature-selection.b3",
        "9812843be2e738af10cc401d1d0ca5a46eb1e6d08c95abd8172f86fc4599d553",
    ),
    "r2_descriptor_heap": (
        "docs/reference/reference-m0-descriptor-heap.txt",
        "docs/reference/reference-m0-descriptor-heap.b3",
        "a31f501b96a5cc3467a67c8025a4f7ca585c47fa94c1887c4469c7595c59e594",
    ),
    "r3_slang": (
        "docs/reference/reference-m0-slang-descriptor-heap.txt",
        "docs/reference/reference-m0-slang-descriptor-heap.b3",
        "1793f2d3d23b8ed8455d4f01379578773b48cbe878a46affc0785e95565a7b63",
    ),
    "r4_rt": (
        "docs/reference/reference-m0-rt-descriptor-heap.txt",
        "docs/reference/reference-m0-rt-descriptor-heap.b3",
        "a8aa4a83dc5c3e444159bff55b94c76ea18d4c7907043a53cf3101ce7a53c07a",
    ),
    "r5_jolt_sanitizer": (
        "docs/reference/reference-m0-jolt-stress-sanitizer.txt",
        "docs/reference/reference-m0-jolt-stress-sanitizer.b3",
        "8a3ca9b8c29010f19bbf4ba744e357d80d9b627289ed6726f5fc88a2cb5c8653",
    ),
    "r5_jolt": (
        "docs/reference/reference-m0-jolt-stress.txt",
        "docs/reference/reference-m0-jolt-stress.b3",
        "c39472f995d570d298219ca2fb5fe95f99ef646a88b31f41f597684155cdcd88",
    ),
}

ALLOWED_OUTER_PATHS = {
    ".gitignore",
    str(REFERENCE_DOC_REL),
    str(EVIDENCE_REL),
    str(SIDECAR_REL),
    str(RUNNER_REL),
    str(PROVISIONER_REL),
}


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_capture(args: list[str], *, cwd: Path, env: dict[str, str] | None = None,
                check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.run(
        args, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if check and proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}")
    return proc


def run_logged(args: list[str], *, cwd: Path, log: Path,
               env: dict[str, str] | None = None) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    print("+ " + " ".join(args), flush=True)
    with log.open("w", encoding="utf-8", newline="\n") as out:
        proc = subprocess.Popen(
            args, cwd=cwd, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            out.write(line)
        rc = proc.wait()
    if rc != 0:
        raise GateError(f"command failed ({rc}): {' '.join(args)} (log: {log})")


def repo_root(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError("run M0.8 from inside the UFOAIREMASTER checkout")
    return Path(proc.stdout.strip()).resolve()


def git_output(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=repo, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} failed: {(proc.stderr or proc.stdout).strip()}")
    # Preserve leading bytes: porcelain-v1 uses column 0/1 spaces as status data.
    # Only remove line terminators so the first status line cannot be shifted.
    return proc.stdout.rstrip("\r\n")


def require_outer_state(repo: Path) -> None:
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_REVISION, "HEAD"],
        cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if ancestry.returncode != 0:
        raise GateError(f"current HEAD is not a descendant of sealed R5 baseline {BASELINE_REVISION}")
    raw = git_output(repo, "status", "--porcelain=v1", "--untracked-files=all")
    bad: list[str] = []
    for line in raw.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path not in ALLOWED_OUTER_PATHS:
            bad.append(line)
    if bad:
        raise GateError("M0.8 outer checkout has unrelated changes:\n" + "\n".join(bad))


def b3_file(path: Path) -> str:
    proc = subprocess.run(
        ["b3sum", str(path)], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"b3sum failed for {path}: {proc.stderr.strip()}")
    token = proc.stdout.split()[0] if proc.stdout.split() else ""
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise GateError(f"invalid b3sum output for {path}: {proc.stdout!r}")
    return token


def verify_sidecars(clone: Path) -> None:
    print("\n=== COMMITTED M0 EVIDENCE INTEGRITY ===", flush=True)
    for name, (evidence_rel, sidecar_rel, expected) in EXPECTED_SIDECARS.items():
        evidence = clone / evidence_rel
        sidecar = clone / sidecar_rel
        if not evidence.is_file() or not sidecar.is_file():
            raise GateError(f"missing committed M0 evidence pair for {name}")
        fields = sidecar.read_text(encoding="utf-8").strip().split()
        declared = fields[0] if fields else ""
        actual = b3_file(evidence)
        if declared != expected or actual != expected:
            raise GateError(
                f"{name} evidence mismatch: expected={expected} sidecar={declared} actual={actual}"
            )
        print(f"{name}: PASS ({actual})", flush=True)


def ensure_clean(clone: Path, label: str) -> None:
    status = git_output(clone, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise GateError(f"{label} checkout is not clean:\n{status}")
    print(f"{label}: PASS (tracked/untracked status clean)", flush=True)


def parse_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key] = value
    return values


def safe_workspace(repo: Path, requested: Path | None) -> Path:
    workspace = (requested or (repo / BUILD_REL)).resolve()
    if workspace == repo or repo in workspace.parents and workspace.name != BUILD_REL.name:
        raise GateError("refusing unsafe M0.8 workspace path inside repository")
    if workspace.name != BUILD_REL.name:
        raise GateError(f"M0.8 workspace basename must be {BUILD_REL.name!r}")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    return workspace


def cleanup_clone_generated(clone: Path) -> None:
    for rel in (
        "tools/slang",
        "build-m0-legacy-f44",
        "build-m0-feature-selection-check",
        "build-m0-slang-descriptor-heap-f44",
        "build-m0-remaster-f44",
    ):
        path = clone / rel
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def execute(repo: Path, workspace: Path) -> dict[str, str]:
    clone = workspace / CHECKOUT_NAME
    logs = workspace / LOGS_NAME
    logs.mkdir(parents=True, exist_ok=True)
    ccache_dir = workspace / "ccache"
    if ccache_dir.exists():
        shutil.rmtree(ccache_dir)
    test_env = os.environ.copy()
    test_env["CCACHE_DIR"] = str(ccache_dir)

    print("=== M0.8 PUBLIC CLEAN CHECKOUT ===", flush=True)
    clone_env = os.environ.copy()
    clone_env.update({
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    })
    for key in ("GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE"):
        clone_env.pop(key, None)
    run_logged(
        ["git", "clone", "--no-tags", "--no-checkout", PUBLIC_REPOSITORY, str(clone)],
        cwd=workspace, log=logs / "01-git-clone.log", env=clone_env,
    )
    run_logged(
        ["git", "checkout", "--detach", BASELINE_REVISION],
        cwd=clone, log=logs / "02-git-checkout.log",
    )
    head = git_output(clone, "rev-parse", "HEAD")
    if head != BASELINE_REVISION:
        raise GateError(f"clean checkout revision mismatch: expected {BASELINE_REVISION}, got {head}")
    ensure_clean(clone, "initial clean checkout")
    if (clone / "tools/slang/v2026.17").exists():
        raise GateError("public clean checkout unexpectedly contains project-local Slang binary cache")
    print("binary tool cache absent from source checkout: PASS", flush=True)

    verify_sidecars(clone)

    print("\n=== FRESH PINNED SLANG PROVISION ===", flush=True)
    provisioner = repo / PROVISIONER_REL
    run_logged(
        [sys.executable, str(provisioner), "--repo", str(clone), "--fresh-download", "--force"],
        cwd=repo, log=logs / "03-slang-provision.log", env=test_env,
    )
    slangc = clone / "tools/slang/v2026.17/bin/slangc"
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "tools/slang/v2026.17/bin/slangc"],
        cwd=clone, check=False,
    )
    if ignored.returncode != 0:
        raise GateError("provisioned Slang cache is not covered by committed ignore policy")
    ensure_clean(clone, "post-Slang clean checkout")

    manifest = parse_kv(clone / "docs/reference/reference-m0-environment-manifest.txt")
    slangc_sha = sha256_file(slangc)
    libslang_sha = sha256_file(clone / "tools/slang/v2026.17/lib/libslang.so")
    if slangc_sha != manifest.get("observed.slang.slangc_sha256"):
        raise GateError("fresh Slang slangc identity does not match committed M0 manifest")
    if libslang_sha != manifest.get("observed.slang.libslang_so_sha256"):
        raise GateError("fresh Slang libslang.so identity does not match committed M0 manifest")

    print("\n=== M0.3 ENVIRONMENT/VENDOR/TOOL VERIFY ===", flush=True)
    run_logged(
        [sys.executable, "tools/remaster/capture-m0-manifest.py", "--verify"],
        cwd=clone, log=logs / "04-environment-verify.log", env=test_env,
    )

    print("\n=== M0.4 FRESH LEGACY CONFIGURE/BUILD/LAUNCH SMOKE ===", flush=True)
    run_logged(
        [sys.executable, "tools/remaster/run-m0-legacy-smoke.py"],
        cwd=clone, log=logs / "05-legacy-smoke.log", env=test_env,
    )
    fresh_legacy_evidence = clone / "docs/reference/reference-m0-legacy-build-launch-smoke.txt"
    fresh_legacy_sidecar = clone / "docs/reference/reference-m0-legacy-build-launch-smoke.b3"
    fresh_legacy_digest = b3_file(fresh_legacy_evidence)
    declared_fresh = fresh_legacy_sidecar.read_text(encoding="utf-8").strip().split()[0]
    if fresh_legacy_digest != declared_fresh:
        raise GateError("fresh legacy smoke evidence sidecar mismatch")
    shutil.copy2(fresh_legacy_evidence, logs / "fresh-legacy-build-launch-smoke.txt")
    shutil.copy2(fresh_legacy_sidecar, logs / "fresh-legacy-build-launch-smoke.b3")
    run_capture(
        ["git", "restore", "--source=HEAD", "--",
         "docs/reference/reference-m0-legacy-build-launch-smoke.txt",
         "docs/reference/reference-m0-legacy-build-launch-smoke.b3"],
        cwd=clone,
    )
    ensure_clean(clone, "post-legacy evidence restore")

    print("\n=== M0.6 FEATURE-SELECTION + M0.5 CANONICAL VERIFY ===", flush=True)
    run_logged(
        [sys.executable, "tools/remaster/verify-m0-feature-selection.py", "--verify"],
        cwd=clone, log=logs / "06-feature-canonical-verify.log", env=test_env,
    )

    print("\n=== R3 FRESHLY PROVISIONED SLANG EXECUTION VERIFY ===", flush=True)
    run_logged(
        [sys.executable, "tools/remaster/run-m0-slang-descriptor-heap-fixture.py", "--verify"],
        cwd=clone, log=logs / "07-r3-slang-verify.log", env=test_env,
    )

    print("\n=== FINAL GENERATED-STATE CLEANUP ===", flush=True)
    cleanup_clone_generated(clone)
    ensure_clean(clone, "final clean checkout")

    pins = json.loads((clone / "tools/remaster/m0-pins.json").read_text(encoding="utf-8"))
    slang_pin = pins["slang"]
    return {
        "fresh_legacy_digest": fresh_legacy_digest,
        "slang_version": str(slang_pin["version"]),
        "slang_artifact": str(slang_pin["artifact"]),
        "slang_artifact_sha256": str(slang_pin["artifact_sha256"]),
        "slangc_sha256": slangc_sha,
        "libslang_sha256": libslang_sha,
    }


def evidence_bytes(repo: Path, result: dict[str, str]) -> bytes:
    lines = [
        "ufoai-remaster-m0-clean-bootstrap-v1",
        "schema.version=1",
        f"baseline.m0_revision={BASELINE_REVISION}",
        f"source.repository={PUBLIC_REPOSITORY}",
        "source.clone_transport=https-public",
        "source.local_object_reuse=none",
        "source.git_global_config=disabled-for-clone",
        "source.git_system_config=disabled-for-clone",
        "source.git_terminal_prompt=disabled",
        "source.initial_clean_checkout=PASS",
        "source.final_clean_checkout=PASS",
        f"input.runner.sha256={sha256_file(repo / RUNNER_REL)}",
        f"input.slang_provisioner.sha256={sha256_file(repo / PROVISIONER_REL)}",
        f"input.reference_doc.sha256={sha256_file(repo / REFERENCE_DOC_REL)}",
        f"input.gitignore.sha256={sha256_file(repo / '.gitignore')}",
        f"slang.version={result['slang_version']}",
        f"slang.artifact={result['slang_artifact']}",
        f"slang.artifact_sha256={result['slang_artifact_sha256']}",
        f"slang.slangc_sha256={result['slangc_sha256']}",
        f"slang.libslang_so_sha256={result['libslang_sha256']}",
        "slang.network_fresh_download=PASS",
        "slang.cache_from_source_checkout=absent",
        "slang.cache_ignore_policy=PASS",
        f"environment.m0_manifest_blake3_256={EXPECTED_SIDECARS['environment'][2]}",
        "environment.manifest_verify=PASS",
        "environment.jolt_vendor_identity=PASS",
        "configure.legacy_m0=PASS",
        "build.legacy_ufo_ufoded_game=PASS",
        "launch.legacy_smoke=PASS",
        f"launch.fresh_evidence_blake3_256={result['fresh_legacy_digest']}",
        f"tests.canonical_m0_5_blake3_256={EXPECTED_SIDECARS['canonical'][2]}",
        "tests.canonical_m0_5_verify=PASS",
        f"tests.feature_selection_m0_6_blake3_256={EXPECTED_SIDECARS['feature_selection'][2]}",
        "tests.feature_selection_m0_6_verify=PASS",
        f"risk.r2_descriptor_heap_evidence_blake3_256={EXPECTED_SIDECARS['r2_descriptor_heap'][2]}",
        "risk.r2_committed_evidence_integrity=PASS",
        f"risk.r3_slang_evidence_blake3_256={EXPECTED_SIDECARS['r3_slang'][2]}",
        "risk.r3_fresh_tool_execution_verify=PASS",
        f"risk.r4_rt_evidence_blake3_256={EXPECTED_SIDECARS['r4_rt'][2]}",
        "risk.r4_committed_evidence_integrity=PASS",
        f"risk.r5_jolt_sanitizer_evidence_blake3_256={EXPECTED_SIDECARS['r5_jolt_sanitizer'][2]}",
        f"risk.r5_jolt_evidence_blake3_256={EXPECTED_SIDECARS['r5_jolt'][2]}",
        "risk.r5_committed_evidence_integrity=PASS",
        "build.ccache_state=fresh-isolated-per-proof",
        "dependencies.undocumented_binary_cache=none",
        "production.behavior_replacement=none",
        "result=PASS",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture", action="store_true", help="run fresh proof and capture normalized evidence")
    mode.add_argument("--verify", action="store_true", help="rerun fresh proof and compare normalized evidence")
    parser.add_argument("--workspace", type=Path, help=f"workspace; basename must be {BUILD_REL.name}")
    args = parser.parse_args()

    try:
        repo = repo_root(Path.cwd())
        require_outer_state(repo)
        for tool in ("git", "b3sum", "cmake", "ninja"):
            if not shutil.which(tool):
                raise GateError(f"required host tool missing before clean-bootstrap proof: {tool}")
        workspace = safe_workspace(repo, args.workspace)
        result = execute(repo, workspace)
        generated = evidence_bytes(repo, result)
        digest_proc = subprocess.run(
            ["b3sum"], input=generated, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if digest_proc.returncode != 0:
            raise GateError(f"b3sum failed for M0.8 evidence: {digest_proc.stderr.decode(errors='replace')}")
        digest = digest_proc.stdout.decode().split()[0]
        evidence = repo / EVIDENCE_REL
        sidecar = repo / SIDECAR_REL

        if args.verify:
            if not evidence.is_file() or not sidecar.is_file():
                raise GateError("M0.8 evidence missing; run --capture first")
            stored = evidence.read_bytes()
            if stored != generated:
                diff = "".join(difflib.unified_diff(
                    stored.decode("utf-8", errors="replace").splitlines(True),
                    generated.decode("utf-8", errors="replace").splitlines(True),
                    fromfile=str(EVIDENCE_REL) + " (stored)",
                    tofile=str(EVIDENCE_REL) + " (current)",
                ))
                raise GateError("M0.8 clean-bootstrap evidence drift detected:\n" + diff)
            declared = sidecar.read_text(encoding="utf-8").strip().split()[0]
            actual = b3_file(evidence)
            if declared != digest or actual != digest:
                raise GateError(
                    f"M0.8 sidecar mismatch: generated={digest} stored={actual} sidecar={declared}"
                )
            print(f"\nM0.8 clean-checkout reproducibility verification: PASS ({digest})")
        else:
            write_atomic(evidence, generated)
            write_atomic(sidecar, f"{digest}  {EVIDENCE_REL.name}\n".encode("utf-8"))
            print(f"\nM0.8 clean-checkout reproducibility capture: PASS ({digest})")
            print(f"evidence: {EVIDENCE_REL}")
            print(f"sidecar:  {SIDECAR_REL}")
        print(f"workspace/logs: {workspace / LOGS_NAME}")
        return 0
    except GateError as exc:
        print(f"M0.8 clean-checkout reproducibility: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
