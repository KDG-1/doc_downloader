# -*- coding: utf-8 -*-
"""公共小工具：文件名清洗、目录准备、带重试的下载。"""
from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path

import requests

# Windows 文件名非法字符 + 保留名
_INVALID = r'<>:"/\\|?*'
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_IMG_MAGIC = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"GIF8", "gif"),
    (b"RIFF", "webp"),
    (b"BM", "bmp"),
)


def save_image(resp: requests.Response, path: Path, *, context: str = "") -> str:
    """校验响应确实是图片再落盘，避免留下 0 字节文件让后续 PIL 报错。"""
    data = resp.content or b""
    if len(data) < 200:
        raise RuntimeError(
            f"图片内容异常{context}：HTTP {resp.status_code}，{len(data)} 字节，"
            "通常是图床防盗链或该页未解锁"
        )
    kind = next((name for magic, name in _IMG_MAGIC if data.startswith(magic)), None)
    if kind is None:
        raise RuntimeError(f"返回的不是图片{context}：HTTP {resp.status_code}，开头 {data[:40]!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return kind


def safe_name(name: str, fallback: str = "document", maxlen: int = 80) -> str:
    """把网页标题转成各平台都能建目录/文件的名字。"""
    name = unicodedata.normalize("NFC", str(name or ""))
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    for ch in _INVALID:
        name = name.replace(ch, "_")
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = fallback
    if name.split(".")[0].upper() in _RESERVED:
        name = "_" + name
    return name[:maxlen].rstrip(" .")


def ensure_dirs(*paths: str | os.PathLike) -> None:
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)


def http_get(
    url: str,
    *,
    timeout: int = 30,
    retries: int = 3,
    referer: str | None = None,
    allow_http_fallback: bool = False,
) -> requests.Response:
    """带重试的 GET，默认伪装成浏览器，避免部分站点直接 403。

    ``allow_http_fallback`` 用于图床常见的两种情况：按页限流导致的
    ``SSLEOFError``，以及只对 http 放行的图片域名。
    """
    headers = {"User-Agent": _UA}
    if referer:
        headers["Referer"] = referer
    last_exc: Exception | None = None
    target = url
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(target, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.SSLError as exc:
            last_exc = exc
            if allow_http_fallback and target.startswith("https://"):
                target = "http://" + target[len("https://"):]
            time.sleep(attempt)
        except Exception as exc:  # noqa: BLE001 - 统一重试
            last_exc = exc
            if attempt < retries:
                time.sleep(attempt)
    raise last_exc  # type: ignore[misc]


def prepare_workdir(title: str, kind: str = "temp") -> Path:
    """建立并清空 temp/<标题>，返回路径。"""
    import shutil

    name = safe_name(title)
    target = Path(kind) / name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    return target


def save_pdf_path(title: str) -> Path:
    ensure_dirs("output")
    return Path("output") / f"{safe_name(title)}.pdf"
