import struct
from pathlib import Path
from zipfile import ZipFile

from daxxl.jvmdg_usage_report import scan_archive


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
