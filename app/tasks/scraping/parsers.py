"""Pure HTML/URL parsing helpers for document scraping."""

import re
from pathlib import Path
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse
from app.tasks.scraping.constants import MAX_PDFS_PER_PAGE, MIN_PDFS_PER_PAGE
from app.tasks.scraping.exceptions import ScrapingInvalidURLError

OFFLINE_PREFIX = "offline:"

_DATE_PATTERNS = (
    re.compile(r"\d{4}-\d{2}-\d{2}"),
    re.compile(r"\d{1,2}[./]\d{1,2}[./]\d{4}"),
)
_PDF_SUFFIX = re.compile(r"\.pdf(\?|#|$)", re.IGNORECASE)
_PDF_PATH_HINTS = re.compile(
    r"(/pdf/|/pdfs/|/getpdf|/download/pdf|/file/download|/documents/download|"
    r"/storage/|/upload/|format=pdf|type=pdf)",
    re.IGNORECASE,
)
_DOCUMENT_PORTAL = re.compile(r"/documents/\d+/?$", re.IGNORECASE)
_SKIP_HREF_PREFIXES = ("#", "javascript:", "mailto:", "tel:")


@dataclass(frozen=True)
class ScrapeTarget:
    """A page to scrape: live URL or offline HTML with a canonical page URL."""

    page_url: str
    html: str | None = None


@dataclass(frozen=True)
class PdfLinkCandidate:
    """A PDF hyperlink discovered on a page."""

    url: str
    title: str
    date_published: str | None


def read_urls_from_file(path: str | Path) -> list[str]:
    """Load non-empty, non-comment URL lines from a text file."""
    return [target.page_url for target in read_scrape_targets_from_file(path)]


def read_scrape_targets_from_file(path: str | Path) -> list[ScrapeTarget]:
    """Load scrape targets, including offline HTML entries."""
    file_path = Path(path)
    if not file_path.is_file():
        raise ScrapingInvalidURLError(f"URL file not found: {file_path}")

    targets: list[ScrapeTarget] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        targets.append(parse_scrape_line(text))
    return targets


def parse_scrape_line(line: str) -> ScrapeTarget:
    """Parse a URL line or ``offline:path|canonical_page_url``."""
    if line.startswith(OFFLINE_PREFIX):
        return _parse_offline_line(line)
    validate_url(line)
    return ScrapeTarget(page_url=line)


def _parse_offline_line(line: str) -> ScrapeTarget:
    """Load HTML from disk for offline scraping."""
    payload = line[len(OFFLINE_PREFIX):]
    if "|" not in payload:
        raise ScrapingInvalidURLError(
            "Offline entry must be offline:relative/path.html|https://canonical-page-url"
        )
    rel_path, page_url = payload.split("|", 1)
    page_url = page_url.strip()
    validate_url(page_url)

    html_path = Path(rel_path.strip())
    if not html_path.is_file():
        raise ScrapingInvalidURLError(f"Offline HTML file not found: {html_path}")

    html = html_path.read_text(encoding="utf-8")
    return ScrapeTarget(page_url=page_url, html=html)


