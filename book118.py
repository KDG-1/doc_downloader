# -*- coding: utf-8 -*-
"""原创力（book118）下载；PPT 类文档转交 book118_PPT。"""
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from tqdm import trange

from driver_setup import create_driver
from img2pdf import conpdf
from utils import http_get, prepare_workdir, save_image, save_pdf_path


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

        print(title)
        if "ppt" in title.lower():
            driver.quit()
            driver = None
            import book118_PPT

            book118_PPT.download(url)
            return
        time.sleep(2)

        try:
            driver.find_element(By.ID, "agree_full").click()
        except NoSuchElementException:
            try:
                driver.find_elements(By.CLASS_NAME, "big")[0].click()
            except Exception:
                pass
        finally:
            time.sleep(1)

        while True:
            try:
                # 展开全部
                elem_cont_button = driver.find_element(By.ID, "btn_preview_remain")
                driver.execute_script("arguments[0].scrollIntoView(true);", elem_cont_button)
                ActionChains(driver).move_to_element(elem_cont_button).perform()
                driver.execute_script("window.scrollBy(0, -100)")
                time.sleep(2)
                elem_cont_button.click()
            except NoSuchElementException:
                break
            except Exception:
                import traceback

                traceback.print_exc()
            finally:
                time.sleep(1)

        # 获取页数
        num_of_pages = driver.find_element(By.CLASS_NAME, "counts").get_attribute("innerHTML")
        num_of_pages = int(num_of_pages.split(" ")[-1])

        workdir = prepare_workdir(title)

        elems = driver.find_elements(By.CLASS_NAME, "webpreview-item")
        for pages in trange(num_of_pages):
            elem = elems[pages]
            time.sleep(0.5)
            ActionChains(driver).move_to_element(elem).perform()
            img = elem.find_element(By.TAG_NAME, "img")
            count = 0
            while (
                count < 10
                and img.get_attribute("data-src") is None
                and img.get_attribute("src") is None
            ):
                count += 1
                time.sleep(1)

            img_url = img.get_attribute("src")
            if img_url is None or "http" not in img_url:
                img_url = "http:" + (img.get_attribute("data-src") or "")
            res = http_get(img_url, referer=url)
            save_image(res, workdir / f"{pages}.png", context=f"（第 {pages + 1} 页）")
    finally:
        if driver is not None:
            driver.quit()

    if workdir is None:
        print("未取到页数，放弃")
        return
    print("下载完毕，正在转码")
    conpdf(str(save_pdf_path(title)), str(workdir), ".png")


if __name__ == "__main__":
    download("https://max.book118.com/html/2017/1206/143048522.shtm")
