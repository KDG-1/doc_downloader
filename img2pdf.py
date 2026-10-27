# -*- coding: utf-8 -*-
"""把一目录的图片按文件名顺序拼成 PDF。"""
import os
import re
from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import portrait
from reportlab.pdfgen import canvas
from tqdm import trange


def _sort_key(path: str):
    """按文件名里的数字排序（0.png < 2.png < 10.png），没有数字则退回字典序。"""
    stem = Path(path).stem
    match = re.search(r"\d+", stem)
    return (0, int(match.group())) if match else (1, stem)


def file_name(file_dir, suffix=".jpg"):
    files = [
        str(Path(root) / name)
        for root, _dirs, names in os.walk(file_dir)
        for name in names
        if os.path.splitext(name)[1].lower() == suffix.lower()
    ]
    return sorted(files, key=_sort_key)


def conpdf(f_pdf, filedir, suffix=".jpg", scale=False):
    file_list = file_name(filedir, suffix)
    if not file_list:
        raise RuntimeError(f"{filedir} 下没有 {suffix} 文件，无法生成 PDF")

    Path(f_pdf).parent.mkdir(parents=True, exist_ok=True)

    with Image.open(file_list[0]) as first:
        if scale and first.size[0] < first.size[1]:
            w, h = 848, 1168
        else:
            w, h = first.size

    c = canvas.Canvas(f_pdf, pagesize=(w, h))

    for i in trange(len(file_list)):
        f = file_list[i]
        with Image.open(f) as img_file:
            xsize, ysize = img_file.size

        ratx = xsize / w
        raty = ysize / h
        ratxy = xsize / (1.0 * ysize)
        if ratx > 1:
            ratx = 0.99
        if raty > 1:
            raty = 0.99
        rat = max(ratx, raty)
        widthx = w * rat
        widthy = h * rat
        widthx = widthy * ratxy
        posx = max((w - widthx) / 2, 0)
        posy = max((h - widthy) / 2, 0)

        c.drawImage(f, posx, posy, widthx, widthy)
        c.showPage()
    c.save()
    print(f"转码完毕：{f_pdf}")


if __name__ == "__main__":
    conpdf("output/output.pdf", "temp", ".png")
