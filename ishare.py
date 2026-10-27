# -*- coding: utf-8 -*-
"""新浪爱问下载：图片直接保存，SVG 需要额外工具转 PNG。"""
import shutil
import subprocess
import time

from PIL import Image
from selenium.common.exceptions import JavascriptException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from tqdm import trange

from driver_setup import create_driver
from img2pdf import conpdf
from utils import http_get, prepare_workdir, save_pdf_path

SVG_HINT = (
    "该页是 SVG 格式，需要 svg2png 或 cairosvg 才能转换：\n"
    "  npm install -g svg2png      （Windows 需先装 nodejs）\n"
    "  pip install cairosvg        （备选方案）"
)


def _svg_to_png(svg_path, png_path, width=1500):
    """优先调用 svg2png，退回 cairosvg。"""
    if shutil.which("svg2png"):
        subprocess.run(
            ["svg2png", str(svg_path), "-o", str(png_path), "-w", str(width)],
            check=True,
            timeout=120,
        )
        return
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError(SVG_HINT) from exc
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width)


def download(url):
    driver = create_driver(headless=True)
    title = "output"
    workdir = None
    try:
        try:
            driver.get(url)
            title = driver.title or "output"
        except Exception:
            print("Timeout - start download anyway.")

        print(f"新浪爱问: 《{title}》")
        time.sleep(5)

        last_page_num = None
        while True:
            try:
                driver.execute_script("window.scrollBy(0,10000)")
                time.sleep(1)
                # 展开全部
                elem_cont_button = driver.find_element(By.CLASS_NAME, "state-bottom")
                elem_cont_button = elem_cont_button.find_element(By.TAG_NAME, "a")
                text = elem_cont_button.find_element(By.TAG_NAME, "p").get_attribute("innerHTML")
                if text == last_page_num:
                    print("收费文档！无法下载")
                    return
                last_page_num = text
                if "结束" in text or ">0</em>" in text:
                    break
                driver.execute_script("arguments[0].scrollIntoView(true);", elem_cont_button)
                ActionChains(driver).move_to_element(elem_cont_button).perform()
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", elem_cont_button)
            except JavascriptException:
                continue

        # 获取页数
        num_of_pages = int(
            driver.find_element(By.CLASS_NAME, "page-input-con")
            .find_element(By.TAG_NAME, "span")
            .get_attribute("innerHTML")
        )
        driver.execute_script("window.scrollBy(0,10000)")

        workdir = prepare_workdir(title)
        imgs = driver.find_elements(By.CLASS_NAME, "data-detail")

        for pages in trange(num_of_pages):
            try:
                # svg 格式
                img_url = imgs[pages].find_element(By.TAG_NAME, "embed").get_attribute("src")
                svg_file = workdir / f"{pages}.svg"
                svg_file.write_bytes(http_get(img_url, referer=url).content)
                png_file = workdir / f"{pages}.png"
                _svg_to_png(svg_file, png_file)
                im = Image.open(png_file)
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, im)
                bg.save(workdir / f"{pages}.jpg")
                png_file.unlink(missing_ok=True)
                svg_file.unlink(missing_ok=True)
            except NoSuchElementException:
                # 图片格式
                for _ in range(10):
                    try:
                        img_url = imgs[pages].find_element(By.TAG_NAME, "img").get_attribute("src")
                        (workdir / f"{pages}.jpg").write_bytes(
                            http_get(img_url, referer=url).content
                        )
                        break
                    except Exception:
                        ActionChains(driver).move_to_element(imgs[pages]).perform()
                        time.sleep(1)
                        driver.execute_script("window.scrollBy(0,10000)")
                else:
                    print(f"第 {pages + 1} 页取图失败，跳过")
    finally:
        driver.quit()

    if workdir is None:
        print("未取到页数，放弃")
        return
    print("下载完毕，正在转码")
    conpdf(str(save_pdf_path(title)), str(workdir), ".jpg", True)


if __name__ == "__main__":
    download("http://ishare.iask.sina.com.cn/f/CSBjG4CX6D.html")
