# codex: 2025-11-25 调整 razfull.csv 解析与同步翻译
"""
将 razfull.csv 中的单词列表逐词翻译为中文，并输出四列结构：
RAZ Level, Book Title, English, Chinese。
"""

import csv
import time
from typing import List, Sequence


def build_default_translator():
    """构造默认翻译器，延迟导入以便测试时可注入假实现。"""
    try:
        from googletrans import Translator
    except ImportError as exc:  # pragma: no cover - 环境缺依赖时提醒
        raise ImportError("请先安装 googletrans==4.0.0-rc1") from exc

    return Translator()


def parse_word_list(row: Sequence[str]) -> List[str]:
    """
    从一行中提取单词列表。前两列为等级和书名，剩余列均视为单词。
    会去除空白并过滤空字符串。
    """
    words = []
    for cell in row[2:]:
        cleaned = cell.strip()
        if cleaned:
            words.append(cleaned)
    return words


def translate_in_chunks(
    words: Sequence[str],
    translator,
    *,
    chunk_size: int = 10,
    pause_seconds: float = 0.5,
    src: str = "en",
    dest: str = "zh-cn",
) -> List[str]:
    """
    分块翻译单词，出现异常时为对应单词写入占位错误信息。
    """
    translated: List[str] = []
    for start in range(0, len(words), chunk_size):
        chunk = words[start : start + chunk_size]
        for word in chunk:
            try:
                result = translator.translate(word, src=src, dest=dest)
                translated.append(result.text)
            except Exception as exc:  # pragma: no cover - 依赖外部服务
                translated.append(f"[翻译失败:{exc}]")
        if pause_seconds:
            time.sleep(pause_seconds)
    return translated


def process_file(
    input_path: str = "razfull.csv",
    output_path: str = "translated_output.csv",
    *,
    translator=None,
    chunk_size: int = 10,
    pause_seconds: float = 0.5,
) -> None:
    """
    将输入文件逐行解析并写出翻译结果。
    """
    translator = translator or build_default_translator()

    with open(input_path, "r", encoding="utf-8", newline="") as f_in, open(
        output_path, "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        writer.writerow(["RAZ Level", "Book Title", "English", "Chinese"])

        # 跳过表头
        header = next(reader, None)
        if header is None:
            return

        for row_index, row in enumerate(reader, start=1):
            if len(row) < 3:
                continue
            level, title = row[0].strip(), row[1].strip()
            words = parse_word_list(row)
            if not words:
                continue

            translated_words = translate_in_chunks(
                words,
                translator,
                chunk_size=chunk_size,
                pause_seconds=pause_seconds,
            )

            for english, chinese in zip(words, translated_words):
                writer.writerow([level, title, english, chinese])


def main() -> None:
    """脚本入口。"""
    process_file()
    print("翻译完成，结果已写入 translated_output.csv。")


if __name__ == "__main__":
    main()
