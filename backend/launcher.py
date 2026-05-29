# -*- coding: utf-8 -*-
"""Dao-Mind v2 桌面启动器 — PyInstaller 入口"""

import sys
import os
import time
import threading
import webbrowser

import uvicorn
from main import app
import config


def open_browser():
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{config.PORT}")


if __name__ == "__main__":
    print(f"  道心 · Dao-Mind v2")
    print(f"  启动于 http://127.0.0.1:{config.PORT}")
    print()

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="warning",
    )
