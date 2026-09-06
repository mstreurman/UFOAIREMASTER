#!/usr/bin/env python3
"""Provision the exact M0 Slang tool cache from committed repository pins."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

RELEASE_BASE = "https://github.com/shader-slang/slang/releases/download"
PIN_REL = Path("tools/remaster/m0-pins.json")
MANIFEST_REL = Path("docs/reference/reference-m0-environment-manifest.txt")


class ProvisionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def repo_root(start: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise ProvisionError(f"not inside a Git checkout: {start}")
    return Path(proc.stdout.strip()).resolve()


def load_pin(repo: Path) -> tuple[str, str, str, str, str]:
    pins_path = repo / PIN_REL
    manifest_path = repo / MANIFEST_REL
    try:
        pins = json.loads(pins_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProvisionError(f"cannot read committed pins {pins_path}: {exc}") from exc
    if pins.get("schema") != 1:
        raise ProvisionError("unsupported m0-pins.json schema")
    slang = pins.get("slang")
    if not isinstance(slang, dict):
        raise ProvisionError("m0-pins.json has no Slang pin")

    version = str(slang.get("version", ""))
    artifact = str(slang.get("artifact", ""))
    artifact_sha = str(slang.get("artifact_sha256", ""))
    if version != "2026.17":
        raise ProvisionError(f"unexpected Slang version pin: {version!r}")
    expected_artifact = "slang-2026.17-linux-x86_64-glibc-2.28.tar.gz"
    if artifact != expected_artifact:
        raise ProvisionError(f"unexpected Slang artifact pin: {artifact!r}")
    if len(artifact_sha) != 64:
        raise ProvisionError("Slang artifact SHA-256 pin is malformed")

    manifest = parse_kv(manifest_path)
    if manifest.get("pin.slang.version") != version:
        raise ProvisionError("M0 environment manifest Slang version disagrees with m0-pins.json")
    if manifest.get("pin.slang.artifact") != artifact:
        raise ProvisionError("M0 environment manifest Slang artifact disagrees with m0-pins.json")
    if manifest.get("pin.slang.artifact_sha256") != artifact_sha:
        raise ProvisionError("M0 environment manifest Slang SHA-256 disagrees with m0-pins.json")

    slangc_sha = manifest.get("observed.slang.slangc_sha256", "")
    lib_sha = manifest.get("observed.slang.libslang_so_sha256", "")
    if len(slangc_sha) != 64 or len(lib_sha) != 64:
        raise ProvisionError("M0 environment manifest lacks accepted Slang binary identities")
    return version, artifact, artifact_sha, slangc_sha, lib_sha


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    if partial.exists():
        partial.unlink()
    request = urllib.request.Request(url, headers={"User-Agent": "UFOAIREMASTER-M0-clean-bootstrap/1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as out:
            if response.status != 200:
                raise ProvisionError(f"Slang download returned HTTP {response.status}")
            shutil.copyfileobj(response, out, length=1024 * 1024)
    except Exception as exc:
        if partial.exists():
            partial.unlink()
        if isinstance(exc, ProvisionError):
            raise
        raise ProvisionError(f"Slang download failed: {exc}") from exc
    os.replace(partial, dest)


def distribution_root(extracted: Path) -> Path:
    candidates: list[Path] = []
    for slangc in extracted.rglob("slangc"):
        if slangc.name != "slangc" or slangc.parent.name != "bin":
            continue
        root = slangc.parent.parent
        required = (
            root / "include/slang.h",
            root / "include/slang-com-ptr.h",
            root / "lib/libslang.so",
        )
        if all(p.is_file() for p in required):
            candidates.append(root)
    unique = sorted({p.resolve() for p in candidates}, key=lambda p: (len(p.parts), str(p)))
    if len(unique) != 1:
        raise ProvisionError(
            f"expected exactly one Slang distribution root after extraction, found {len(unique)}"
        )
    return unique[0]


def verify_distribution(dest: Path, version: str, slangc_sha: str, lib_sha: str) -> None:
    slangc = dest / "bin/slangc"
    header = dest / "include/slang.h"
    comptr = dest / "include/slang-com-ptr.h"
    library = dest / "lib/libslang.so"
    for path in (slangc, header, comptr, library):
        if not path.is_file():
            raise ProvisionError(f"provisioned Slang file missing: {path}")
    if not os.access(slangc, os.X_OK):
        raise ProvisionError(f"provisioned Slang compiler is not executable: {slangc}")
    actual_slangc = sha256_file(slangc)
    actual_lib = sha256_file(library)
    if actual_slangc != slangc_sha:
        raise ProvisionError(f"slangc SHA-256 mismatch: expected {slangc_sha}, got {actual_slangc}")
    if actual_lib != lib_sha:
        raise ProvisionError(f"libslang.so SHA-256 mismatch: expected {lib_sha}, got {actual_lib}")

    env = os.environ.copy()
    old_ld = env.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = str(dest / "lib") + ((":" + old_ld) if old_ld else "")
    proc = subprocess.run(
        [str(slangc), "-version"], env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    observed = next((ln.strip() for ln in proc.stdout.splitlines() if ln.strip()), "")
    if proc.returncode != 0 or observed != version:
        raise ProvisionError(
            f"provisioned slangc version mismatch: expected {version!r}, got {observed!r}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, help="target checkout (default: current Git checkout)")
    parser.add_argument("--archive", type=Path, help="use this local tarball instead of downloading")
    parser.add_argument("--fresh-download", action="store_true", help="discard any cached tarball and download again")
    parser.add_argument("--force", action="store_true", help="replace an existing tools/slang/v2026.17 cache")
    args = parser.parse_args()

    try:
        repo = repo_root((args.repo or Path.cwd()).resolve())
        version, artifact, artifact_sha, slangc_sha, lib_sha = load_pin(repo)
        dest = repo / "tools/slang" / f"v{version}"

        if dest.exists() and not args.force:
            verify_distribution(dest, version, slangc_sha, lib_sha)
            print(f"M0 Slang provisioning: PASS (existing v{version} cache verified)")
            return 0
        if dest.exists():
            shutil.rmtree(dest)

        if args.archive:
            archive = args.archive.resolve()
            if not archive.is_file():
                raise ProvisionError(f"local Slang archive not found: {archive}")
            source = "local-verified-archive"
        else:
            cache_dir = repo / "tools/slang/.downloads"
            archive = cache_dir / artifact
            if args.fresh_download and archive.exists():
                archive.unlink()
            url = f"{RELEASE_BASE}/v{version}/{artifact}"
            if not archive.is_file():
                print(f"Downloading pinned Slang v{version}: {url}", flush=True)
                download(url, archive)
            source = url

        actual_archive_sha = sha256_file(archive)
        if actual_archive_sha != artifact_sha:
            raise ProvisionError(
                f"Slang archive SHA-256 mismatch: expected {artifact_sha}, got {actual_archive_sha}"
            )
        print(f"Slang archive SHA-256: PASS ({actual_archive_sha})", flush=True)

        extract_parent = repo / "tools/slang"
        extract_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".extract-slang-", dir=extract_parent) as tmp_name:
            tmp = Path(tmp_name)
            try:
                with tarfile.open(archive, mode="r:gz") as tf:
                    tf.extractall(tmp, filter="data")
            except (tarfile.TarError, OSError) as exc:
                raise ProvisionError(f"cannot extract Slang archive: {exc}") from exc
            root = distribution_root(tmp)
            shutil.copytree(root, dest, symlinks=True)

        verify_distribution(dest, version, slangc_sha, lib_sha)
        provenance = {
            "schema": 1,
            "version": version,
            "artifact": artifact,
            "artifact_sha256": artifact_sha,
            "source": source,
            "slangc_sha256": slangc_sha,
            "libslang_so_sha256": lib_sha,
        }
        (dest / ".ufoai-provision.json").write_text(
            json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(f"M0 Slang provisioning: PASS (v{version}, exact committed artifact)")
        print(f"destination: {dest}")
        return 0
    except ProvisionError as exc:
        print(f"M0 Slang provisioning: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
