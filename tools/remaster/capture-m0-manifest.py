#!/usr/bin/env python3
"""Capture/verify the UFO:AI Remaster M0.3 reference environment manifest.

The generated manifest is intentionally deterministic for a fixed reference
workstation state. It contains no capture timestamp, hostname, username, or
absolute checkout path. Environment drift is therefore visible as a content
and BLAKE3-256 change rather than hidden by capture metadata.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Iterable

SCHEMA = "ufoai-remaster-m0-reference-manifest-v1"
DEFAULT_OUTPUT = Path("docs/reference/reference-m0-environment-manifest.txt")
EXPECTED_FEDORA = "44"
EXPECTED_ARCH = "x86_64"


class CaptureError(RuntimeError):
    pass


def run(argv: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
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
        raise CaptureError(f"required command not found: {argv[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f": {detail}" if detail else ""
        raise CaptureError(f"command failed ({' '.join(argv)}){suffix}") from exc


def first_line(text: str) -> str:
    for line in text.splitlines():
        line = " ".join(line.strip().split())
        if line:
            return line
    return ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def b3sum_bytes(data: bytes) -> str:
    try:
        proc = subprocess.run(
            ["b3sum"],
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise CaptureError("required command not found: b3sum") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", "replace").strip()
        raise CaptureError(f"b3sum failed: {detail}") from exc
    token = proc.stdout.decode("ascii", "strict").split()[0]
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise CaptureError(f"unexpected b3sum output: {proc.stdout!r}")
    return token


def b3sum_jolt_tree(root: Path) -> str:
    """Recompute the documented Jolt sorted-file-manifest BLAKE3-256."""
    if not root.is_dir():
        raise CaptureError(f"Jolt vendor root missing: {root}")

    manifest_name = "UFOAI_VENDOR_MANIFEST.txt"
    files: list[tuple[bytes, Path]] = []
    for path in root.rglob("*"):
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(mode):
            continue
        rel = path.relative_to(root).as_posix()
        if rel == manifest_name:
            continue
        rel_bytes = rel.encode("utf-8")
        files.append((rel_bytes, path))

    files.sort(key=lambda item: item[0])
    if not files:
        raise CaptureError("Jolt vendor tree contains no regular files")

    try:
        proc = subprocess.Popen(
            ["b3sum"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise CaptureError("required command not found: b3sum") from exc

    assert proc.stdin is not None
    try:
        for rel_bytes, path in files:
            size = path.stat().st_size
            proc.stdin.write(rel_bytes)
            proc.stdin.write(b"\0")
            proc.stdin.write(str(size).encode("ascii"))
            proc.stdin.write(b"\0")
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    proc.stdin.write(chunk)
            proc.stdin.write(b"\0")
        proc.stdin.close()
        stdout = proc.stdout.read() if proc.stdout is not None else b""
        stderr = proc.stderr.read() if proc.stderr is not None else b""
        rc = proc.wait()
    except BrokenPipeError as exc:
        proc.kill()
        raise CaptureError("b3sum terminated while hashing Jolt vendor tree") from exc

    if rc != 0:
        raise CaptureError(f"b3sum failed while hashing Jolt tree: {stderr.decode('utf-8', 'replace').strip()}")
    token = stdout.decode("ascii", "strict").split()[0]
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise CaptureError(f"unexpected b3sum output for Jolt tree: {stdout!r}")
    return token


def parse_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    path = Path("/etc/os-release")
    if not path.is_file():
        raise CaptureError("/etc/os-release is missing")
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        values[key] = value
    return values


def rpm_records(spec: str) -> list[str]:
    qf = "%{NAME}\\t%{EPOCH}\\t%{VERSION}\\t%{RELEASE}\\t%{ARCH}\\n"
    proc = run(["rpm", "-q", "--qf", qf, spec], check=False)
    if proc.returncode != 0:
        return []
    records: list[str] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 5:
            raise CaptureError(f"unexpected rpm query output for {spec!r}: {line!r}")
        name, epoch, version, release, arch = parts
        if epoch in ("", "(none)", "None"):
            epoch = "0"
        records.append(f"{name}-{epoch}:{version}-{release}.{arch}")
    return sorted(set(records))


def rpm_owner(path: Path) -> str:
    qf = "%{NAME}\\t%{EPOCH}\\t%{VERSION}\\t%{RELEASE}\\t%{ARCH}\\n"
    proc = run(["rpm", "-qf", "--qf", qf, str(path)], check=False)
    if proc.returncode != 0:
        return "unowned"
    parts = proc.stdout.strip().split("\t")
    if len(parts) != 5:
        return "unparseable"
    name, epoch, version, release, arch = parts
    if epoch in ("", "(none)", "None"):
        epoch = "0"
    return f"{name}-{epoch}:{version}-{release}.{arch}"


def parse_rpm_scope(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        raise CaptureError(f"RPM scope file missing: {path}")
    rows: list[tuple[str, str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2 or parts[0] not in {"required", "optional"}:
            raise CaptureError(f"invalid RPM scope line {lineno}: {raw!r}")
        rows.append((parts[0], parts[1]))
    if not rows:
        raise CaptureError("RPM scope is empty")
    return rows


def parse_cpu() -> dict[str, str]:
    wanted = {"vendor_id", "cpu family", "model", "model name", "stepping"}
    out: dict[str, str] = {}
    path = Path("/proc/cpuinfo")
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            if out:
                break
            continue
        if ":" not in raw:
            continue
        key, value = [part.strip() for part in raw.split(":", 1)]
        if key in wanted:
            out[key] = " ".join(value.split())
    return out


def parse_display_pci() -> list[str]:
    rows: list[str] = []
    root = Path("/sys/bus/pci/devices")
    if not root.is_dir():
        return rows
    for dev in sorted(root.iterdir(), key=lambda p: p.name):
        try:
            cls = (dev / "class").read_text().strip().lower()
            if not cls.startswith("0x03"):
                continue
            vendor = (dev / "vendor").read_text().strip().lower()
            device = (dev / "device").read_text().strip().lower()
            subvendor = (dev / "subsystem_vendor").read_text().strip().lower()
            subdevice = (dev / "subsystem_device").read_text().strip().lower()
            driver = "none"
            driver_link = dev / "driver"
            if driver_link.exists():
                driver = driver_link.resolve().name
            rows.append(
                f"{dev.name}|vendor={vendor}|device={device}|subsystem={subvendor}:{subdevice}|driver={driver}"
            )
        except OSError:
            continue
    return rows


def tool_specs(repo: Path) -> list[dict[str, object]]:
    slangc = repo / "tools/slang/v2026.17/bin/slangc"
    return [
        {"key": "gcc", "path": Path("/usr/bin/gcc"), "cmd": ["/usr/bin/gcc", "-dumpfullversion", "-dumpversion"], "required": True},
        {"key": "gxx", "path": Path("/usr/bin/g++"), "cmd": ["/usr/bin/g++", "-dumpfullversion", "-dumpversion"], "required": True},
        {"key": "ld", "path": Path("/usr/bin/ld"), "cmd": ["/usr/bin/ld", "--version"], "required": True},
        {"key": "clang", "path": Path("/usr/bin/clang"), "cmd": ["/usr/bin/clang", "--version"], "required": False},
        {"key": "cmake", "path": Path("/usr/bin/cmake"), "cmd": ["/usr/bin/cmake", "--version"], "required": True},
        {"key": "ninja", "path": Path("/usr/bin/ninja"), "cmd": ["/usr/bin/ninja", "--version"], "required": True},
        {"key": "ccache", "path": Path("/usr/bin/ccache"), "cmd": ["/usr/bin/ccache", "--version"], "required": True},
        {"key": "git", "path": Path("/usr/bin/git"), "cmd": ["/usr/bin/git", "--version"], "required": True},
        {"key": "python3", "path": Path("/usr/bin/python3"), "cmd": ["/usr/bin/python3", "--version"], "required": True},
        {"key": "pkg_config", "path": Path("/usr/bin/pkg-config"), "cmd": ["/usr/bin/pkg-config", "--version"], "required": True},
        {"key": "spirv_val", "path": Path("/usr/bin/spirv-val"), "cmd": ["/usr/bin/spirv-val", "--version"], "required": True},
        {"key": "b3sum", "path": Path("/usr/bin/b3sum"), "cmd": ["/usr/bin/b3sum", "--version"], "required": True},
        {"key": "glslc", "path": Path("/usr/bin/glslc"), "cmd": ["/usr/bin/glslc", "--version"], "required": False},
        {"key": "glslang_validator", "path": Path("/usr/bin/glslangValidator"), "cmd": ["/usr/bin/glslangValidator", "--version"], "required": False},
        {"key": "slangc", "path": slangc, "cmd": [str(slangc), "-version"], "required": True, "repo_relative": True},
    ]


def read_jolt_vendor_manifest(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise CaptureError(f"Jolt vendor manifest missing: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def validate_presets(repo: Path) -> str:
    path = repo / "CMakePresets.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot parse {path}: {exc}") from exc
    presets = {item.get("name"): item for item in data.get("configurePresets", [])}
    base = presets.get("m0-f44-base")
    if not isinstance(base, dict):
        raise CaptureError("CMakePresets.json lacks m0-f44-base")
    cache = base.get("cacheVariables", {})
    if cache.get("CMAKE_C_COMPILER_LAUNCHER") != "ccache" or cache.get("CMAKE_CXX_COMPILER_LAUNCHER") != "ccache":
        raise CaptureError("M0 Fedora preset does not pin ccache launchers")
    return sha256_file(path)


def manifest_text(repo: Path) -> str:
    pins_path = repo / "tools/remaster/m0-pins.json"
    rpm_scope_path = repo / "tools/remaster/m0-reference-rpms.txt"
    script_path = repo / "tools/remaster/capture-m0-manifest.py"

    try:
        pins = json.loads(pins_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot parse {pins_path}: {exc}") from exc

    if pins.get("schema") != 1:
        raise CaptureError("unsupported m0-pins.json schema")
    slang = pins.get("slang", {})
    jolt = pins.get("jolt", {})

    osr = parse_os_release()
    if osr.get("ID") != "fedora" or osr.get("VERSION_ID") != EXPECTED_FEDORA:
        raise CaptureError(
            f"reference capture requires Fedora {EXPECTED_FEDORA}; observed ID={osr.get('ID')!r} VERSION_ID={osr.get('VERSION_ID')!r}"
        )
    arch = first_line(run(["rpm", "--eval", "%{_arch}"]).stdout)
    if arch != EXPECTED_ARCH:
        raise CaptureError(f"reference capture requires {EXPECTED_ARCH}; observed {arch!r}")

    lines: list[str] = [SCHEMA]
    add = lambda key, value: lines.append(f"{key}={value}")

    add("schema.version", "1")
    add("source.canonical_revision", pins["canonical_source_revision"])
    add("platform.id", osr.get("ID", "unknown"))
    add("platform.version_id", osr.get("VERSION_ID", "unknown"))
    add("platform.arch", arch)
    add("platform.kernel_release", first_line(run(["uname", "-r"]).stdout))

    cpu = parse_cpu()
    for key in ("vendor_id", "cpu family", "model", "model name", "stepping"):
        if key in cpu:
            add("machine.cpu." + key.replace(" ", "_"), cpu[key])
    for idx, row in enumerate(parse_display_pci()):
        add(f"machine.display_pci.{idx:02d}", row)

    add("input.capture_script.sha256", sha256_file(script_path))
    add("input.pins.sha256", sha256_file(pins_path))
    add("input.rpm_scope.sha256", sha256_file(rpm_scope_path))
    add("input.cmake_presets.sha256", validate_presets(repo))

    # Capture exact direct reference RPM NEVRAs.
    for requirement, spec in parse_rpm_scope(rpm_scope_path):
        records = rpm_records(spec)
        if not records and requirement == "required":
            raise CaptureError(f"required reference RPM is not installed: {spec}")
        if not records:
            add(f"rpm.{spec}", "missing")
        elif len(records) == 1:
            add(f"rpm.{spec}", records[0])
        else:
            for idx, record in enumerate(records):
                add(f"rpm.{spec}.{idx:02d}", record)

    # Capture tool versions and the RPM owning each system executable.
    for spec in tool_specs(repo):
        key = str(spec["key"])
        path = Path(spec["path"])
        required = bool(spec["required"])
        repo_relative = bool(spec.get("repo_relative", False))
        if not path.exists():
            if required:
                raise CaptureError(f"required tool is missing: {path}")
            add(f"tool.{key}.state", "missing")
            continue
        proc = run([str(x) for x in spec["cmd"]], check=False)
        if proc.returncode != 0:
            if required:
                raise CaptureError(f"required tool failed: {path}: {(proc.stderr or proc.stdout).strip()}")
            add(f"tool.{key}.state", "present-version-command-failed")
            continue
        version = first_line(proc.stdout + "\n" + proc.stderr)
        if not version:
            raise CaptureError(f"tool produced no version identity: {path}")
        add(f"tool.{key}.version", version)
        if repo_relative:
            add(f"tool.{key}.path", path.relative_to(repo).as_posix())
        else:
            add(f"tool.{key}.path", str(path))
            add(f"tool.{key}.owner_nevra", rpm_owner(path))

    # Record how compiler invocation resolves in the user's normal PATH.
    for command in ("gcc", "g++"):
        proc = run(["bash", "-lc", f"command -v {command}"], check=False)
        resolved = first_line(proc.stdout) if proc.returncode == 0 else "missing"
        add(f"tool.{command.replace('+', 'x')}.command_path", resolved)

    # Slang exact accepted pin + observed compiler/library identities.
    slang_root = repo / "tools/slang/v2026.17"
    slangc = slang_root / "bin/slangc"
    slang_lib = slang_root / "lib/libslang.so"
    slang_version_proc = run([str(slangc), "-version"], check=False)
    if slang_version_proc.returncode != 0:
        raise CaptureError(
            f"Slang version command failed: {(slang_version_proc.stderr or slang_version_proc.stdout).strip()}"
        )
    observed_slang = first_line(slang_version_proc.stdout + "\n" + slang_version_proc.stderr)
    if observed_slang != str(slang["version"]):
        raise CaptureError(f"Slang version mismatch: expected {slang['version']}, observed {observed_slang!r}")
    if not slang_lib.is_file():
        raise CaptureError(f"Slang compiler library missing: {slang_lib}")
    add("pin.slang.version", slang["version"])
    add("pin.slang.release_commit", slang["release_commit"])
    add("pin.slang.artifact", slang["artifact"])
    add("pin.slang.artifact_sha256", slang["artifact_sha256"])
    add("pin.slang.license", slang["license"])
    add("observed.slang.slangc_sha256", sha256_file(slangc))
    add("observed.slang.libslang_so_sha256", sha256_file(slang_lib))

    # Jolt exact accepted pin + independent tree identity recomputation.
    jolt_root = repo / "third_party/JoltPhysics"
    jolt_manifest_path = jolt_root / "UFOAI_VENDOR_MANIFEST.txt"
    jolt_values = read_jolt_vendor_manifest(jolt_manifest_path)
    expected_markers = {
        "release_tag": str(jolt["release_tag"]),
        "commit_sha": str(jolt["commit"]),
        "license_identifier": str(jolt["license"]),
        "sorted_file_manifest_blake3_256": str(jolt["vendor_blake3_256"]),
        "local_patch_list": str(jolt["local_patch_list"]),
    }
    for marker, expected in expected_markers.items():
        observed = jolt_values.get(marker)
        if observed != expected:
            raise CaptureError(f"Jolt vendor marker mismatch for {marker}: expected {expected!r}, observed {observed!r}")
    recomputed = b3sum_jolt_tree(jolt_root)
    if recomputed != str(jolt["vendor_blake3_256"]):
        raise CaptureError(
            f"Jolt vendor tree BLAKE3 mismatch: expected {jolt['vendor_blake3_256']}, recomputed {recomputed}"
        )
    add("pin.jolt.version", jolt["version"])
    add("pin.jolt.release_tag", jolt["release_tag"])
    add("pin.jolt.commit", jolt["commit"])
    add("pin.jolt.license", jolt["license"])
    add("pin.jolt.local_patch_list", jolt["local_patch_list"])
    add("pin.jolt.vendor_blake3_256", jolt["vendor_blake3_256"])
    add("observed.jolt.vendor_manifest_sha256", sha256_file(jolt_manifest_path))
    add("observed.jolt.vendor_tree_blake3_256", recomputed)

    # pkg-config API identities used by the M0 dependency gate.
    modules = ["sdl3", "openal", "libavcodec", "libavformat", "libavutil", "libswresample", "libswscale"]
    for module in modules:
        proc = run(["pkg-config", "--modversion", module], check=False)
        if proc.returncode != 0:
            raise CaptureError(f"required pkg-config module missing: {module}")
        add(f"pkg_config.{module}.version", first_line(proc.stdout))

    # Stable final newline is part of the manifest hash contract.
    return "\n".join(lines) + "\n"


def find_repo_root(start: Path) -> Path:
    proc = run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], check=False)
    if proc.returncode != 0:
        raise CaptureError("run this tool from inside the UFO:AI Remaster Git checkout")
    return Path(proc.stdout.strip()).resolve()


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def sidecar_for(output: Path) -> Path:
    return output.with_suffix(".b3")


def verify_existing(output: Path, generated: bytes) -> None:
    sidecar = sidecar_for(output)
    if not output.is_file() or not sidecar.is_file():
        raise CaptureError(f"manifest or BLAKE3 sidecar missing: {output}, {sidecar}")
    existing = output.read_bytes()
    if existing != generated:
        old = existing.decode("utf-8", "replace").splitlines()
        new = generated.decode("utf-8", "replace").splitlines()
        diff = "\n".join(
            difflib.unified_diff(old, new, fromfile=str(output), tofile=str(output) + " (current)", lineterm="")
        )
        raise CaptureError("reference environment drift detected:\n" + diff)
    expected_hash = sidecar.read_text(encoding="utf-8").strip().split()[0]
    actual_hash = b3sum_bytes(existing)
    if expected_hash != actual_hash:
        raise CaptureError(f"manifest BLAKE3 sidecar mismatch: expected {expected_hash}, actual {actual_hash}")
    print(f"M0.3 reference manifest verification: PASS ({actual_hash})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"manifest path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--verify", action="store_true", help="compare current reference environment against the committed manifest")
    args = parser.parse_args()

    try:
        repo = find_repo_root(Path.cwd())
        output = args.output
        if not output.is_absolute():
            output = repo / output
        generated_text = manifest_text(repo)
        generated = generated_text.encode("utf-8")
        digest = b3sum_bytes(generated)
        sidecar = sidecar_for(output)

        if args.verify:
            verify_existing(output, generated)
            return 0

        write_atomic(output, generated)
        sidecar_text = f"{digest}  {output.name}\n".encode("utf-8")
        write_atomic(sidecar, sidecar_text)
        print(f"M0.3 reference manifest capture: PASS")
        print(f"manifest: {output.relative_to(repo)}")
        print(f"BLAKE3-256: {digest}")
        print(f"sidecar:  {sidecar.relative_to(repo)}")
        return 0
    except CaptureError as exc:
        print(f"M0.3 reference manifest capture: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
