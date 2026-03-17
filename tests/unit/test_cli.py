from src.cli import _sanitize
from src.papers.schemas import _format_author, _format_authors_short


class TestSanitize:
    def test_strips_ansi_codes(self):
        assert _sanitize("\x1b[31mred text\x1b[0m") == "red text"

    def test_strips_cursor_movement(self):
        assert _sanitize("\x1b[2Jhello") == "hello"

    def test_returns_empty_for_none(self):
        assert _sanitize("") == ""

    def test_passes_clean_text(self):
        assert _sanitize("normal text") == "normal text"


class TestFormatAuthor:
    def test_dict_author(self):
        assert _format_author({"last_name": "Zhang", "first_name": "Li"}) == "Zhang L"

    def test_dict_no_first_name(self):
        assert _format_author({"last_name": "Zhang", "first_name": ""}) == "Zhang"

    def test_fallback_to_str(self):
        assert _format_author("plain string") == "plain string"


class TestFormatAuthorsShort:
    def test_empty_list(self):
        assert _format_authors_short([]) == ""

    def test_one_author(self):
        authors = [{"last_name": "Zhang", "first_name": "Li"}]
        assert _format_authors_short(authors) == "Zhang L"

    def test_two_authors(self):
        authors = [
            {"last_name": "Zhang", "first_name": "Li"},
            {"last_name": "Chen", "first_name": "Wei"},
        ]
        assert _format_authors_short(authors) == "Zhang L, Chen W"

    def test_three_authors(self):
        authors = [
            {"last_name": "Zhang", "first_name": "Li"},
            {"last_name": "Chen", "first_name": "Wei"},
            {"last_name": "Park", "first_name": "Soo"},
        ]
        assert _format_authors_short(authors) == "Zhang L, Chen W et al."
