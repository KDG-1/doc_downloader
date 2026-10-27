# -*- coding: utf-8 -*-
"""道客巴巴（doc88）下载。

注意：2024 年之后 doc88 的阅读器改成「单页 canvas + 拖动滑块解锁」，未解锁时
只有第 1 页可用。本模块只处理可自由预览的部分，遇到滑块/付费墙会明确退出，
不做验证码或付费绕过。
"""
import base64
import re
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from tqdm import trange

from driver_setup import create_driver
from img2pdf import conpdf
from utils import prepare_workdir, save_pdf_path

GATE_MARKERS = ("拖动滑块", "未读", "继续阅读", "解锁全文")


def _has_gate(driver) -> bool:
    try:
        source = driver.page_source
    except Exception:
        return False
    return any(marker in source for marker in GATE_MARKERS)


def _page_count(driver) -> int:
    """从工具栏文本里解析总页数，失败返回 1。"""
    try:
        text = driver.find_element(By.ID, "toolbar").text
    except NoSuchElementException:
        return 1
    nums = re.findall(r"/\s*(\d+)", text) or re.findall(r"(\d+)", text)
    return int(nums[-1]) if nums else 1


def download(url):
    driver = create_driver(headless=True)
    title = "output"
    workdir = None
    captured = 0
    try:
        try:
            driver.get(url)
            title = driver.title or "output"
        except Exception:
            print("Timeout - start download anyway.")

        print(f"道客巴巴: 《{title}》")
        time.sleep(5)

        if _has_gate(driver):
            print("该文档需要拖动滑块/付费才能继续阅读，已停止（不做验证码绕过）")
            return

        try:
            elem_cont_button = driver.find_element(By.ID, "continueButton")
            driver.execute_script("arguments[0].scrollIntoView(true);", elem_cont_button)
            ActionChains(driver).move_to_element(elem_cont_button).perform()
            time.sleep(0.5)
            elem_cont_button.click()
        except NoSuchElementException:
            pass

        num_of_pages = _page_count(driver)
        print(f"共 {num_of_pages} 页")

        for _ in range(5):
            try:
                driver.find_element(By.ID, "zoomInButton").click()
                time.sleep(0.5)
            except NoSuchElementException:
                break

        workdir = prepare_workdir(title)

        for pages in trange(num_of_pages):
            canvas_id = f"outer_page_{pages + 1}"
            pagepb_id = f"page_{pages + 1}"

            element = None
            for _ in range(12):
                found = driver.find_elements(By.ID, canvas_id)
                if found:
                    element = found[0]
                    break
                driver.execute_script("window.scrollBy(0, 800)")
                time.sleep(0.5)
            if element is None:
                print(f"\n第 {pages + 1} 页未渲染（可能需要滚动解锁或已到预览上限），停止")
                break

            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            ActionChains(driver).move_to_element(element).perform()
            time.sleep(0.8)

            img_data = driver.execute_script(
                "var c = document.getElementById(arguments[0]);"
                "return c ? c.toDataURL() : null;",
                pagepb_id,
            )
            if not img_data:
                print(f"\n第 {pages + 1} 页取不到 canvas，停止")
                break
            (workdir / f"{pages}.png").write_bytes(base64.decodebytes(img_data[22:].encode()))
            captured += 1
    finally:
        driver.quit()

    if not captured:
        print("没有抓到任何页面，放弃")
        return
    print(f"已抓取 {captured} 页，正在转码")
    conpdf(str(save_pdf_path(title)), str(workdir), ".png")


if __name__ == "__main__":
    download("https://www.doc88.com/p-6099938057537.html")
