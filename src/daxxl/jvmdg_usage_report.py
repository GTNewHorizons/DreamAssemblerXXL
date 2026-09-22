#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

JVMDG_PREFIX = "xyz/wagyourtail/jvmdg/"
DESCRIPTOR_REFERENCE = re.compile(r"L(xyz/wagyourtail/jvmdg/[A-Za-z0-9_$/]+)")
DOTTED_REFERENCE = re.compile(r"(?<![A-Za-z0-9_$.])xyz\.wagyourtail\.jvmdg(?:\.[A-Za-z0-9_$]+)+")
MULTI_RELEASE_PREFIX = re.compile(r"^META-INF/versions/\d+/")
MEMBER_KINDS = {9: "field", 10: "method", 11: "interface-method"}

ConstantValue = str | int | tuple[int, int] | None
ConstantPoolEntry = tuple[int, ConstantValue]


@dataclass
class ArchiveScan:
    class_count: int = 0
    classes: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    members: dict[tuple[str, str, str, str], set[str]] = field(default_factory=lambda: defaultdict(set))
    dynamic: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))


@dataclass
class ArchiveGroup:
    path: Path
    locations: set[str] = field(default_factory=set)


def _u2(data: bytes, offset: int) -> tuple[int, int]:
    if offset + 2 > len(data):
        raise ValueError("truncated class file")
    return struct.unpack_from(">H", data, offset)[0], offset + 2


def _constant_pool(data: bytes) -> list[ConstantPoolEntry | None]:
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("invalid class file header")

    count = struct.unpack_from(">H", data, 8)[0]
    entries: list[ConstantPoolEntry | None] = [None] * count
    offset = 10
    index = 1

    while index < count:
        if offset >= len(data):
            raise ValueError("truncated constant pool")
        tag = data[offset]
        offset += 1

        if tag == 1:
            length, offset = _u2(data, offset)
            if offset + length > len(data):
                raise ValueError("truncated UTF-8 constant")
            entries[index] = (tag, data[offset : offset + length].decode("utf-8", errors="replace"))
            offset += length
        elif tag in {3, 4}:
            offset += 4
            entries[index] = (tag, None)
        elif tag in {5, 6}:
            offset += 8
            entries[index] = (tag, None)
            index += 1
        elif tag in {7, 8, 16, 19, 20}:
            value, offset = _u2(data, offset)
            entries[index] = (tag, value)
        elif tag in {9, 10, 11, 12, 17, 18}:
            first, offset = _u2(data, offset)
            second, offset = _u2(data, offset)
            entries[index] = (tag, (first, second))
        elif tag == 15:
            if offset >= len(data):
                raise ValueError("truncated method handle")
            kind = data[offset]
            reference, offset = _u2(data, offset + 1)
            entries[index] = (tag, (kind, reference))
        else:
            raise ValueError(f"unsupported constant pool tag {tag}")

        if offset > len(data):
            raise ValueError("truncated constant pool entry")
        index += 1

    return entries


def _utf8(entries: list[ConstantPoolEntry | None], index: int) -> str | None:
    if index <= 0 or index >= len(entries):
        return None
    entry = entries[index]
    return entry[1] if entry is not None and entry[0] == 1 and isinstance(entry[1], str) else None


def _class_name(entries: list[ConstantPoolEntry | None], index: int) -> str | None:
    if index <= 0 or index >= len(entries):
        return None
    entry = entries[index]
    return _utf8(entries, entry[1]) if entry is not None and entry[0] == 7 and isinstance(entry[1], int) else None


def scan_class(data: bytes) -> tuple[set[str], set[tuple[str, str, str, str]], set[str]]:
    entries = _constant_pool(data)
    classes: set[str] = set()
    members: set[tuple[str, str, str, str]] = set()
    dynamic: set[str] = set()

    for entry in entries:
        if entry is None:
            continue
        tag, value = entry
        if tag == 7 and isinstance(value, int):
            name = _utf8(entries, value)
            if name is not None:
                if name.startswith(JVMDG_PREFIX):
                    classes.add(name)
                classes.update(DESCRIPTOR_REFERENCE.findall(name))
        elif tag in MEMBER_KINDS and isinstance(value, tuple):
            owner = _class_name(entries, value[0])
            name_and_type = entries[value[1]] if 0 < value[1] < len(entries) else None
            if owner is None or not owner.startswith(JVMDG_PREFIX) or name_and_type is None or name_and_type[0] != 12:
                continue
            name_and_type_value = name_and_type[1]
            if not isinstance(name_and_type_value, tuple):
                continue
            name_index, descriptor_index = name_and_type_value
            name = _utf8(entries, name_index)
            descriptor = _utf8(entries, descriptor_index)
            if name is not None and descriptor is not None:
                members.add((MEMBER_KINDS[tag], owner, name, descriptor))
        elif tag == 8 and isinstance(value, int):
            text = _utf8(entries, value)
            if text is not None:
                dynamic.update(DOTTED_REFERENCE.findall(text))
                if text.startswith(JVMDG_PREFIX):
                    dynamic.add(text)

    for entry in entries:
        if entry is not None and entry[0] == 1 and isinstance(entry[1], str):
            classes.update(DESCRIPTOR_REFERENCE.findall(entry[1]))

    return classes, members, dynamic


