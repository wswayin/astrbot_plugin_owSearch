from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .renderers import render_all_players_image, render_match_detail_image, save_image
from .services.sample_data import build_sample_match_detail


@dataclass
class CheckResult:
    name: str
    ok: bool
    message: str = ""


@dataclass
class SelfCheckReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(result.ok for result in self.results)

    def add(self, name: str, ok: bool, message: str = "") -> None:
        self.results.append(CheckResult(name=name, ok=ok, message=message))

    def to_text(self) -> str:
        lines = ["OW Search self-check"]
        for result in self.results:
            status = "OK" if result.ok else "FAIL"
            suffix = f" - {result.message}" if result.message else ""
            lines.append(f"[{status}] {result.name}{suffix}")
        lines.append(f"result: {'OK' if self.ok else 'FAIL'}")
        return "\n".join(lines)


def _check_imports(report: SelfCheckReport) -> None:
    for module_name in ("httpx", "PIL", "zoneinfo"):
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            report.add(f"import {module_name}", False, f"{type(exc).__name__}: {exc}")
        else:
            report.add(f"import {module_name}", True)


def _check_files(report: SelfCheckReport, root: Path) -> None:
    required = ["main.py", "metadata.yaml", "_conf_schema.json", "requirements.txt", "README.md"]
    for relative in required:
        path = root / relative
        report.add(f"file {relative}", path.exists(), "missing" if not path.exists() else "")


def _check_schema(report: SelfCheckReport, root: Path) -> None:
    path = root / "_conf_schema.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.add("config schema JSON", False, f"{type(exc).__name__}: {exc}")
        return
    for key in ("dashen", "ai", "render"):
        report.add(f"config schema {key}", key in data, "missing" if key not in data else "")


async def _check_render(report: SelfCheckReport) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        detail = build_sample_match_detail()
        output_dir = Path(temp_dir)
        images = (
            render_match_detail_image(detail),
            render_all_players_image(detail),
        )
        saved = [save_image(image, output_dir, prefix=f"self_check_{index}", max_bytes=5 * 1024 * 1024) for index, image in enumerate(images, 1)]
        report.add("local render reply count", len(saved) == 2, f"got {len(saved)} image files")
        for index, item in enumerate(saved, 1):
            path = item.path
            ok = path.exists() and path.stat().st_size > 1000
            size = path.stat().st_size if path.exists() else 0
            report.add(f"local render image {index}", ok, f"{size} bytes")


def _check_text(report: SelfCheckReport, root: Path) -> None:
    checks: Iterable[tuple[str, str, str]] = (
        ("main alias", "main.py", "守望"),
        ("README courtroom", "README.md", "/ow 开庭"),
        ("README self debug", "README.md", "/ow debug 图片"),
        ("schema dashen", "_conf_schema.json", "网易大神"),
    )
    for name, relative, needle in checks:
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            report.add(name, False, f"{type(exc).__name__}: {exc}")
            continue
        report.add(name, needle in text, f"missing {needle!r}" if needle not in text else "")


async def run_self_check(root: Path | None = None) -> SelfCheckReport:
    root = (root or Path(__file__).resolve().parents[1]).resolve()
    report = SelfCheckReport()
    _check_imports(report)
    _check_files(report, root)
    _check_schema(report, root)
    _check_text(report, root)
    await _check_render(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local self-checks for astrbot_plugin_owSearch.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    report = asyncio.run(run_self_check(args.root))
    print(report.to_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
