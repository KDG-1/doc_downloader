# -*- coding: utf-8 -*-
"""把图片目录拼成 PDF（独立小工具，主流程用的是 img2pdf.conpdf）。"""
import os
import re
import time
from pathlib import Path

import PIL.ExifTags
import PIL.Image
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


class ImgToPdf:
    def img_search(self, mypath, filenames):
        for lists in os.listdir(mypath):
            path = os.path.join(mypath, lists)
            if os.path.isfile(path):
                expression = r"[\w]+\.(jpg|png|jpeg)$"
                if re.search(expression, path, re.IGNORECASE):
                    filenames.append(path)
            elif os.path.isdir(path):
                self.img_search(path, filenames)

    def rotate_img_to_proper(self, image):
        try:
            if hasattr(image, "_getexif"):  # 只有 JPEG 有 EXIF
                orientation = None
                for tag in PIL.ExifTags.TAGS:
                    if PIL.ExifTags.TAGS[tag] == "Orientation":
                        orientation = tag
                        break
                if orientation is None:
                    return image
                exif_data = image._getexif()  # 没有 EXIF 时返回 None
                if exif_data is None:
                    return image
                value = dict(exif_data.items()).get(orientation)
                if value == 3:
                    image = image.transpose(PIL.Image.Transpose.ROTATE_180)
                elif value == 6:
                    image = image.transpose(PIL.Image.Transpose.ROTATE_270)
                elif value == 8:
                    image = image.rotate(90, expand=True)
        except Exception:
            pass
        return image

    def pmain(self, src_folder, title, direction="|"):
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file_name = str(output_dir / f"{title}.pdf")

        img_doc = canvas.Canvas(output_file_name)
        # 修改 PDF 文件方向：- 为横向，其余为纵向
        if direction == "-":
            img_doc.setPageSize(landscape(A4))
            document_width, document_height = landscape(A4)
        else:
            img_doc.setPageSize(A4)
            document_width, document_height = A4

        mypath = src_folder if src_folder is not None else input("Input the image folder please:")
        filenames = []
        start = time.perf_counter()
        self.img_search(mypath, filenames)
        print("find file cost time: ", time.perf_counter() - start, "find files: ", len(filenames))

        for image in filenames:
            try:
                with PIL.Image.open(image) as image_file:
                    image_file = self.rotate_img_to_proper(image_file)
                    image_width, image_height = image_file.size
                    if not (image_width > 0 and image_height > 0):
                        raise ValueError("图片尺寸为 0")
                    image_aspect = image_height / float(image_width)
                    print_width = document_width
                    print_height = document_width * image_aspect
                    img_doc.drawImage(
                        ImageReader(image_file),
                        document_width - print_width,
                        document_height - print_height,
                        width=print_width,
                        height=print_height,
                        preserveAspectRatio=True,
                    )
                    img_doc.showPage()
            except Exception as exc:
                print("error:", exc, image)
        img_doc.save()
        print("Done")


if __name__ == "__main__":
    pass
