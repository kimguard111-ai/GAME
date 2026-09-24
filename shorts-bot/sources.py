"""이슈 후보 수집.

커뮤니티 사이트를 통째로 크롤링하지 않습니다(약관·차단 리스크).
- 키워드 기반 구글 뉴스 RSS로 '지금 뜨는 이슈' 후보를 모으고
- 커뮤니티 글은 사용자가 URL 또는 본문을 직접 넣는 방식으로 받습니다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote

import feedparser
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (shorts-bot; personal use)"}


@dataclass
class Candidate:
    title: str
    url: str
    source: str = ""
    published: str = ""
    summary: str = ""
    extra: dict = field(default_factory=dict)


def google_news(keyword: str, limit: int = 20) -> list[Candidate]:
    """키워드로 최근 한국어 뉴스 헤드라인을 가져옵니다."""
    url = f"https://news.google.com/rss/search?q={quote(keyword)}+when:7d&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    out = []
    for e in feed.entries[:limit]:
        src = e.get("source", {}).get("title", "") if isinstance(e.get("source"), dict) else ""
        summary = BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" ", strip=True)
        out.append(Candidate(title=e.title, url=e.link, source=src,
                             published=e.get("published", ""), summary=summary))
    return out


def fetch_article_text(url: str, max_chars: int = 8000) -> str:
    """URL 본문을 대충 추출합니다. 막히는 사이트는 본문을 직접 붙여넣으세요."""
    r = requests.get(url, headers=UA, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe"]):
        tag.decompose()
    node = soup.find("article") or soup.find("main") or soup.body or soup
    text = node.get_text("\n", strip=True)
    text = re.sub(r"\n{2,}", "\n", text)
    title = soup.title.get_text(strip=True) if soup.title else ""
    return f"[제목] {title}\n[URL] {url}\n\n{text[:max_chars]}"
