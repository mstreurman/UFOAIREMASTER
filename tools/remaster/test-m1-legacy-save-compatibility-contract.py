#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BASELINE_REVISION = "cefabf0ef5686b76921f10418dcb19a02152ade3"


class GateError(RuntimeError):
    pass


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def require_baseline(root: Path) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_REVISION, "HEAD"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    if proc.returncode != 0:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        ).stdout.strip()
        raise GateError(f"HEAD {head} is not a descendant of compatibility baseline {BASELINE_REVISION}")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def require_token(text: str, token: str, what: str) -> None:
    if token not in text:
        raise GateError(f"{what}: missing {token!r}")


def main() -> int:
    root = repo_root()
    require_baseline(root)

    cp_save_h = (root / "src/client/cgame/campaign/cp_save.h").read_text(encoding="utf-8")
    save_h = (root / "src/client/cgame/campaign/save/save.h").read_text(encoding="utf-8")
    cp_save_cpp = (root / "src/client/cgame/campaign/cp_save.cpp").read_text(encoding="utf-8")

    require_token(cp_save_h, "#define SAVE_FILE_VERSION 4", "save version ABI")
    require_token(cp_save_h, '#define SAVEGAME_EXTENSION "savx"', "save extension ABI")
    require_token(save_h, '#define SAVE_ROOTNODE "savegame"', "save XML root ABI")

    clean = strip_comments(cp_save_h)
    match = re.search(r"typedef\s+struct\s+saveFileHeader_s\s*\{(.*?)\}\s*saveFileHeader_t\s*;", clean, re.S)
    if not match:
        raise GateError("saveFileHeader_t declaration not found")
    body = re.sub(r"\s+", " ", match.group(1)).strip()

    expected_fields = [
        r"uint32_t\s+version\s*;",
        r"uint32_t\s+compressed\s*;",
        r"uint32_t\s+subsystems\s*;",
        r"uint32_t\s+dummy\s*\[\s*13\s*\]\s*;",
        r"char\s+gameVersion\s*\[\s*16\s*\]\s*;",
        r"char\s+name\s*\[\s*32\s*\]\s*;",
        r"char\s+gameDate\s*\[\s*32\s*\]\s*;",
        r"char\s+realDate\s*\[\s*32\s*\]\s*;",
        r"uint32_t\s+xmlSize\s*;",
    ]
    pos = 0
    for pattern in expected_fields:
        m = re.search(pattern, body[pos:])
        if not m:
            raise GateError(f"saveFileHeader_t field/layout anchor missing or reordered: {pattern}")
        if m.start() != 0:
            prefix = body[pos:pos + m.start()].strip()
            if prefix:
                raise GateError(f"unexpected saveFileHeader_t declaration before {pattern}: {prefix}")
        pos += m.end()
        body = body[:pos] + body[pos:].lstrip()
    if body[pos:].strip():
        raise GateError(f"unexpected extra saveFileHeader_t fields: {body[pos:].strip()}")

    for token in (
        "SAVEGAME_EXTENSION",
        "SAVE_FILE_VERSION",
        "SAVE_ROOTNODE",
        "SAV_GameLoad",
        "SAV_GameSave",
    ):
        require_token(cp_save_cpp, token, "shared canonical save owner")

    for forbidden in (
        "#ifdef UFOAI_REMASTER",
        "#if defined(UFOAI_REMASTER",
        "presentation/",
        "canonical::ProductionId",
        "canonical::StoredUfoId",
        "RemasterSave",
        "remasterSave",
    ):
        if forbidden in cp_save_cpp or forbidden in cp_save_h:
            raise GateError(f"remaster-specific state/fork leaked into canonical save owner: {forbidden}")

    # Runtime-only presentation identity must not gain a canonical save tag.
    campaign_save_tree = root / "src/client/cgame/campaign"
    forbidden_save_tokens = (
        "SAVE_PRODUCTION_RUNTIMEID",
        "SAVE_PRESENTATION_ID",
        "SAVE_RENDER_ID",
        "SAVE_VULKAN",
        "SAVE_JOLT",
    )
    for path in campaign_save_tree.rglob("*"):
        if path.suffix not in {".h", ".cpp", ".c"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_save_tokens:
            if token in text:
                raise GateError(f"remaster/runtime-only save token leaked into {path.relative_to(root)}: {token}")

    print("PASS legacy save compatibility contract")
    print("  SAVE_FILE_VERSION: 4")
    print("  extension/root: savx / savegame")
    print("  saveFileHeader_t source layout: locked")
    print("  shared canonical serializer ownership: locked")
    print("  remaster-only save fork/state leakage audit: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"FAIL legacy save compatibility contract: {exc}", file=sys.stderr)
        raise SystemExit(1)
