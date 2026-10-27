# -*- coding: utf-8 -*-
"""多种文档下载器入口。

用法：
    python docDownloader.py                     # 交互式，循环输入网址
    python docDownloader.py <url>               # 直接处理一个网址
"""
import os

import fire


def _route(url: str) -> bool:
    url_l = url.strip().lower()
    if not url_l:
        return True

    if "doc88" in url_l:
        import doc88

        doc88.download(url)
    elif "book118" in url_l:
        import book118

        book118.download(url)
    elif "taodocs" in url_l:
        import taodocs

        taodocs.download(url)
    elif "docin" in url_l:
        import douding

        douding.download(url)
    elif "jinchutou" in url_l:
        import jinchutou

        jinchutou.download(url)
    elif "ishare" in url_l:
        import ishare

        ishare.download(url)
    else:
        print("暂不支持该站点")
    return True


def main(url: str = ""):
    for path in ("./temp", "./output"):
        os.makedirs(path, exist_ok=True)

    if url and url.lower() != "exit":
        _route(url)
        return

    while True:
        try:
            url = input("请输入网址（输入 exit 退出）：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if url.lower() in {"exit", "quit", "q"}:
            break
        try:
            _route(url)
        except KeyboardInterrupt:
            print("\n已中断当前任务")
        except Exception as exc:  # 单个链接失败不影响后续
            print(f"处理失败：{exc!r}")


if __name__ == "__main__":
    fire.Fire(main)
