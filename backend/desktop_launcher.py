# -*- coding: utf-8 -*-
"""Dao-Mind v2 桌面启动器 — pywebview 原生窗口"""

import sys
import os
import time
import threading
import socket

# PyInstaller 打包时设置工作目录
if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)


def reserve_server_socket(host, preferred, max_tries=20):
    """从 preferred 端口开始预占一个可用端口，避免探测后被其他进程抢占。"""
    start = max(1, min(65535, int(preferred)))
    end = min(65535, start + max_tries - 1)
    last_error = None

    for port in range(start, end + 1):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server_socket.bind((host, port))
            server_socket.listen(128)
            return server_socket
        except OSError as exc:
            last_error = exc
            server_socket.close()

    raise RuntimeError(f"未找到可用端口：{start}-{end}，最后错误：{last_error}")


def start_server(server_socket):
    """在后台线程启动 FastAPI 服务"""
    import uvicorn
    from main import app
    uvicorn_config = uvicorn.Config(app, log_level="warning")
    server = uvicorn.Server(uvicorn_config)
    server.run(sockets=[server_socket])


def wait_for_server(host, port, timeout=15):
    """等待服务就绪"""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


if __name__ == "__main__":
    import webview
    import config

    try:
        server_socket = reserve_server_socket(config.HOST, config.PORT)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)

    host, port = server_socket.getsockname()[:2]
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host

    print("  道心 · Dao-Mind v2")
    if port != config.PORT:
        print(f"  端口 {config.PORT} 被占用，自动切换到 {port}")
    print(f"  启动于 http://{display_host}:{port}")

    # 启动后端
    server_thread = threading.Thread(target=start_server, args=(server_socket,), daemon=True)
    server_thread.start()

    # 等待服务就绪
    if not wait_for_server(display_host, port):
        print("[ERROR] 服务启动超时")
        sys.exit(1)

    # 创建原生桌面窗口
    window = webview.create_window(
        title='道心 · Dao-Mind',
        url=f'http://{display_host}:{port}',
        width=960,
        height=640,
        min_size=(480, 400),
        text_select=True,
    )

    # 启动窗口（阻塞直到窗口关闭）
    webview.start(debug=False, http_server=False)
