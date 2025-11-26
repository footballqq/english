# codex: 2025-11-25 生成 razaa_ce.csv 同款格式（中英两行、固定列数），兼容协程译者
"""
将 razfull.csv 中的标题和单词逐词翻译，输出与 razaa_ce.csv 相同结构：
表头：标题, 单词1..N
每本书两行：中文标题+中文词汇；英文标题+英文词汇。
"""

import argparse
import asyncio
import csv
import os
import sys
from dataclasses import dataclass
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


async def translate_in_chunks(
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
                    result = await translate_func(word, src=src, dest=dest)
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
                        await asyncio.sleep(pause_seconds or 0.2)
            else:
                translated.append(f"[翻译失败:{last_error}]")
                if stats:
                    stats.processed += 1
                    stats.fail += 1
                    stats.retries += max_retries
                if progress_callback:
                    progress_callback(stats, word, False, max_retries)
        if pause_seconds:
            await asyncio.sleep(pause_seconds)
    return translated


def get_processed_titles(output_path: str) -> set[str]:
    """从已存在的输出文件中读取并返回已处理过的英文书名集合。"""
    processed = set()
    if not os.path.exists(output_path):
        return processed
    with open(output_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
            title_idx = header.index("Book Title")
        except (StopIteration, ValueError):
            return processed  # 文件为空或表头不正确

        # 每两行（中文、英文）构成一个记录
        while True:
            try:
                _ = next(reader)  # 跳过中文行
                row_en = next(reader)
                if len(row_en) > title_idx:
                    processed.add(row_en[title_idx])
            except StopIteration:
                break
    return processed


def compute_records(
    input_path: str, limit: Optional[int] = None
) -> Tuple[List[Tuple[str, str, List[str]]], int]:
    """读取输入，返回 (level, title, words) 列表及最大单词数。"""
    records: List[Tuple[str, str, List[str]]] = []
    max_words = 0
    with open(input_path, "r", encoding="utf-8", newline="") as f_in:
        reader = csv.reader(f_in)
        header = next(reader, None)
        if header is None:
            return records, max_words
        for i, row in enumerate(reader):
            if limit is not None and i >= limit:
                print(f"已达到处理行数上限 ({limit})。")
                break
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


async def process_file(
    input_path: str = "razfull.csv",
    output_path: str = "translated_output.csv",
    *,
    translator=None,
    chunk_size: int = 10,
    pause_seconds: float = 0.5,
    show_progress: bool = True,
    limit: Optional[int] = None,
    resume: bool = False,
) -> TranslationStats:
    """
    逐行解析并输出两行格式（中文行+英文章），表头为“RAZ Level,Book Title,单词1..N”。
    包含 RAZ 等级列和书名。
    """
    translator = translator or build_default_translator()

    # Resume logic
    processed_titles = set()
    if resume:
        processed_titles = get_processed_titles(output_path)
        if processed_titles:
            print(f"断点续传模式：检测到 {len(processed_titles)} 个已处理书目，将跳过。")

    records, max_words = compute_records(input_path, limit=limit)
    if not records:
        return TranslationStats(total_words=0)

    # Filter records if resuming
    records_to_process = [r for r in records if r[1] not in processed_titles]
    if not records_to_process:
        print("所有书目均已处理完毕。")
        return TranslationStats()

    stats = TranslationStats(total_words=sum(len(r[2]) for r in records_to_process))

    progress_callback = None
    if show_progress:

        def print_progress(
            s: TranslationStats, word: str, success: bool, attempts: int
        ):
            status = "OK" if success else "FAIL"
            print(
                f"[{s.processed}/{s.total_words}] {status} {word} "
                f"(attempts:{attempts + 1}, retries_total:{s.retries})"
            )

        progress_callback = print_progress

    open_mode = "a" if resume else "w"
    is_new_file = not os.path.exists(output_path) or os.path.getsize(output_path) == 0

    with open(output_path, open_mode, encoding="utf-8", newline="") as f_out:
        writer = csv.writer(f_out)
        if is_new_file:
            header_row = ["RAZ Level", "Book Title"] + [
                f"单词{i}" for i in range(1, max_words + 1)
            ]
            writer.writerow(header_row)

        translate_func = getattr(translator, "translate")

        for level, title_en, words_en in records_to_process:
            title_result = await translate_func(title_en, src="en", dest="zh-cn")
            title_cn = (
                title_result.text
                if hasattr(title_result, "text")
                else str(title_result)
            )
            words_cn = await translate_in_chunks(
                words_en,
                translator,
                chunk_size=chunk_size,
                pause_seconds=pause_seconds,
                stats=stats,
                progress_callback=progress_callback,
            )

            writer.writerow([level, title_cn] + pad_words(words_cn, max_words))
            writer.writerow([level, title_en] + pad_words(words_en, max_words))
            f_out.flush()  # Immediately save progress
    return stats


async def re_translate_failures(
    input_path: str,
    output_path: str,
    *,
    translator=None,
    chunk_size: int = 10,
    pause_seconds: float = 0.5,
    show_progress: bool = True,
) -> TranslationStats:
    """读取包含失败标记的文件，仅重试失败的单词，并生成一个全新的、修正过的文件。"""
    translator = translator or build_default_translator()
    stats = TranslationStats()  # Stats will be for retried words

    print(f"错误恢复模式：正在读取 '{input_path}'...")

    with open(input_path, "r", encoding="utf-8", newline="") as f_in, open(
        output_path, "w", encoding="utf-8", newline=""
    ) as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)

        try:
            header = next(reader)
            writer.writerow(header)
            title_idx = header.index("Book Title")
        except (StopIteration, ValueError):
            print("错误：输入文件为空或表头不正确。")
            return stats

        while True:
            try:
                row_cn = next(reader)
                row_en = next(reader)
            except StopIteration:
                break

            words_to_retry_indices = []
            words_to_retry_en = []

            # Words start at index 2 (after Level and Title)
            for i in range(2, len(row_cn)):
                if row_cn[i].strip().startswith("[翻译失败"):
                    words_to_retry_indices.append(i)
                    if i < len(row_en):
                        words_to_retry_en.append(row_en[i])

            if not words_to_retry_en:
                writer.writerow(row_cn)
                writer.writerow(row_en)
                continue

            print(f"书目 '{row_en[title_idx]}': 找到 {len(words_to_retry_en)} 个失败单词，正在重试...")
            stats.total_words += len(words_to_retry_en)

            newly_translated_words = await translate_in_chunks(
                words_to_retry_en,
                translator,
                chunk_size=chunk_size,
                pause_seconds=pause_seconds,
                stats=stats,
                progress_callback=None,  # Simplified progress for retry
            )

            new_row_cn = list(row_cn)
            for i, translated_word in enumerate(newly_translated_words):
                original_index = words_to_retry_indices[i]
                new_row_cn[original_index] = translated_word

            writer.writerow(new_row_cn)
            writer.writerow(row_en)
            f_out.flush()

    return stats


def main() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="翻译 razfull.csv 文件，并生成双语对照 CSV。",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        default="razfull.csv",
        help="输入 CSV 文件路径。",
    )
    parser.add_argument(
        "output_path",
        nargs="?",
        default="translated_output.csv",
        help="输出 CSV 文件路径。",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="要处理的最大行数（用于测试）。"
    )
    parser.add_argument(
        "--resume", action="store_true", help="从已部分完成的输出文件中继续翻译。"
    )
    parser.add_argument(
        "--retry-failures",
        action="store_true",
        help="对一个已完成但包含翻译失败条目的文件进行重试。",
    )

    args = parser.parse_args()

    if args.resume and args.retry_failures:
        print("错误：--resume 和 --retry-failures 参数不能同时使用。")
        sys.exit(1)

    try:
        if args.retry_failures:
            print("启动错误恢复模式...")
            stats = asyncio.run(
                re_translate_failures(
                    input_path=args.input_path,
                    output_path=args.output_path,
                )
            )
            print(
                f"\n错误恢复完成，结果已写入 {args.output_path}.\n"
                f"重试单词总数: {stats.total_words}, 成功: {stats.success}, 失败: {stats.fail}"
            )
        else:
            print(f"开始处理文件: {args.input_path}")
            if args.limit:
                print(f"仅处理前 {args.limit} 行。")
            if args.resume:
                print("启用断点续传模式。")

            stats = asyncio.run(
                process_file(
                    input_path=args.input_path,
                    output_path=args.output_path,
                    limit=args.limit,
                    resume=args.resume,
                )
            )
            print(
                f"\n翻译完成，结果已写入 {args.output_path}.\n"
                f"总单词: {stats.total_words}, 已处理: {stats.processed}, "
                f"成功: {stats.success}, 失败: {stats.fail}, 重试总数: {stats.retries}"
            )
    except KeyboardInterrupt:
        print("\n操作被用户中断。程序已终止。")
    except FileNotFoundError:
        print(f"\n错误：输入文件未找到于 '{args.input_path}'")


if __name__ == "__main__":
    main()
