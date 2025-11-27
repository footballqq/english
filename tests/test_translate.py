# codex: 2025-11-25 校验 translate 脚本的解析、协程兼容与 razaa_ce 输出格式
import asyncio
import csv
from pathlib import Path

import pytest

from translate import (
    TranslationStats,
    parse_word_list,
    process_file,
    translate_in_chunks,
)


class DummyTranslator:
    """假翻译器，返回预设映射或附加后缀。"""

    def __init__(self, mapping=None):
        self.mapping = mapping or {}
        self.calls = []

    class _Result:
        def __init__(self, text):
            self.text = text

    async def translate(self, text, src="en", dest="zh-cn"):
        self.calls.append((text, src, dest))
        translated = self.mapping.get(text, f"{text}-zh")
        return self._Result(translated)


def test_parse_word_list_trims_and_filters():
    row = ["aa", "Farm", " animals ", "", "dog", "  "]
    assert parse_word_list(row) == ["animals", "dog"]


def test_translate_in_chunks_calls_translator_once_per_word():
    translator = DummyTranslator({"cat": "猫", "dog": "狗"})
    stats = TranslationStats(total_words=3)
    result = asyncio.run(
        translate_in_chunks(
            ["cat", "dog", "cow"],
            translator,
            chunk_size=2,
            pause_seconds=0,
            stats=stats,
        )
    )
    assert result == ["猫", "狗", "cow-zh"]
    assert translator.calls == [
        ("cat", "en", "zh-cn"),
        ("dog", "en", "zh-cn"),
        ("cow", "en", "zh-cn"),
    ]
    assert stats.processed == 3 and stats.success == 3 and stats.fail == 0


class AsyncTranslator:
    """translate 返回协程结果。"""

    class _Result:
        def __init__(self, text):
            self.text = text

    async def translate(self, text, src="en", dest="zh-cn"):
        return self._Result(f"{text}-async")


def test_translate_in_chunks_handles_coroutine_result():
    translator = AsyncTranslator()
    result = asyncio.run(
        translate_in_chunks(
            ["bird", "cat"],
            translator,
            chunk_size=1,
            pause_seconds=0,
        )
    )
    assert result == ["bird-async", "cat-async"]


class AsyncFuncTranslator:
    """translate 为协程函数。"""

    class _Result:
        def __init__(self, text):
            self.text = text

    async def translate(self, text, src="en", dest="zh-cn"):
        return self._Result(f"{text}-async-func")


def test_translate_in_chunks_handles_coroutine_function():
    translator = AsyncFuncTranslator()
    result = asyncio.run(
        translate_in_chunks(
            ["ant", "bee"],
            translator,
            chunk_size=2,
            pause_seconds=0,
        )
    )
    assert result == ["ant-async-func", "bee-async-func"]


def test_translate_in_chunks_handles_none_result_with_retry():
    class NoneOnceTranslator(DummyTranslator):
        def __init__(self):
            super().__init__({"ok": "好"})
            self.seen = False

        async def translate(self, text, src="en", dest="zh-cn"):
            if not self.seen:
                self.seen = True
                return None
            return await super().translate(text, src=src, dest=dest)

    translator = NoneOnceTranslator()
    result = asyncio.run(
        translate_in_chunks(
            ["ok"],
            translator,
            chunk_size=1,
            pause_seconds=0,
        )
    )
    assert result == ["好"]


def test_translate_in_chunks_gives_placeholder_after_retries():
    class AlwaysFailTranslator:
        async def translate(self, text, src="en", dest="zh-cn"):
            raise RuntimeError("boom")

    stats = TranslationStats(total_words=1)
    result = asyncio.run(
        translate_in_chunks(
            ["fail"],
            AlwaysFailTranslator(),
            chunk_size=1,
            pause_seconds=0,
            stats=stats,
        )
    )
    assert len(result) == 1 and result[0].startswith("[翻译失败:")
    assert stats.fail == 1 and stats.processed == 1


def test_process_file_outputs_razaa_ce_like_rows(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_rows = [
        ["RAZ Level", "Book Title", "Word List"],
        ["aa", "Farm Animals", "cat", "dog"],
        ["bb", "Tree House", "tree", "house", ""],
    ]
    with input_path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(input_rows)

    translator = DummyTranslator(
        {
            "Farm Animals": "农场动物",
            "Tree House": "树屋",
            "cat": "猫",
            "dog": "狗",
            "tree": "树",
            "house": "房子",
        }
    )
    asyncio.run(
        process_file(
            input_path=str(input_path),
            output_path=str(output_path),
            translator=translator,
            chunk_size=10,
            pause_seconds=0,
            show_progress=False,
        )
    )

    with output_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["RAZ Level", "Book Title", "单词1", "单词2"]
    assert rows[1:] == [
        ["aa", translator.mapping["Farm Animals"], translator.mapping["cat"], translator.mapping["dog"]],
        ["aa", "Farm Animals", "cat", "dog"],
        ["bb", translator.mapping["Tree House"], translator.mapping["tree"], translator.mapping["house"]],
        ["bb", "Tree House", "tree", "house"],
    ]


def test_process_file_returns_stats(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_rows = [
        ["RAZ Level", "Book Title", "Word List"],
        ["aa", "One Book", "a", "b"],
    ]
    with input_path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(input_rows)

    translator = DummyTranslator({"One Book": "一本书", "a": "啊", "b": "波"})
    stats = asyncio.run(
        process_file(
            input_path=str(input_path),
            output_path=str(output_path),
            translator=translator,
            chunk_size=10,
            pause_seconds=0,
            show_progress=False,
        )
    )
    assert stats.total_words == 2
    assert stats.processed == 2
    assert stats.success == 2
    assert stats.fail == 0
