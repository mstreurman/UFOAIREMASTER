#!/usr/bin/env python3
"""UFO:AI Remaster M0.4 clean legacy build + launch smoke harness.

The harness deliberately exercises the canonical legacy SDL2/OpenGL path.
It removes the legacy M0 build directory, configures/builds through the
committed legacy-m0-f44 presets, launches the real client with isolated user
state, waits for the post-initialization marker emitted by Qcommon_Init(),
requires a short post-marker survival window, then terminates the client.

On PASS it writes a deterministic evidence record and BLAKE3-256 sidecar.
Raw configure/build/launch logs remain in the ignored build tree.
"""

from __future__ import annotations

import errno
import hashlib
import os
import pty
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import time

M03_REVISION = "f9cc60dd84aa5eef4b433bc7c2af1314ab0bb140"
CANONICAL_REVISION = "763173ed036ebbee32c2a7bf6aefa19748df89ff"
BUILD_DIR_NAME = "build-m0-legacy-f44"
CONFIGURE_PRESET = "legacy-m0-f44"
BUILD_PRESET = "legacy-m0-f44"
INIT_MARKER = "====== UFO Initialized ======"
LAUNCH_TIMEOUT_SECONDS = 60.0
POST_MARKER_SURVIVAL_SECONDS = 5.0
TERMINATION_GRACE_SECONDS = 5.0
EVIDENCE_PATH = Path("docs/reference/reference-m0-legacy-build-launch-smoke.txt")
EVIDENCE_B3_PATH = Path("docs/reference/reference-m0-legacy-build-launch-smoke.b3")
ALLOWED_WORKTREE_PATHS = {
    "docs/reference/reference-m0-legacy-build-launch-smoke.md",
    "docs/reference/reference-m0-legacy-build-launch-smoke.txt",
    "docs/reference/reference-m0-legacy-build-launch-smoke.b3",
    "tools/remaster/run-m0-legacy-smoke.py",
}


class SmokeError(RuntimeError):
    pass


