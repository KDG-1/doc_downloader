# -*- coding: utf-8 -*-
"""Chrome / chromedriver 自动管理。

原项目内置的是 Chrome 89 时代的 chromedriver.exe，与本机浏览器版本不匹配；
Selenium 4 又取消了 ``executable_path`` 参数。这里改为自动匹配：

1. 读取本机 Chrome 版本（注册表 BLBeacon，失败则读 exe 文件版本）；
2. 命中缓存则直接复用；
3. 否则从 npmmirror 的 chrome-for-testing 镜像下载同主版本号的 driver；
4. 都失败时退回 Selenium Manager。

可用环境变量：
    CHROMEDRIVER           直接指定 chromedriver 路径，跳过全部探测
    CHROMEDRIVER_MIRROR    覆盖镜像地址
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
import zipfile
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

MIRROR = os.environ.get(
    "CHROMEDRIVER_MIRROR",
    "https://registry.npmmirror.com/-/binary/chrome-for-testing",
).rstrip("/")

CACHE_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "doc_downloader" / "driver"

CHROME_CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)") ) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
]

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/{version} Safari/537.36"
)


def chrome_version() -> str | None:
    """返回本机 Chrome 的完整版本号，例如 ``155.0.8059.86``。"""
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon") as key:
                return winreg.QueryValueEx(key, "version")[0].strip()
        except OSError:
            pass

    exe = next((p for p in CHROME_CANDIDATES if p.exists()), None)
    if exe is None:
        return None
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             f"(Get-Item '{exe}').VersionInfo.ProductVersion"],
            text=True,
            timeout=20,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        return out.strip() or None
    except Exception:
        return None


def _platform_dir() -> str:
    machine = platform.machine().lower()
    return "win32" if machine in {"x86", "i386", "i686"} else "win64"


def _available_versions() -> list[str]:
    resp = requests.get(MIRROR + "/", timeout=20)
    resp.raise_for_status()
    names = [str(item.get("name", "")).rstrip("/") for item in resp.json()]
    return [n for n in names if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", n)]


def _as_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def _pick_version(target: str, available: list[str]) -> str:
    """在镜像里挑一个与 target 主版本相同、且尽量接近的版本。"""
    if target in available:
        return target
    major = target.split(".")[0]
    same_major = [v for v in available if v.startswith(major + ".")]
    if not same_major:
        raise RuntimeError(f"镜像里没有 Chrome {major} 对应的 chromedriver，可用示例：{available[:3]}")
    same_major.sort(key=_as_tuple)
    want = _as_tuple(target)
    lower = [v for v in same_major if _as_tuple(v) <= want]
    return lower[-1] if lower else same_major[0]


def _download_driver(version: str) -> Path:
    plat = _platform_dir()
    url = f"{MIRROR}/{version}/{plat}/chromedriver-{plat}.zip"
    target_dir = CACHE_DIR / version / plat
    exe = target_dir / "chromedriver.exe"
    if exe.exists():
        return exe

    print(f"正在下载 chromedriver {version} …")
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()

    target_dir.mkdir(parents=True, exist_ok=True)
    zip_path = target_dir / "chromedriver.zip"
    zip_path.write_bytes(resp.content)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            member = next(n for n in zf.namelist() if n.endswith("chromedriver.exe"))
            exe.write_bytes(zf.read(member))
    finally:
        zip_path.unlink(missing_ok=True)
    return exe


def resolve_driver() -> Path | None:
    """返回可用的 chromedriver 路径；无法确定时返回 None（交给 Selenium Manager）。"""
    explicit = os.environ.get("CHROMEDRIVER")
    if explicit:
        path = Path(explicit)
        if path.exists():
            return path
        raise FileNotFoundError(f"CHROMEDRIVER 指向的文件不存在：{path}")

    version = chrome_version()
    if version:
        cached = CACHE_DIR / version / _platform_dir() / "chromedriver.exe"
        if cached.exists():
            return cached
        try:
            picked = _pick_version(version, _available_versions())
            print(f"本机 Chrome {version}，使用 chromedriver {picked}")
            return _download_driver(picked)
        except Exception as exc:  # 网络失败不应直接中断
            print(f"自动获取 chromedriver 失败（{exc}），改用 Selenium Manager")
    return None


def create_driver(headless: bool = False, timeout: int = 30, page_load_timeout: int = 30):
    """创建 Chrome 驱动，参数与旧代码里的用法保持一致。"""
    opts = Options()
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)

    version = chrome_version() or "124"
    opts.add_argument(f"user-agent={_UA.format(version='.'.join(version.split('.')[:3]))}")
    if headless:
        opts.add_argument("--headless=new")

    driver_path = resolve_driver()
    if driver_path:
        driver = webdriver.Chrome(service=Service(str(driver_path)), options=opts)
    else:
        driver = webdriver.Chrome(options=opts)

    driver.set_page_load_timeout(page_load_timeout)
    driver.implicitly_wait(timeout if timeout else 0)
    return driver


if __name__ == "__main__":
    print("Chrome:", chrome_version())
    print("Driver:", resolve_driver())
