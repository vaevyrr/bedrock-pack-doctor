#!/usr/bin/env python3
"""Read-only checks for Minecraft Bedrock pack folders and ZIP-based archives."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable
from uuid import UUID

@dataclass
class Finding:
    level: str
    path: str
    message: str

class PackDoctor:
    def __init__(self) -> None:
        self.findings: list[Finding] = []
        self.files: dict[str, bytes] = {}

    def add(self, level: str, path: str, message: str) -> None:
        self.findings.append(Finding(level, path, message))

    def scan(self, target: Path) -> None:
        if target.is_dir():
            for item in target.rglob("*"):
                if item.is_file():
                    try:
                        self.files[item.relative_to(target).as_posix()] = item.read_bytes()
                    except OSError as exc:
                        self.add("error", str(item), f"Could not read file: {exc}")
        elif target.is_file() and zipfile.is_zipfile(target):
            with zipfile.ZipFile(target) as archive:
                bad_member = archive.testzip()
                if bad_member:
                    self.add("error", bad_member, "CRC check failed")
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    name = PurePosixPath(info.filename)
                    if name.is_absolute() or ".." in name.parts:
                        self.add("error", info.filename, "Unsafe path in archive")
                        continue
                    try:
                        self.files[name.as_posix()] = archive.read(info)
                    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
                        self.add("error", info.filename, f"Could not read member: {exc}")
        else:
            raise ValueError("Input must be a folder or a readable ZIP-based .mcpack/.mcaddon file")
        self.check_manifest()
        self.check_json()
        self.check_references()

    def check_manifest(self) -> None:
        raw = self.files.get("manifest.json")
        if raw is None:
            self.add("error", "manifest.json", "No manifest.json at the pack root")
            return
        try:
            manifest = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.add("error", "manifest.json", f"Invalid JSON: {exc}")
            return
        if not isinstance(manifest, dict):
            self.add("error", "manifest.json", "Manifest root must be an object")
            return
        for key in ("format_version", "header", "modules"):
            if key not in manifest:
                self.add("error", "manifest.json", f"Missing required field: {key}")
        header = manifest.get("header")
        if not isinstance(header, dict):
            self.add("error", "manifest.json", "header must be an object")
            return
        for key in ("name", "description", "uuid", "version"):
            if key not in header:
                self.add("error", "manifest.json", f"header is missing {key}")
        modules = manifest.get("modules", [])
        if not isinstance(modules, list):
            self.add("error", "manifest.json", "modules must be an array")
            modules = []
        seen: dict[str, str] = {}
        entries = [("header", header)] + [
            (f"modules[{i}]", item) for i, item in enumerate(modules) if isinstance(item, dict)
        ]
        for label, item in entries:
            value = item.get("uuid")
            if value:
                try:
                    normalized = str(UUID(str(value)))
                except (ValueError, TypeError, AttributeError):
                    self.add("error", "manifest.json", f"{label}.uuid is not a valid UUID")
                else:
                    if normalized in seen:
                        self.add("error", "manifest.json", f"Duplicate UUID: {label} matches {seen[normalized]}")
                    else:
                        seen[normalized] = label
            version = item.get("version")
            if version is not None and (
                not isinstance(version, list) or len(version) != 3
                or any(not isinstance(n, int) or n < 0 for n in version)
            ):
                self.add("error", "manifest.json", f"{label}.version must be three non-negative integers")

    def check_json(self) -> None:
        for name, raw in self.files.items():
            if not name.lower().endswith(".json"):
                continue
            try:
                json.loads(raw.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.add("error", name, f"Invalid JSON: {exc}")

    def check_references(self) -> None:
        keys = {"texture", "textures", "geometry", "render_controller", "particle_effect"}
        for name, raw in self.files.items():
            if not name.lower().endswith(".json"):
                continue
            try:
                data = json.loads(raw.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            refs: list[str] = []
            def walk(value: object, parent: str = "") -> None:
                if isinstance(value, dict):
                    for key, child in value.items():
                        walk(child, str(key).lower())
                elif isinstance(value, list):
                    for child in value:
                        walk(child, parent)
                elif isinstance(value, str) and parent in keys:
                    refs.append(value)
            walk(data)
            for ref in refs:
                candidate = ref.replace("\\", "/").lstrip("/")
                if candidate.startswith(("textures/", "models/", "particles/")):
                    possible = (candidate, candidate + ".png", candidate + ".json")
                    if not any(path in self.files for path in possible):
                        self.add("warning", name, f"Referenced asset not found: {ref}")

    def report(self) -> dict:
        counts = {level: sum(f.level == level for f in self.findings)
                  for level in ("error", "warning", "info")}
        return {"summary": counts, "findings": [asdict(f) for f in self.findings]}

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a Bedrock pack without changing it.")
    parser.add_argument("target", type=Path, help=".mcpack/.mcaddon archive or extracted folder")
    parser.add_argument("--json", dest="json_path", type=Path, help="write a JSON report")
    args = parser.parse_args(argv)
    doctor = PackDoctor()
    try:
        doctor.scan(args.target)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Could not scan {args.target}: {exc}", file=sys.stderr)
        return 2
    report = doctor.report()
    for finding in doctor.findings:
        print(f"[{finding.level.upper()}] {finding.path}: {finding.message}")
    summary = report["summary"]
    print(f"\n{summary['error']} error(s), {summary['warning']} warning(s)")
    if args.json_path:
        try:
            args.json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"Could not write report: {exc}", file=sys.stderr)
            return 2
    return 1 if summary["error"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