def run_capture(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )
    except FileNotFoundError as exc:
        raise SmokeError(f"required command not found: {argv[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise SmokeError(f"command failed ({' '.join(argv)}){suffix}") from exc


def run_logged(argv: list[str], log_path: Path, *, cwd: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"+ {' '.join(argv)}")
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        try:
            proc = subprocess.Popen(
                argv,
                cwd=cwd,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
            )
        except FileNotFoundError as exc:
            raise SmokeError(f"required command not found: {argv[0]}") from exc

        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log.write(line)
        rc = proc.wait()
    if rc != 0:
        raise SmokeError(f"command failed with exit code {rc}: {' '.join(argv)} (log: {log_path})")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def b3sum_file(path: Path) -> str:
    proc = run_capture(["b3sum", str(path)])
    token = proc.stdout.split()[0] if proc.stdout.split() else ""
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise SmokeError(f"unexpected b3sum output for {path}: {proc.stdout!r}")
    return token


def git_root() -> Path:
    proc = run_capture(["git", "rev-parse", "--show-toplevel"])
    root = Path(proc.stdout.strip()).resolve()
    if not root.is_dir():
        raise SmokeError("git repository root is unavailable")
    return root


def git_head(root: Path) -> str:
    return run_capture(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()


def require_m03_ancestor(root: Path) -> None:
    proc = run_capture(
        ["git", "merge-base", "--is-ancestor", M03_REVISION, "HEAD"],
        cwd=root,
        check=False,
    )
    if proc.returncode != 0:
        raise SmokeError(f"M0.4 requires M0.3 ancestor {M03_REVISION}")


def require_no_unrelated_worktree_changes(root: Path) -> None:
    proc = run_capture(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
    )
    unexpected: list[str] = []
    for raw in proc.stdout.splitlines():
        if not raw:
            continue
        path = raw[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path not in ALLOWED_WORKTREE_PATHS:
            unexpected.append(raw)
    if unexpected:
        joined = "\n".join(unexpected)
        raise SmokeError(f"unrelated working-tree changes present:\n{joined}")


def safe_remove_build_dir(root: Path) -> Path:
    build_dir = (root / BUILD_DIR_NAME).resolve()
    expected = root / BUILD_DIR_NAME
    if build_dir != expected.resolve():
        raise SmokeError(f"refusing unexpected build path: {build_dir}")
    if expected.is_symlink():
        expected.unlink()
    elif expected.exists():
        shutil.rmtree(expected)
    expected.mkdir(parents=True, exist_ok=True)
    return expected


def parse_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise SmokeError(f"CMake cache missing: {path}")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw or raw.startswith("//") or raw.startswith("#") or "=" not in raw:
            continue
        lhs, value = raw.split("=", 1)
        name = lhs.split(":", 1)[0]
        out[name] = value
    return out


def require_artifacts(build_dir: Path) -> dict[str, Path]:
    artifacts = {
        "ufo": build_dir / "ufo",
        "ufoded": build_dir / "ufoded",
        "game_so": build_dir / "base" / "game.so",
    }
    for name, path in artifacts.items():
        if not path.is_file():
            raise SmokeError(f"required build artifact missing ({name}): {path}")
    for name in ("ufo", "ufoded"):
        if not os.access(artifacts[name], os.X_OK):
            raise SmokeError(f"required build artifact is not executable ({name}): {artifacts[name]}")
    return artifacts


def terminate_process_group(proc: subprocess.Popen[bytes]) -> str:
    if proc.poll() is not None:
        return "already-exited"
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return "already-exited"
    try:
        proc.wait(timeout=TERMINATION_GRACE_SECONDS)
        return "sigterm"
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=TERMINATION_GRACE_SECONDS)
        return "sigkill-after-sigterm-timeout"


def launch_smoke(root: Path, build_dir: Path, ufo: Path) -> tuple[str, Path]:
    if not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DISPLAY"):
        raise SmokeError("launch smoke requires an active graphical session (WAYLAND_DISPLAY or DISPLAY)")

    state_dir = build_dir / "m0-legacy-smoke-state"
    if state_dir.exists():
        shutil.rmtree(state_dir)
    home = state_dir / "home"
    config = state_dir / "config"
    data = state_dir / "data"
    cache = state_dir / "cache"
    for path in (home, config, data, cache):
        path.mkdir(parents=True, exist_ok=True)

    log_path = build_dir / "m0-legacy-launch-smoke.log"
    if log_path.exists():
        log_path.unlink()

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(config),
            "XDG_DATA_HOME": str(data),
            "XDG_CACHE_HOME": str(cache),
        }
    )

    argv = [
        str(ufo),
        "+set", "vid_fullscreen", "0",
        "+set", "vid_grabmouse", "0",
        "+set", "vid_width", "1024",
        "+set", "vid_height", "768",
    ]

    print("=== LEGACY CLIENT LAUNCH SMOKE ===")
    print(f"marker: {INIT_MARKER}")
    print(f"timeout: {int(LAUNCH_TIMEOUT_SECONDS)} s")
    print(f"post-marker survival: {int(POST_MARKER_SURVIVAL_SECONDS)} s")
    print(f"log: {log_path.relative_to(root)}")
    print(f"+ {' '.join(argv)}")

    master_fd, slave_fd = pty.openpty()
    try:
        try:
            proc: subprocess.Popen[bytes] = subprocess.Popen(
                argv,
                cwd=root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=slave_fd,
                stderr=slave_fd,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as exc:
            raise SmokeError(f"failed to launch legacy client: {exc}") from exc
        finally:
            os.close(slave_fd)

        start = time.monotonic()
        marker_time: float | None = None
        marker_bytes = INIT_MARKER.encode("utf-8")
        observed = bytearray()

        with log_path.open("wb", buffering=0) as log:
            try:
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0.10)
                    if ready:
                        try:
                            chunk = os.read(master_fd, 65536)
                        except OSError as exc:
                            # Linux PTYs return EIO after the slave side closes.
                            if exc.errno == errno.EIO:
                                chunk = b""
                            else:
                                raise
                        if chunk:
                            log.write(chunk)
                            observed.extend(chunk)

                    now = time.monotonic()
                    rc = proc.poll()

                    if marker_time is None and marker_bytes in observed:
                        marker_time = now
                        print("launch marker: PASS")

                    if marker_time is None:
                        if rc is not None:
                            raise SmokeError(
                                f"legacy client exited before initialization marker (exit {rc}; "
                                f"log: {log_path.relative_to(root)})"
                            )
                        if now - start >= LAUNCH_TIMEOUT_SECONDS:
                            raise SmokeError(
                                f"legacy client did not reach initialization marker within "
                                f"{int(LAUNCH_TIMEOUT_SECONDS)} s (log: {log_path.relative_to(root)})"
                            )
                    else:
                        if rc is not None:
                            raise SmokeError(
                                f"legacy client exited during post-marker survival window "
                                f"(exit {rc}; log: {log_path.relative_to(root)})"
                            )
                        if now - marker_time >= POST_MARKER_SURVIVAL_SECONDS:
                            print("post-marker survival: PASS")
                            termination = terminate_process_group(proc)
                            return termination, log_path
            except Exception:
                terminate_process_group(proc)
                raise
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass


def read_manifest_hash(root: Path) -> str:
    sidecar = root / "docs/reference/reference-m0-environment-manifest.b3"
    if not sidecar.is_file():
        raise SmokeError(f"M0.3 environment sidecar missing: {sidecar}")
    token = sidecar.read_text(encoding="utf-8").split()[0]
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise SmokeError(f"invalid M0.3 environment BLAKE3 sidecar: {sidecar}")
    return token


