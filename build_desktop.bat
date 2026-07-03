@echo off
chcp 65001 >nul
echo ============================================================
echo   电商AI助手 - 桌面应用打包脚本 (PyInstaller)
echo ============================================================
echo.

REM ----------------------------------------------------------
REM 检查 PyInstaller 是否安装
REM ----------------------------------------------------------
where pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 PyInstaller，正在安装...
    pip install pyinstaller
)

echo [1/3] 清理旧构建产物...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

echo [2/3] 开始 PyInstaller 打包...

REM ----------------------------------------------------------
REM PyInstaller 打包参数说明：
REM   --name:           输出应用名称
REM   --onefile:        打包成单个 exe 文件
REM   --windowed:       无控制台窗口（桌面应用）
REM   --icon:           应用图标（如果有的话）
REM   --add-data:       添加数据文件/目录到包内
REM   --hidden-import:  显式指定 PyInstaller 可能漏掉的模块
REM   --collect-all:    收集指定包的所有数据文件（包括模型文件）
REM   --copy-metadata:  复制包的元数据（chromadb 需要）
REM   --exclude-module: 排除不需要的模块以减小体积
REM ----------------------------------------------------------

pyinstaller ^
    --name="电商AI助手" ^
    --onefile ^
    --windowed ^
    --icon=icon.ico ^
    --add-data "static;static" ^
    --add-data "chroma_db;chroma_db" ^
    --add-data "data;data" ^
    --add-data "config.py;." ^
    --hidden-import=chromadb ^
    --hidden-import=chromadb.config ^
    --hidden-import=chromadb.api ^
    --hidden-import=chromadb.api.types ^
    --hidden-import=chromadb.utils ^
    --hidden-import=chromadb.utils.embedding_functions ^
    --hidden-import=chromadb.utils.embedding_functions.openai_embedding_function ^
    --hidden-import=sentence_transformers ^
    --hidden-import=sentence_transformers.models ^
    --hidden-import=sentence_transformers.util ^
    --hidden-import=torch ^
    --hidden-import=transformers ^
    --hidden-import=transformers.models ^
    --hidden-import=jieba ^
    --hidden-import=jieba.analyse ^
    --hidden-import=jieba.posseg ^
    --hidden-import=langchain ^
    --hidden-import=langchain_community ^
    --hidden-import=langchain_community.embeddings ^
    --hidden-import=langchain_community.vectorstores ^
    --hidden-import=langchain_openai ^
    --hidden-import=langchain.text_splitter ^
    --hidden-import=sqlalchemy ^
    --hidden-import=sqlalchemy.orm ^
    --hidden-import=pydantic ^
    --hidden-import=pydantic_settings ^
    --hidden-import=sse_starlette ^
    --hidden-import=rank_bm25 ^
    --hidden-import=uvicorn ^
    --hidden-import=uvicorn.loops ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols ^
    --hidden-import=uvicorn.protocols.http ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.lifespan ^
    --hidden-import=uvicorn.lifespan.on ^
    --hidden-import=starlette ^
    --hidden-import=fastapi ^
    --hidden-import=webview ^
    --hidden-import=webview.platforms.cef ^
    --hidden-import=webview.platforms.edgechromium ^
    --hidden-import=webview.guilib ^
    --hidden-import=webview.js ^
    --hidden-import=clr ^
    --hidden-import=pythonnet ^
    --hidden-import=dotenv ^
    --hidden-import=urllib3 ^
    --hidden-import=urllib3.util ^
    --hidden-import=urllib3.util.retry ^
    --hidden-import=certifi ^
    --hidden-import=multiprocessing ^
    --hidden-import=multiprocessing.pool ^
    --hidden-import=multiprocessing.process ^
    --hidden-import=concurrent.futures ^
    --hidden-import=shutil ^
    --hidden-import=tqdm ^
    --hidden-import=numpy ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=huggingface_hub ^
    --hidden-import=sklearn ^
    --hidden-import=scipy ^
    --collect-all=chromadb ^
    --collect-all=sentence_transformers ^
    --collect-all=transformers ^
    --copy-metadata=chromadb ^
    --copy-metadata=sentence_transformers ^
    --copy-metadata=transformers ^
    desktop_app.py

echo.
echo [3/3] 打包完成！
echo.
echo ============================================================
echo   输出文件: dist\电商AI助手.exe
echo.
echo   注意事项:
echo   1. 运行 exe 前请确保 .env 文件与 exe 同目录
echo   2. 首次启动会自动将 chroma_db 迁移到:
echo      %%APPDATA%%\EcomAIAgent\chroma_db\
echo      后续数据持久化存储，卸载不丢数据
echo   3. 首次启动会解压临时文件，启动较慢属正常现象
echo   4. sentence_transformers 模型文件已通过 --collect-all 收集
echo   5. 如遇到缺少模块错误，在 --hidden-import 中补充
echo ============================================================
pause
