# codex: 2025-11-25 生成 razaa_ce.csv 同款格式（中英两行、固定列数），兼容协程译者
"""
将 razfull.csv 中的标题和单词逐词翻译，输出与 razaa_ce.csv 相同结构：
表头：标题, 单词1..N
每本书两行：中文标题+中文词汇；英文标题+英文词汇。
"""

import asyncio
import csv
import sys
import time
from dataclasses import dataclass
from inspect import iscoroutine, iscoroutinefunction
from typing import Callable, List, Optional, Sequence, Tuple


def build_default_translator():
    """延迟导入默认翻译器，便于测试替换。"""
    try:
        from googletrans import Translator
    except ImportError as exc:  # pragma: no cover
        raise ImportError("请先安装 googletrans==4.0.0-rc1") from exc
    return Translator()


def parse_word_list(row: Sequence[str]) -> List[str]:
    """前两列为等级与书名，剩余列视为单词；去空白并过滤空字符串。"""
    words: List[str] = []
    for cell in row[2:]:
        cleaned = cell.strip()
        if cleaned:
            words.append(cleaned)
    return words


def _run_translate(translate_func, text: str, *, src: str, dest: str):
    """兼容同步/协程翻译函数与协程返回值。"""
    if iscoroutinefunction(translate_func):
        return asyncio.run(translate_func(text, src=src, dest=dest))
    result = translate_func(text, src=src, dest=dest)
    if iscoroutine(result):
        result = asyncio.run(result)
    return result


def translate_in_chunks(
    words: Sequence[str],
    translator,
    *,
    chunk_size: int = 10,
    pause_seconds: float = 0.5,
    src: str = "en",
    dest: str = "zh-cn",
    max_retries: int = 2,
    stats: Optional["TranslationStats"] = None,
    progress_callback: Optional[
        Callable[["TranslationStats", str, bool, int], None]
    ] = None,
) -> List[str]:
    """分块翻译单词；重试失败写占位。"""
    translated: List[str] = []
    translate_func = getattr(translator, "translate")

    for start in range(0, len(words), chunk_size):
        chunk = words[start : start + chunk_size]
        for word in chunk:
            attempt = 0
            last_error = None
            while attempt <= max_retries:
                try:
                    result = _run_translate(translate_func, word, src=src, dest=dest)
                    if hasattr(result, "text"):
                        translated.append(result.text)
                    elif isinstance(result, str):
                        translated.append(result)
                    elif result is not None:
                        translated.append(str(result))
                    else:
                        raise ValueError("翻译结果为空")
                    if stats:
                        stats.processed += 1
                        stats.success += 1
                        stats.retries += attempt
                    if progress_callback:
                        progress_callback(stats, word, True, attempt)
                    break
                except Exception as exc:  # pragma: no cover
                    last_error = exc
                    attempt += 1
                    if attempt <= max_retries:
                        time.sleep(pause_seconds or 0.2)
            else:
                translated.append(f"[翻译失败:{last_error}]")
                if stats:
                    stats.processed += 1
                    stats.fail += 1
                    stats.retries += max_retries
                if progress_callback:
                    progress_callback(stats, word, False, max_retries)
        if pause_seconds:
            time.sleep(pause_seconds)
    return translated


def compute_records(input_path: str) -> Tuple[List[Tuple[str, str, List[str]]], int]:
    """读取输入，返回 (level, title, words) 列表及最大单词数。"""
    records: List[Tuple[str, str, List[str]]] = []
    max_words = 0
    with open(input_path, "r", encoding="utf-8", newline="") as f_in:
        reader = csv.reader(f_in)
        header = next(reader, None)
        if header is None:
            return records, max_words
        for row in reader:
            if len(row) < 3:
                continue
            level, title = row[0].strip(), row[1].strip()
            words = parse_word_list(row)
            if not words:
                continue
            max_words = max(max_words, len(words))
            records.append((level, title, words))
    return records, max_words


def pad_words(words: List[str], max_words: int) -> List[str]:
    """将单词列表补齐到最大列数。"""
    return words + [""] * (max_words - len(words))


@dataclass
class TranslationStats:
    total_words: int = 0
    processed: int = 0
    success: int = 0
    fail: int = 0
    retries: int = 0


def process_file(
    input_path: str = "razfull.csv",
    output_path: str = "translated_output.csv",
    *,
    translator=None,
    chunk_size: int = 10,
    pause_seconds: float = 0.5,
    show_progress: bool = True,
) -> TranslationStats:
    """
    逐行解析并输出两行格式（中文行+英文章），表头为“标题,单词1..N”。
    不包含 RAZ 等级列，以保持与 razaa_ce.csv 一致。
    """
    translator = translator or build_default_translator()
    records, max_words = compute_records(input_path)
    if not records:
        return TranslationStats(total_words=0)

    stats = TranslationStats(total_words=sum(len(r[2]) for r in records))

    progress_callback = None
    if show_progress:
        def print_progress(s: TranslationStats, word: str, success: bool, attempts: int):
            status = "OK" if success else "FAIL"
            print(
                f"[{s.processed}/{s.total_words}] {status} {word} "
                f"(attempts:{attempts + 1}, retries_total:{s.retries})"
            )
        progress_callback = print_progress

    with open(output_path, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.writer(f_out)
        header_row = ["标题"] + [f"单词{i}" for i in range(1, max_words + 1)]
        writer.writerow(header_row)

        translate_func = getattr(translator, "translate")

        for _, title_en, words_en in records:
            title_result = _run_translate(
                translate_func, title_en, src="en", dest="zh-cn"
            )
            title_cn = (
                title_result.text
                if hasattr(title_result, "text")
                else str(title_result)
            )
            words_cn = translate_in_chunks(
                words_en,
                translator,
                chunk_size=chunk_size,
                pause_seconds=pause_seconds,
                stats=stats,
                progress_callback=progress_callback,
            )

            writer.writerow([title_cn] + pad_words(words_cn, max_words))
            writer.writerow([title_en] + pad_words(words_en, max_words))
    return stats


def main() -> None:
    """命令行入口：python translate.py [输入路径] [输出路径]"""
    input_path = sys.argv[1] if len(sys.argv) >= 2 else "razfull.csv"
    output_path = sys.argv[2] if len(sys.argv) >= 3 else "translated_output.csv"

    stats = process_file(input_path=input_path, output_path=output_path)
    print(
        f"翻译完成，结果已写入 {output_path}。\n"
        f"总单词: {stats.total_words}, 已处理: {stats.processed}, "
        f"成功: {stats.success}, 失败: {stats.fail}, 重试总数: {stats.retries}"
    )


if __name__ == "__main__":
    main()
