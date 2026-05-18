"""Tests for the MMD → Block translator (no nougat binary required)."""

from __future__ import annotations

from doc2latex.readers.nougat_reader import mmd_to_blocks


def test_headings_and_paragraphs():
    mmd = "# Title\n\nSome **body** text.\n\n## Sub\n\nAnother paragraph.\n"
    blocks = list(mmd_to_blocks(mmd))
    kinds = [b.kind for b in blocks]
    assert "heading" in kinds
    assert "para" in kinds
    headings = [b for b in blocks if b.kind == "heading"]
    assert headings[0].level == 1
    assert any(b.level == 2 for b in headings)


def test_unordered_list():
    mmd = "- one\n- two\n- three\n"
    blocks = list(mmd_to_blocks(mmd))
    lists = [b for b in blocks if b.kind == "list"]
    assert len(lists) == 1
    assert lists[0].items == ["one", "two", "three"]
    assert lists[0].ordered is False


def test_ordered_list():
    mmd = "1. one\n2. two\n"
    blocks = list(mmd_to_blocks(mmd))
    lists = [b for b in blocks if b.kind == "list"]
    assert lists and lists[0].ordered is True


def test_display_and_inline_math():
    mmd = r"some text \(x^2\) more text" + "\n\n\\[ a = b + c \\]\n"
    blocks = list(mmd_to_blocks(mmd))
    eqs = [b for b in blocks if b.kind == "equation"]
    assert any("a = b + c" in b.content for b in eqs)
    paras = [b for b in blocks if b.kind == "para"]
    assert any("$x^2$" in b.content for b in paras)


def test_image_reference():
    mmd = "![cap](fig1.png)\n"
    blocks = list(mmd_to_blocks(mmd))
    figs = [b for b in blocks if b.kind == "figure"]
    assert figs and figs[0].content == "fig1.png"
    assert figs[0].caption == "cap"
