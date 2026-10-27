# -*- coding: utf-8 -*-
"""淘豆网下载。"""
import time
import urllib.request

from selenium.common.exceptions import (
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.action_chains import ActionChains
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
            title = (driver.title or "output")[:-8] or "output"
        except Exception:
            print("Timeout - start download anyway.")

        print(f"淘豆网: 《{title}》")
        time.sleep(5)

        while True:
            try:
                driver.execute_script("window.scrollBy(0,10000)")
                time.sleep(1)
                # 展开全部
                elem_cont_button = driver.find_element(By.CLASS_NAME, "banner-more-btn")
                elem_cont_button = elem_cont_button.find_element(By.TAG_NAME, "span")
                driver.execute_script("arguments[0].scrollIntoView(true);", elem_cont_button)
                ActionChains(driver).move_to_element(elem_cont_button).perform()
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", elem_cont_button)
            except (NoSuchElementException, StaleElementReferenceException):
                break
            except JavascriptException:
                continue

        # 获取页数
        num_of_pages = int(driver.find_element(By.ID, "docPage").get_attribute("innerHTML"))

        workdir = prepare_workdir(title)

        for pages in trange(num_of_pages):
            time.sleep(0.5)
            element = driver.find_element(By.ID, f"page{pages + 1}")
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            ActionChains(driver).move_to_element(element).perform()
            time.sleep(0.5)
            img_url = element.find_element(By.TAG_NAME, "img").get_attribute("src")
            with urllib.request.urlopen(img_url, timeout=30) as response:
                (workdir / f"{pages}.jpg").write_bytes(response.read())
    finally:
        driver.quit()

    if workdir is None:
        print("未取到页数，放弃")
        return
    print("下载完毕，正在转码")
    conpdf(str(save_pdf_path(title)), str(workdir), ".jpg")


if __name__ == "__main__":
    download("https://www.taodocs.com/p-292564682.html")
