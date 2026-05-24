"""Unit tests for scraping parser helpers."""

import pytest

from app.tasks.scraping.exceptions import ScrapingInvalidURLError
from app.tasks.scraping.parsers import (
    extract_date_near_link,
    extract_link_title,
    find_pdf_links,
    is_direct_pdf_link,
    is_document_portal_link,
    is_pdf_link,
    is_pdf_url,
    parse_scrape_line,
    read_urls_from_file,
    resolve_pdf_url,
    truncate_preview,
    validate_url,
)
from bs4 import BeautifulSoup


def test_parse_scrape_line_offline_format(tmp_path):
    """parse_scrape_line reads offline HTML and canonical page URL."""
    html_file = tmp_path / "page.html"
    html_file.write_text(
        '<a href="https://example.com/a.pdf">Doc</a>',
        encoding="utf-8",
    )
    target = parse_scrape_line(f"offline:{html_file}|https://example.com/news/")
    assert target.page_url == "https://example.com/news/"
    assert "a.pdf" in (target.html or "")


def test_read_urls_from_file_skips_comments_and_blanks(tmp_path):
    """URL file loader ignores blank lines and # comments."""
    path = tmp_path / "urls.txt"
    path.write_text(
        "# comment\n\nhttps://example.com/page\n# another\nhttps://test.org/x\n",
        encoding="utf-8",
    )
    assert read_urls_from_file(path) == [
        "https://example.com/page",
        "https://test.org/x",
    ]


def test_validate_url_rejects_invalid_scheme():
    """validate_url rejects non-http(s) URLs."""
    with pytest.raises(ScrapingInvalidURLError):
        validate_url("ftp://example.com")


def test_is_pdf_url_detects_pdf_paths():
    """is_pdf_url matches .pdf paths and query strings."""
    assert is_pdf_url("https://site.com/doc/report.pdf")
    assert is_pdf_url("https://site.com/file.PDF?version=1")


def test_is_pdf_link_detects_download_paths_without_suffix():
    """is_pdf_link matches common public PDF download URL patterns."""
    assert is_pdf_link("/bg/storage/files/report?format=pdf")
    assert is_pdf_link("/documents/download/12345")
    assert is_pdf_link("https://minfin.bg/getpdf?id=99")
    assert not is_pdf_link("/documents/215")
    assert not is_pdf_link("mailto:test@example.com")
    assert not is_pdf_link("javascript:void(0)")


def test_nsi_catalog_link_is_portal_not_pdf():
    """NSI /documents/ID pages are catalogs, not direct PDF files."""
    assert is_document_portal_link("/documents/215")
    assert not is_direct_pdf_link("/documents/215")
    assert is_direct_pdf_link(
        "sites/default/files/files/pages/GOD2025/Zapoved_NSI_NAP_2025.pdf"
    )


def test_resolve_pdf_url_handles_relative_href():
    """Relative PDF hrefs resolve against the page URL."""
    assert resolve_pdf_url("https://example.com/news/", "/files/report.pdf") == (
        "https://example.com/files/report.pdf"
    )


def test_resolve_pdf_url_handles_cms_root_relative_path():
    """CMS paths like sites/default/... resolve against the site root, not the page path."""
    page = "https://www.nsi.bg/pages/godishna-otchetnost-2025"
    href = "sites/default/files/report.pdf"
    assert resolve_pdf_url(page, href) == (
        "https://www.nsi.bg/sites/default/files/report.pdf"
    )


def test_find_pdf_links_finds_absolute_and_relative(tmp_path):
    """find_pdf_links returns up to MAX_PDFS_PER_PAGE unique PDF URLs from HTML."""
    html = """
    <html><body>
      <a href="/docs/report.pdf">Annual Report 2024</a>
      <a href="https://cdn.example.com/other.pdf">Other</a>
      <a href="/files/download?id=9&amp;format=pdf">Budget PDF</a>
      <a href="/docs/report.pdf">Duplicate</a>
      <a href="/page.html">Not PDF</a>
    </body></html>
    """
    links = find_pdf_links(html, "https://example.com/news/")
    urls = [link.url for link in links]
    assert "https://example.com/docs/report.pdf" in urls
    assert "https://cdn.example.com/other.pdf" in urls
    assert len(urls) == 3


def test_extract_link_title_uses_text_or_filename():
    """Title comes from anchor text or the PDF filename."""
    anchor = BeautifulSoup(
        '<a href="/a.pdf">Annual Report</a>', "lxml"
    ).find("a")
    assert extract_link_title(anchor, "https://x.com/a.pdf") == "Annual Report"
    assert extract_link_title(
        BeautifulSoup('<a href="/b.pdf"></a>', "lxml").find("a"),
        "https://x.com/files/b.pdf",
    ) == "b.pdf"


def test_extract_date_near_link_reads_time_tag():
    """Publication date is taken from a nearby time[datetime] element."""
    soup = BeautifulSoup(
        '<div><time datetime="2024-03-15"></time><a href="/r.pdf">R</a></div>',
        "lxml",
    )
    anchor = soup.find("a")
    assert extract_date_near_link(anchor) == "2024-03-15"


def test_truncate_preview_limits_length():
    """truncate_preview returns at most the requested character count."""
    text = "word " * 200
    assert len(truncate_preview(text, 20)) == 20