def write_evidence(
    root: Path,
    *,
    tested_revision: str,
    environment_blake3: str,
    cache: dict[str, str],
    termination: str,
) -> str:
    script_rel = Path("tools/remaster/run-m0-legacy-smoke.py")
    presets_rel = Path("CMakePresets.json")
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown") or "unknown"
    display_path = "wayland" if os.environ.get("WAYLAND_DISPLAY") else "x11"

    lines = [
        "ufoai-remaster-m0-legacy-build-launch-smoke-v1",
        "schema.version=1",
        f"source.tested_revision={tested_revision}",
        f"source.canonical_revision={CANONICAL_REVISION}",
        f"environment.m0_manifest_blake3_256={environment_blake3}",
        f"input.smoke_script.sha256={sha256_file(root / script_rel)}",
        f"input.cmake_presets.sha256={sha256_file(root / presets_rel)}",
        f"build.configure_preset={CONFIGURE_PRESET}",
        f"build.build_preset={BUILD_PRESET}",
        f"build.type={cache.get('CMAKE_BUILD_TYPE', 'unknown')}",
        f"build.ufoai_remaster={cache.get('UFOAI_REMASTER', 'unknown')}",
        "build.clean_binary_dir=true",
        "build.target.game=PASS",
        "build.target.ufo=PASS",
        "build.target.ufoded=PASS",
        "build.artifact.ufo=present-executable",
        "build.artifact.ufoded=present-executable",
        "build.artifact.base_game_so=present",
        "launch.user_state=isolated",
        f"launch.session_type={session_type}",
        f"launch.display_path={display_path}",
        "launch.video_driver=not-forced",
        "launch.windowed=true",
        "launch.size=1024x768",
        f"launch.init_marker={INIT_MARKER}",
        "launch.init_marker_seen=true",
        f"launch.timeout_seconds={int(LAUNCH_TIMEOUT_SECONDS)}",
        f"launch.post_marker_survival_seconds={int(POST_MARKER_SURVIVAL_SECONDS)}",
        "launch.post_marker_survival=PASS",
        f"launch.harness_termination={termination}",
        "result=PASS",
    ]
    text = "\n".join(lines) + "\n"
    evidence = root / EVIDENCE_PATH
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(text, encoding="utf-8")
    digest = b3sum_file(evidence)
    (root / EVIDENCE_B3_PATH).write_text(f"{digest}  {EVIDENCE_PATH.name}\n", encoding="utf-8")
    return digest


def main() -> int:
    try:
        root = git_root()
        os.chdir(root)
        require_m03_ancestor(root)
        require_no_unrelated_worktree_changes(root)
        tested_revision = git_head(root)

        # Never leave a stale PASS record behind if this run fails.
        for rel in (EVIDENCE_PATH, EVIDENCE_B3_PATH):
            path = root / rel
            if path.exists():
                path.unlink()

        print("=== M0.4 PRECONDITION: M0.3 ENVIRONMENT ===")
        verify = subprocess.run(
            [sys.executable, "tools/remaster/capture-m0-manifest.py", "--verify"],
            cwd=root,
            text=True,
        )
        if verify.returncode != 0:
            raise SmokeError("M0.3 environment manifest verification failed")
        environment_blake3 = read_manifest_hash(root)

        build_dir = safe_remove_build_dir(root)
        configure_log = build_dir / "m0-legacy-configure.log"
        build_log = build_dir / "m0-legacy-build.log"

        print("\n=== CLEAN LEGACY CONFIGURE ===")
        run_logged(["cmake", "--preset", CONFIGURE_PRESET], configure_log, cwd=root)

        cache = parse_cache(build_dir / "CMakeCache.txt")
        if cache.get("UFOAI_REMASTER") != "OFF":
            raise SmokeError(
                f"legacy preset did not configure UFOAI_REMASTER=OFF (observed {cache.get('UFOAI_REMASTER')!r})"
            )
        if cache.get("CMAKE_BUILD_TYPE") != "RelWithDebInfo":
            raise SmokeError(
                f"legacy preset did not configure RelWithDebInfo (observed {cache.get('CMAKE_BUILD_TYPE')!r})"
            )
        print("legacy preset cache gate: PASS (UFOAI_REMASTER=OFF, RelWithDebInfo)")

        print("\n=== CLEAN LEGACY BUILD ===")
        run_logged(["cmake", "--build", "--preset", BUILD_PRESET], build_log, cwd=root)
        artifacts = require_artifacts(build_dir)
        print("legacy build artifacts: PASS (ufo, ufoded, base/game.so)")

        print()
        termination, launch_log = launch_smoke(root, build_dir, artifacts["ufo"])
        print(f"harness termination: {termination}")

        digest = write_evidence(
            root,
            tested_revision=tested_revision,
            environment_blake3=environment_blake3,
            cache=cache,
            termination=termination,
        )

        print("\nM0.4 clean canonical legacy build + launch smoke: PASS")
        print(f"evidence: {EVIDENCE_PATH}")
        print(f"BLAKE3-256: {digest}")
        print(f"sidecar:  {EVIDENCE_B3_PATH}")
        print(f"configure log: {configure_log.relative_to(root)}")
        print(f"build log:     {build_log.relative_to(root)}")
        print(f"launch log:    {launch_log.relative_to(root)}")
        return 0
    except SmokeError as exc:
        print(f"M0.4 clean canonical legacy build + launch smoke: FAIL: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("M0.4 clean canonical legacy build + launch smoke: FAIL: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
