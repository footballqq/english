# codex: 2025-11-27 ��֤ kid_quiz ���� UTF-8 ��������移动端��
import re
from pathlib import Path


def test_csv_is_utf8_without_errors():
    data = Path("razfulltranslate666.csv").read_bytes()
    text = data.decode("utf-8")  # �澯��ֱ��ʧ��
    assert "单词1" in text.splitlines()[0]


def test_kid_quiz_prefers_utf8_decoder():
    html = Path("kid_quiz.html").read_text(encoding="utf-8")
    assert "TextDecoder('utf-8', { fatal: true })" in html
    utf8_pos = html.find("TextDecoder('utf-8'")
    gbk_pos = html.find("TextDecoder('gbk'")
    assert utf8_pos != -1 and gbk_pos != -1 and utf8_pos < gbk_pos
