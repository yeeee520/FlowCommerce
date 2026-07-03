"""启动脚本 - 从 .env 加载环境变量并启动 FastAPI"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 从 .env 文件加载环境变量（.env 不会提交到 Git，安全）
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, os.path.dirname(__file__))

import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("API_PORT", "8000")), reload=False)
