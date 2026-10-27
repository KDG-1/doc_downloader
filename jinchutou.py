# -*- coding: utf-8 -*-
"""金锄头下载。"""
import time

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
        time.sleep(5)

        while True:
            try:
                # 展开全部
                elem_cont_button = driver.find_element(By.CLASS_NAME, "banner-download")
                driver.execute_script("arguments[0].scrollIntoView(true);", elem_cont_button)
                ActionChains(driver).move_to_element(elem_cont_button).perform()
                time.sleep(0.5)
                driver.find_element(By.CLASS_NAME, "down-arrow").click()
            except Exception:
                break

        # 获取页数
        num_of_pages = (
            driver.find_element(By.ID, "readshop")
            .find_element(By.CLASS_NAME, "mainpart")
            .find_element(By.CLASS_NAME, "shop3")
            .find_elements(By.CLASS_NAME, "text")[-1]
            .get_attribute("innerHTML")
        )
        num_of_pages = int(num_of_pages.split(";")[-1])

        workdir = prepare_workdir(title)

        for pages in trange(num_of_pages):
            time.sleep(0.5)
            elem = driver.find_element(By.ID, f"outer_page_{pages + 1}")
            ActionChains(driver).move_to_element(elem).perform()
            img = elem.find_element(By.TAG_NAME, "img")
            img_url = img.get_attribute("src")
            res = http_get(img_url, referer=url)
            save_image(res, workdir / f"{pages}.gif", context=f"（第 {pages + 1} 页）")
    finally:
        driver.quit()

    if workdir is None:
        print("未取到页数，放弃")
        return
    print("下载完毕，正在转码")
    conpdf(str(save_pdf_path(title)), str(workdir), ".gif")


if __name__ == "__main__":
    download("https://www.jinchutou.com/p-120187856.html")
