"""Tests for text processing and file parsing utilities."""

import os
import tempfile

import pytest

from app.utils.file_parser import FileParser, split_text_into_chunks, _read_text_with_fallback
from app.services.text_processor import TextProcessor


# --------------- split_text_into_chunks ---------------

class TestSplitTextIntoChunks:
    def test_empty_text(self):
        assert split_text_into_chunks("", 100, 10) == []

    def test_whitespace_only(self):
        assert split_text_into_chunks("   \n\n  ", 100, 10) == []

    def test_smaller_than_chunk_size(self):
        text = "Hello world"
        assert split_text_into_chunks(text, 100, 10) == [text]

    def test_exact_chunk_size(self):
        text = "A" * 50
        assert split_text_into_chunks(text, 50, 10) == [text]

    def test_simple_split_no_overlap(self):
        text = "A" * 100 + "B" * 100
        result = split_text_into_chunks(text, 50, 0)
        # No sentence boundaries: splits every 50 chars → 200/50 = 4 chunks
        assert len(result) == 4

    def test_split_with_overlap(self):
        text = "A" * 30 + "B" * 30 + "C" * 30
        result = split_text_into_chunks(text, 30, 10)
        assert len(result) >= 2

    def test_split_at_sentence_boundary_chinese_period(self):
        chunk_size = 30
        text = "今天天气不错。" + "A" * 30
        result = split_text_into_chunks(text, chunk_size, 5)
        assert len(result) >= 2
        assert "今天天气不错。" in result[0]

    def test_no_sentence_boundary_splits_anyway(self):
        text = "A" * 100
        result = split_text_into_chunks(text, 30, 0)
        assert len(result) == 4

    def test_strips_whitespace_from_chunks(self):
        text = "A" * 100 + "  B  " + "C" * 100
        result = split_text_into_chunks(text, 30, 5)
        assert all(c == c.strip() for c in result)


# --------------- FileParser ---------------

class TestFileParser:
    def test_unsupported_extension(self):
        with pytest.raises((ValueError, FileNotFoundError)):
            FileParser.extract_text("file.xyz")

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            FileParser.extract_text("nonexistent_file.pdf")

    def test_extract_text_from_txt(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("Hello from txt")
            tmp_path = f.name
        try:
            text = FileParser.extract_text(tmp_path)
            assert text == "Hello from txt"
        finally:
            os.unlink(tmp_path)

    def test_extract_from_md(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", newline="", delete=False
        ) as f:
            f.write("# Markdown\ncontent")
            tmp_path = f.name
        try:
            text = FileParser.extract_text(tmp_path)
            assert text == "# Markdown\ncontent"
        finally:
            os.unlink(tmp_path)

    def test_extract_from_multiple(self):
        with (
            tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", encoding="utf-8", delete=False
            ) as f1,
            tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", encoding="utf-8", delete=False
            ) as f2,
        ):
            f1.write("File1 content")
            f2.write("File2 content")
            p1, p2 = f1.name, f2.name

        try:
            result = FileParser.extract_from_multiple([p1, p2])
            assert "File1 content" in result
            assert "File2 content" in result
            assert "文档 1" in result
        finally:
            os.unlink(p1)
            os.unlink(p2)

    def test_extract_from_multiple_with_failure(self):
        result = FileParser.extract_from_multiple(["/nonexistent/file.txt"])
        assert "提取失败" in result

    def test_read_text_with_fallback_utf8(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write("UTF-8 content".encode("utf-8"))
            tmp_path = f.name
        try:
            assert _read_text_with_fallback(tmp_path) == "UTF-8 content"
        finally:
            os.unlink(tmp_path)

    def test_read_text_with_fallback_gb18030(self):
        """Detecting GB18030 depends on external libs and OS locale — skip."""
        pytest.skip("encoding detection is environment-dependent")


# --------------- TextProcessor ---------------

class TestTextProcessor:
    def test_split_text(self, sample_text):
        chunks = TextProcessor.split_text(sample_text, chunk_size=30, overlap=5)
        assert len(chunks) >= 2
        assert all(isinstance(c, str) for c in chunks)

    def test_preprocess_text_normalize_newlines(self):
        text = "Line1\r\nLine2\rLine3"
        result = TextProcessor.preprocess_text(text)
        assert "\r" not in result

    def test_preprocess_text_collapse_blank_lines(self):
        text = "A\n\n\n\n\nB"
        result = TextProcessor.preprocess_text(text)
        assert "\n\n\n" not in result

    def test_preprocess_text_strips_lines(self):
        text = "  Hello  \n  World  "
        result = TextProcessor.preprocess_text(text)
        lines = result.split("\n")
        assert all(line == line.strip() for line in lines)

    def test_preprocess_text_strips_outer(self):
        text = "  \nHello\n  "
        result = TextProcessor.preprocess_text(text)
        assert result == "Hello"

    def test_get_text_stats(self, sample_text):
        stats = TextProcessor.get_text_stats(sample_text)
        assert stats["total_chars"] == len(sample_text)
        assert stats["total_lines"] == sample_text.count("\n") + 1
        assert stats["total_words"] == len(sample_text.split())

    def test_get_text_stats_empty(self):
        stats = TextProcessor.get_text_stats("")
        assert stats["total_chars"] == 0
        assert stats["total_lines"] == 1
        assert stats["total_words"] == 0

    def test_extract_from_files(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("TextProcessor test")
            tmp_path = f.name
        try:
            result = TextProcessor.extract_from_files([tmp_path])
            assert "TextProcessor test" in result
        finally:
            os.unlink(tmp_path)
