"""Formatting helpers for paper and author display."""


def format_author(a) -> str:
    """Format a single author as 'LastName F' (initial)."""
    if hasattr(a, "last_name"):
        last, first = a.last_name, a.first_name
    elif isinstance(a, dict):
        last, first = a.get("last_name", ""), a.get("first_name", "")
    else:
        return str(a)
    initial = first[0] if first else ""
    return f"{last} {initial}" if initial else last


def format_authors_short(authors: list) -> str:
    """Format an author list as 'First F, Second S et al.' for 3+ authors."""
    if not authors:
        return ""
    if len(authors) <= 2:
        return ", ".join(format_author(a) for a in authors)
    return f"{format_author(authors[0])}, {format_author(authors[1])} et al."


def paper_to_response(paper, compact: bool = False):
    """Convert a Paper ORM object to a response schema."""
    from src.papers.schemas import PaperCompactResponse, PaperResponse

    if compact:
        return PaperCompactResponse.model_validate(paper)
    return PaperResponse.model_validate(paper)


def extract_tag_names(v: list) -> list[str]:
    """Extract tag name strings from a list of Tag objects, dicts, or strings."""
    if not v:
        return []
    first = v[0]
    if isinstance(first, str):
        return v
    if hasattr(first, "name"):
        return [t.name for t in v]
    if isinstance(first, dict) and "name" in first:
        return [t["name"] for t in v]
    raise TypeError(f"Cannot extract tag names from {type(first).__name__}")
