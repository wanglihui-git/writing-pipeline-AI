from __future__ import annotations

from pathlib import Path

from app.corpus.ingest_loader import list_author_txt_files, load_txt_file, load_txt_file_safe


def test_author_dir_missing_returns_empty(tmp_path: Path) -> None:
    assert list_author_txt_files(tmp_path, "nobody") == []


def test_empty_directory(tmp_path: Path) -> None:
    d = tmp_path / "raw" / "a1"
    d.mkdir(parents=True)
    assert list_author_txt_files(tmp_path / "raw", "a1") == []


def test_lists_only_txt_sorted(tmp_path: Path) -> None:
    raw = tmp_path / "raw" / "au"
    raw.mkdir(parents=True)
    (raw / "z.txt").write_text("乙", encoding="utf-8")
    (raw / "a.txt").write_text("甲", encoding="utf-8")
    (raw / "skip.bin").write_bytes(b"\x00\x01binary")
    (raw / "x.md").write_text("md", encoding="utf-8")
    got = list_author_txt_files(tmp_path / "raw", "au")
    assert [p.name for p in got] == ["a.txt", "z.txt"]


def test_load_skips_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "e.txt"
    p.write_bytes(b"  \n  ")
    r = load_txt_file(p)
    assert r.skipped and r.skip_reason == "empty_file"


def test_load_utf8_bytes(tmp_path: Path) -> None:
    p = tmp_path / "u.txt"
    p.write_text("中文测试。", encoding="utf-8")
    r = load_txt_file(p)
    assert not r.skipped and r.text and "中文" in r.text


def test_safe_loader_skips_binary_like(tmp_path: Path) -> None:
    p = tmp_path / "b.txt"
    p.write_bytes(b"\x00" * 200)
    r = load_txt_file_safe(p)
    assert r.skipped and r.skip_reason == "binary_like"
