# codex: 2025-11-25 添加 translate 脚本单元测试
import csv
from pathlib import Path

import pytest

from translate import parse_word_list, process_file, translate_in_chunks


class DummyTranslator:
    """假翻译器，返回预设映射或默认附加后缀。"""

    def __init__(self, mapping=None):
        self.mapping = mapping or {}
        self.calls = []

    class _Result:
        def __init__(self, text):
            self.text = text

    def translate(self, text, src="en", dest="zh-cn"):
        self.calls.append((text, src, dest))
        translated = self.mapping.get(text, f"{text}-zh")
        return self._Result(translated)


def test_parse_word_list_trims_and_filters():
    row = ["aa", "Farm", " animals ", "", "dog", "  "]
    assert parse_word_list(row) == ["animals", "dog"]


def test_translate_in_chunks_calls_translator_once_per_word():
    translator = DummyTranslator({"cat": "猫", "dog": "狗"})
    result = translate_in_chunks(
        ["cat", "dog", "cow"],
        translator,
        chunk_size=2,
        pause_seconds=0,
    )
    assert result == ["猫", "狗", "cow-zh"]
    assert translator.calls == [
        ("cat", "en", "zh-cn"),
        ("dog", "en", "zh-cn"),
        ("cow", "en", "zh-cn"),
    ]


def test_process_file_writes_expected_rows(tmp_path: Path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_rows = [
        ["RAZ Level", "Book Title", "Word List"],
        ["aa", "Farm Animals", "cat", "dog"],
        ["bb", "Tree House", "tree", "house", ""],
    ]
    with input_path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(input_rows)

    translator = DummyTranslator({"cat": "猫", "dog": "狗", "tree": "树", "house": "房子"})
    process_file(
        input_path=str(input_path),
        output_path=str(output_path),
        translator=translator,
        chunk_size=10,
        pause_seconds=0,
    )

    with output_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["RAZ Level", "Book Title", "English", "Chinese"]
    assert rows[1:] == [
        ["aa", "Farm Animals", "cat", "猫"],
        ["aa", "Farm Animals", "dog", "狗"],
        ["bb", "Tree House", "tree", "树"],
        ["bb", "Tree House", "house", "房子"],
    ]
