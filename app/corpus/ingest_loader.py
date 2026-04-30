from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TextFileLoadResult:
    path: Path
    text: str | None
    encoding_used: str | None
    skipped: bool
    skip_reason: str | None = None


def author_raw_directory(raw_root: Path, author_slug: str) -> Path:
    return raw_root / author_slug


def list_author_txt_files(raw_root: Path, author_slug: str) -> list[Path]:
    """列出 data/raw/<author_slug> 下全部 .txt；目录不存在或为空返回空列表。"""
    d = author_raw_directory(raw_root, author_slug)
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.txt") if p.is_file())


def _decode_bytes(data: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8(replace)"


def load_txt_file(path: Path) -> TextFileLoadResult:
    """读取 txt；空文件、非文件、明显非法路径跳过。"""
    if not path.is_file():
        return TextFileLoadResult(path, None, None, True, "not a file")
    try:
        data = path.read_bytes()
    except OSError as e:
        return TextFileLoadResult(path, None, None, True, f"os_error:{e}")
    if not data.strip():
        return TextFileLoadResult(path, None, None, True, "empty_file")
    text, enc = _decode_bytes(data)
    return TextFileLoadResult(path, text, enc, False, None)


def is_probably_binary_sample(data: bytes, sample: int = 512) -> bool:
    chunk = data[:sample]
    if b"\x00" in chunk:
        return True
    # 高比例不可打印字节
    non_text = sum(1 for b in chunk if b < 9 or (b > 13 and b < 32))
    return len(chunk) > 0 and non_text / len(chunk) > 0.30


def load_txt_file_safe(path: Path) -> TextFileLoadResult:
    base = load_txt_file(path)
    if base.skipped:
        return base
    raw = path.read_bytes()
    if is_probably_binary_sample(raw):
        return TextFileLoadResult(path, None, None, True, "binary_like")
    return base
