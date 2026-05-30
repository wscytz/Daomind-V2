# -*- coding: utf-8 -*-
"""Dao-Mind v2 桌面启动器 — pywebview 原生窗口"""

import sys
import os
import time
import threading

# PyInstaller 打包时设置工作目录
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)


def start_server():
    """在后台线程启动 FastAPI 服务"""
    import uvicorn
    from main import app
    import config
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="warning")


def wait_for_server(port, timeout=15):
    """等待服务就绪"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


if __name__ == "__main__":
    import webview
    import config

    print("  道心 · Dao-Mind v2")
    print(f"  启动于 http://127.0.0.1:{config.PORT}")

    # 启动后端
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 等待服务就绪
    if not wait_for_server(config.PORT):
        print("[ERROR] 服务启动超时")
        sys.exit(1)

    # 创建原生桌面窗口
    window = webview.create_window(
        title='道心 · Dao-Mind',
        url=f'http://127.0.0.1:{config.PORT}',
        width=960,
        height=640,
        min_size=(480, 400),
        text_select=True,
    )

    # 启动窗口（阻塞直到窗口关闭）
    webview.start(debug=False, http_server=False)
