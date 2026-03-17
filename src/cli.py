"""PubSave CLI — save, tag, and search PubMed papers from your terminal."""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

import httpx

from src.papers.schemas import _format_author

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
_MIN_SHORT_ID = 6

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _sanitize(text: str) -> str:
    return _ANSI_RE.sub("", text) if text else ""


def _validate_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        print(f"{RED}Error: PUBSAVE_URL must use http or https, got: {parsed.scheme!r}{RESET}")
        sys.exit(1)
    if not parsed.netloc:
        print(f"{RED}Error: PUBSAVE_URL is missing a host{RESET}")
        sys.exit(1)
    host = parsed.hostname or ""
    if parsed.scheme == "http" and host not in ("localhost", "127.0.0.1", "::1"):
        print(f"{DIM}Warning: using plain http with non-localhost host ({host}){RESET}")
    return url.rstrip("/")


def _get_client(args) -> tuple[httpx.Client, str]:
    import os

    base = os.environ.get("PUBSAVE_URL", "http://localhost:8000")
    base = _validate_base_url(base)
    return httpx.Client(timeout=30), base


def _handle_error(resp: httpx.Response) -> None:
    if resp.status_code >= 400:
        try:
            body = resp.json()
            msg = body.get("error") or body.get("detail") or resp.text
        except Exception:
            msg = resp.text
        print(f"{RED}Error ({resp.status_code}): {_sanitize(str(msg))}{RESET}")
        sys.exit(1)


def _print_paper_table(papers: list[dict]) -> None:
    if not papers:
        print("  No papers found.")
        return
    print(f"  {'ID':<10} {'PMID':<12} {'TITLE':<50} {'TAGS'}")
    print(f"  {'—'*10} {'—'*12} {'—'*50} {'—'*20}")
    for p in papers:
        pid = _sanitize(str(p.get("id", ""))[:8])
        pmid = _sanitize(str(p.get("pmid", "")))
        title = _sanitize(str(p.get("title", "")))
        if len(title) > 47:
            title = title[:44] + "..."
        tags_list = p.get("tags", [])
        tags = ", ".join(_sanitize(str(t)) for t in tags_list)
        print(f"  {pid:<10} {pmid:<12} {title:<50} {tags}")


def _print_paper_detail(p: dict) -> None:
    print(f"  {BOLD}Title:{RESET}    {_sanitize(str(p.get('title', '')))}")
    print(f"  {BOLD}PMID:{RESET}     {_sanitize(str(p.get('pmid', '')))}")
    if p.get("journal"):
        print(f"  {BOLD}Journal:{RESET}  {_sanitize(str(p['journal']))}")
    authors = p.get("authors", [])
    if authors:
        names = [_format_author(a) for a in authors]
        print(f"  {BOLD}Authors:{RESET}  {_sanitize(', '.join(names))}")
    tags = p.get("tags", [])
    if tags:
        print(f"  {BOLD}Tags:{RESET}     {_sanitize(', '.join(str(t) for t in tags))}")
    if p.get("doi"):
        print(f"  {BOLD}DOI:{RESET}      {_sanitize(str(p['doi']))}")
    if p.get("created_at"):
        date = str(p["created_at"])[:10]
        print(f"  {BOLD}Saved:{RESET}    {date}")
    abstract = p.get("abstract")
    if abstract:
        clean = _sanitize(str(abstract))
        if len(clean) > 300:
            clean = clean[:297] + "..."
        print(f"\n  {BOLD}Abstract:{RESET}")
        print(f"  {clean}")


def _resolve_id(client: httpx.Client, base: str, short_id: str) -> str:
    if len(short_id) >= 32:
        return short_id
    if len(short_id) < _MIN_SHORT_ID:
        print(f"{RED}Error: ID prefix must be at least {_MIN_SHORT_ID} characters{RESET}")
        sys.exit(1)
    resp = client.get(
        f"{base}/api/v1/papers",
        params={"compact": "true", "id_prefix": short_id, "limit": 10},
    )
    _handle_error(resp)
    data = resp.json().get("data", [])
    if len(data) == 0:
        print(f"{RED}Error: no paper found matching '{short_id}'{RESET}")
        sys.exit(1)
    if len(data) > 1:
        print(f"{RED}Error: '{short_id}' matches {len(data)} papers. Be more specific:{RESET}")
        for m in data:
            title = _sanitize(str(m.get("title", "")))[:60]
            print(f"  {str(m['id'])[:8]}  {title}")
        sys.exit(1)
    return str(data[0]["id"])


def cmd_fetch(args, client: httpx.Client, base: str) -> None:
    resp = client.post(f"{base}/api/v1/papers/fetch/{args.pmid}")
    _handle_error(resp)
    body = resp.json()
    p = body.get("data", {})
    print(f"{GREEN}Saved paper {str(p.get('id', ''))[:8]}{RESET}")
    _print_paper_detail(p)


def cmd_ls(args, client: httpx.Client, base: str) -> None:
    params = {"compact": "true", "limit": args.limit, "page": args.page}
    if args.full:
        params.pop("compact")
    resp = client.get(f"{base}/api/v1/papers", params=params)
    _handle_error(resp)
    body = resp.json()
    if args.json_output:
        print(json.dumps(body, indent=2))
        return
    meta = body.get("meta", {})
    total = meta.get("total", 0)
    print(f"\n  {BOLD}Papers ({total} total){RESET}\n")
    _print_paper_table(body.get("data", []))
    print()


