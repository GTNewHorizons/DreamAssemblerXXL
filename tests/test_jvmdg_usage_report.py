import json
import struct
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from daxxl.jvmdg_usage_report import build_report, main, markdown_summary, scan_archive


def _utf8(value: str) -> bytes:
    encoded = value.encode()
    return b"\x01" + struct.pack(">H", len(encoded)) + encoded


def _pair(tag: int, first: int, second: int) -> bytes:
    return bytes([tag]) + struct.pack(">HH", first, second)


def _class_file() -> bytes:
    entries = [
        _utf8("example/Consumer"),
        b"\x07\x00\x01",
        _utf8("xyz/wagyourtail/jvmdg/j9/stub/J_U_Foo"),
        b"\x07\x00\x03",
        _utf8("run"),
        _utf8("()V"),
        _pair(12, 5, 6),
        _pair(10, 4, 7),
        _utf8("(Lxyz/wagyourtail/jvmdg/j9/stub/J_U_Bar;)V"),
        _utf8("xyz.wagyourtail.jvmdg.dynamic.Loader"),
        b"\x08\x00\x0a",
        _utf8("relocated.xyz.wagyourtail.jvmdg.dynamic.Ignored"),
        b"\x08\x00\x0c",
        _utf8("Lrelocated/xyz/wagyourtail/jvmdg/Ignored;"),
        b"\x07\x00\x0e",
    ]
    return b"\xca\xfe\xba\xbe" + struct.pack(">HHH", 0, 52, len(entries) + 1) + b"".join(entries)


def test_scans_direct_member_descriptor_and_dynamic_references(tmp_path: Path) -> None:
    jar = tmp_path / "consumer.jar"
    with ZipFile(jar, "w") as archive:
        archive.writestr("example/Consumer.class", _class_file())
        archive.writestr("xyz/wagyourtail/jvmdg/IgnoredProvider.class", b"not a class")

    result = scan_archive(jar)

    assert result.class_count == 1
    assert result.classes == {
        "xyz/wagyourtail/jvmdg/j9/stub/J_U_Bar": {"example.Consumer"},
        "xyz/wagyourtail/jvmdg/j9/stub/J_U_Foo": {"example.Consumer"},
    }
    assert result.members == {("method", "xyz/wagyourtail/jvmdg/j9/stub/J_U_Foo", "run", "()V"): {"example.Consumer"}}
    assert result.dynamic == {"xyz.wagyourtail.jvmdg.dynamic.Loader": {"example.Consumer"}}


def test_corrupt_deflate_preserves_healthy_results_and_writes_failed_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with ZipFile(tmp_path / "healthy.jar", "w") as archive:
        archive.writestr("example/Consumer.class", _class_file())
    corrupt = tmp_path / "corrupt.jar"
    with ZipFile(corrupt, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("example/Consumer.class", _class_file())
    data = bytearray(corrupt.read_bytes())
    name_length, extra_length = struct.unpack_from("<HH", data, 26)
    data[30 + name_length + extra_length] = 0x07  # Final DEFLATE block with reserved block type.
    corrupt.write_bytes(data)
    with pytest.raises(zlib.error):
        scan_archive(corrupt)

    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["report", "--build-id", "test", "--java-target", "8", "--output", str(output), "--input", f"pack={tmp_path}"])
    assert main() == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["stats"]["unique_archives_scanned"] == 1
    assert report["stats"]["referenced_members"] == 1
    assert len(report["errors"]) == 1
    assert "pack/corrupt.jar" in report["errors"][0]


def test_eof_is_recorded_as_archive_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    jar = tmp_path / "truncated.jar"
    with ZipFile(jar, "w") as archive:
        archive.writestr("example/Consumer.class", _class_file())

    def truncated_read(*args: object, **kwargs: object) -> bytes:
        raise EOFError("truncated compressed entry")

    monkeypatch.setattr(ZipFile, "read", truncated_read)
    report = build_report("test", "8", [("pack", tmp_path)])
    assert report["errors"] == ["pack/truncated.jar: truncated compressed entry"]


def test_empty_input_is_reported_alongside_healthy_input(tmp_path: Path) -> None:
    client = tmp_path / "client"
    client.mkdir()
    server = tmp_path / "server.jar"
    with ZipFile(server, "w") as archive:
        archive.writestr("example/Consumer.class", _class_file())

    report = build_report("test", "8", [("server", server), ("client", client)])
    assert report["stats"]["unique_archives_scanned"] == 1
    assert report["errors"] == [f"no JAR files found in input: client={client}"]


def test_multi_release_scan_is_conservative_and_documented(tmp_path: Path) -> None:
    with ZipFile(tmp_path / "multi-release.jar", "w") as archive:
        archive.writestr("META-INF/versions/21/example/Consumer.class", _class_file())

    for target in ("8", "17"):
        report = build_report("test", target, [("pack", tmp_path)])
        assert report["stats"]["referenced_members"] == 1
        assert "All multi-release class variants are scanned" in markdown_summary(report)
