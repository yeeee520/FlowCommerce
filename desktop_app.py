"""
桌面应用入口 — PyWebView 包装方案

功能：
- 使用 webview 库创建桌面窗口
- 在后台线程启动 FastAPI 服务器
- 窗口加载 http://localhost:8000
- 窗口关闭时自动停止 FastAPI 服务
- 打包环境下自动迁移 ChromaDB 到 %APPDATA%
- 窗口背景色适配 V1 极简苹果风格 (#f5f5f7)
"""

import os
import sys
import shutil
import threading
import time

import webview
import uvicorn

from config import API_HOST, API_PORT


# ============================================================
# 全局变量：用于优雅关闭
# ============================================================
_server_instance: uvicorn.Server | None = None
_shutdown_event = threading.Event()


# ============================================================
# 打包环境检测
# ============================================================
def _is_frozen() -> bool:
    """
    检测当前是否为 PyInstaller 打包后的运行环境。

    打包后 sys.frozen 为 True，且 sys._MEIPASS 指向临时解压目录。
    """
    return getattr(sys, "frozen", False)


def _get_bundled_path(relative_path: str) -> str:
    """
    获取打包环境中的资源路径。

    开发环境下返回项目根目录的相对路径；
    打包环境下返回 PyInstaller 临时解压目录 (_MEIPASS) 中的路径。
    """
    if _is_frozen():
        # PyInstaller 将 --add-data 文件解压到 sys._MEIPASS
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def _get_appdata_chroma_dir() -> str:
    """
    获取 APPDATA 下的 ChromaDB 持久化目录。
    路径: %APPDATA%/EcomAIAgent/chroma_db
    """
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "EcomAIAgent", "chroma_db")


def _migrate_chromadb():
    """
    将打包内的 chroma_db 初始数据复制到 APPDATA 持久化目录。

    逻辑：
    - 仅在打包环境 (sys.frozen) 且目标目录不存在时执行迁移
    - 开发环境下不执行迁移，直接使用项目本地的 chroma_db
    - 迁移完成后设置环境变量 CHROMA_PERSIST_DIR 指向 APPDATA 路径
    """
    if not _is_frozen():
        # 开发环境：不迁移，直接使用项目本地 chroma_db
        print("[Desktop] 开发环境，使用本地 chroma_db")
        return

    appdata_chroma = _get_appdata_chroma_dir()

    if os.path.exists(appdata_chroma):
        print(f"[Desktop] APPDATA chroma_db 已存在，跳过迁移: {appdata_chroma}")
    else:
        # 从打包资源中复制初始 chroma_db
        bundled_chroma = _get_bundled_path("chroma_db")
        if os.path.exists(bundled_chroma):
            print(f"[Desktop] 首次启动，迁移 chroma_db: {bundled_chroma} -> {appdata_chroma}")
            os.makedirs(os.path.dirname(appdata_chroma), exist_ok=True)
            shutil.copytree(bundled_chroma, appdata_chroma)
            print("[Desktop] chroma_db 迁移完成")
        else:
            print(f"[Desktop] 警告: 打包内 chroma_db 不存在 ({bundled_chroma})，创建空目录")
            os.makedirs(appdata_chroma, exist_ok=True)

    # 设置环境变量，让 config.py 使用 APPDATA 路径
    os.environ["CHROMA_PERSIST_DIR"] = appdata_chroma
    print(f"[Desktop] CHROMA_PERSIST_DIR = {appdata_chroma}")


def _run_fastapi():
    """
    在后台线程中启动 FastAPI 服务器。
    使用 uvicorn.Server 实例以便通过编程方式关闭。
    """
    global _server_instance

    config = uvicorn.Config(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        reload=False,  # 打包后不支持 reload
    )
    _server_instance = uvicorn.Server(config)

    print(f"[Desktop] FastAPI 服务器启动中: http://{API_HOST}:{API_PORT}")
    _server_instance.run()


def _wait_for_server(url: str, timeout: int = 20) -> bool:
    """
    轮询等待服务器就绪。

    Args:
        url: 健康检查地址
        timeout: 超时时间（秒）

    Returns:
        True 表示服务器就绪，False 表示超时
    """
    import urllib.request
    import urllib.error

    print(f"[Desktop] 等待服务器就绪: {url}")
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    print("[Desktop] 服务器已就绪")
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            pass
        time.sleep(0.5)

    print("[Desktop] 警告: 服务器启动超时，尝试继续加载")
    return False


def _on_closed():
    """
    窗口关闭回调：停止 FastAPI 服务器并退出进程。
    """
    global _server_instance

    print("[Desktop] 窗口已关闭，正在停止 FastAPI 服务器...")
    if _server_instance is not None:
        _server_instance.should_exit = True
    _shutdown_event.set()

    # 强制退出进程，防止残留线程阻塞退出
    os._exit(0)


def _init_env():
    """
    初始化环境变量。
    桌面应用中 .env 由 config.py 在导入时自动加载。
    """
    pass


def main():
    """桌面应用主入口"""
    _init_env()

    # ---- 0. 打包环境：迁移 ChromaDB 到 APPDATA ----
    _migrate_chromadb()

    # ---- 1. 启动 FastAPI 后台线程 ----
    server_thread = threading.Thread(target=_run_fastapi, daemon=True)
    server_thread.start()

    # ---- 2. 等待服务器就绪 ----
    server_url = f"http://127.0.0.1:{API_PORT}/health"
    _wait_for_server(server_url, timeout=20)

    # ---- 3. 创建桌面窗口 ----
    app_url = f"http://127.0.0.1:{API_PORT}"

    print(f"[Desktop] 创建窗口，加载: {app_url}")

    window = webview.create_window(
        title="电商AI助手",
        url=app_url,
        width=1200,
        height=800,
        min_size=(900, 600),
        resizable=True,
        fullscreen=False,
        easy_drag=False,
        on_top=False,
        confirm_close=False,  # 关闭时不弹出确认框
        background_color="#f5f5f7",  # V1 极简苹果风格背景色
    )

    # ---- 4. 注册关闭事件 ----
    window.events.closed += _on_closed

    # ---- 5. 启动 WebView GUI 主循环 ----
    webview.start(gui="edgechromium" if sys.platform == "win32" else None)


if __name__ == "__main__":
    main()
