# -*- coding: utf-8 -*-
"""原创力（book118）PPT 版：逐页截图再拼 PDF。"""
import time

from PIL import Image
from selenium.webdriver.common.by import By
from tqdm import trange

from driver_setup import create_driver
from img2pdf import conpdf
from utils import prepare_workdir, save_pdf_path


def download(url):
    driver = create_driver(headless=False)
    title = "output"
    workdir = None
    try:
        try:
            driver.get(url)
            title = driver.title or "output"
        except Exception:
            print("Timeout - start download anyway.")

        print(f"原创力: 《{title}》")
        time.sleep(5)

        driver.find_element(By.ID, "btn_preview_remain").click()

        time.sleep(2)
        frame = driver.find_elements(By.CLASS_NAME, "preview-iframe")[0]
        src = frame.get_attribute("src")
        print(src)

        driver.get(src)
        time.sleep(5)

        workdir = prepare_workdir(title)
        shot = workdir / "capture.png"

        page_count = int(driver.find_element(By.ID, "PageCount").get_attribute("innerHTML"))
        for i in trange(page_count):
            driver.save_screenshot(str(shot))
            page = driver.find_element(By.ID, "ppt")

            left = page.location["x"]
            top = page.location["y"]
            right = left + page.size["width"]
            bottom = top + page.size["height"] - 35

            im = Image.open(shot)
            im = im.crop((left, top, right, bottom))  # 元素裁剪
            im.save(workdir / f"{i}.png")  # 元素截图
            driver.find_element(By.ID, "pageNext").click()
            time.sleep(1)  # 防止还没加载出来
        shot.unlink(missing_ok=True)
    finally:
        driver.quit()

    if workdir is None:
        print("未取到页数，放弃")
        return
    print("下载完毕，正在转码")
    conpdf(str(save_pdf_path(title)), str(workdir), ".png")


if __name__ == "__main__":
    download("https://max.book118.com/html/2019/1002/8052020057002053.shtm")
