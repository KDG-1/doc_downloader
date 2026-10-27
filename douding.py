# -*- coding: utf-8 -*-
"""豆丁网（docin）下载：解析页面里的 sid 与页数，直接取图。"""
import re
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from tqdm import trange

from img2pdf import conpdf
from utils import http_get, prepare_workdir, save_image, save_pdf_path


def _parse(text):
    sid_match = re.search(r"""flash_param_hzq["']?\s*[:=]\s*["']([0-9a-f]+)""", text)
    pages_match = re.search(r"allPage\s*[:=]\s*(\d+)", text)
    if not (sid_match and pages_match):
        raise RuntimeError("页面结构已变化：找不到 sid / allPage，可能不是文档预览页")
    return sid_match.group(1), int(pages_match.group(1))


def download(url):
    resp = http_get(url)
    resp.encoding = resp.apparent_encoding or "utf-8"
    text = resp.text

    sid, pages = _parse(text)
    match = re.search(r"/p-(\d+)\.html", urlparse(url).path) or re.search(r"file=(\d+)", url)
    if match is None:
        raise RuntimeError("无法从链接中解析文档 id")
    doc_id = match.group(1)

    html = BeautifulSoup(text, features="html.parser")
    title = (html.title.string if html.title and html.title.string else "output").strip()
    print(f"豆丁：《{title}》")

    workdir = prepare_workdir(title)
    for i in trange(pages):
        img_url = (
            f"https://docimg1.docin.com/docinpic.jsp?file={doc_id}"
            f"&width=1600&pageno={i + 1}&sid={sid}"
        )
        resp = http_get(img_url, referer=url, allow_http_fallback=True)
        save_image(resp, workdir / f"{i + 1}.jpg", context=f"（第 {i + 1} 页）")
        time.sleep(0.3)  # 图床按页限流，太快会直接断 TLS 连接

    print("下载完毕，正在转码")
    conpdf(str(save_pdf_path(title)), str(workdir), ".jpg", True)


if __name__ == "__main__":
    download("https://jz.docin.com/p-1995868152.html")
