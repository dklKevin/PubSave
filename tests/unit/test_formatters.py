"""Tests for src.papers.formatters."""

from types import SimpleNamespace

import pytest

from src.papers.formatters import (
    extract_tag_names,
    format_author,
    format_authors_short,
)


class TestFormatAuthor:
    def test_dict_author(self):
        assert format_author({"last_name": "Zhang", "first_name": "Wei"}) == "Zhang W"

    def test_dict_no_first_name(self):
        assert format_author({"last_name": "Zhang", "first_name": ""}) == "Zhang"

    def test_object_author(self):
        a = SimpleNamespace(last_name="Lee", first_name="Kevin")
        assert format_author(a) == "Lee K"

    def test_fallback_to_str(self):
        assert format_author(42) == "42"


class TestFormatAuthorsShort:
    def test_empty(self):
        assert format_authors_short([]) == ""

    def test_one_author(self):
        authors = [{"last_name": "Zhang", "first_name": "Wei"}]
        assert format_authors_short(authors) == "Zhang W"

    def test_two_authors(self):
        authors = [
            {"last_name": "Zhang", "first_name": "Wei"},
            {"last_name": "Lee", "first_name": "Kevin"},
        ]
        assert format_authors_short(authors) == "Zhang W, Lee K"

    def test_three_plus_authors(self):
        authors = [
            {"last_name": "A", "first_name": "X"},
            {"last_name": "B", "first_name": "Y"},
            {"last_name": "C", "first_name": "Z"},
        ]
        assert format_authors_short(authors) == "A X, B Y et al."


class TestExtractTagNames:
    def test_strings_passthrough(self):
        assert extract_tag_names(["ml", "bio"]) == ["ml", "bio"]

    def test_empty_list(self):
        assert extract_tag_names([]) == []

    def test_objects_with_name(self):
        tags = [SimpleNamespace(name="ml"), SimpleNamespace(name="bio")]
        assert extract_tag_names(tags) == ["ml", "bio"]

    def test_dicts_with_name(self):
        tags = [{"name": "ml", "id": 1}, {"name": "bio", "id": 2}]
        assert extract_tag_names(tags) == ["ml", "bio"]

    def test_unknown_type_raises(self):
        with pytest.raises(TypeError, match="Cannot extract tag names from int"):
            extract_tag_names([42, 43])