def scan_archive(path: Path) -> ArchiveScan:
    result = ArchiveScan()
    with ZipFile(path) as archive:
        for entry in sorted(archive.infolist(), key=lambda item: item.filename):
            logical_name = MULTI_RELEASE_PREFIX.sub("", entry.filename)
            if entry.is_dir() or not logical_name.endswith(".class") or logical_name.startswith(JVMDG_PREFIX):
                continue
            consumer = logical_name.removesuffix(".class").replace("/", ".")
            classes, members, dynamic = scan_class(archive.read(entry))
            result.class_count += 1
            for target in classes:
                result.classes[target].add(consumer)
            for target in members:
                result.members[target].add(consumer)
            for target in dynamic:
                result.dynamic[target].add(consumer)
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inputs(values: list[str]) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    for value in values:
        label, separator, raw_path = value.partition("=")
        if not separator or not label or not raw_path:
            raise ValueError(f"input must be LABEL=PATH: {value}")
        roots.append((label, Path(raw_path)))
    return roots


def _archives(roots: list[tuple[str, Path]]) -> tuple[dict[Path, set[str]], list[str]]:
    found: dict[Path, set[str]] = defaultdict(set)
    errors: list[str] = []
    for label, root in roots:
        if not root.exists():
            errors.append(f"missing input: {label}={root}")
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*.jar"))
        has_archive = False
        for path in paths:
            if not path.is_file() or path.suffix.lower() != ".jar":
                continue
            resolved = path.resolve()
            has_archive = True
            relative = path.name if root.is_file() else path.relative_to(root).as_posix()
            found[resolved].add(f"{label}/{relative}")
        if not has_archive:
            errors.append(f"no JAR files found in input: {label}={root}")
    if not found:
        errors.append("no JAR files found")
    return found, errors


def build_report(build_id: str, java_target: str, roots: list[tuple[str, Path]]) -> dict[str, Any]:
    archive_paths, errors = _archives(roots)
    by_digest: dict[str, ArchiveGroup] = {}
    for path, locations in archive_paths.items():
        try:
            digest = _sha256(path)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
            continue
        record = by_digest.setdefault(digest, ArchiveGroup(path))
        record.locations.update(locations)

    class_references: dict[str, set[tuple[str, str]]] = defaultdict(set)
    member_references: dict[tuple[str, str, str, str], set[tuple[str, str]]] = defaultdict(set)
    dynamic_references: dict[str, set[tuple[str, str]]] = defaultdict(set)
    archive_records: list[dict[str, object]] = []
    classes_scanned = 0

    for digest, record in sorted(by_digest.items()):
        locations = sorted(record.locations)
        try:
            scan = scan_archive(record.path)
        except (BadZipFile, EOFError, OSError, RuntimeError, ValueError, zlib.error) as exc:
            errors.append(f"{', '.join(locations)}: {exc}")
            continue

        classes_scanned += scan.class_count
        archive_records.append({"sha256": digest, "locations": locations, "classes_scanned": scan.class_count})
        for target, consumers in scan.classes.items():
            class_references[target].update((digest, consumer) for consumer in consumers)
        for target, consumers in scan.members.items():
            member_references[target].update((digest, consumer) for consumer in consumers)
        for target, consumers in scan.dynamic.items():
            dynamic_references[target].update((digest, consumer) for consumer in consumers)

    def consumers(values: set[tuple[str, str]]) -> list[dict[str, str]]:
        return [{"archive_sha256": digest, "class": consumer} for digest, consumer in sorted(values)]

    return {
        "schema_version": 1,
        "analysis": "conservative constant-pool roots; provider classes under the exact JvmDowngrader prefix are excluded",
        "build_id": build_id,
        "java_target": java_target,
        "inputs": [label for label, _ in roots],
        "stats": {
            "unique_archives_scanned": len(archive_records),
            "classes_scanned": classes_scanned,
            "referenced_classes": len(class_references),
            "referenced_members": len(member_references),
            "possible_dynamic_references": len(dynamic_references),
            "errors": len(errors),
        },
        "archives": archive_records,
        "class_references": [{"class": target.replace("/", "."), "consumers": consumers(values)} for target, values in sorted(class_references.items())],
        "member_references": [
            {
                "kind": target[0],
                "owner": target[1].replace("/", "."),
                "name": target[2],
                "descriptor": target[3],
                "consumers": consumers(values),
            }
            for target, values in sorted(member_references.items())
        ],
        "possible_dynamic_references": [{"value": target, "consumers": consumers(values)} for target, values in sorted(dynamic_references.items())],
        "errors": sorted(errors),
    }


def markdown_summary(report: dict[str, Any]) -> str:
    stats = report["stats"]
    lines = [
        f"## JvmDowngrader usage report — target Java {report['java_target']}",
        "",
        f"Build: `{report['build_id']}`",
        "",
        f"Scanned {stats['unique_archives_scanned']} unique JARs and {stats['classes_scanned']} classes; "
        f"found {stats['referenced_classes']} API classes, {stats['referenced_members']} API members, "
        f"and {stats['possible_dynamic_references']} possible dynamic references.",
        "",
        "Conservative static references, not runtime usage. All multi-release class variants are scanned; "
        "the Java target labels the pack variant and does not filter class entries.",
    ]
    if stats["errors"]:
        lines.extend(["", f"Warning: {stats['errors']} inputs could not be scanned; see the JSON report."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report references to the shared JvmDowngrader runtime API from finalized GTNH JARs.")
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--java-target", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--input", action="append", required=True, metavar="LABEL=PATH")
    args = parser.parse_args()

    try:
        roots = _inputs(args.input)
    except ValueError as exc:
        parser.error(str(exc))

    report = build_report(args.build_id, args.java_target, roots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(markdown_summary(report), end="")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
