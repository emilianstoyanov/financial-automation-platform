"""Tests for Cloudflare detection and offline scraping."""

from pathlib import Path

import pytest

from app.tasks.scraping.cloudflare import is_cloudflare_challenge
from app.tasks.scraping.exceptions import ScrapingInvalidURLError
from app.tasks.scraping.parsers import parse_scrape_line, read_scrape_targets_from_file
from app.tasks.scraping.scraper import DocumentScraper


def test_is_cloudflare_challenge_detects_just_a_moment():
    """Cloudflare interstitial HTML is recognized."""
    html = "<html><title>Just a moment...</title></html>"
    assert is_cloudflare_challenge(403, html, {})


def test_parse_offline_line_loads_fixture():
    """offline:path|url entries load HTML from disk."""
    target = parse_scrape_line(
        "offline:data/scraping/fixtures/minfin_bg_1394_demo.html|https://www.minfin.bg/bg/1394"
    )
    assert target.html is not None
    assert "sample.pdf" in target.html
    assert target.page_url == "https://www.minfin.bg/bg/1394"


def test_parse_offline_line_rejects_missing_file():
    """Missing offline HTML files raise ScrapingInvalidURLError."""
    with pytest.raises(ScrapingInvalidURLError, match="not found"):
        parse_scrape_line("offline:data/missing.html|https://www.minfin.bg/bg/1394")


def test_offline_fixture_scrape_downloads_pdfs(tmp_path):
    """Offline minfin demo fixture yields documents via public test PDFs."""
    scraper = DocumentScraper(
        urls_file=tmp_path / "urls.txt",
        output_json=tmp_path / "out.json",
    )
    target = parse_scrape_line(
        "offline:data/scraping/fixtures/minfin_bg_1394_demo.html|https://www.minfin.bg/bg/1394"
    )
    docs = scraper._scrape_target(target)
    assert len(docs) >= 1
    assert docs[0].document_type == "PDF"


def test_read_scrape_targets_from_sample_file():
    """sample_urls.txt includes at least one offline minfin demo target."""
    root = Path(__file__).resolve().parents[2]
    path = root / "data" / "scraping" / "sample_urls.txt"
    targets = read_scrape_targets_from_file(path)
    assert any(t.html for t in targets)