def validate_url(url: str) -> None:
    """Raise if ``url`` is not a valid http(s) URL."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ScrapingInvalidURLError(f"Invalid URL: {url}")


def is_direct_pdf_link(href: str) -> bool:
    """True when href is a direct PDF file (``.pdf`` suffix)."""
    if not href:
        return False
    text = href.strip()
    if text.lower().startswith(_SKIP_HREF_PREFIXES):
        return False
    return bool(_PDF_SUFFIX.search(text))


def is_document_portal_link(href: str) -> bool:
    """True for catalog pages like ``/documents/215`` that may link to a PDF inside."""
    if not href:
        return False
    text = href.strip()
    if text.lower().startswith(_SKIP_HREF_PREFIXES) or is_direct_pdf_link(text):
        return False
    path = urlparse(urljoin("https://placeholder/", text)).path
    return bool(_DOCUMENT_PORTAL.search(path))


def is_pdf_link(href: str) -> bool:
    """True when href points to a PDF file or a common public PDF download path."""
    if is_direct_pdf_link(href):
        return True
    if not href:
        return False
    text = href.strip()
    if text.lower().startswith(_SKIP_HREF_PREFIXES):
        return False
    return bool(_PDF_PATH_HINTS.search(text))


def is_pdf_url(url: str) -> bool:
    """Return True when the resolved URL looks like a PDF resource."""
    return is_pdf_link(url)


_ROOT_RELATIVE_PREFIXES = ("sites/", "files/", "upload/", "media/", "static/")


def resolve_pdf_url(page_url: str, href: str) -> str:
    """Turn a relative or root-relative href into an absolute PDF URL."""
    text = href.strip()
    if text.startswith(("http://", "https://")):
        return text

    parsed = urlparse(page_url)
    site_root = f"{parsed.scheme}://{parsed.netloc}/"

    if text.startswith("/"):
        return urljoin(site_root, text)

    if text.lower().startswith(_ROOT_RELATIVE_PREFIXES):
        return urljoin(site_root, text)

    base = page_url if page_url.endswith("/") else f"{page_url}/"
    return urljoin(base, text)


def find_pdf_links(html: str, page_url: str) -> list[PdfLinkCandidate]:
    """Discover up to MAX_PDFS_PER_PAGE unique PDF links; direct ``.pdf`` hrefs are preferred."""
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    candidates: list[PdfLinkCandidate] = []

    # Prefer direct .pdf links first (avoids NSI /documents/ catalog false positives).
    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = str(anchor.get("href", "")).strip()
        if not is_direct_pdf_link(href):
            continue
        candidate = _anchor_to_candidate(anchor, href, page_url, seen)
        if candidate:
            candidates.append(candidate)
        if len(candidates) >= MAX_PDFS_PER_PAGE:
            return candidates

    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = str(anchor.get("href", "")).strip()
        if not is_pdf_link(href) or is_direct_pdf_link(href):
            continue
        candidate = _anchor_to_candidate(anchor, href, page_url, seen)
        if candidate:
            candidates.append(candidate)
        if len(candidates) >= MAX_PDFS_PER_PAGE:
            break

    if len(candidates) < MAX_PDFS_PER_PAGE:
        candidates.extend(
            _find_pdf_links_in_embeds(soup, page_url, seen, MAX_PDFS_PER_PAGE - len(candidates))
        )

    return candidates


def find_document_portal_links(html: str, page_url: str) -> list[PdfLinkCandidate]:
    """Collect catalog URLs such as NSI ``/documents/215`` (not PDF files themselves)."""
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    portals: list[PdfLinkCandidate] = []
    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = str(anchor.get("href", "")).strip()
        if not is_document_portal_link(href):
            continue
        candidate = _anchor_to_candidate(anchor, href, page_url, seen)
        if candidate:
            portals.append(candidate)
        if len(portals) >= MAX_PDFS_PER_PAGE:
            break
    return portals


def _anchor_to_candidate(
        anchor: Tag,
        href: str,
        page_url: str,
        seen: set[str],
) -> PdfLinkCandidate | None:
    absolute = resolve_pdf_url(page_url, href)
    if absolute in seen:
        return None
    seen.add(absolute)
    return PdfLinkCandidate(
        url=absolute,
        title=extract_link_title(anchor, absolute),
        date_published=extract_date_near_link(anchor),
    )


def _find_pdf_links_in_embeds(
        soup: BeautifulSoup,
        page_url: str,
        seen: set[str],
        limit: int,
) -> list[PdfLinkCandidate]:
    """Collect PDF URLs from iframe/embed/object src attributes."""
    found: list[PdfLinkCandidate] = []
    for tag_name, attr in (("iframe", "src"), ("embed", "src"), ("object", "data")):
        for tag in soup.find_all(tag_name):
            src = str(tag.get(attr, "")).strip()
            if not is_pdf_link(src):
                continue
            absolute = resolve_pdf_url(page_url, src)
            if absolute in seen:
                continue
            seen.add(absolute)
            title = Path(urlparse(absolute).path).name or absolute
            found.append(PdfLinkCandidate(url=absolute, title=title, date_published=None))
            if len(found) >= limit:
                return found
    return found


def extract_link_title(anchor: Tag, pdf_url: str) -> str:
    """Use anchor text as title, or fall back to the PDF filename."""
    text = anchor.get_text(strip=True)
    if text:
        return text[:200]
    filename = Path(urlparse(pdf_url).path).name
    return filename or pdf_url


def extract_date_near_link(anchor: Tag) -> str | None:
    """Read ``time[datetime]`` or a date pattern near the PDF link."""
    time_tag = anchor.find("time")
    if not time_tag and anchor.parent:
        time_tag = anchor.parent.find("time")
    if time_tag and time_tag.get("datetime"):
        return str(time_tag["datetime"])[:10]

    context = " ".join(anchor.parent.get_text(" ", strip=True) if anchor.parent else [])
    for pattern in _DATE_PATTERNS:
        match = pattern.search(context)
        if match:
            return normalize_date_text(match.group(0))
    return None


def normalize_date_text(value: str) -> str:
    """Normalize DD.MM.YYYY style dates toward ISO when possible."""
    if re.match(r"\d{4}-\d{2}-\d{2}", value):
        return value
    parts = re.split(r"[./]", value)
    if len(parts) == 3 and len(parts[2]) == 4:
        day, month, year = parts
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return value


def truncate_preview(text: str, max_chars: int) -> str:
    """Return the first ``max_chars`` characters of whitespace-normalized text."""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars]


def has_minimum_pdfs(candidates: list[PdfLinkCandidate]) -> bool:
    """True when at least ``MIN_PDFS_PER_PAGE`` PDF links were found."""
    return len(candidates) >= MIN_PDFS_PER_PAGE
