"""Crawler implementations and integration helpers."""

from src.crawlers.base import BaseCrawler, BlogCrawler, PaperCrawler
from src.crawlers.allbsides_talk_crawler import AllBsidesTalkCrawler
from src.crawlers.blackhat_schedule_crawler import BlackHatScheduleCrawler
from src.crawlers.browser_use_conference_crawler import BrowserUseConferenceCrawler
from src.crawlers.ccs_crawler import CCSCrawler
from src.crawlers.cloudflare_blog_crawler import CloudflareSecurityCrawler
from src.crawlers.defcon_talk_crawler import DefconTalkCrawler
from src.crawlers.ndss_crawler import NDSSCrawler
from src.crawlers.portswigger_crawler import PortSwiggerResearchCrawler
from src.crawlers.project_zero_crawler import ProjectZeroCrawler
from src.crawlers.rss_crawler import RSSFeedCrawler
from src.crawlers.rsac_agenda_crawler import RSACAgendaCrawler
from src.crawlers.sitemap_crawler import SitemapCrawler
from src.crawlers.webpage_crawler import WebpageCrawler
from src.crawlers.registry import (
    BLOG_CRAWLER_REGISTRY,
    PAPER_CRAWLER_REGISTRY,
    build_default_blog_crawlers,
    build_default_paper_crawlers,
    crawl_default_blogs,
    crawl_default_papers,
)
from src.crawlers.sp_crawler import SPCrawler
from src.crawlers.usenix_security_crawler import USENIXSecurityCrawler

__all__ = [
    "BaseCrawler",
    "PaperCrawler",
    "BlogCrawler",
    "AllBsidesTalkCrawler",
    "BlackHatScheduleCrawler",
    "BrowserUseConferenceCrawler",
    "NDSSCrawler",
    "SPCrawler",
    "CCSCrawler",
    "USENIXSecurityCrawler",
    "DefconTalkCrawler",
    "PortSwiggerResearchCrawler",
    "ProjectZeroCrawler",
    "CloudflareSecurityCrawler",
    "RSSFeedCrawler",
    "SitemapCrawler",
    "WebpageCrawler",
    "PAPER_CRAWLER_REGISTRY",
    "BLOG_CRAWLER_REGISTRY",
    "build_default_paper_crawlers",
    "build_default_blog_crawlers",
    "crawl_default_papers",
    "crawl_default_blogs",
]
