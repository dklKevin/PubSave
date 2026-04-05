"""CLI command tests — mock httpx.Client to test every command path."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.cli import (
    EXIT_CANCELLED,
    EXIT_ERROR,
    EXIT_OK,
    _get_client,
    _get_version,
    _handle_error,
    _print_paper_detail,
    _print_semantic_results,
    _resolve_id,
    _validate_base_url,
    cmd_ask,
    cmd_embed_all,
    cmd_fetch,
    cmd_get,
    cmd_ls,
    cmd_rm,
    cmd_search,
    cmd_tag,
    cmd_tags,
    cmd_untag,
    main,
)


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = json.dumps(json_data or {})
    return resp


def _make_args(**overrides):
    defaults = {
        "json_output": False,
        "full": False,
        "page": 1,
        "limit": 20,
    }
    args = MagicMock()
    for k, v in {**defaults, **overrides}.items():
        setattr(args, k, v)
    return args


class TestValidateBaseUrl:
    def test_valid_https(self):
        assert _validate_base_url("https://api.example.com") == "https://api.example.com"

    def test_valid_localhost_http(self):
        assert _validate_base_url("http://localhost:8000") == "http://localhost:8000"

    def test_strips_trailing_slash(self):
        assert _validate_base_url("http://localhost:8000/") == "http://localhost:8000"

    def test_invalid_scheme_exits(self):
        with pytest.raises(SystemExit):
            _validate_base_url("ftp://example.com")

    def test_missing_host_exits(self):
        with pytest.raises(SystemExit):
            _validate_base_url("http://")


class TestGetClient:
    def test_returns_client_and_base(self):
        client, base = _get_client()
        assert base == "http://localhost:8000"
        client.close()

    @patch.dict("os.environ", {"PUBSAVE_URL": "https://api.test.com"})
    def test_uses_env_var(self):
        client, base = _get_client()
        assert base == "https://api.test.com"
        client.close()


class TestHandleError:
    def test_passes_on_success(self):
        resp = _mock_response(200)
        _handle_error(resp)

    def test_exits_on_400(self):
        resp = _mock_response(400, {"error": "Bad request"})
        with pytest.raises(SystemExit):
            _handle_error(resp)

    def test_exits_on_500(self):
        resp = _mock_response(500, {"detail": "Internal error"})
        with pytest.raises(SystemExit):
            _handle_error(resp)


class TestResolveId:
    def test_full_uuid_returned_as_is(self):
        full_id = "12345678-1234-1234-1234-123456789012"
        result = _resolve_id(MagicMock(), "http://test", full_id)
        assert result == full_id

    def test_short_id_too_short_exits(self):
        with pytest.raises(SystemExit):
            _resolve_id(MagicMock(), "http://test", "abc")

    def test_short_id_resolves_single_match(self):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200, {"data": [{"id": "12345678-aaaa-bbbb-cccc-dddddddddddd", "title": "Paper"}]}
        )
        result = _resolve_id(client, "http://test", "12345678")
        assert result == "12345678-aaaa-bbbb-cccc-dddddddddddd"

    def test_short_id_no_match_exits(self):
        client = MagicMock()
        client.get.return_value = _mock_response(200, {"data": []})
        with pytest.raises(SystemExit):
            _resolve_id(client, "http://test", "000000")

    def test_short_id_ambiguous_exits(self):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [
                    {"id": "12345678-aaaa", "title": "A"},
                    {"id": "12345678-bbbb", "title": "B"},
                ]
            },
        )
        with pytest.raises(SystemExit):
            _resolve_id(client, "http://test", "123456")


class TestCmdFetch:
    def test_fetch_prints_paper(self, capsys):
        client = MagicMock()
        client.post.return_value = _mock_response(
            201,
            {
                "data": {
                    "id": "aaaa-bbbb",
                    "pmid": "12345678",
                    "title": "Fetched Paper",
                    "authors": [],
                    "tags": [],
                }
            },
        )
        args = _make_args(pmid="12345678")
        cmd_fetch(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Saved paper" in out


class TestCmdLs:
    def test_ls_prints_table(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [
                    {"id": "aaaa-bbbb", "pmid": "111", "title": "Paper One", "tags": ["ml"]},
                ],
                "meta": {"total": 1, "page": 1, "limit": 20},
            },
        )
        args = _make_args()
        cmd_ls(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Papers" in out
        assert "111" in out

    def test_ls_json_output(self, capsys):
        client = MagicMock()
        body = {"data": [], "meta": {"total": 0}}
        client.get.return_value = _mock_response(200, body)
        args = _make_args(json_output=True)
        cmd_ls(args, client, "http://test")
        out = capsys.readouterr().out
        assert json.loads(out) == body


class TestCmdGet:
    def test_get_prints_detail(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": {
                    "id": "aaaa-bbbb",
                    "pmid": "111",
                    "title": "Detail Paper",
                    "authors": [{"last_name": "Kim", "first_name": "Ji"}],
                    "tags": ["bio"],
                    "journal": "Nature",
                    "doi": "10.1000/x",
                    "created_at": "2025-01-01T00:00:00",
                    "abstract": "Short abstract text.",
                }
            },
        )
        args = _make_args(id="aaaa-bbbb-cccc-dddd-eeee-ffffffffffff", json_output=False)
        cmd_get(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Detail Paper" in out
        assert "Kim" in out


class TestCmdSearch:
    def test_keyword_search(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [{"id": "aa", "pmid": "111", "title": "Found", "tags": []}],
                "meta": {"total": 1, "page": 1, "limit": 20},
            },
        )
        args = _make_args(query="test", semantic=False, tag=None, author=None)
        cmd_search(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Search results" in out

    def test_semantic_search(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [
                    {"paper": {"pmid": "111", "title": "Semantic Hit"}, "score": 0.92},
                ],
            },
        )
        args = _make_args(query="gene therapy", semantic=True)
        cmd_search(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Semantic search" in out
        assert "0.92" in out

    def test_semantic_search_requires_query(self):
        args = _make_args(query=None, semantic=True)
        with pytest.raises(SystemExit):
            cmd_search(args, MagicMock(), "http://test")


class TestCmdTag:
    def test_tag_prints_confirmation(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200, {"data": [{"id": "aaaa-full-uuid-here-1234567890ab", "title": "P"}]}
        )
        client.post.return_value = _mock_response(200, {"data": {"tags": ["ml"]}})
        args = _make_args(id="aaaa-f", tags=["ml"])
        cmd_tag(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Tagged" in out


class TestCmdUntag:
    def test_untag_prints_confirmation(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200, {"data": [{"id": "aaaa-full-uuid-here-1234567890ab", "title": "P"}]}
        )
        client.delete.return_value = _mock_response(200, {"data": {"tags": []}})
        args = _make_args(id="aaaa-f", tag="ml")
        cmd_untag(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Removed tag" in out


class TestCmdRm:
    def test_rm_with_confirm(self, capsys):
        client = MagicMock()
        client.get.side_effect = [
            _mock_response(
                200,
                {
                    "data": [
                        {"id": "aaaa-full-uuid-here-1234567890ab", "title": "P"},
                    ]
                },
            ),
            _mock_response(200, {"data": {"title": "Paper to Delete"}}),
        ]
        client.delete.return_value = _mock_response(200, {})
        args = _make_args(id="aaaa-f", force=False)
        with patch("builtins.input", return_value="y"):
            cmd_rm(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Deleted" in out

    def test_rm_cancelled_exits_with_cancelled_code(self):
        client = MagicMock()
        client.get.side_effect = [
            _mock_response(
                200,
                {
                    "data": [
                        {"id": "aaaa-full-uuid-here-1234567890ab", "title": "P"},
                    ]
                },
            ),
            _mock_response(200, {"data": {"title": "Paper"}}),
        ]
        args = _make_args(id="aaaa-f", force=False)
        with patch("builtins.input", return_value="n"):
            with pytest.raises(SystemExit) as exc_info:
                cmd_rm(args, client, "http://test")
            assert exc_info.value.code == EXIT_CANCELLED
        client.delete.assert_not_called()

    def test_rm_force_skips_confirmation_and_detail_fetch(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [
                    {"id": "aaaa-full-uuid-here-1234567890ab", "title": "P"},
                ]
            },
        )
        client.delete.return_value = _mock_response(200, {})
        args = _make_args(id="aaaa-f", force=True)
        cmd_rm(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Deleted" in out
        client.delete.assert_called_once()
        assert client.get.call_count == 1  # only _resolve_id, no detail fetch


class TestCmdAsk:
    def test_ask_prints_answer(self, capsys):
        client = MagicMock()
        client.post.return_value = _mock_response(
            200,
            {
                "data": {
                    "answer": "Gene therapy uses viral vectors.",
                    "citations": [
                        {"pmid": "111", "title": "Gene Review", "score": 0.95},
                    ],
                    "model": "gpt-4o-mini",
                    "took_ms": 1200,
                }
            },
        )
        args = _make_args(question="What is gene therapy?", top_k=5, json_output=False)
        cmd_ask(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Gene therapy uses viral vectors" in out
        assert "111" in out
        assert "gpt-4o-mini" in out


class TestCmdEmbedAll:
    def test_embed_all_prints_count(self, capsys):
        client = MagicMock()
        client.post.return_value = _mock_response(200, {"data": {"embedded": 15}})
        args = _make_args()
        cmd_embed_all(args, client, "http://test")
        out = capsys.readouterr().out
        assert "Embedded 15" in out


class TestCmdTags:
    def test_tags_prints_list(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [{"name": "ml"}, {"name": "bio"}],
                "meta": {"total": 2, "page": 1, "limit": 20},
            },
        )
        args = _make_args(json_output=False)
        cmd_tags(args, client, "http://test")
        out = capsys.readouterr().out
        assert "ml" in out
        assert "bio" in out

    def test_tags_empty(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [],
                "meta": {"total": 0},
            },
        )
        args = _make_args(json_output=False)
        cmd_tags(args, client, "http://test")
        out = capsys.readouterr().out
        assert "No tags found" in out


class TestExitCodes:
    def test_exit_code_constants(self):
        assert EXIT_OK == 0
        assert EXIT_ERROR == 1
        assert EXIT_CANCELLED == 2

    def test_handle_error_exits_with_error_code(self):
        resp = _mock_response(400, {"error": "Bad request"})
        with pytest.raises(SystemExit) as exc_info:
            _handle_error(resp)
        assert exc_info.value.code == EXIT_ERROR

    def test_short_id_no_match_exits_with_error_code(self):
        client = MagicMock()
        client.get.return_value = _mock_response(200, {"data": []})
        with pytest.raises(SystemExit) as exc_info:
            _resolve_id(client, "http://test", "000000")
        assert exc_info.value.code == EXIT_ERROR


class TestGetVersion:
    def test_returns_version_string(self):
        version = _get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_returns_dev_when_not_installed(self):
        from importlib.metadata import PackageNotFoundError

        with patch("src.cli.pkg_version", side_effect=PackageNotFoundError):
            assert _get_version() == "0.0.0-dev"


class TestHttpWarning:
    def test_warns_on_non_localhost_http(self, capsys):
        _validate_base_url("http://remote-server.com")
        out = capsys.readouterr().out
        assert "Warning" in out

    def test_no_warning_on_localhost(self, capsys):
        _validate_base_url("http://localhost:8000")
        out = capsys.readouterr().out
        assert "Warning" not in out


class TestHandleErrorJsonParseFail:
    def test_falls_back_to_text_on_json_parse_failure(self):
        resp = MagicMock()
        resp.status_code = 500
        resp.json.side_effect = ValueError("no json")
        resp.text = "Raw error text"
        with pytest.raises(SystemExit):
            _handle_error(resp)


class TestCmdGetJson:
    def test_get_json_output(self, capsys):
        client = MagicMock()
        body = {"data": {"id": "aaaa", "pmid": "111", "title": "Test"}}
        client.get.return_value = _mock_response(200, body)
        args = _make_args(id="aaaa-bbbb-cccc-dddd-eeee-ffffffffffff", json_output=True)
        cmd_get(args, client, "http://test")
        out = capsys.readouterr().out
        assert json.loads(out) == body


class TestCmdSearchBranches:
    def test_semantic_json_output(self, capsys):
        client = MagicMock()
        body = {"data": [{"paper": {"pmid": "111"}, "score": 0.9}]}
        client.get.return_value = _mock_response(200, body)
        args = _make_args(query="test", semantic=True, json_output=True)
        cmd_search(args, client, "http://test")
        out = capsys.readouterr().out
        assert json.loads(out) == body

    def test_search_with_tag_and_author(self, capsys):
        client = MagicMock()
        client.get.return_value = _mock_response(
            200,
            {
                "data": [{"id": "aa", "pmid": "111", "title": "Found", "tags": []}],
                "meta": {"total": 1, "page": 1, "limit": 20},
            },
        )
        args = _make_args(query=None, semantic=False, tag="ml", author="Kim")
        cmd_search(args, client, "http://test")
        call_args = client.get.call_args
        params = call_args[1].get("params", call_args.kwargs.get("params", {}))
        assert params.get("tag") == "ml"
        assert params.get("author") == "Kim"


class TestCmdAskBranches:
    def test_ask_json_output(self, capsys):
        client = MagicMock()
        body = {"data": {"answer": "Yes", "citations": [], "model": "m", "took_ms": 100}}
        client.post.return_value = _mock_response(200, body)
        args = _make_args(question="Q", top_k=5, json_output=True)
        cmd_ask(args, client, "http://test")
        out = capsys.readouterr().out
        assert json.loads(out) == body

    def test_ask_with_long_citation_title(self, capsys):
        client = MagicMock()
        long_title = "A" * 70
        client.post.return_value = _mock_response(
            200,
            {
                "data": {
                    "answer": "Answer text",
                    "citations": [{"pmid": "111", "title": long_title, "score": 0.95}],
                    "model": "gpt-4o-mini",
                    "took_ms": 500,
                }
            },
        )
        args = _make_args(question="Q", top_k=5, json_output=False)
        cmd_ask(args, client, "http://test")
        out = capsys.readouterr().out
        assert "..." in out
        assert "111" in out


class TestCmdTagsJson:
    def test_tags_json_output(self, capsys):
        client = MagicMock()
        body = {"data": [{"name": "ml"}], "meta": {"total": 1}}
        client.get.return_value = _mock_response(200, body)
        args = _make_args(json_output=True)
        cmd_tags(args, client, "http://test")
        out = capsys.readouterr().out
        assert json.loads(out) == body


class TestPrintPaperDetail:
    def test_detail_with_all_fields(self, capsys):
        _print_paper_detail(
            {
                "title": "Full Paper",
                "pmid": "12345678",
                "journal": "Nature",
                "authors": [{"last_name": "Kim", "first_name": "Ji"}],
                "tags": ["ml", "bio"],
                "doi": "10.1000/x",
                "created_at": "2025-01-01T00:00:00",
                "abstract": "Short abstract.",
            }
        )
        out = capsys.readouterr().out
        assert "Full Paper" in out
        assert "Nature" in out
        assert "Kim" in out
        assert "10.1000/x" in out
        assert "2025-01-01" in out

    def test_detail_truncates_long_abstract(self, capsys):
        _print_paper_detail(
            {
                "title": "Long Abstract Paper",
                "pmid": "111",
                "abstract": "X" * 400,
            }
        )
        out = capsys.readouterr().out
        assert "..." in out


class TestPrintSemanticResults:
    def test_empty_results(self, capsys):
        _print_semantic_results([])
        out = capsys.readouterr().out
        assert "No results found" in out

    def test_results_with_long_title(self, capsys):
        _print_semantic_results([{"paper": {"pmid": "111", "title": "T" * 60}, "score": 0.88}])
        out = capsys.readouterr().out
        assert "..." in out
        assert "0.88" in out


class TestMainEntrypoint:
    def test_no_command_prints_help_and_exits_0(self):
        with patch("sys.argv", ["pubsave"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == EXIT_OK

    def test_dispatches_fetch_command(self):
        with (
            patch("sys.argv", ["pubsave", "fetch", "12345678"]),
            patch("src.cli._get_client") as mock_get_client,
            patch("src.cli.cmd_fetch") as mock_cmd,
        ):
            mock_client = MagicMock()
            mock_get_client.return_value = (mock_client, "http://test")
            main()
            mock_cmd.assert_called_once()

    def test_connection_error_exits_1(self):
        import httpx

        with (
            patch("sys.argv", ["pubsave", "ls"]),
            patch("src.cli._get_client") as mock_get_client,
            patch("src.cli.cmd_ls", side_effect=httpx.ConnectError("refused")),
        ):
            mock_client = MagicMock()
            mock_get_client.return_value = (mock_client, "http://test")
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == EXIT_ERROR
