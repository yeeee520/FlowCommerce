"""
scripts/seed_data.py — 种子数据初始化脚本

将 sample_dialogues.json 中的示例对话数据导入知识库。
用于开发和演示环境快速搭建。

用法:
    python scripts/seed_data.py

接口契约（供后端 Agent 实现）：
    main() -> None
        读取 data/sample_dialogues.json，调用 DataPipeline.run() 导入
"""

import json
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中，以便导入项目模块
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from data_platform.pipeline import DataPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_sample_data() -> list[dict]:
    """
    加载示例对话数据

    Returns:
        对话数据列表
    """
    data_path = _PROJECT_ROOT / "data" / "sample_dialogues.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    """
    主函数：加载数据并导入知识库

    流程：
    1. 调用 load_sample_data() 加载数据
    2. 调用 DataPipeline.run() 完成清洗+向量化
    3. 打印导入统计
    """
    data = load_sample_data()
    logger.info(f"加载了 {len(data)} 条商品对话数据")

    data_path = _PROJECT_ROOT / "data" / "sample_dialogues.json"

    def on_progress(current: int, total: int) -> None:
        """进度回调"""
        pct = current / total * 100 if total > 0 else 0
        print(f"\r处理进度: {current}/{total} ({pct:.1f}%)", end="", flush=True)

    print("开始执行 ETL 流水线...")
    pipeline = DataPipeline()
    result = pipeline.run(source_path=str(data_path), on_progress=on_progress)
    print()  # 换行

    print("\n========== 导入完成 ==========")
    print(f"  总计:   {result['total']} 条")
    print(f"  清洗成功: {result['cleaned']} 条")
    print(f"  入库成功: {result['embedded']} 条")
    print(f"  失败:   {result['failed']} 条")
    print("================================")

    if result["failed"] > 0:
        logger.warning(f"有 {result['failed']} 条数据导入失败")
    else:
        logger.info("所有数据导入成功!")


if __name__ == "__main__":
    main()
