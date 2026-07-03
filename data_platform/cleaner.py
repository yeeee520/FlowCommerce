"""
data_platform.cleaner — 数据清洗器

负责原始商品数据的清洗、标准化、去重等预处理操作。
"""

import logging
import re
from datetime import datetime
from typing import Optional

from config import MAX_RETRIES
from data_platform.models import CleaningLog

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    数据清洗器

    对原始商品文本进行清洗，包括：
    - HTML 标签去除
    - 特殊字符清理
    - 空白字符规范化
    - 表情符号去除
    - 标点统一

    接口契约：
        clean(raw_text: str) -> tuple[str, CleaningLog]
            - 参数: raw_text — 待清洗的原始文本
            - 返回: (清洗后文本, 清洗日志记录)
            - 清洗失败时返回 (原始文本, 含错误信息的日志)

        batch_clean(texts: list[str]) -> list[tuple[str, CleaningLog]]
            - 参数: texts — 待批量清洗的文本列表
            - 返回: [(清洗后文本, 日志), ...] 与输入一一对应
    """

    # HTML 标签正则
    _HTML_TAG_PATTERN: re.Pattern = re.compile(r"<[^>]*>")
    # 多余空白正则
    _MULTI_SPACE_PATTERN: re.Pattern = re.compile(r"\s+")
    # 表情符号正则（覆盖 Emoji、杂项符号、装饰符号等）
    _EMOJI_PATTERN: re.Pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed chars
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended-A
        "\U00002600-\U000026FF"  # misc symbols
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U0000200D"             # zero-width joiner
        "]+",
        flags=re.UNICODE,
    )
    # 中文标点映射为英文标点
    _PUNCTUATION_MAP: dict[int, int] = str.maketrans(
        {
            "\u201c": '"',   # "
            "\u201d": '"',   # "
            "\u2018": "'",   # '
            "\u2019": "'",   # '
            "\uff0c": ",",   # ，
            "\uff1a": ":",   # ：
            "\uff1b": ";",   # ；
            "\uff01": "!",   # ！
            "\uff1f": "?",   # ？
            "\u3001": ",",   # 、
            "\u3002": ".",   # 。
            "\uff08": "(",   # （
            "\uff09": ")",   # ）
            "\u3010": "[",   # 【
            "\u3011": "]",   # 】
        }
    )

    def clean(self, raw_text: str) -> tuple[str, CleaningLog]:
        """
        清洗单条文本

        步骤：
        1. 去除 HTML 标签
        2. 去除表情符号
        3. 统一中文标点为英文标点
        4. 规范化空白字符
        5. 去除首尾空白

        Args:
            raw_text: 原始文本

        Returns:
            (cleaned_text, log): 清洗结果与日志
        """
        log_entry = CleaningLog(
            raw_text=raw_text,
            status="pending",
            created_at=datetime.utcnow(),
        )
        try:
            text = raw_text
            # 1. 去除 HTML 标签
            text = self._HTML_TAG_PATTERN.sub("", text)
            # 2. 去除表情符号
            text = self._EMOJI_PATTERN.sub("", text)
            # 3. 统一中文标点为英文标点
            text = text.translate(self._PUNCTUATION_MAP)
            # 4. 规范化空白（多个空白合并为一个空格）
            text = self._MULTI_SPACE_PATTERN.sub(" ", text)
            # 5. 去除首尾空白
            text = text.strip()

            log_entry.cleaned_text = text
            log_entry.status = "success"
            logger.debug(f"清洗成功: 原始长度 {len(raw_text)} -> 清洗后长度 {len(text)}")
            return text, log_entry

        except Exception as exc:
            log_entry.status = "failed"
            log_entry.error_message = str(exc)
            log_entry.cleaned_text = None
            logger.warning(f"清洗失败: {exc}")
            return raw_text, log_entry

    def batch_clean(self, texts: list[str]) -> list[tuple[str, CleaningLog]]:
        """
        批量清洗文本，支持重试机制

        每条文本独立清洗，失败时重试最多 MAX_RETRIES 次。
        某条文本失败不影响其他文本的清洗。

        Args:
            texts: 原始文本列表

        Returns:
            [(cleaned_text, log), ...] 与输入顺序一致
        """
        results: list[tuple[str, CleaningLog]] = []
        for idx, text in enumerate(texts):
            success = False
            last_result: Optional[tuple[str, CleaningLog]] = None
            for attempt in range(1, MAX_RETRIES + 1):
                result = self.clean(text)
                if result[1].status == "success":
                    success = True
                    results.append(result)
                    break
                last_result = result
                logger.warning(
                    f"文本 {idx} 第 {attempt}/{MAX_RETRIES} 次清洗失败，"
                    f"错误: {result[1].error_message}"
                )
            if not success:
                # 所有重试均失败，返回最后一次的结果
                if last_result is not None:
                    results.append(last_result)
                else:
                    # 极端情况：clean 本身抛异常
                    log = CleaningLog(
                        raw_text=text,
                        status="failed",
                        error_message="批量清洗: clean 返回异常",
                        created_at=datetime.utcnow(),
                    )
                    results.append((text, log))
        return results