def cmd_get(args, client: httpx.Client, base: str) -> None:
    paper_id = _resolve_id(client, base, args.id)
    resp = client.get(f"{base}/api/v1/papers/{paper_id}")
    _handle_error(resp)
    body = resp.json()
    if args.json_output:
        print(json.dumps(body, indent=2))
        return
    print()
    _print_paper_detail(body.get("data", {}))
    print()


def cmd_search(args, client: httpx.Client, base: str) -> None:
    params = {"compact": "true", "limit": args.limit, "page": args.page}
    if args.full:
        params.pop("compact")
    if args.query:
        params["q"] = args.query
    if args.tag:
        params["tag"] = args.tag
    if args.author:
        params["author"] = args.author
    resp = client.get(f"{base}/api/v1/papers/search", params=params)
    _handle_error(resp)
    body = resp.json()
    if args.json_output:
        print(json.dumps(body, indent=2))
        return
    meta = body.get("meta", {})
    total = meta.get("total", 0)
    print(f"\n  {BOLD}Search results ({total} total){RESET}\n")
    _print_paper_table(body.get("data", []))
    print()


def cmd_tag(args, client: httpx.Client, base: str) -> None:
    paper_id = _resolve_id(client, base, args.id)
    resp = client.post(
        f"{base}/api/v1/papers/{paper_id}/tags",
        json={"tags": args.tags},
    )
    _handle_error(resp)
    tags = ", ".join(args.tags)
    print(f"{GREEN}Tagged {paper_id[:8]} with: {tags}{RESET}")


def cmd_untag(args, client: httpx.Client, base: str) -> None:
    paper_id = _resolve_id(client, base, args.id)
    resp = client.delete(f"{base}/api/v1/papers/{paper_id}/tags/{args.tag}")
    _handle_error(resp)
    print(f"{GREEN}Removed tag '{args.tag}' from {paper_id[:8]}{RESET}")


def cmd_rm(args, client: httpx.Client, base: str) -> None:
    paper_id = _resolve_id(client, base, args.id)
    get_resp = client.get(f"{base}/api/v1/papers/{paper_id}")
    _handle_error(get_resp)
    p = get_resp.json().get("data", {})
    title = _sanitize(str(p.get("title", "")))[:80]
    print(f"  {paper_id[:8]}  {title}")
    confirm = input(f"  {BOLD}Delete this paper? [y/N]:{RESET} ").strip().lower()
    if confirm != "y":
        print("  Cancelled.")
        return
    resp = client.delete(f"{base}/api/v1/papers/{paper_id}")
    _handle_error(resp)
    print(f"{GREEN}Deleted {paper_id[:8]}{RESET}")


def cmd_tags(args, client: httpx.Client, base: str) -> None:
    params = {"limit": args.limit, "page": args.page}
    resp = client.get(f"{base}/api/v1/tags", params=params)
    _handle_error(resp)
    body = resp.json()
    if args.json_output:
        print(json.dumps(body, indent=2))
        return
    tags = body.get("data", [])
    if not tags:
        print("  No tags found.")
        return
    meta = body.get("meta", {})
    total = meta.get("total", 0)
    print(f"\n  {BOLD}Tags ({total} total){RESET}\n")
    for t in tags:
        name = _sanitize(str(t.get("name", "")))
        print(f"  {name}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pubsave",
        description="Save, tag, and search PubMed papers from your terminal.",
    )
    parser.add_argument("--json", dest="json_output", action="store_true", help="raw JSON output")
    sub = parser.add_subparsers(dest="command")

    # fetch
    p_fetch = sub.add_parser("fetch", help="fetch a paper from PubMed by PMID")
    p_fetch.add_argument("pmid", help="PubMed ID (e.g. 33057194)")

    # ls
    p_ls = sub.add_parser("ls", help="list all saved papers")
    p_ls.add_argument("--full", action="store_true", help="show full details")
    p_ls.add_argument("--page", type=int, default=1)
    p_ls.add_argument("--limit", type=int, default=20)

    # get
    p_get = sub.add_parser("get", help="get a single paper by ID")
    p_get.add_argument("id", help="paper ID (full UUID or 6+ char prefix)")

    # search
    p_search = sub.add_parser("search", help="search papers")
    p_search.add_argument("query", nargs="?", default=None, help="keyword search")
    p_search.add_argument("-t", "--tag", help="filter by tag")
    p_search.add_argument("-a", "--author", help="filter by author")
    p_search.add_argument("--full", action="store_true", help="show full details")
    p_search.add_argument("--page", type=int, default=1)
    p_search.add_argument("--limit", type=int, default=20)

    # tag
    p_tag = sub.add_parser("tag", help="add tags to a paper")
    p_tag.add_argument("id", help="paper ID")
    p_tag.add_argument("tags", nargs="+", help="tag names")

    # untag
    p_untag = sub.add_parser("untag", help="remove a tag from a paper")
    p_untag.add_argument("id", help="paper ID")
    p_untag.add_argument("tag", help="tag name")

    # rm
    p_rm = sub.add_parser("rm", help="delete a paper")
    p_rm.add_argument("id", help="paper ID")

    # tags
    p_tags = sub.add_parser("tags", help="list all tags")
    p_tags.add_argument("--page", type=int, default=1)
    p_tags.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    client, base = _get_client(args)

    commands = {
        "fetch": cmd_fetch,
        "ls": cmd_ls,
        "get": cmd_get,
        "search": cmd_search,
        "tag": cmd_tag,
        "untag": cmd_untag,
        "rm": cmd_rm,
        "tags": cmd_tags,
    }
    commands[args.command](args, client, base)


if __name__ == "__main__":
    main()
