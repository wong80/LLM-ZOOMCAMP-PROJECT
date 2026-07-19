"""Split scraped HTML documentation into heading-based chunks."""

import re
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urlunparse


def _heading_level(tag: Tag) -> int:
    """Extract heading level (1-4) from tag name, 99 for non-heading."""
    return int(tag.name[1]) if tag.name and tag.name.startswith("h") and len(tag.name) == 2 else 99


def _make_id(title: str, index: int, doc_library: str = "fastapi") -> str:
    """Generate unique chunk ID from title, global index, and library."""
    if not title.strip():
        return f"{doc_library}-section-{index:03d}"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
    if not slug:
        return f"{doc_library}-section-{index:03d}"
    return f"{doc_library}-{slug}-{index:03d}"


def _extract_anchor(base_url: str, heading_tag: Tag) -> str:
    """Build URL fragment from heading's id attribute, parent section id, or slug fallback."""
    heading_id = heading_tag.get("id")
    if heading_id:
        parsed = urlparse(base_url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, heading_id))
    section_parent = heading_tag.find_parent("section")
    if section_parent and section_parent.get("id"):
        parsed = urlparse(base_url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, section_parent.get("id")))
    anchor = re.sub(r"[^a-z0-9]+", "-", heading_tag.get_text(" ", strip=True).lower()).strip("-")
    parsed = urlparse(base_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, anchor))


def chunk_document(
    content_html: str,
    base_url: str,
    doc_library: str = "fastapi",
    overlap: bool = False,
    start_index: int = 0,
) -> list[dict]:
    """Split HTML into chunks at h1-h4 boundaries. Heading text is excluded from content."""
    soup = BeautifulSoup(content_html, "html.parser")
    chunks = []
    current_section: list[Tag] = []
    current_heading_tag: Tag | None = None
    current_title = ""
    current_heading_level = 0
    parent_section = ""

    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "pre", "ul", "ol", "table"]):
        if element.name in ("h1", "h2", "h3", "h4"):
            if current_section:
                content_text = "\n".join(
                    c.get_text(" ", strip=True) for c in current_section if hasattr(c, "get_text")
                )
                if content_text.strip():
                    chunks.append({
                        "id": _make_id(current_title, start_index + len(chunks), doc_library),
                        "title": current_title,
                        "section": parent_section,
                        "content": content_text,
                        "url": _extract_anchor(base_url, current_heading_tag) if current_heading_tag else base_url,
                        "doc_library": doc_library,
                    })
                    if overlap and current_section:
                        overlap_content = current_section[-1]
                        current_section = [overlap_content]
                    else:
                        current_section = []
            current_heading_tag = element
            current_title = element.get_text(" ", strip=True)
            current_heading_level = _heading_level(element)
            if current_heading_level == 1:
                parent_section = current_title
        else:
            current_section.append(element)

    if current_section:
        content_text = "\n".join(
            c.get_text(" ", strip=True) for c in current_section if hasattr(c, "get_text")
        )
        if content_text.strip():
            chunks.append({
                "id": _make_id(current_title, start_index + len(chunks), doc_library),
                "title": current_title,
                "section": parent_section,
                "content": content_text,
                "url": _extract_anchor(base_url, current_heading_tag) if current_heading_tag else base_url,
                "doc_library": doc_library,
            })

    return chunks
